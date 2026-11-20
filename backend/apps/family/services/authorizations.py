"""Manager authorization lifecycle and permissions (FR-FAM-001…009; doc 05 §2; doc 14 §1–§8;
doc 15 §4; owner decisions DR-2026-11-20-O-1, -2).

Rules implemented (all approved):
- Only the profile owner invites (invitations), answers requests (requests), pauses,
  resumes, renews, revokes and changes permissions. The invited account accepts or rejects an
  invitation [DECIDED]. Nobody manages their own profile, and a manager never manages another
  manager: every owner operation is filtered by the caller's own profile ownership, the
  endpoints are account-scoped (X-Acting-Profile refused), and
  manage_family_authorizations is Owner-only.
- At most one PENDING/ACTIVE/PAUSED authorization per (profile, manager).
- Transitions (doc 15 §4): PENDING→ACTIVE (accept), PENDING→REJECTED (reject), PENDING→REVOKED
  (owner cancels the invitation), PENDING→EXPIRED (not accepted within 30 days),
  ACTIVE↔PAUSED (owner), ACTIVE/PAUSED→REVOKED (owner, at any time), ACTIVE→EXPIRED (optional
  expiry; job and runtime). Revoked, expired and rejected authorizations are never reactivated.
- The authorization's own expiry is optional and absent by default; the owner may set, extend
  or clear it ("renew") on ACTIVE or PAUSED authorizations. It is separate from the 30-day
  acceptance deadline of invitations and requests.
- Permissions are per authorization and selected by the owner only (base.select_permissions);
  the owner can grant or revoke individual permissions later without a new authorization.
- Every change writes append-only history and an audit row; the counterpart is notified through
  the outbox, and the owner on sensitive permission changes (doc 14 §7).

Not implemented (OPEN decisions): manager resignation (OD-05f), template pre-selection semantics
and tiers (OD-05a, §9), per-share approval (OD-05d).
"""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from common.db.locking import LockLevel, lock_plan, lock_rows_for_update

from ..models import ManagerInvitation, ProfileManagerAuthorization
from .base import (  # noqa: F401 - re-exported for callers of this module
    AlreadyInvited,
    AlreadyManaging,
    AlreadyRequested,
    InvalidAuthorizationState,
    InvitationExpired,
    InvitationRateLimited,
    OwnerStepUpRequired,
    _apply_grants,
    _audit,
    _expire_if_due,
    _history,
    _lock,
    _notify,
    _snapshot,
    phone_digest,
    phone_hint,
    record_permission_change,
    select_permissions,
)
from .invitations import (  # noqa: F401 - re-exported
    cancel_invitation,
    expire_invitations,
    invite,
    resolve_invitation,
)
from .requests import expire_requests

Status = ProfileManagerAuthorization.Status


# --- Manager responses ---------------------------------------------------------------------


def _respond(manager: User, authorization_id, accept: bool) -> ProfileManagerAuthorization:
    with (
        transaction.atomic(),
        lock_plan("family.respond", [LockLevel.AUTHORIZATION, LockLevel.ACCOUNT, LockLevel.DOMAIN]),
    ):
        a = _lock(authorization_id, manager=manager)
        if a.status != Status.PENDING:
            raise InvalidAuthorizationState()
        previous, now = _snapshot(a), timezone.now()
        if a.invitation_expires_at is not None and a.invitation_expires_at <= now:
            raise InvitationExpired()  # the job records EXPIRED; it can never be accepted
        if accept:
            a.status, a.accepted_at, a.authorized_at = Status.ACTIVE, now, now
        else:
            a.status, a.rejected_at = Status.REJECTED, now
        a.save()
        action = "ACCEPTED" if accept else "REJECTED"
        _audit(action.lower(), manager, a)
        invitations = lock_rows_for_update(
            ManagerInvitation.objects.filter(authorization=a), LockLevel.DOMAIN
        )
        # One row on both the authorization and the invitation (visible to the owner now).
        _history(
            a,
            action,
            manager,
            previous,
            _snapshot(a),
            invitation=invitations[0] if invitations else None,
        )
        for invitation in invitations:
            invitation.status = (
                ManagerInvitation.Status.ACCEPTED if accept else ManagerInvitation.Status.DECLINED
            )
            invitation.responded_at = now
            invitation.save(update_fields=["status", "responded_at", "updated_at"])
        invitation_id = str(invitations[0].pk) if invitations else None
        _notify(a.profile.owner_id, "invitation_" + action.lower(), a, invitation_id=invitation_id)
        return a


def accept(manager: User, authorization_id) -> ProfileManagerAuthorization:
    return _respond(manager, authorization_id, True)


def reject(manager: User, authorization_id) -> ProfileManagerAuthorization:
    return _respond(manager, authorization_id, False)


# --- Owner controls ------------------------------------------------------------------------


