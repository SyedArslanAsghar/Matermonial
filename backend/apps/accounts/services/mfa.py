"""Account authenticator (TOTP) enrollment and verification (TR-16; DR-2026-11-20-O-3).

- Enrolling or removing needs a recent password step-up of the current session (TR-01), so a
  stolen session alone can't attach or remove an authenticator.
- The seed is generated server-side, sealed under the ``ACCOUNT_MFA`` key ring (associated data
  binds it to the account) and shown **once**, to the account holder, while the device is
  unconfirmed. A valid code confirms the device.
- ``verify_code`` locks the device row, accepts each time step once (replay protection), applies
  django-otp's exponential throttling, and records failures as security events. Codes and seeds
  are never logged.
- Lock order: account (2) FOR SHARE, then the device row (domain).
"""

import base64
import re
import secrets
import time
from dataclasses import dataclass
from urllib.parse import quote, urlencode

from django.conf import settings
from django.db import transaction
from django_otp.oath import TOTP
from rest_framework import status
from rest_framework.exceptions import APIException

from common.api.throttles import allow
from common.crypto.aead import open_sealed, seal
from common.crypto.keys import ring
from common.db.locking import LockLevel, lock_plan, lock_rows_for_share, lock_rows_for_update

from ..models import AccountTotpDevice, User
from .security_events import record_security_event

SEED_BYTES = 20


