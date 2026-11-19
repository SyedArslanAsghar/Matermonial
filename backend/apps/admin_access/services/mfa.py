"""Admin MFA with django-otp TOTP (TR-07; doc 06 §15, §22.2; doc 03 §22.15).

Design (documented in docs/decisions/ADR-033-admin-mfa.md):
- **Mandatory.** The admin site accepts only sessions verified by a confirmed TOTP device
  (``OTPMiddleware`` + ``is_verified()``), for superusers too. There is no "skip".
- **Seed at rest:** AES-256-GCM with the ADMIN_MFA key ring; the associated data binds the
  ciphertext to the account, so a seed copied to another row doesn't decrypt.
- **Enrollment** needs the password and a single-use enrollment code (24 h by default) issued out
  of band by an administrator holding ``admin_access.reset_admin_mfa`` or by the CLI operator.
  The code is stored only as an HMAC. The seed is shown once, to the enrolling account only, and
  the device is confirmed by a valid TOTP code.
- **Verification:** the device row is locked, the token must be exactly ``digits`` digits, a
  time step is accepted at most once (replay), django-otp's exponential throttling applies, and
  failures are security events.
- **Recovery** is administrator-assisted: ``reset_mfa`` removes the device, revokes open codes and
  every admin session, and issues a new enrollment code. No backup codes exist: the approved
  documents don't specify them and django-otp's static tokens are stored in plaintext.
"""

import base64
import re
import secrets
import time
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import quote, urlencode

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django_otp.oath import TOTP

from apps.accounts.models import User
from apps.accounts.services.security_events import record_security_event
from common.crypto.aead import keyed_hash, open_sealed, seal
from common.crypto.keys import ring
from common.db.locking import LockLevel, lock_plan, lock_rows_for_update

from ..catalogue import RESET_ADMIN_MFA
from ..models import AdminMfaEnrollment, AdminTotpDevice
from ..selectors import has_admin_access
from .roles import (
    Actor,
    AdminAccessError,
    InvalidTarget,
    NotAuthorized,
    _lock_target,
    audit,
    require_permission,
    revoke_admin_sessions,
)

SEED_BYTES = 20  # RFC 4226 recommends 160 bits for HMAC-SHA1
ENROLLMENT_CODE_BYTES = 15  # 120 bits, shown as 24 base32 characters
RESOURCE = "admin_access.admin_totp_device"


class EnrollmentInvalid(AdminAccessError):
    code = "enrollment_invalid"


class AlreadyEnrolled(AdminAccessError):
    code = "already_enrolled"


@dataclass(frozen=True)
class PendingEnrollment:
    device: AdminTotpDevice
    enrollment_id: object
    secret_base32: str
    otpauth_uri: str


# --- Seeds ---------------------------------------------------------------------------------


def _aad(user_id, version: int) -> bytes:
    return f"admin-totp:{user_id}:v{version}".encode()


def _seal_seed(user_id, seed: bytes) -> dict:
    keys = ring("ADMIN_MFA")
    nonce, ciphertext = seal(keys.active_key, seed, _aad(user_id, keys.active_version))
    return {"key_version": keys.active_version, "key_nonce": nonce, "key_ciphertext": ciphertext}


def _seed(device: AdminTotpDevice) -> bytes:
    keys = ring("ADMIN_MFA")
    return open_sealed(
        keys.key(device.key_version),
        bytes(device.key_nonce),
        bytes(device.key_ciphertext),
        _aad(device.user_id, device.key_version),
    )


def _otpauth_uri(user: User, seed: bytes, device: AdminTotpDevice) -> str:
    issuer = settings.OTP_TOTP_ISSUER.replace(":", "")
    # The label shows the issuer and a short account hint, not the full phone number.
    label = f"{issuer}:{user.phone_number[:4]}…{user.phone_number[-2:]}"
    params = {
        "secret": base64.b32encode(seed).decode().rstrip("="),
        "issuer": issuer,
        "algorithm": "SHA1",
        "digits": device.digits,
        "period": device.step,
    }
    return f"otpauth://totp/{quote(label)}?{urlencode(params, quote_via=quote)}"


def verify_device_token(device: AdminTotpDevice, token) -> bool:
    """django-otp ``verify_token`` contract. The caller must hold the device row lock."""
    allowed, _ = device.verify_is_allowed()
    if not allowed:
        return False
    text = str(token or "").strip()
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


# --- Login verification --------------------------------------------------------------------


def confirmed_device(user: User) -> AdminTotpDevice | None:
    return AdminTotpDevice.objects.filter(user=user, confirmed=True).first()