def _owner_transition(owner, authorization_id, action, allowed, apply, reason=None):
    with (
        transaction.atomic(),
        lock_plan("family.owner_control", [LockLevel.AUTHORIZATION, LockLevel.ACCOUNT]),
    ):
        a = _lock(authorization_id, owner=owner)
        now = timezone.now()
        due = a.expires_at is not None and a.expires_at <= now
        if due and action != "REVOKED":
            # Effectively expired (the job records it): never paused, resumed or renewed.
            raise InvalidAuthorizationState("The authorization has expired.")
        if a.status not in allowed:
            raise InvalidAuthorizationState()
        previous = _snapshot(a)
        apply(a, now)
        a.reason = reason
        a.save()
        _history(a, action, owner, previous, _snapshot(a), reason)
        _audit(action.lower(), owner, a)
        _notify(a.manager_id, "authorization_" + action.lower(), a)
        return a


def pause(owner, authorization_id, reason=None):
    def apply(a, now):
        a.status, a.paused_at = Status.PAUSED, now

    return _owner_transition(owner, authorization_id, "PAUSED", {Status.ACTIVE}, apply, reason)


def resume(owner, authorization_id, reason=None):
    def apply(a, now):
        a.status, a.paused_at = Status.ACTIVE, None

    return _owner_transition(owner, authorization_id, "RESUMED", {Status.PAUSED}, apply, reason)


def revoke(owner, authorization_id, reason=None):
    def apply(a, now):
        a.status, a.revoked_at = Status.REVOKED, now

    allowed = {Status.PENDING, Status.ACTIVE, Status.PAUSED}
    return _owner_transition(owner, authorization_id, "REVOKED", allowed, apply, reason)


def renew(owner, authorization_id, expires_at):
    """Set, extend or clear (``None``) the optional expiry of an ACTIVE or PAUSED authorization."""
    if expires_at is not None and expires_at <= timezone.now():
        raise ValidationError({"expires_at": ["The expiry must be in the future."]})

    def apply(a, now):
        a.expires_at = expires_at

    allowed = {Status.ACTIVE, Status.PAUSED}
    return _owner_transition(owner, authorization_id, "RENEWED", allowed, apply)


def set_permissions(
    owner,
    authorization_id,
    *,
    permission_group: str | None,
    permissions: list[str],
    confirm_sensitive: bool,
    auth_session,
) -> dict:
    """Replace the granted set. Applying a template grants its Normal permissions; Sensitive
    permissions must be listed explicitly, confirmed, and preceded by an owner step-up."""
    with (
        transaction.atomic(),
        lock_plan(
            "family.permissions", [LockLevel.AUTHORIZATION, LockLevel.ACCOUNT, LockLevel.INSERT]
        ),
    ):
        a = _lock(authorization_id, owner=owner)
        if a.status not in (Status.PENDING, Status.ACTIVE, Status.PAUSED):
            raise InvalidAuthorizationState()
        currently = set(
            a.permission_grants.filter(
                is_granted=True, permission__sensitivity="SENSITIVE"
            ).values_list("permission__code", flat=True)
        )
        group, codes, sensitive = select_permissions(
            permission_group,
            permissions,
            confirm_sensitive=confirm_sensitive,
            auth_session=auth_session,
            already_sensitive=frozenset(currently),
        )
        previous = {
            **_snapshot(a),
            "granted": sorted(
                a.permission_grants.filter(is_granted=True).values_list(
                    "permission__code", flat=True
                )
            ),
        }
        now = timezone.now()
        a.permission_group = group
        a.save(update_fields=["permission_group", "updated_at"])
        change = _apply_grants(a, codes, owner, now)
        record_permission_change(a, owner, change, previous)
        sensitive_changed = bool(
            set(change["granted"]) & set(sensitive) or set(change["revoked"]) & currently
        )
        _audit(
            "permissions_changed",
            owner,
            a,
            sensitive_changed=sensitive_changed,
            granted_count=len(change["granted"]),
            revoked_count=len(change["revoked"]),
        )
        _notify(a.manager_id, "permissions_changed", a)
        if sensitive_changed:  # doc 14 §7: the owner is notified of sensitive changes
            _notify(a.profile.owner_id, "sensitive_permissions_changed", a)
        return change


# --- Expiry job ----------------------------------------------------------------------------


def expire_due() -> int:
    """Scheduled (doc 15 §4): ACTIVE/PAUSED authorizations past their optional expiry become
    EXPIRED (the runtime check already denies access), and pending invitations and requests
    not accepted within 30 days expire (DR-2026-11-20-O-2). Idempotent. Returns the number of
    rows expired."""
    now = timezone.now()
    expired_pending = expire_invitations(now) + expire_requests(now)
    due = list(
        ProfileManagerAuthorization.objects.filter(
            status__in=[Status.ACTIVE, Status.PAUSED], expires_at__lte=now
        ).values_list("pk", flat=True)
    )
    done = 0
    for pk in due:
        with transaction.atomic(), lock_plan("family.expire", [LockLevel.AUTHORIZATION]):
            a = _lock(pk)
            if _expire_if_due(a, now):
                _audit("expired", None, a)
                _notify(a.manager_id, "authorization_expired", a)
                _notify(a.profile.owner_id, "authorization_expired", a)
                done += 1
    return done + expired_pending