class MfaAlreadyEnrolled(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "mfa_already_enrolled"
    default_detail = "An authenticator is already set up for this account."


class MfaNotPending(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "mfa_enrollment_not_started"
    default_detail = "Start the authenticator setup first."


class MfaNotEnrolled(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "mfa_not_enrolled"
    default_detail = "No authenticator is set up for this account."


class MfaCodeInvalid(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "mfa_code_invalid"
    default_detail = "That code didn't match. Check the time on your device and try again."


class MfaRateLimited(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = "throttled"
    default_detail = "Too many attempts. Try again later."


@dataclass(frozen=True)
class Enrollment:
    secret_base32: str
    otpauth_uri: str


def _aad(user_id, version: int) -> bytes:
    return f"account-totp:{user_id}:v{version}".encode()


def _seal(user_id, seed: bytes) -> dict:
    keys = ring("ACCOUNT_MFA")
    nonce, ciphertext = seal(keys.active_key, seed, _aad(user_id, keys.active_version))
    return {"key_version": keys.active_version, "key_nonce": nonce, "key_ciphertext": ciphertext}


def _seed(device: AccountTotpDevice) -> bytes:
    keys = ring("ACCOUNT_MFA")
    return open_sealed(
        keys.key(device.key_version),
        bytes(device.key_nonce),
        bytes(device.key_ciphertext),
        _aad(device.user_id, device.key_version),
    )


def _uri(user: User, seed: bytes, device: AccountTotpDevice) -> str:
    issuer = settings.OTP_TOTP_ISSUER.replace(":", "")
    label = f"{issuer}:{user.phone_number[:4]}…{user.phone_number[-2:]}"
    params = {
        "secret": base64.b32encode(seed).decode().rstrip("="),
        "issuer": issuer,
        "algorithm": "SHA1",
        "digits": device.digits,
        "period": device.step,
    }
    return f"otpauth://totp/{quote(label)}?{urlencode(params, quote_via=quote)}"


def _require_step_up(auth_session) -> None:
    from common.api.auth_errors import StepUpRequired

    from .auth import require_recent_step_up

    if auth_session is None:
        raise StepUpRequired()
    require_recent_step_up(auth_session)


def is_enrolled(user: User) -> bool:
    return AccountTotpDevice.objects.filter(user=user, confirmed=True).exists()


def _check(device: AccountTotpDevice, code) -> bool:
    """django-otp verification contract. The caller holds the device row lock."""
    allowed, _ = device.verify_is_allowed()
    if not allowed:
        return False
    text = str(code or "").strip()
    if not re.fullmatch(rf"\d{{{device.digits}}}", text):
        device.throttle_increment(commit=True)
        return False
    totp = TOTP(_seed(device), device.step, 0, device.digits, device.drift)
    totp.time = time.time()
    if totp.verify(int(text), device.tolerance, device.last_t + 1):
        device.last_t = totp.t()
        device.drift = totp.drift
        device.throttle_reset(commit=False)
        device.set_last_used_timestamp(commit=False)
        device.save()
        return True
    device.throttle_increment(commit=True)
    return False


def _locked_device(user: User, *, confirmed: bool | None, account_locked: bool = False):
    if not account_locked:
        lock_rows_for_share(User.objects.filter(pk=user.pk), LockLevel.ACCOUNT)
    query = AccountTotpDevice.objects.filter(user=user)
    if confirmed is not None:
        query = query.filter(confirmed=confirmed)
    rows = lock_rows_for_update(query, LockLevel.DOMAIN)
    return rows[0] if rows else None


def begin_enrollment(user: User, auth_session) -> Enrollment:
    _require_step_up(auth_session)
    with (
        transaction.atomic(),
        lock_plan("accounts.mfa.begin", [LockLevel.ACCOUNT, LockLevel.DOMAIN, LockLevel.INSERT]),
    ):
        existing = _locked_device(user, confirmed=None)
        if existing is not None and existing.confirmed:
            raise MfaAlreadyEnrolled()
        if existing is not None:
            existing.delete()  # an abandoned, never-confirmed setup
        seed = secrets.token_bytes(SEED_BYTES)
        device = AccountTotpDevice.objects.create(
            user=user, name="authenticator", confirmed=False, **_seal(user.pk, seed)
        )
        return Enrollment(base64.b32encode(seed).decode().rstrip("="), _uri(user, seed, device))


def confirm_enrollment(user: User, code: str, request_id=None) -> None:
    if not allow("account_mfa_account", str(user.pk)):
        raise MfaRateLimited()
    with (
        transaction.atomic(),
        lock_plan("accounts.mfa.confirm", [LockLevel.ACCOUNT, LockLevel.DOMAIN]),
    ):
        device = _locked_device(user, confirmed=False)
        if device is None:
            raise MfaNotPending()
        ok = _check(device, code)
        if ok:
            device.confirmed = True
            device.save(update_fields=["confirmed"])
    record_security_event(
        "ACCOUNT_MFA_ENROLLED" if ok else "ACCOUNT_MFA_FAILED",
        "SUCCESS" if ok else "FAILURE",
        actor_type="SELF",
        subject_user_id=user.pk,
        reason_code=None if ok else "ENROLLMENT_CONFIRM_FAILED",
        request_id=request_id,
    )
    if not ok:
        raise MfaCodeInvalid()


def remove(user: User, code: str, auth_session, request_id=None) -> None:
    _require_step_up(auth_session)
    if not allow("account_mfa_account", str(user.pk)):
        raise MfaRateLimited()
    with (
        transaction.atomic(),
        lock_plan("accounts.mfa.remove", [LockLevel.ACCOUNT, LockLevel.DOMAIN]),
    ):
        device = _locked_device(user, confirmed=True)
        if device is None:
            raise MfaNotEnrolled()
        ok = _check(device, code)
        if ok:
            device.delete()
    record_security_event(
        "ACCOUNT_MFA_REMOVED" if ok else "ACCOUNT_MFA_FAILED",
        "SUCCESS" if ok else "FAILURE",
        actor_type="SELF",
        subject_user_id=user.pk,
        reason_code=None if ok else "REMOVE_CONFIRM_FAILED",
        request_id=request_id,
    )
    if not ok:
        raise MfaCodeInvalid()


def verify_code(user: User, code: str, *, account_locked: bool = False) -> bool:
    """Check a code against the account's confirmed authenticator (inside the caller's
    transaction and lock plan: account level, then domain). False when none is enrolled."""
    device = _locked_device(user, confirmed=True, account_locked=account_locked)
    if device is None:
        return False
    return _check(device, code)
