"""Manager authorization lifecycle and permissions (FR-FAM-001…009; doc 05 §2; doc 14 §1–§8;
doc 15 §4).

Rules implemented (all approved):
- Only the profile owner invites, pauses, resumes, renews, revokes and sets permissions; the
  invited account accepts or rejects [DECIDED]. Nobody manages their own profile.
- The invitee must be another registered, active, phone-verified account (FR-FAM-001).
  Invitations are enumeration-safe (KI-34): every invite request records a ``ManagerInvitation``
  and gets the same answer; eligibility is decided in a background task, and the owner sees an
  authorization only after the invitee accepts. Invitations are rate limited per owner.
- At most one PENDING/ACTIVE/PAUSED authorization per (profile, manager).
- Transitions (doc 15 §4): PENDING→ACTIVE (accept), PENDING→REJECTED (reject), PENDING→REVOKED
  (owner cancels the invitation), ACTIVE↔PAUSED (owner), ACTIVE/PAUSED→REVOKED (owner), ACTIVE→EXPIRED (job and
  runtime). Revoked, expired and rejected authorizations are never reactivated.
- Expiry is optional and absent by default; the owner may set, extend or clear it ("renew") on
  ACTIVE or PAUSED authorizations. A PAUSED authorization whose expiry has passed can't resume.
- Permissions are per authorization. Applying a template grants only its **Normal** permissions;
  **Sensitive** permissions are granted only individually with explicit owner confirmation and a
  recent owner step-up (doc 14 §4, FR-FAM-005); **Owner-only** permissions are never granted.
- Every change writes append-only history and an audit row; the counterpart is notified through
  the outbox, and the owner on sensitive permission changes (doc 14 §7).

Not implemented (OPEN decisions): invitation TTL (OD-05e), manager resignation (OD-05f), template
pre-selection semantics and tiers (OD-05a, §9), the H tier and per-share approval (OD-05d).
"""

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError

from apps.accounts.managers import normalize_phone_number
from apps.accounts.models import User
from apps.accounts.services.pseudonyms import pseudonym_for
from apps.audit.services import record_audit
from common.api.throttles import allow
from common.db.locking import LockLevel, lock_plan, lock_rows_for_share, lock_rows_for_update
from common.events.services import emit

from ..models import (
    AuthorizationPermission,
    ManagerAuthorizationHistory,
    ManagerInvitation,
    ManagerPermission,
    ManagerPermissionGroup,
    ProfileManagerAuthorization,
)

Status = ProfileManagerAuthorization.Status


