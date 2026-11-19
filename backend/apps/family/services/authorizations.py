"""Manager authorization lifecycle and permissions (FR-FAM-001…009; doc 05 §2; doc 14 §1–§8;
doc 15 §4).

Rules implemented (all approved):
- Only the profile owner invites, pauses, resumes, renews, revokes and sets permissions; the
  invited account accepts or rejects [DECIDED]. Nobody manages their own profile.
- The invitee must be another registered, active, phone-verified account (FR-FAM-001). Every
  ineligible case answers with the same error, and invitations are rate limited per owner.
- At most one PENDING/ACTIVE/PAUSED authorization per (profile, manager).
- Transitions (doc 15 §4): PENDING→ACTIVE (accept), PENDING→REJECTED (reject), PENDING→REVOKED
  (owner cancels), ACTIVE↔PAUSED (owner), ACTIVE/PAUSED→REVOKED (owner), ACTIVE→EXPIRED (job and
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
    ManagerPermission,
    ManagerPermissionGroup,
    ProfileManagerAuthorization,
)

Status = ProfileManagerAuthorization.Status


class InviteeNotAvailable(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "invitee_not_available"
    default_detail = "This account can't be invited."


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
        query = query.filter(profile__owner_id=owner.pk)
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


def invite(
    owner_context,
    *,
    phone_number: str,
    permission_group: str | None,
    permissions: list[str] | None,
    expires_at=None,
) -> ProfileManagerAuthorization:
    """The owner invites another registered account. Only Normal permissions can be set here;
    Sensitive ones are granted afterwards with ``set_permissions`` (confirmation + step-up)."""
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
        raise InviteeNotAvailable() from None
    invitee = User.objects.filter(phone_number=phone).first()
    if (
        invitee is None
        or invitee.pk == owner.pk
        or not invitee.is_active
        or invitee.deactivated
        or not invitee.is_phone_verified
    ):
        raise InviteeNotAvailable()  # one answer for every case (no account enumeration detail)
    try:
        with (
            transaction.atomic(),
            lock_plan("family.invite", [LockLevel.ACCOUNT, LockLevel.PROFILE, LockLevel.INSERT]),
        ):
            lock_rows_for_share(
                User.objects.filter(pk__in=[owner.pk, invitee.pk]), LockLevel.ACCOUNT
            )
            from apps.profiles.models import MatrimonialProfile

            lock_rows_for_update(
                MatrimonialProfile.objects.filter(pk=owner_context.profile_id), LockLevel.PROFILE
            )
            a = ProfileManagerAuthorization.objects.create(
                profile_id=owner_context.profile_id,
                manager=invitee,
                invited_by=owner,
                permission_group=group,
                invited_at=now,
                expires_at=expires_at,
            )
            a = ProfileManagerAuthorization.objects.select_related(
                "profile", "permission_group"
            ).get(pk=a.pk)
            change = _apply_grants(a, _normal_codes(group) | explicit, owner, now)
            _history(a, "INVITED", owner, {}, {**_snapshot(a), **change})
            _audit("invited", owner, a, permission_group=permission_group)
            _notify(invitee.pk, "invitation_received", a)
            return a
    except IntegrityError:
        raise InviteeNotAvailable() from None  # already invited or managing this profile


# --- Manager responses ---------------------------------------------------------------------


def _respond(manager: User, authorization_id, accept: bool) -> ProfileManagerAuthorization:
    with (
        transaction.atomic(),
        lock_plan("family.respond", [LockLevel.AUTHORIZATION, LockLevel.ACCOUNT]),
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
        _notify(a.profile.owner_id, "invitation_" + action.lower(), a)
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
