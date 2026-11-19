"""Two-person admin MFA recovery and emergency recovery (ADR-033 Amendment 1, approved by
DR-2026-11-19-O-8).

Normal recovery (A1-1, A1-2):
1. An administrator holding ``admin_access.reset_admin_mfa`` *requests* recovery for another
   administrator, with a reason code. The request is an ``AdminActionApproval`` (doc 03 §16.7),
   PENDING for ``ADMIN_MFA_RECOVERY_TTL_SECONDS``.
2. A *different* administrator holding ``admin_access.approve_admin_mfa_recovery`` approves or
   rejects it. Neither may be the target, and the requester never decides (service check plus
   database CHECKs). Approval executes the recovery exactly once (the request row is locked).
3. The recovery removes the authenticator, revokes open enrollment codes and ends every admin
   session of the target. A replacement enrollment code is created (HMAC only) and **sent only by
   SMS to the target's verified phone**. No administrator ever sees it, and no response, audit
   row, event or log contains it.
4. If SMS delivery fails, recovery fails safe: the code is revoked, the outcome is recorded as
   DELIVERY_FAILED, and nothing is revealed. A new request or the emergency procedure follows.

Emergency recovery (A1-4): ``manage.py admin_access emergency-mfa-recovery --emergency
--reason CODE`` runs the same recovery and SMS delivery without a second administrator (for
example, when the only other administrator is unavailable). It is audited as
``admin.mfa_emergency_recovery`` with ``ADMIN_MFA_EMERGENCY_RECOVERY`` and never prints the code.

Every step is audited and writes a security event (A1-5). The target and every active superuser
are notified through the outbox (``security.admin_mfa_recovery``; delivery handlers arrive with
Phase 12). Hashed recovery codes are not implemented (A1-3, not approved).
"""

import re
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services.pseudonyms import pseudonym_for
from apps.accounts.services.security_events import record_security_event
from common.db.locking import LockLevel, lock_plan, lock_rows_for_update
from common.events.services import emit

from ..catalogue import APPROVE_ADMIN_MFA_RECOVERY, RESET_ADMIN_MFA
from ..models import AdminActionApproval, AdminMfaEnrollment, AdminTotpDevice
from ..selectors import has_admin_access
from .mfa import new_enrollment_code
from .roles import (
    CLI,
    Actor,
    AdminAccessError,
    InvalidTarget,
    NotAuthorized,
    _lock_target,
    audit,
    require_permission,
    revoke_admin_sessions,
)

ACTION = AdminActionApproval.ActionType.ADMIN_MFA_RECOVERY
RESOURCE = "admin_access.admin_mfa_recovery"
REASON = re.compile(r"^[A-Z0-9_]{3,40}$")


class RecoveryNotPending(AdminAccessError):
    code = "recovery_not_pending"


class RecoveryAlreadyPending(AdminAccessError):
    code = "recovery_already_pending"


def _check_reason(reason_code: str) -> None:
    if not REASON.fullmatch(reason_code or ""):
        raise InvalidTarget("The reason must be an upper-case code (A-Z, 0-9, _).")


def _notify(target: User, stage: str, request_id) -> None:
    """Security notice to the account holder and every active superuser (in the caller's
    transaction). The payload carries no secret."""
    recipients = {
        target.pk,
        *User.objects.filter(is_superuser=True, is_active=True).values_list("pk", flat=True),
    }
    for user_id in sorted(recipients, key=str):
        emit(
            "security.admin_mfa_recovery",
            event_class="NOTIFICATION",
            category="SECURITY",
            aggregate_type="AdminMfaRecovery",
            recipient_pseudonym=pseudonym_for("ACCOUNT", user_id),
            payload={
                "stage": stage,
                "is_account_holder": user_id == target.pk,
                "reference": str(request_id),
            },
            dedupe_identity=f"admin-mfa-recovery:{request_id}:{stage}:{user_id}",
        )


def _event(event_type: str, target: User, actor: Actor, reason_code: str) -> None:
    record_security_event(
        event_type,
        "INFO",
        actor_type="ADMIN" if actor.user else "SYSTEM",
        subject_user_id=target.pk,
        actor_user_id=actor.user_id,
        reason_code=reason_code,
        request_id=actor.request_id,
    )


def _deny(actor: Actor, action: str, target_id, exc: AdminAccessError):
    audit(actor, action, "DENIED", target_id=target_id, resource=RESOURCE, reason=exc.code)
    raise exc


# --- Request -------------------------------------------------------------------------------