def verify_login_token(user: User, token: str, request_id=None) -> AdminTotpDevice | None:
    """Check a login TOTP code. Returns the device, or None (failure recorded and committed)."""
    with transaction.atomic(), lock_plan("admin_access.mfa.verify", [LockLevel.DOMAIN]):
        devices = lock_rows_for_update(
            AdminTotpDevice.objects.filter(user=user, confirmed=True), LockLevel.DOMAIN
        )
        device = devices[0] if devices else None
        ok = device is not None and device.verify_token(token)
    if not ok:
        record_security_event(
            "LOGIN_FAILED",
            "FAILURE",
            actor_type="SELF",
            subject_user_id=user.pk,
            reason_code="ADMIN_MFA_NOT_ENROLLED" if device is None else "ADMIN_MFA_INVALID",
            request_id=request_id,
        )
        return None
    return device


# --- Enrollment ----------------------------------------------------------------------------


def _code_hash(code: str) -> str:
    normalised = re.sub(r"[\s-]", "", code or "").upper()
    return keyed_hash(ring("ADMIN_MFA").active_key, f"enroll:{normalised}")


def issue_enrollment(actor: Actor, target: User) -> str:
    """Issue a single-use enrollment code for ``target`` (returned once, never stored)."""
    try:
        require_permission(actor, RESET_ADMIN_MFA)
        if actor.user is not None and actor.user.pk == target.pk:
            raise NotAuthorized("You can't issue an enrollment code for yourself.")
    except NotAuthorized as exc:
        audit(
            actor,
            "admin.mfa_enrollment_issue",
            "DENIED",
            target_id=target.pk,
            resource=RESOURCE,
            reason=exc.code,
        )
        raise
    now = timezone.now()
    raw = base64.b32encode(secrets.token_bytes(ENROLLMENT_CODE_BYTES)).decode()
    code = "-".join(raw[i : i + 4] for i in range(0, len(raw), 4))
    with (
        transaction.atomic(),
        lock_plan(
            "admin_access.mfa.issue", [LockLevel.ACCOUNT, LockLevel.DOMAIN, LockLevel.INSERT]
        ),
    ):
        user = _lock_target(target.pk)
        if not has_admin_access(user):
            raise InvalidTarget("Only accounts with administrative access can enroll MFA.")
        if AdminTotpDevice.objects.filter(user=user, confirmed=True).exists():
            raise AlreadyEnrolled("Reset the existing device first.")
        open_codes = lock_rows_for_update(
            AdminMfaEnrollment.objects.filter(
                user=user, used_at__isnull=True, revoked_at__isnull=True
            ),
            LockLevel.DOMAIN,
        )
        for row in open_codes:
            row.revoked_at = now
            row.save(update_fields=["revoked_at"])
        AdminMfaEnrollment.objects.create(
            user=user,
            issued_by=actor.user,
            code_hash=_code_hash(code),
            created_at=now,
            expires_at=now + timedelta(seconds=settings.ADMIN_MFA_ENROLLMENT_TTL_SECONDS),
        )
        audit(actor, "admin.mfa_enrollment_issue", "SUCCESS", target_id=user.pk, resource=RESOURCE)
    return code


def _open_enrollment(user: User, code: str) -> AdminMfaEnrollment | None:
    return AdminMfaEnrollment.objects.filter(
        user=user,
        code_hash=_code_hash(code),
        used_at__isnull=True,
        revoked_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).first()


def begin_enrollment(user: User, code: str, request_id=None) -> PendingEnrollment:
    """Password already verified by the caller. Creates an unconfirmed device and returns the
    seed for display; the enrollment code is consumed only by ``confirm_enrollment``."""
    enrollment = _open_enrollment(user, code) if has_admin_access(user) else None
    if enrollment is None:
        record_security_event(
            "LOGIN_FAILED",
            "FAILURE",
            actor_type="SELF",
            subject_user_id=user.pk,
            reason_code="ADMIN_ENROLLMENT_INVALID",
            request_id=request_id,
        )
        raise EnrollmentInvalid()
    seed = secrets.token_bytes(SEED_BYTES)
    with (
        transaction.atomic(),
        lock_plan(
            "admin_access.mfa.begin", [LockLevel.ACCOUNT, LockLevel.DOMAIN, LockLevel.INSERT]
        ),
    ):
        locked = _lock_target(user.pk)
        existing = lock_rows_for_update(
            AdminTotpDevice.objects.filter(user=locked), LockLevel.DOMAIN
        )
        if existing and existing[0].confirmed:
            raise AlreadyEnrolled()
        if existing:
            existing[0].delete()  # an abandoned, never-confirmed enrollment
        device = AdminTotpDevice.objects.create(
            user=locked, name="Authenticator app", confirmed=False, **_seal_seed(locked.pk, seed)
        )
    return PendingEnrollment(
        device=device,
        enrollment_id=enrollment.pk,
        secret_base32=base64.b32encode(seed).decode().rstrip("="),
        otpauth_uri=_otpauth_uri(user, seed, device),
    )


