"""Role assignment, revocation and the ``is_staff`` projection (TR-07, ADR-027; doc 06 §15).

Rules:
- Only an eligible actor holding ``admin_access.manage_roles`` (or a break-glass superuser) may
  assign or revoke, never for their own account (also a database CHECK).
- Anti-escalation: a non-superuser may only grant or revoke a role whose every permission they
  hold themselves.
- The target must be an active, non-deactivated account. An end user or family manager gains
  administrative permissions only through such an assignment; nothing else confers them.
- Every change and every denied attempt is written to the audit log (ADMINISTRATIVE).
- Lock order (doc 12 §5): the target ``User`` FOR UPDATE (level 2, the state anchor), then the
  assignment rows (level 7), then inserts. Concurrent assignments of one role to one account
  therefore serialise; the partial unique index ``admin_user_role_one_live`` is the backstop.
- ``is_staff`` is recomputed in the same transaction. Losing all administrative access revokes
  every ADMIN session of the account at once.

``actor=None`` means an operator using the ``admin_access`` management command (shell access to
the server is itself privileged); the audit log records ``channel=cli``.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import AuthSession, User
from apps.accounts.services.auth import revoke_sessions
from apps.audit.services import record_audit
from common.db.locking import LockLevel, lock_plan, lock_rows_for_update

from ..catalogue import MANAGE_ROLES
from ..models import AdminRole, AdminUserRole
from ..selectors import account_eligible, has_admin_access, permission_codes


class AdminAccessError(Exception):
    code = "admin_access_error"


class NotAuthorized(AdminAccessError):
    code = "not_authorized"


class InvalidTarget(AdminAccessError):
    code = "invalid_target"


class AlreadyAssigned(AdminAccessError):
    code = "already_assigned"


class NotAssigned(AdminAccessError):
    code = "not_assigned"


@dataclass(frozen=True)
class Actor:
    """Who performs an administrative change. ``user`` is None for the CLI operator."""

    user: User | None = None
    request_id: str | None = None

    @property
    def channel(self) -> str:
        return "admin" if self.user is not None else "cli"

    @property
    def audit_actor_type(self) -> str:
        return "ADMIN" if self.user is not None else "SYSTEM"

    @property
    def user_id(self) -> uuid.UUID | None:
        return self.user.pk if self.user is not None else None


CLI = Actor()


def audit(actor: Actor, action: str, result: str, *, target_id, resource: str, **metadata):
    record_audit(
        action=action,
        resource_type=resource,
        actor_type=actor.audit_actor_type,
        result=result,
        category="ADMINISTRATIVE",
        actor_user_id=actor.user_id,
        subject_user_id=target_id,
        request_id=actor.request_id,
        metadata={"channel": actor.channel, **metadata},
    )


def require_permission(actor: Actor, permission: str) -> None:
    """The CLI operator passes; an admin needs the permission (superusers hold all)."""
    if actor.user is None:
        return
    user = User.objects.get(pk=actor.user.pk)  # fresh state, never a stale request copy
    if not account_eligible(user):
        raise NotAuthorized()
    if not user.is_superuser and permission not in permission_codes(user):
        raise NotAuthorized()


def _role_codes_held(actor: Actor) -> frozenset[str] | None:
    """None = unrestricted (CLI or superuser)."""
    if actor.user is None:
        return None
    user = User.objects.get(pk=actor.user.pk)
    return None if user.is_superuser else permission_codes(user)


def assignment_problem(actor: Actor, target: User, role: AdminRole) -> AdminAccessError | None:
    """Pre-checks shared by the service and the admin form (no locks, no writes)."""
    try:
        require_permission(actor, MANAGE_ROLES)
    except NotAuthorized as exc:
        return exc
    if actor.user is not None and actor.user.pk == target.pk:
        return NotAuthorized("You can't change your own administrative roles.")
    held = _role_codes_held(actor)
    if held is not None:
        needed = set(role.permissions.values_list("code", flat=True))
        if not needed <= held:
            return NotAuthorized("You can only grant roles whose permissions you hold.")
    if not role.is_active:
        return InvalidTarget("This role is retired.")
    return None


def refresh_staff_projection(user_id) -> bool:
    """Recompute ``is_staff`` for a locked account; must run inside the caller's transaction.

    Returns the new value. This is the only writer of ``User.is_staff`` (ADR-027).
    """
    user = User.objects.get(pk=user_id)
    value = has_admin_access(user)
    if user.is_staff != value:
        User.objects.filter(pk=user_id).update(is_staff=value, updated_at=timezone.now())
    return value


def revoke_admin_sessions(user: User, actor: Actor) -> int:
    sessions = list(AuthSession.objects.filter(user=user, client_type="ADMIN", status="ACTIVE"))
    if not sessions:
        return 0
    return revoke_sessions(
        user,
        sessions,
        AuthSession.RevokedReason.ADMIN,
        actor_type="ADMIN" if actor.user else "SYSTEM",
        actor_user_id=actor.user_id,
        request_id=actor.request_id,
    )


def _lock_target(target_id) -> User:
    locked = lock_rows_for_update(
        User.objects.filter(pk=target_id), LockLevel.ACCOUNT, label="accounts.User", anchor=True
    )
    if not locked:
        raise InvalidTarget()
    return locked[0]


def assign_role(
    actor: Actor, target: User, role_code: str, *, expires_at: datetime | None = None
) -> AdminUserRole:
    role = AdminRole.objects.filter(code=role_code).first()
    if role is None:
        raise InvalidTarget("Unknown role.")
    problem = assignment_problem(actor, target, role)
    now = timezone.now()
    if problem is None and expires_at is not None and expires_at <= now:
        problem = InvalidTarget("The expiry must be in the future.")
    if problem is not None:
        audit(
            actor,
            "admin.role_assign",
            "DENIED",
            target_id=target.pk,
            resource="admin_access.admin_user_role",
            role=role.code,
            reason=problem.code,
        )
        raise problem
    try:
        with (
            transaction.atomic(),
            lock_plan(
                "admin_access.assign_role", [LockLevel.ACCOUNT, LockLevel.DOMAIN, LockLevel.INSERT]
            ),
        ):
            user = _lock_target(target.pk)
            if not account_eligible(user):
                raise InvalidTarget("Only active accounts can hold administrative roles.")
            current = lock_rows_for_update(
                AdminUserRole.objects.filter(user=user, role=role, revoked_at__isnull=True),
                LockLevel.DOMAIN,
            )
            for row in current:
                if row.expires_at is None or row.expires_at > now:
                    raise AlreadyAssigned()
                # An expired assignment is closed so a new one can be opened (history kept).
                row.revoked_at = now
                row.save(update_fields=["revoked_at"])
            assignment = AdminUserRole.objects.create(
                user=user, role=role, assigned_by=actor.user, assigned_at=now, expires_at=expires_at
            )
            refresh_staff_projection(user.pk)
            audit(
                actor,
                "admin.role_assign",
                "SUCCESS",
                target_id=user.pk,
                resource="admin_access.admin_user_role",
                role=role.code,
                expires=expires_at is not None,
            )
            return assignment
    except IntegrityError:  # backstop: the partial unique index won a race
        raise AlreadyAssigned() from None


def revoke_role(actor: Actor, target: User, role_code: str) -> AdminUserRole:
    role = AdminRole.objects.filter(code=role_code).first()
    if role is None:
        raise InvalidTarget("Unknown role.")
    problem = assignment_problem(actor, target, role)
    if isinstance(problem, InvalidTarget):  # a retired role can still be revoked
        problem = None
    if problem is not None:
        audit(
            actor,
            "admin.role_revoke",
            "DENIED",
            target_id=target.pk,
            resource="admin_access.admin_user_role",
            role=role.code,
            reason=problem.code,
        )
        raise problem
    now = timezone.now()
    with (
        transaction.atomic(),
        lock_plan("admin_access.revoke_role", [LockLevel.ACCOUNT, LockLevel.DOMAIN]),
    ):
        user = _lock_target(target.pk)
        rows = lock_rows_for_update(
            AdminUserRole.objects.filter(user=user, role=role, revoked_at__isnull=True),
            LockLevel.DOMAIN,
        )
        if not rows:
            raise NotAssigned()
        row = rows[0]
        row.revoked_at = now
        row.save(update_fields=["revoked_at"])
        if not refresh_staff_projection(user.pk):
            revoke_admin_sessions(user, actor)
        audit(
            actor,
            "admin.role_revoke",
            "SUCCESS",
            target_id=user.pk,
            resource="admin_access.admin_user_role",
            role=role.code,
        )
        return row


def sync_expired_assignments() -> int:
    """Periodic job: recompute ``is_staff`` for accounts whose assignments have expired and
    end their admin sessions when no access remains. Permission checks never wait for this job
    (selectors ignore expired rows); it keeps the projection and sessions tidy. Idempotent."""
    now = timezone.now()
    candidates = (
        AdminUserRole.objects.filter(revoked_at__isnull=True, expires_at__lte=now)
        .values_list("user_id", flat=True)
        .distinct()
    )
    changed = 0
    for user_id in list(candidates):
        with transaction.atomic(), lock_plan("admin_access.expire", [LockLevel.ACCOUNT]):
            user = _lock_target(user_id)
            was_staff = user.is_staff
            if not refresh_staff_projection(user.pk):
                revoked = revoke_admin_sessions(user, CLI)
                if was_staff or revoked:
                    changed += 1
                    audit(
                        CLI,
                        "admin.role_expired",
                        "SUCCESS",
                        target_id=user.pk,
                        resource="admin_access.admin_user_role",
                        sessions_revoked=revoked,
                    )
    return changed