def request_recovery(actor: Actor, target: User, reason_code: str) -> AdminActionApproval:
    try:
        _check_reason(reason_code)
        require_permission(actor, RESET_ADMIN_MFA)
        if actor.user is None:
            raise NotAuthorized("Use the emergency procedure from the command line.")
        if actor.user.pk == target.pk:
            raise NotAuthorized("You can't request recovery of your own MFA.")
    except AdminAccessError as exc:
        _deny(actor, "admin.mfa_recovery_request", target.pk, exc)
    now = timezone.now()
    try:
        with (
            transaction.atomic(),
            lock_plan("admin_access.recovery.request", [LockLevel.ACCOUNT, LockLevel.INSERT]),
        ):
            user = _lock_target(target.pk)
            if not has_admin_access(user) or not user.is_phone_verified:
                raise InvalidTarget(
                    "Recovery needs an administrator account with a verified phone number."
                )
            approval = AdminActionApproval.objects.create(
                requested_by=actor.user,
                action_type=ACTION,
                resource_type="accounts.user",
                resource_id=user.pk,
                reason=reason_code,
                requested_at=now,
                expires_at=now + timedelta(seconds=settings.ADMIN_MFA_RECOVERY_TTL_SECONDS),
            )
            _event("ADMIN_MFA_RECOVERY_REQUESTED", user, actor, reason_code)
            audit(
                actor,
                "admin.mfa_recovery_request",
                "SUCCESS",
                target_id=user.pk,
                resource=RESOURCE,
                reason_code=reason_code,
            )
            _notify(user, "REQUESTED", approval.pk)
            return approval
    except IntegrityError:
        raise RecoveryAlreadyPending(
            "A recovery request for this account is already pending."
        ) from None


# --- Decide --------------------------------------------------------------------------------


def _lock_pending(request_id) -> AdminActionApproval:
    rows = lock_rows_for_update(
        AdminActionApproval.objects.filter(pk=request_id, action_type=ACTION), LockLevel.DOMAIN
    )
    if not rows or rows[0].status != AdminActionApproval.Status.PENDING:
        raise RecoveryNotPending()
    return rows[0]


def _authorize_decision(approver: Actor, approval: AdminActionApproval) -> None:
    require_permission(approver, APPROVE_ADMIN_MFA_RECOVERY)
    if approver.user is None:
        raise NotAuthorized()
    if approver.user.pk in (approval.requested_by_id, approval.resource_id):
        raise NotAuthorized("The requester and the account holder can't decide this request.")


def _reset_and_send(target: User, actor: Actor, approval_id) -> None:
    """Remove the authenticator, end admin sessions, create the replacement code and send it by
    SMS after commit. Runs inside the caller's transaction, with the target locked."""
    now = timezone.now()
    for device in lock_rows_for_update(
        AdminTotpDevice.objects.filter(user=target), LockLevel.DOMAIN
    ):
        device.delete()
    AdminMfaEnrollment.objects.filter(
        user=target, used_at__isnull=True, revoked_at__isnull=True
    ).update(revoked_at=now)
    revoke_admin_sessions(target, actor)
    _event("ADMIN_MFA_REMOVED", target, actor, "RECOVERY")
    enrollment, code = new_enrollment_code(target, issued_by=actor.user, now=now)
    # Sent directly after commit, not through Celery, so the code never sits in the message
    # broker (A1-2: no persistence beyond what delivery strictly needs).
    transaction.on_commit(
        lambda: deliver_code(enrollment.pk, code, str(approval_id) if approval_id else None)
    )


def _peek(approver: Actor, request_id, action: str) -> AdminActionApproval:
    peek = AdminActionApproval.objects.filter(pk=request_id, action_type=ACTION).first()
    if peek is None:
        raise RecoveryNotPending()
    try:
        _authorize_decision(approver, peek)  # requester/target never decide (immutable fields)
    except AdminAccessError as exc:
        _deny(approver, action, peek.resource_id, exc)
    return peek


def approve_recovery(approver: Actor, request_id) -> AdminActionApproval:
    peek = _peek(approver, request_id, "admin.mfa_recovery_approve")
    with (
        transaction.atomic(),
        lock_plan(
            "admin_access.recovery.approve",
            [LockLevel.ACCOUNT, LockLevel.DOMAIN, LockLevel.INSERT],
        ),
    ):
        target = _lock_target(peek.resource_id)
        approval = _lock_pending(request_id)  # one execution per request, even under races
        now = timezone.now()
        expired = approval.expires_at <= now
        if expired:
            approval.status = AdminActionApproval.Status.EXPIRED
            approval.save(update_fields=["status"])
            _event("ADMIN_MFA_RECOVERY_DECIDED", target, CLI, "EXPIRED")
            _notify(target, "EXPIRED", approval.pk)
        else:
            approval.status = AdminActionApproval.Status.APPROVED
            approval.approved_by = approver.user
            approval.approved_at = now
            approval.outcome = "DELIVERY_PENDING"
            approval.save(update_fields=["status", "approved_by", "approved_at", "outcome"])
            _reset_and_send(target, approver, approval.pk)
            _event("ADMIN_MFA_RECOVERY_DECIDED", target, approver, "APPROVED")
            audit(
                approver,
                "admin.mfa_recovery_approve",
                "SUCCESS",
                target_id=target.pk,
                resource=RESOURCE,
            )
            _notify(target, "APPROVED", approval.pk)
    if expired:
        raise RecoveryNotPending("The request has expired.")
    approval.refresh_from_db()  # outcome: DELIVERED or DELIVERY_FAILED (after-commit SMS)
    return approval