def pending_secret(user: User, device_id: int) -> tuple[str, str] | None:
    """Re-display the seed of the caller's own unconfirmed device (after a mistyped code)."""
    device = AdminTotpDevice.objects.filter(pk=device_id, user=user, confirmed=False).first()
    if device is None:
        return None
    seed = _seed(device)
    return base64.b32encode(seed).decode().rstrip("="), _otpauth_uri(user, seed, device)


def confirm_enrollment(
    user: User, device_id: int, enrollment_id, token: str, request_id=None
) -> bool:
    """Confirm the pending device with a TOTP code and consume the enrollment code."""
    with (
        transaction.atomic(),
        lock_plan("admin_access.mfa.confirm", [LockLevel.ACCOUNT, LockLevel.DOMAIN]),
    ):
        locked = _lock_target(user.pk)
        enrollment = AdminMfaEnrollment.objects.filter(
            pk=enrollment_id,
            user=locked,
            used_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).first()
        devices = lock_rows_for_update(
            AdminTotpDevice.objects.filter(pk=device_id, user=locked, confirmed=False),
            LockLevel.DOMAIN,
        )
        ok = bool(enrollment and devices and has_admin_access(locked)) and devices[0].verify_token(
            token
        )
        if ok:
            device = devices[0]
            device.confirmed = True
            device.save(update_fields=["confirmed"])
            enrollment.used_at = timezone.now()
            enrollment.save(update_fields=["used_at"])
            record_security_event(
                "ADMIN_MFA_ENROLLED",
                "SUCCESS",
                actor_type="SELF",
                subject_user_id=locked.pk,
                reason_code="TOTP",
                request_id=request_id,
            )
    if not ok:
        record_security_event(
            "LOGIN_FAILED",
            "FAILURE",
            actor_type="SELF",
            subject_user_id=user.pk,
            reason_code="ADMIN_ENROLLMENT_CONFIRM_FAILED",
            request_id=request_id,
        )
    return ok


# --- Recovery ------------------------------------------------------------------------------


def reset_mfa(actor: Actor, target: User) -> str | None:
    """Administrator-assisted recovery. Removes the device, revokes open enrollment codes and
    every admin session of ``target``, then issues a new enrollment code (returned once; None
    when the account no longer has administrative access)."""
    try:
        require_permission(actor, RESET_ADMIN_MFA)
        if actor.user is not None and actor.user.pk == target.pk:
            raise NotAuthorized("You can't reset your own MFA.")
    except NotAuthorized as exc:
        audit(
            actor,
            "admin.mfa_reset",
            "DENIED",
            target_id=target.pk,
            resource=RESOURCE,
            reason=exc.code,
        )
        raise
    now = timezone.now()
    with (
        transaction.atomic(),
        lock_plan("admin_access.mfa.reset", [LockLevel.ACCOUNT, LockLevel.DOMAIN]),
    ):
        user = _lock_target(target.pk)
        devices = lock_rows_for_update(AdminTotpDevice.objects.filter(user=user), LockLevel.DOMAIN)
        had_device = any(d.confirmed for d in devices)
        for device in devices:
            device.delete()
        AdminMfaEnrollment.objects.filter(
            user=user, used_at__isnull=True, revoked_at__isnull=True
        ).update(revoked_at=now)
        revoked = revoke_admin_sessions(user, actor)
        if had_device:
            record_security_event(
                "ADMIN_MFA_REMOVED",
                "SUCCESS",
                actor_type="ADMIN" if actor.user else "SYSTEM",
                subject_user_id=user.pk,
                actor_user_id=actor.user_id,
                reason_code="RESET",
                request_id=actor.request_id,
            )
        audit(
            actor,
            "admin.mfa_reset",
            "SUCCESS",
            target_id=user.pk,
            resource=RESOURCE,
            had_device=had_device,
            sessions_revoked=revoked,
        )
        access = has_admin_access(user)
    return issue_enrollment(actor, target) if access else None