class AlreadyInvited(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "already_invited"
    default_detail = "You already have a pending invitation for this number."


class AlreadyManaging(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "already_managing"
    default_detail = "This number already belongs to one of your managers."


class InvalidAuthorizationState(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "invalid_authorization_state"
    default_detail = "This action isn't possible in the authorization's current state."


class OwnerStepUpRequired(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "step_up_required"
    default_detail = "Confirm your password before granting sensitive permissions."


class InvitationRateLimited(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = "throttled"
    default_detail = "Too many invitations. Try again later."


# --- Helpers -------------------------------------------------------------------------------


def _snapshot(a: ProfileManagerAuthorization) -> dict:
    return {
        "status": a.status,
        "expires_at": a.expires_at.isoformat() if a.expires_at else None,
        "permission_group": a.permission_group.code if a.permission_group_id else None,
    }


def _history(a, action, by, previous, new, reason=None):
    ManagerAuthorizationHistory.objects.create(
        authorization=a,
        action=action,
        performed_by=by,
        previous_values=previous,
        new_values=new,
        reason=reason,
    )


def _audit(action, by, a, result="SUCCESS", **metadata):
    record_audit(
        action=f"family.{action}",
        resource_type="family.authorization",
        actor_type="USER" if by is not None else "SYSTEM",
        result=result,
        category="STATE_CHANGE",
        actor_user_id=by.pk if by is not None else None,
        subject_user_id=a.profile.owner_id,
        represented_profile_pseudonym=pseudonym_for("PROFILE", a.profile_id),
        metadata={"status": a.status, **metadata},
    )


def _notify(recipient_id, event: str, a: ProfileManagerAuthorization, **payload):
    emit(
        f"family.{event}",
        event_class="NOTIFICATION",
        category="ACCOUNT",
        aggregate_type="ProfileManagerAuthorization",
        recipient_pseudonym=pseudonym_for("ACCOUNT", recipient_id),
        payload={"authorization_id": str(a.pk), **payload},
        dedupe_identity=f"family:{event}:{a.pk}:{a.updated_at.isoformat()}:{recipient_id}",
    )


def _lock(authorization_id, *, owner=None, manager=None) -> ProfileManagerAuthorization:
    """Lock the authorization (level 1). Anything that isn't the caller's gets the same 404."""
    query = ProfileManagerAuthorization.objects.filter(pk=authorization_id)
    if owner is not None:
        # Owners act on invitations until the manager accepts (KI-34): a never-accepted
        # authorization is invisible to them, like a number without an account.
        query = query.filter(profile__owner_id=owner.pk, accepted_at__isnull=False)
    if manager is not None:
        query = query.filter(manager_id=manager.pk)
    rows = lock_rows_for_update(query, LockLevel.AUTHORIZATION, anchor=True)
    if not rows:
        raise NotFound()
    actor = owner or manager
    if actor is not None:  # the acting account (history/grant FKs are then prior-locked)
        lock_rows_for_share(User.objects.filter(pk=actor.pk), LockLevel.ACCOUNT)
    return ProfileManagerAuthorization.objects.select_related("profile", "permission_group").get(
        pk=rows[0].pk
    )


def _expire_if_due(a: ProfileManagerAuthorization, now) -> bool:
    if a.status in (Status.ACTIVE, Status.PAUSED) and a.expires_at and a.expires_at <= now:
        previous = _snapshot(a)
        a.status, a.expired_at = Status.EXPIRED, now
        a.save(update_fields=["status", "expired_at", "updated_at"])
        _history(a, "EXPIRED", None, previous, _snapshot(a))
        return True
    return False


def _apply_grants(a, codes: set[str], by, now) -> dict:
    """Set the granted set to exactly ``codes``; returns {"granted": [...], "revoked": [...]}."""
    permissions = {p.code: p for p in ManagerPermission.objects.filter(code__in=codes)}
    rows = {r.permission.code: r for r in a.permission_grants.select_related("permission")}
    granted, revoked = [], []
    for code, permission in permissions.items():
        row = rows.get(code)
        if row is None:
            AuthorizationPermission.objects.create(
                authorization=a,
                permission=permission,
                is_granted=True,
                granted_by=by,
                granted_at=now,
            )
            granted.append(code)
        elif not row.is_granted:
            row.is_granted, row.granted_by, row.granted_at = True, by, now
            row.save(update_fields=["is_granted", "granted_by", "granted_at", "updated_at"])
            granted.append(code)
    for code, row in rows.items():
        if row.is_granted and code not in codes:
            row.is_granted = False
            row.save(update_fields=["is_granted", "updated_at"])
            revoked.append(code)
    return {"granted": sorted(granted), "revoked": sorted(revoked)}


def _validate_codes(codes: set[str]) -> dict[str, ManagerPermission]:
    found = {p.code: p for p in ManagerPermission.objects.filter(code__in=codes)}
    errors = {}
    for code in sorted(codes):
        permission = found.get(code)
        if permission is None or not permission.is_active:
            errors[code] = ["Unknown or unavailable permission."]
        elif permission.sensitivity == ManagerPermission.Sensitivity.OWNER_ONLY:
            errors[code] = ["Owner-only permissions can't be delegated."]
    if errors:
        raise ValidationError({"permissions": errors})
    return found


def _group(code: str | None) -> ManagerPermissionGroup | None:
    if code is None:
        return None
    group = ManagerPermissionGroup.objects.filter(code=code, is_active=True).first()
    if group is None:
        raise ValidationError({"permission_group": ["Unknown or inactive template."]})
    return group


def _normal_codes(group: ManagerPermissionGroup | None) -> set[str]:
    if group is None:
        return set()
    return set(
        group.permissions.filter(is_active=True, sensitivity="NORMAL").values_list(
            "code", flat=True
        )
    )


# --- Invitation ----------------------------------------------------------------------------


def phone_digest(normalized_phone: str) -> str:
    """Keyed hash of a normalized phone number (the number itself is never stored)."""
    from common.crypto.aead import keyed_hash
    from common.crypto.keys import ring

    return keyed_hash(ring("SUBJECT_HASH").active_key, f"family-invitation:{normalized_phone}")


def phone_hint(normalized_phone: str) -> str:
    p = normalized_phone
    return f"{p[:4]}{'•' * max(len(p) - 6, 0)}{p[-2:]}"


def invite(
    owner_context,
    *,
    phone_number: str,
    permission_group: str | None,
    permissions: list[str] | None,
    expires_at=None,
) -> ManagerInvitation:
    """The owner invites another registered account (FR-FAM-001). Only Normal permissions can
    be set here; Sensitive ones are granted afterwards with ``set_permissions`` (confirmation +
    step-up).

    Enumeration-safe (KI-34): the request records a ``ManagerInvitation`` and answers the same
    way whether or not the number belongs to an account, and whether that account is verified,
    active or already linked to this profile. The only refusals depend on the owner's own data
    (rate limit, input validation, their own number, a number they already invited and that is
    still pending, or a number of a manager they already have). Eligibility is decided later by
    ``resolve_invitation`` in a background task, so the request does the same work either way.
    """
    if not owner_context.is_owner:
        from ..context import PermissionNotGranted

        raise PermissionNotGranted()
    owner = owner_context.actual_account
    if not allow("family_invite_account", str(owner.pk)):
        raise InvitationRateLimited()
    group = _group(permission_group)
    explicit = set(permissions or [])
    found = _validate_codes(explicit)
    if any(p.sensitivity == "SENSITIVE" for p in found.values()):
        raise ValidationError(
            {"permissions": ["Grant sensitive permissions after acceptance, with confirmation."]}
        )
    now = timezone.now()
    if expires_at is not None and expires_at <= now:
        raise ValidationError({"expires_at": ["The expiry must be in the future."]})
    try:
        phone = normalize_phone_number(phone_number)
    except Exception:
        raise ValidationError({"phone_number": ["Enter a valid phone number."]}) from None
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
                requested_permissions=sorted(explicit),
                requested_expires_at=expires_at,
                invited_at=now,
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
    account, create the PENDING authorization with the requested Normal permissions and notify
    the invitee. Otherwise nothing visible happens (the owner's invitation simply stays pending).
    Idempotent: a cancelled, answered or already linked invitation is left alone."""
    from apps.profiles.models import MatrimonialProfile

    invitation = ManagerInvitation.objects.filter(pk=invitation_id).first()
    if invitation is None or invitation.status != ManagerInvitation.Status.PENDING:
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
            if (
                invitation.status != ManagerInvitation.Status.PENDING
                or invitation.authorization_id is not None
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
            now = timezone.now()
            a = ProfileManagerAuthorization.objects.create(
                profile_id=invitation.profile_id,
                manager=invitee,
                invited_by=owner,
                permission_group=group,
                invited_at=invitation.invited_at,
                expires_at=invitation.requested_expires_at,
            )
            a = ProfileManagerAuthorization.objects.select_related(
                "profile", "permission_group"
            ).get(pk=a.pk)
            # Re-validated: the catalogue may have changed since the request (Normal only).
            codes = {
                p.code
                for p in ManagerPermission.objects.filter(
                    code__in=invitation.requested_permissions,
                    is_active=True,
                    sensitivity=ManagerPermission.Sensitivity.NORMAL,
                )
            }
            change = _apply_grants(a, _normal_codes(group) | codes, owner, now)
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


def _cancel_attempt(owner: User, invitation_id, reason) -> ManagerInvitation | None:
    row = (
        ManagerInvitation.objects.filter(pk=invitation_id, profile__owner_id=owner.pk)
        .values("authorization_id")
        .first()
    )
    if row is None:
        raise NotFound()
    seen = row["authorization_id"]
    with (
        transaction.atomic(),
        lock_plan(
            "family.cancel_invitation",
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
        lock_rows_for_share(User.objects.filter(pk=owner.pk), LockLevel.ACCOUNT)
        invitation = lock_rows_for_update(
            ManagerInvitation.objects.filter(pk=invitation_id), LockLevel.DOMAIN
        )[0]
        if invitation.authorization_id != seen:
            return None  # linked meanwhile by the resolution task: retry in lock order
        if invitation.status != ManagerInvitation.Status.PENDING:
            raise InvalidAuthorizationState("This invitation is no longer pending.")
        now = timezone.now()
        if a is not None and a.status == Status.PENDING:
            a = ProfileManagerAuthorization.objects.select_related(
                "profile", "permission_group"
            ).get(pk=a.pk)
            previous = _snapshot(a)
            a.status, a.revoked_at, a.reason = Status.REVOKED, now, reason
            a.save()
            _history(a, "REVOKED", owner, previous, _snapshot(a), reason)
            _audit("revoked", owner, a)
            _notify(a.manager_id, "authorization_revoked", a)
        invitation.status, invitation.cancelled_at, invitation.reason = (
            ManagerInvitation.Status.CANCELLED,
            now,
            reason,
        )
        invitation.save(update_fields=["status", "cancelled_at", "reason", "updated_at"])
        record_audit(
            action="family.invitation_cancelled",
            resource_type="family.invitation",
            actor_type="USER",
            result="SUCCESS",
            category="STATE_CHANGE",
            actor_user_id=owner.pk,
            subject_user_id=owner.pk,
            represented_profile_pseudonym=pseudonym_for("PROFILE", invitation.profile_id),
            metadata={"invitation_id": str(invitation.pk)},
        )
        return invitation


def cancel_invitation(owner: User, invitation_id, reason=None) -> ManagerInvitation:
    """The owner cancels a pending invitation (doc 15 §4 PENDING → REVOKED for a linked
    authorization). Locks follow the global order: authorization (1) before the invitation."""
    for _ in range(3):
        invitation = _cancel_attempt(owner, invitation_id, reason)
        if invitation is not None:
            return invitation
    raise InvalidAuthorizationState("Try again.")


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
        if accept:
            a.status, a.accepted_at, a.authorized_at = Status.ACTIVE, now, now
        else:
            a.status, a.rejected_at = Status.REJECTED, now
        a.save()
        action = "ACCEPTED" if accept else "REJECTED"
        _history(a, action, manager, previous, _snapshot(a))
        _audit(action.lower(), manager, a)
        invitations = lock_rows_for_update(
            ManagerInvitation.objects.filter(authorization=a), LockLevel.DOMAIN
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
    group = _group(permission_group)
    explicit = set(permissions)
    found = _validate_codes(explicit)
    sensitive = sorted(c for c, p in found.items() if p.sensitivity == "SENSITIVE")
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
        newly_sensitive = set(sensitive) - currently
        if newly_sensitive:
            if not confirm_sensitive:
                raise ValidationError(
                    {"confirm_sensitive": ["Confirm explicitly to grant sensitive permissions."]}
                )
            from apps.accounts.services.auth import require_recent_step_up
            from common.api.auth_errors import StepUpRequired

            if auth_session is None:
                raise OwnerStepUpRequired()
            try:
                require_recent_step_up(auth_session)
            except StepUpRequired:
                raise OwnerStepUpRequired() from None
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
        change = _apply_grants(a, _normal_codes(group) | explicit, owner, now)
        _history(a, "PERMISSIONS_CHANGED", owner, previous, {**_snapshot(a), **change})
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
    """Scheduled ACTIVE → EXPIRED (doc 15 §4); the runtime check already denies access. Also
    closes PAUSED authorizations whose expiry passed (they can never resume). Idempotent."""
    now = timezone.now()
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
    return done
