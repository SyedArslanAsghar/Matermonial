"""Flow A: the profile owner invites a manager (FR-FAM-001/002; ADR-034; owner decisions
DR-2026-11-20-O-1, -2).

- The owner selects the permissions when inviting (template + individual codes; Sensitive ones
  with confirmation and an owner step-up). The invitee gets exactly those when accepting.
- Enumeration-safe (KI-34, ADR-034): every valid request records a ``ManagerInvitation`` and
  answers the same way; eligibility is decided by ``resolve_invitation`` in a background task.
  Refusals depend only on the owner's own data.
- A pending invitation expires 30 days after it was sent if it isn't accepted, the same way
  whether or not it was resolved to an account (``expire_invitations``). Expired invitations
  can't be accepted; a new invitation may be sent.
- History: INVITATION_CREATED, INVITATION_CANCELLED and INVITATION_EXPIRED are recorded on the
  invitation (owner-visible); the background resolution is recorded on the authorization only.
"""

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.models import User
from apps.accounts.services.pseudonyms import pseudonym_for
from apps.audit.services import record_audit
from common.api.throttles import allow
from common.db.locking import LockLevel, lock_plan, lock_rows_for_share, lock_rows_for_update

from ..models import ManagerInvitation, ProfileManagerAuthorization
from .base import (
    EXPIRY_REASON,
    AlreadyInvited,
    AlreadyManaging,
    InvalidAuthorizationState,
    InvitationRateLimited,
    _apply_grants,
    _audit,
    _history,
    _normal_codes,
    _notify,
    _snapshot,
    acceptance_deadline,
    audit_subject,
    grantable,
    normalize_or_400,
    notify_event,
    phone_digest,
    phone_hint,
    select_permissions,
)

Status = ProfileManagerAuthorization.Status
Inv = ManagerInvitation.Status


def invite(
    owner_context,
    *,
    phone_number: str,
    permission_group: str | None,
    permissions: list[str] | None,
    expires_at=None,
    confirm_sensitive: bool = False,
    auth_session=None,
) -> ManagerInvitation:
    """The owner invites another registered account with the permissions they selected.

    The request does the same work whether or not the number belongs to an account (one
    lookup, the same lock statement, one insert); nothing returned depends on the account."""
    if not owner_context.is_owner:
        from ..context import PermissionNotGranted

        raise PermissionNotGranted()
    owner = owner_context.actual_account
    if not allow("family_invite_account", str(owner.pk)):
        raise InvitationRateLimited()
    group, _codes, _sensitive = select_permissions(
        permission_group,
        permissions,
        confirm_sensitive=confirm_sensitive,
        auth_session=auth_session,
    )
    explicit = sorted(set(permissions or []))
    now = timezone.now()
    if expires_at is not None and expires_at <= now:
        raise ValidationError({"expires_at": ["The expiry must be in the future."]})
    phone = normalize_or_400(phone_number)
    if phone == owner.phone_number:
        raise ValidationError({"phone_number": ["You can't invite yourself."]})
    digest = phone_digest(phone)
    # The owner already knows their current managers' numbers (they invited them).
    if ProfileManagerAuthorization.objects.filter(
        profile_id=owner_context.profile_id,
        status__in=[Status.ACTIVE, Status.PAUSED],
        invitation__phone_digest=digest,
    ).exists():
        raise AlreadyManaging()
    # Looked up for every request (same query either way); stored internally only.
    invitee_id = (
        User.objects.filter(phone_number=phone).exclude(pk=owner.pk).values_list("pk", flat=True)
    ).first()
    try:
        with (
            transaction.atomic(),
            lock_plan("family.invite", [LockLevel.ACCOUNT, LockLevel.PROFILE, LockLevel.INSERT]),
        ):
            # One query either way (the invitee FK is then prior-locked, TR-22).
            lock_rows_for_share(
                User.objects.filter(pk__in=[pk for pk in (owner.pk, invitee_id) if pk]),
                LockLevel.ACCOUNT,
            )
            from apps.profiles.models import MatrimonialProfile

            lock_rows_for_update(
                MatrimonialProfile.objects.filter(pk=owner_context.profile_id), LockLevel.PROFILE
            )
            invitation = ManagerInvitation.objects.create(
                profile_id=owner_context.profile_id,
                invited_by=owner,
                phone_digest=digest,
                phone_hint=phone_hint(phone),
                invitee_id=invitee_id,
                permission_group=group,
                requested_permissions=explicit,
                requested_expires_at=expires_at,
                invited_at=now,
                expires_at=acceptance_deadline(now),
            )
            _history(
                None,
                "INVITATION_CREATED",
                owner,
                {},
                {
                    "permission_group": permission_group,
                    "permissions": explicit,
                    "expires_at": invitation.expires_at.isoformat(),
                },
                invitation=invitation,
            )
            record_audit(
                action="family.invitation_created",
                resource_type="family.invitation",
                actor_type="USER",
                result="SUCCESS",
                category="STATE_CHANGE",
                actor_user_id=owner.pk,
                subject_user_id=owner.pk,
                represented_profile_pseudonym=pseudonym_for("PROFILE", owner_context.profile_id),
                metadata={
                    "invitation_id": str(invitation.pk),
                    "permission_group": permission_group,
                },
            )
            invitation_id = str(invitation.pk)
            transaction.on_commit(lambda: _enqueue_resolution(invitation_id))
    except IntegrityError:
        raise AlreadyInvited() from None
    return invitation