def reject_recovery(approver: Actor, request_id) -> AdminActionApproval:
    peek = _peek(approver, request_id, "admin.mfa_recovery_reject")
    with (
        transaction.atomic(),
        lock_plan("admin_access.recovery.reject", [LockLevel.ACCOUNT, LockLevel.DOMAIN]),
    ):
        target = _lock_target(peek.resource_id)
        approval = _lock_pending(request_id)
        approval.status = AdminActionApproval.Status.REJECTED
        approval.rejected_by = approver.user
        approval.rejected_at = timezone.now()
        approval.save(update_fields=["status", "rejected_by", "rejected_at"])
        _event("ADMIN_MFA_RECOVERY_DECIDED", target, approver, "REJECTED")
        audit(
            approver, "admin.mfa_recovery_reject", "SUCCESS", target_id=target.pk, resource=RESOURCE
        )
        _notify(target, "REJECTED", approval.pk)
    return approval


def expire_recovery_requests() -> int:
    """Periodic job: PENDING requests past their expiry become EXPIRED. Idempotent."""
    due = list(
        AdminActionApproval.objects.filter(
            action_type=ACTION, status="PENDING", expires_at__lte=timezone.now()
        ).values_list("pk", "resource_id")
    )
    for request_id, target_id in due:
        with (
            transaction.atomic(),
            lock_plan("admin_access.recovery.expire", [LockLevel.ACCOUNT, LockLevel.DOMAIN]),
        ):
            target = _lock_target(target_id)
            rows = lock_rows_for_update(
                AdminActionApproval.objects.filter(pk=request_id, status="PENDING"),
                LockLevel.DOMAIN,
            )
            if not rows:
                continue
            rows[0].status = AdminActionApproval.Status.EXPIRED
            rows[0].save(update_fields=["status"])
            _event("ADMIN_MFA_RECOVERY_DECIDED", target, CLI, "EXPIRED")
            _notify(target, "EXPIRED", request_id)
    return len(due)


# --- Emergency (server access, A1-4) -------------------------------------------------------


def emergency_recovery(target: User, reason_code: str) -> bool:
    """CLI-only break-glass recovery. Returns whether the SMS was delivered; never returns or
    prints the code."""
    _check_reason(reason_code)
    with (
        transaction.atomic(),
        lock_plan(
            "admin_access.recovery.emergency",
            [LockLevel.ACCOUNT, LockLevel.DOMAIN, LockLevel.INSERT],
        ),
    ):
        user = _lock_target(target.pk)
        if not has_admin_access(user) or not user.is_phone_verified:
            raise InvalidTarget("Recovery needs an administrator account with a verified phone.")
        _reset_and_send(user, CLI, None)
        _event("ADMIN_MFA_EMERGENCY_RECOVERY", user, CLI, reason_code)
        audit(
            CLI,
            "admin.mfa_emergency_recovery",
            "SUCCESS",
            target_id=user.pk,
            resource=RESOURCE,
            reason_code=reason_code,
            emergency=True,
        )
        _notify(user, "EMERGENCY", f"emergency-{timezone.now().timestamp():.0f}")
    return AdminMfaEnrollment.objects.filter(
        user=target, used_at__isnull=True, revoked_at__isnull=True
    ).exists()


# --- Delivery (Celery task body) -----------------------------------------------------------


def deliver_code(enrollment_id, code: str, approval_id: str | None) -> str:
    """Send the replacement code by SMS. On any failure, revoke it and record the outcome; the
    code is never logged, stored in plaintext or shown to anyone else."""
    from common.providers import get_sms_provider

    enrollment = (
        AdminMfaEnrollment.objects.select_related("user")
        .filter(pk=enrollment_id, used_at__isnull=True, revoked_at__isnull=True)
        .first()
    )
    if enrollment is None:
        return "skipped"
    try:
        get_sms_provider().send_sms(
            to=enrollment.user.phone_number,
            message=f"Matermonial admin authenticator enrollment code: {code}. "
            "Never share it. If you didn't expect this, contact security.",
        )
        delivered = True
    except Exception:  # noqa: BLE001 - every failure must fail safe, never reveal the code
        delivered = False
    with transaction.atomic():
        if approval_id:
            AdminActionApproval.objects.filter(pk=approval_id).update(
                outcome="DELIVERED" if delivered else "DELIVERY_FAILED"
            )
        if not delivered:
            AdminMfaEnrollment.objects.filter(pk=enrollment.pk, used_at__isnull=True).update(
                revoked_at=timezone.now()
            )
            _event("ADMIN_MFA_RECOVERY_DECIDED", enrollment.user, CLI, "DELIVERY_FAILED")
            audit(
                CLI,
                "admin.mfa_recovery_delivery",
                "FAILURE",
                target_id=enrollment.user_id,
                resource=RESOURCE,
            )
            _notify(enrollment.user, "DELIVERY_FAILED", approval_id or enrollment.pk)
    return "delivered" if delivered else "failed"
