"""Break-glass superusers (TR-07; doc 03 §22.15: "at most two accounts, audited, MFA").

- Granted or revoked only by the CLI operator or by an existing superuser, never for oneself.
- The limit of two is enforced by the database (trigger ``admin_superuser_limit``, migration
  admin_access.0001), which serialises concurrent grants with an advisory lock, so no race can
  produce a third superuser. This service maps the violation to ``SuperuserLimitReached``.
- A superuser still needs a confirmed MFA device and an ADMIN session to use the admin site.
- Every grant, revocation and refusal is audited. Revocation recomputes ``is_staff`` and, when no
  role remains, ends the account's admin sessions.
"""

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from common.db.locking import LockLevel, lock_plan

from .roles import (
    CLI,
    Actor,
    AdminAccessError,
    InvalidTarget,
    NotAuthorized,
    _lock_target,
    audit,
    refresh_staff_projection,
    revoke_admin_sessions,
)

SUPERUSER_LIMIT = 2
LIMIT_CONSTRAINT = "admin_superuser_limit"
RESOURCE = "accounts.user.superuser"


class SuperuserLimitReached(AdminAccessError):
    code = "superuser_limit"


def _authorize(actor: Actor, target: User) -> None:
    if actor.user is None:
        return
    current = User.objects.get(pk=actor.user.pk)
    if not (current.is_active and current.is_superuser):
        raise NotAuthorized()
    if current.pk == target.pk:
        raise NotAuthorized("You can't change your own superuser status.")


def _is_limit_violation(exc: IntegrityError) -> bool:
    diag = getattr(getattr(exc, "__cause__", None), "diag", None)
    return getattr(diag, "constraint_name", None) == LIMIT_CONSTRAINT


def grant_superuser(actor: Actor, target: User, *, reason_code: str) -> None:
    try:
        _authorize(actor, target)
    except NotAuthorized as exc:
        audit(
            actor,
            "admin.superuser_grant",
            "DENIED",
            target_id=target.pk,
            resource=RESOURCE,
            reason=exc.code,
            reason_code=reason_code,
        )
        raise
    try:
        with transaction.atomic(), lock_plan("admin_access.superuser", [LockLevel.ACCOUNT]):
            user = _lock_target(target.pk)
            if not user.is_active or user.deactivated:
                raise InvalidTarget("Only active accounts can be superusers.")
            if user.is_superuser:
                return  # idempotent
            User.objects.filter(pk=user.pk).update(is_superuser=True, updated_at=timezone.now())
            refresh_staff_projection(user.pk)
            audit(
                actor,
                "admin.superuser_grant",
                "SUCCESS",
                target_id=user.pk,
                resource=RESOURCE,
                reason_code=reason_code,
            )
    except IntegrityError as exc:
        if not _is_limit_violation(exc):
            raise
        audit(
            actor,
            "admin.superuser_grant",
            "DENIED",
            target_id=target.pk,
            resource=RESOURCE,
            reason=SuperuserLimitReached.code,
            reason_code=reason_code,
        )
        raise SuperuserLimitReached(
            f"At most {SUPERUSER_LIMIT} break-glass superusers may exist."
        ) from None


def revoke_superuser(actor: Actor, target: User, *, reason_code: str) -> None:
    try:
        _authorize(actor, target)
    except NotAuthorized as exc:
        audit(
            actor,
            "admin.superuser_revoke",
            "DENIED",
            target_id=target.pk,
            resource=RESOURCE,
            reason=exc.code,
            reason_code=reason_code,
        )
        raise
    with transaction.atomic(), lock_plan("admin_access.superuser", [LockLevel.ACCOUNT]):
        user = _lock_target(target.pk)
        if not user.is_superuser:
            return  # idempotent
        User.objects.filter(pk=user.pk).update(is_superuser=False, updated_at=timezone.now())
        if not refresh_staff_projection(user.pk):
            revoke_admin_sessions(user, actor)
        audit(
            actor,
            "admin.superuser_revoke",
            "SUCCESS",
            target_id=user.pk,
            resource=RESOURCE,
            reason_code=reason_code,
        )


def create_break_glass_superuser(manager, phone_number, password, **extra_fields) -> User:
    """``createsuperuser`` path: create a normal account, then grant through the service so the
    limit, the projection and the audit apply exactly as for any other grant."""
    for flag in ("is_staff", "is_superuser"):
        if extra_fields.pop(flag, True) is not True:
            raise ValueError(f"Superuser must have {flag}=True.")
    with transaction.atomic():
        user = manager.create_user(phone_number, password, **extra_fields)
        grant_superuser(CLI, user, reason_code="CREATESUPERUSER")
    user.refresh_from_db()
    return user