def _enqueue_resolution(invitation_id: str) -> None:
    from ..tasks import resolve_manager_invitation

    resolve_manager_invitation.delay(invitation_id)


def _eligible(invitee: User | None, invitation: ManagerInvitation) -> bool:
    """FR-FAM-001: another registered, active, phone-verified account, still holding the
    invited number."""
    return (
        invitee is not None
        and invitee.pk != invitation.invited_by_id
        and invitee.is_active
        and not invitee.deactivated
        and invitee.is_phone_verified
        and phone_digest(invitee.phone_number) == invitation.phone_digest
    )


def resolve_invitation(invitation_id) -> ProfileManagerAuthorization | None:
    """Background step of ``invite``: when the invitation's number belongs to an eligible
    account, create the PENDING authorization with the selected permissions and notify the
    invitee. Otherwise nothing visible happens. Idempotent."""
    from apps.profiles.models import MatrimonialProfile

    invitation = ManagerInvitation.objects.filter(pk=invitation_id).first()
    if invitation is None or invitation.status != Inv.PENDING:
        return None
    if invitation.authorization_id is not None:
        return None
    accounts = [invitation.invited_by_id] + (
        [invitation.invitee_id] if invitation.invitee_id else []
    )
    try:
        with (
            transaction.atomic(),
            lock_plan(
                "family.resolve_invitation",
                [LockLevel.ACCOUNT, LockLevel.PROFILE, LockLevel.DOMAIN, LockLevel.INSERT],
            ),
        ):
            lock_rows_for_share(User.objects.filter(pk__in=accounts), LockLevel.ACCOUNT)
            profile = lock_rows_for_update(
                MatrimonialProfile.objects.filter(pk=invitation.profile_id), LockLevel.PROFILE
            )[0]
            invitation = lock_rows_for_update(
                ManagerInvitation.objects.filter(pk=invitation_id), LockLevel.DOMAIN
            )[0]
            now = timezone.now()
            if (
                invitation.status != Inv.PENDING
                or invitation.authorization_id is not None
                or invitation.expires_at <= now
            ):
                return None
            invitee = User.objects.filter(pk=invitation.invitee_id).first()
            if (
                not _eligible(invitee, invitation)
                or profile.profile_status == MatrimonialProfile.Status.CLOSED
            ):
                # Internal record only; the owner sees no difference.
                record_audit(
                    action="family.invitation_unresolved",
                    resource_type="family.invitation",
                    actor_type="SYSTEM",
                    result="FAILURE",
                    category="STATE_CHANGE",
                    subject_user_id=invitation.invited_by_id,
                    represented_profile_pseudonym=pseudonym_for("PROFILE", invitation.profile_id),
                    metadata={"invitation_id": str(invitation.pk)},
                )
                return None
            owner = invitation.invited_by
            group = invitation.permission_group
            a = ProfileManagerAuthorization.objects.create(
                profile_id=invitation.profile_id,
                manager=invitee,
                invited_by=owner,
                permission_group=group,
                invited_at=invitation.invited_at,
                invitation_expires_at=invitation.expires_at,
                expires_at=invitation.requested_expires_at,
            )
            a = ProfileManagerAuthorization.objects.select_related(
                "profile", "permission_group"
            ).get(pk=a.pk)
            # Re-validated: the catalogue may have changed since the request.
            codes = grantable(_normal_codes(group) | set(invitation.requested_permissions))
            change = _apply_grants(a, codes, owner, now)
            _history(a, "INVITED", owner, {}, {**_snapshot(a), **change})
            _audit(
                "invited",
                owner,
                a,
                permission_group=group.code if group else None,
                invitation_id=str(invitation.pk),
            )
            invitation.authorization = a
            invitation.save(update_fields=["authorization", "updated_at"])
            _notify(invitee.pk, "invitation_received", a)
            return a
    except IntegrityError:
        # Already linked to this profile through another live authorization: nothing to do.
        return None


class _Retry(Exception):
    """The resolution task linked an authorization meanwhile: lock again in global order."""


