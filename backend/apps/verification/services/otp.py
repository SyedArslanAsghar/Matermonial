"""One-time codes over SMS (FR-ACC-002; doc 03 §2.5, doc 06 §3, doc 06 §22.1).

Send (``send_code``):
- 6-digit code from ``secrets``; stored only as ``HMAC(OTP key, "<id>:<code>")``.
- Refused inside the resend cooldown (60 s per phone and purpose) and above the hourly send
  limit (5 per phone); a refusal returns ``retry_after`` and records OTP_RATE_LIMITED once per
  window. Callers that must not reveal whether an account exists (password reset) respond
  identically whatever the outcome.
- A new send supersedes the pending code for the same phone and purpose.
- The SMS is dispatched asynchronously after commit (CC-R53); the code travels only as the task
  argument to the provider and is never stored or logged.

Verify (``verify_code``):
- Lock order (doc 12 §5): the account row (level 2), then the verification row (level 7), so
  two concurrent attempts can't both consume one code.
- At most 5 attempts; then EXHAUSTED. Expired or unknown codes fail generically.
- VERIFY_PHONE success sets ``User.is_phone_verified`` (this service is its single writer,
  doc 03 §22.1 row 5). PASSWORD_RESET success is returned to the caller, which completes the
  reset in the same transaction.
"""

import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.managers import normalize_phone_number
from apps.accounts.models import User
from apps.accounts.services.security_events import record_rate_limit_once, record_security_event
from common.crypto.aead import keyed_hash
from common.crypto.keys import ring
from common.db.locking import LockLevel, lock_plan, lock_rows_for_update

from ..models import PhoneVerification

CODE_DIGITS = 6


@dataclass(frozen=True)
class SendOutcome:
    sent: bool
    retry_after: int | None = None
    verification_id: object = None


@dataclass(frozen=True)
class VerifyOutcome:
    ok: bool
    reason: str | None = None  # "invalid" | "exhausted"


def _hash(verification_id, code: str, key_version: int) -> str:
    return keyed_hash(ring("OTP").key(key_version), f"{verification_id}:{code}")


def _new_code() -> str:
    return f"{secrets.randbelow(10**CODE_DIGITS):0{CODE_DIGITS}d}"


def _retry_after(moment, now) -> int:
    return max(1, int((moment - now).total_seconds()) + 1)


def send_code(*, phone_number: str, purpose: str, user: User | None = None) -> SendOutcome:
    phone = normalize_phone_number(phone_number)
    now = timezone.now()
    with transaction.atomic():
        recent = PhoneVerification.objects.filter(phone_number=phone)
        latest = recent.filter(purpose=purpose).order_by("-created_at").first()
        cooldown = timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS)
        if latest and latest.created_at + cooldown > now:
            return SendOutcome(False, _retry_after(latest.created_at + cooldown, now))
        last_hour = recent.filter(created_at__gt=now - timedelta(hours=1)).order_by("created_at")
        if last_hour.count() >= settings.OTP_MAX_SENDS_PER_HOUR:
            record_rate_limit_once(
                f"otp-send:{phone}",
                actor_type="SELF" if user else "ANONYMOUS",
                subject_user_id=user.id if user else None,
                unknown_subject_phone=None if user else phone,
                reason_code="OTP_SEND_LIMIT",
            )
            oldest = last_hour.first().created_at
            return SendOutcome(False, _retry_after(oldest + timedelta(hours=1), now))

        previous = (
            PhoneVerification.objects.select_for_update()
            .filter(phone_number=phone, purpose=purpose, status="PENDING")
            .first()
        )
        resend_count = 0
        if previous is not None:
            previous.status = PhoneVerification.Status.SUPERSEDED
            previous.save(update_fields=["status"])
            resend_count = previous.resend_count + 1

        code = _new_code()
        otp_ring = ring("OTP")
        verification = PhoneVerification(
            user=user,
            phone_number=phone,
            purpose=purpose,
            key_version=otp_ring.active_version,
            expires_at=now + timedelta(seconds=settings.OTP_VALIDITY_SECONDS),
            resend_count=resend_count,
        )
        verification.code_hash = _hash(verification.id, code, otp_ring.active_version)
        verification.save()

        from ..tasks import send_otp_sms

        transaction.on_commit(lambda: send_otp_sms.delay(str(verification.id), code))
        return SendOutcome(True, verification_id=verification.id)


def verify_code(
    *, phone_number: str, purpose: str, code: str, user: User | None = None
) -> VerifyOutcome:
    phone = normalize_phone_number(phone_number)
    now = timezone.now()
    with transaction.atomic(), lock_plan("otp.verify", [LockLevel.ACCOUNT, LockLevel.DOMAIN]):
        if user is not None:
            [user] = lock_rows_for_update(User.objects.filter(pk=user.pk), LockLevel.ACCOUNT)
        rows = lock_rows_for_update(
            PhoneVerification.objects.filter(phone_number=phone, purpose=purpose, status="PENDING"),
            LockLevel.DOMAIN,
        )
        verification = rows[0] if rows else None
        if verification is None or verification.expires_at <= now:
            return VerifyOutcome(False, "invalid")
        if user is not None and verification.user_id not in (None, user.pk):
            return VerifyOutcome(False, "invalid")

        verification.attempt_count += 1
        expected = _hash(verification.id, str(code), verification.key_version)
        if hmac.compare_digest(expected, verification.code_hash):
            verification.status = PhoneVerification.Status.VERIFIED
            verification.verified_at = now
            verification.save(update_fields=["attempt_count", "status", "verified_at"])
            if purpose == PhoneVerification.Purpose.VERIFY_PHONE and user is not None:
                user.is_phone_verified = True
                user.save(update_fields=["is_phone_verified", "updated_at"])
            return VerifyOutcome(True)

        exhausted = verification.attempt_count >= settings.OTP_MAX_ATTEMPTS
        if exhausted:
            verification.status = PhoneVerification.Status.EXHAUSTED
        verification.save(update_fields=["attempt_count", "status"])
        record_security_event(
            "OTP_ATTEMPTS_EXHAUSTED" if exhausted else "OTP_VERIFICATION_FAILED",
            "FAILURE",
            actor_type="SELF" if user else "ANONYMOUS",
            subject_user_id=verification.user_id,
            unknown_subject_phone=None if verification.user_id else phone,
            reason_code=purpose,
        )
        return VerifyOutcome(False, "exhausted" if exhausted else "invalid")
