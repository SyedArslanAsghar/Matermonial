"""TR-16 step-up for a manager's Sensitive action (owner decision DR-2026-11-20-O-3).

Owner-granted permission, manager authentication and the owner's identity verification are
separate things. Holding a Sensitive permission is never enough: before each Sensitive action
the manager proves their **own** authenticator (account TOTP, ``apps.accounts.services.mfa``):

1. ``POST /api/v1/profiles/step-up/`` with ``X-Acting-Profile`` and ``{"action", "code"}``.
   The action must be a Sensitive permission currently granted on this authorization. On a
   valid code a ``SensitiveActionVerification`` is created, bound to the manager, the profile,
   the authorization and the action, valid for at most 5 minutes.
2. The Sensitive request sends ``X-Step-Up-Verification: <id>``. ``consume`` locks and marks
   it used inside the business transaction; it can't be reused or used for another action.
3. Failures (wrong code, no authenticator, throttled) are denied, audited and recorded as
   security events. After the action the owner is notified (``family.sensitive_action``).
The owner can revoke the permission at any time; the next request is denied.
"""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from apps.accounts.services.pseudonyms import pseudonym_for
from apps.accounts.services.security_events import record_security_event
from apps.audit.services import record_audit
from common.api.throttles import allow
from common.db.locking import LockLevel, lock_plan, lock_rows_for_update
from common.events.services import emit

from ..context import (
    ActorContext,
    PermissionNotGranted,
    StepUpVerificationRequired,
    granted_codes,
    lock_authorization_for_write,
    sensitive_codes,
)
from ..models import SensitiveActionVerification


class AuthenticatorRequired(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "authenticator_required"
    default_detail = "Set up an authenticator app on your account to perform sensitive actions."


class StepUpFailed(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "step_up_failed"
    default_detail = "That code didn't match. Check your authenticator app and try again."


class StepUpRateLimited(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = "throttled"
    default_detail = "Too many attempts. Try again later."


def _audit(ctx: ActorContext, action: str, result: str, **metadata) -> None:
    record_audit(
        action=f"family.step_up_{action}",
        resource_type="family.sensitive_action_verification",
        actor_type="MANAGER",
        result=result,
        category="SECURITY",
        actor_user_id=ctx.actual_account.pk,
        subject_user_id=ctx.represented_profile.owner_id,
        represented_profile_pseudonym=pseudonym_for("PROFILE", ctx.profile_id),
        request_id=ctx.request_id,
        metadata={"authorization_id": str(ctx.authorization_id), **metadata},
    )


def create_verification(ctx: ActorContext, action: str, code: str) -> SensitiveActionVerification:
    from apps.accounts.services.mfa import is_enrolled, verify_code

    if ctx.is_owner:
        raise ValidationError({"action": ["Profile owners don't need a manager step-up."]})
    if action not in ctx.sensitive:
        raise PermissionNotGranted()  # not granted, or not a Sensitive permission
    if not allow("step_up_account", str(ctx.actual_account.pk)):
        raise StepUpRateLimited()
    manager = ctx.actual_account
    if not is_enrolled(manager):
        _audit(ctx, "failed", "DENIED", step_up_action=action, reason="NO_AUTHENTICATOR")
        raise AuthenticatorRequired()
    with (
        transaction.atomic(),
        lock_plan(
            "family.step_up",
            [
                LockLevel.AUTHORIZATION,
                LockLevel.ACCOUNT,
                LockLevel.PROFILE,
                LockLevel.DOMAIN,
                LockLevel.INSERT,
            ],
        ),
    ):
        lock_authorization_for_write(ctx)  # still ACTIVE and not expired (level 1)
        if action not in granted_codes(ctx.authorization_id) or action not in sensitive_codes(
            ctx.authorization_id
        ):
            raise PermissionNotGranted()  # revoked meanwhile
        from apps.accounts.models import User
        from apps.profiles.models import MatrimonialProfile
        from common.db.locking import lock_rows_for_share

        lock_rows_for_share(User.objects.filter(pk=manager.pk), LockLevel.ACCOUNT)
        lock_rows_for_share(MatrimonialProfile.objects.filter(pk=ctx.profile_id), LockLevel.PROFILE)
        ok = verify_code(manager, code, account_locked=True)  # device (domain); throttled
        verification = None
        if ok:
            now = timezone.now()
            verification = SensitiveActionVerification.objects.create(
                manager=manager,
                profile_id=ctx.profile_id,
                authorization_id=ctx.authorization_id,
                action=action,
                verified_at=now,
                expires_at=now + timedelta(seconds=settings.FAMILY_STEP_UP_TTL_SECONDS),
            )
    # Outside the transaction so failures are recorded even though nothing else is written.
    record_security_event(
        "STEP_UP_SUCCEEDED" if ok else "STEP_UP_FAILED",
        "SUCCESS" if ok else "FAILURE",
        actor_type="SELF",
        subject_user_id=manager.pk,
        reason_code="MANAGER_SENSITIVE_ACTION",
        request_id=ctx.request_id,
    )
    if not ok:
        _audit(ctx, "failed", "FAILURE", step_up_action=action, reason="INVALID_CODE")
        raise StepUpFailed()
    _audit(ctx, "verified", "SUCCESS", step_up_action=action, verification_id=str(verification.pk))
    return verification


def consume(ctx: ActorContext, action: str) -> None:
    """Inside the business transaction, after the profile lock (domain level): use the
    request's verification for ``action`` exactly once, then tell the owner."""
    now = timezone.now()
    rows = lock_rows_for_update(
        SensitiveActionVerification.objects.filter(
            pk=ctx.step_up_id,
            manager_id=ctx.actual_account.pk,
            profile_id=ctx.profile_id,
            authorization_id=ctx.authorization_id,
            action=action,
            consumed_at__isnull=True,
            expires_at__gt=now,
        ),
        LockLevel.DOMAIN,
    )
    if ctx.step_up_id is None or not rows:
        _audit(ctx, "rejected", "DENIED", step_up_action=action)
        raise StepUpVerificationRequired()
    verification = rows[0]
    verification.consumed_at = now
    verification.save(update_fields=["consumed_at"])
    _audit(ctx, "consumed", "SUCCESS", step_up_action=action, verification_id=str(verification.pk))
    emit(
        "family.sensitive_action",
        event_class="NOTIFICATION",
        category="ACCOUNT",
        aggregate_type="MatrimonialProfile",
        recipient_pseudonym=pseudonym_for("ACCOUNT", ctx.represented_profile.owner_id),
        payload={"action": action, "authorization_id": str(ctx.authorization_id)},
        dedupe_identity=f"family:sensitive:{verification.pk}",
    )