def _close_attempt(invitation_id, *, owner: User | None, now, expire: bool, reason=None):
    """Cancel (owner) or expire (job) one pending invitation. Lock order: authorization (1),
    accounts (2), invitation (domain). Returns the invitation, or None if not pending."""
    query = ManagerInvitation.objects.filter(pk=invitation_id)
    if owner is not None:
        query = query.filter(profile__owner_id=owner.pk)
    row = query.values("authorization_id", "invited_by_id").first()
    if row is None:
        raise NotFound()
    seen = row["authorization_id"]
    with (
        transaction.atomic(),
        lock_plan(
            "family.close_invitation",
            [LockLevel.AUTHORIZATION, LockLevel.ACCOUNT, LockLevel.DOMAIN],
        ),
    ):
        a = None
        if seen is not None:
            a = lock_rows_for_update(
                ProfileManagerAuthorization.objects.filter(pk=seen),
                LockLevel.AUTHORIZATION,
                anchor=True,
            )[0]
        lock_rows_for_share(User.objects.filter(pk=row["invited_by_id"]), LockLevel.ACCOUNT)
        invitation = lock_rows_for_update(
            ManagerInvitation.objects.filter(pk=invitation_id), LockLevel.DOMAIN
        )[0]
        if invitation.authorization_id != seen:
            raise _Retry()
        if invitation.status != Inv.PENDING:
            if expire:
                return None
            raise InvalidAuthorizationState("This invitation is no longer pending.")
        if expire and invitation.expires_at > now:
            return None
        if a is not None and a.status == Status.PENDING:
            a = ProfileManagerAuthorization.objects.select_related(
                "profile", "permission_group"
            ).get(pk=a.pk)
            previous = _snapshot(a)
            if expire:
                a.status, a.expired_at, a.reason = Status.EXPIRED, now, EXPIRY_REASON
                a.save()
                _history(a, "EXPIRED", None, previous, _snapshot(a), EXPIRY_REASON)
                _audit("expired", None, a, reason=EXPIRY_REASON)
                _notify(a.manager_id, "invitation_expired", a)
            else:
                a.status, a.revoked_at, a.reason = Status.REVOKED, now, reason
                a.save()
                _history(a, "REVOKED", owner, previous, _snapshot(a), reason)
                _audit("revoked", owner, a)
                _notify(a.manager_id, "authorization_revoked", a)
        if expire:
            invitation.status, invitation.expired_at, invitation.reason = (
                Inv.EXPIRED,
                now,
                EXPIRY_REASON,
            )
            invitation.save(update_fields=["status", "expired_at", "reason", "updated_at"])
            _history(
                None,
                "INVITATION_EXPIRED",
                None,
                {"status": "PENDING"},
                {"status": "EXPIRED"},
                EXPIRY_REASON,
                invitation=invitation,
            )
            audit_subject(
                "invitation_expired",
                None,
                invitation.invited_by_id,
                invitation.profile_id,
                "family.invitation",
                invitation_id=str(invitation.pk),
            )
            # The owner is told the same way whether or not the number had an account.
            notify_event(
                invitation.invited_by_id,
                "invitation_expired",
                "ManagerInvitation",
                invitation.pk,
                now,
            )
        else:
            invitation.status, invitation.cancelled_at, invitation.reason = (
                Inv.CANCELLED,
                now,
                reason,
            )
            invitation.save(update_fields=["status", "cancelled_at", "reason", "updated_at"])
            _history(
                None,
                "INVITATION_CANCELLED",
                owner,
                {"status": "PENDING"},
                {"status": "CANCELLED"},
                reason,
                invitation=invitation,
            )
            audit_subject(
                "invitation_cancelled",
                owner,
                owner.pk,
                invitation.profile_id,
                "family.invitation",
                invitation_id=str(invitation.pk),
            )
        return invitation


def cancel_invitation(owner: User, invitation_id, reason=None) -> ManagerInvitation:
    """The owner cancels a pending invitation (doc 15 §4 PENDING → REVOKED for a linked
    authorization)."""
    for _ in range(3):
        try:
            return _close_attempt(
                invitation_id, owner=owner, now=timezone.now(), expire=False, reason=reason
            )
        except _Retry:
            continue
    raise InvalidAuthorizationState("Try again.")


def expire_invitations(now=None) -> int:
    """Scheduled: pending invitations past their 30-day deadline become EXPIRED (with a linked
    pending authorization). Idempotent."""
    now = now or timezone.now()
    due = list(
        ManagerInvitation.objects.filter(status=Inv.PENDING, expires_at__lte=now).values_list(
            "pk", flat=True
        )
    )
    done = 0
    for pk in due:
        for _ in range(3):
            try:
                if _close_attempt(pk, owner=None, now=now, expire=True) is not None:
                    done += 1
                break
            except _Retry:
                continue
    return done
