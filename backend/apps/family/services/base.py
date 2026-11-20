"""Shared building blocks for family management (FR-FAM-001…009; doc 05 §2; doc 14 §1–§8;
doc 15 §4): errors, history, audit, notifications, locking and permission selection.

Permission selection (owner decision DR-2026-11-20-O-1) is the same everywhere the owner chooses
permissions: when sending an invitation, when accepting a request and when changing an
authorization later. A template grants its **Normal** permissions; individually listed
permissions are granted exactly as listed; **Sensitive** ones need explicit confirmation and a
recent owner step-up (doc 14 §4, FR-FAM-005); **Owner-only** ones are never granted. Only the
profile owner ever selects permissions.
"""

from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError

from apps.accounts.managers import normalize_phone_number
from apps.accounts.models import User
from apps.accounts.services.pseudonyms import pseudonym_for
from apps.audit.services import record_audit
from common.db.locking import LockLevel, lock_rows_for_share, lock_rows_for_update
from common.events.services import emit

from ..models import (
    AuthorizationPermission,
    ManagerAuthorizationHistory,
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


class AlreadyRequested(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "already_requested"
    default_detail = "You already have a pending request for this number."


class InvitationExpired(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "invitation_expired"
    default_detail = "This invitation or request expired because it wasn't accepted in time."


# --- Helpers -------------------------------------------------------------------------------


def _snapshot(a: ProfileManagerAuthorization) -> dict:
    return {
        "status": a.status,
        "expires_at": a.expires_at.isoformat() if a.expires_at else None,
        "permission_group": a.permission_group.code if a.permission_group_id else None,
    }


def _history(a, action, by, previous, new, reason=None, *, invitation=None, request=None):
    ManagerAuthorizationHistory.objects.create(
        authorization=a,
        invitation=invitation,
        request=request,
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


# --- Invitations and requests: shared rules ----------------------------------------------

EXPIRY_REASON = "NOT_ACCEPTED_WITHIN_30_DAYS"


def phone_digest(normalized_phone: str) -> str:
    """Keyed hash of a normalized phone number (the number itself is never stored)."""
    from common.crypto.aead import keyed_hash
    from common.crypto.keys import ring

    return keyed_hash(ring("SUBJECT_HASH").active_key, f"family-invitation:{normalized_phone}")


def phone_hint(normalized_phone: str) -> str:
    p = normalized_phone
    return f"{p[:4]}{'•' * max(len(p) - 6, 0)}{p[-2:]}"


def normalize_or_400(phone_number: str) -> str:
    try:
        return normalize_phone_number(phone_number)
    except Exception:
        raise ValidationError({"phone_number": ["Enter a valid phone number."]}) from None


def acceptance_deadline(start):
    """OD-05e (DR-2026-11-20-O-2): pending invitations and requests expire after 30 days."""
    from datetime import timedelta

    from django.conf import settings

    return start + timedelta(days=settings.FAMILY_INVITATION_TTL_DAYS)


def notify_event(recipient_id, event: str, subject_type: str, subject_id, stamp, **payload):
    """Outbox notice about an invitation or a request (no private data in the payload)."""
    emit(
        f"family.{event}",
        event_class="NOTIFICATION",
        category="ACCOUNT",
        aggregate_type=subject_type,
        recipient_pseudonym=pseudonym_for("ACCOUNT", recipient_id),
        payload={f"{subject_type.lower()}_id": str(subject_id), **payload},
        dedupe_identity=f"family:{event}:{subject_id}:{stamp.isoformat()}:{recipient_id}",
    )


def audit_subject(action, by, owner_id, profile_id, resource_type, **metadata):
    record_audit(
        action=f"family.{action}",
        resource_type=resource_type,
        actor_type="USER" if by is not None else "SYSTEM",
        result="SUCCESS",
        category="STATE_CHANGE",
        actor_user_id=by.pk if by is not None else None,
        subject_user_id=owner_id,
        represented_profile_pseudonym=pseudonym_for("PROFILE", profile_id) if profile_id else None,
        metadata=metadata,
    )


def _require_owner_step_up(auth_session) -> None:
    from apps.accounts.services.auth import require_recent_step_up
    from common.api.auth_errors import StepUpRequired

    if auth_session is None:
        raise OwnerStepUpRequired()
    try:
        require_recent_step_up(auth_session)
    except StepUpRequired:
        raise OwnerStepUpRequired() from None


def select_permissions(
    permission_group: str | None,
    permissions,
    *,
    confirm_sensitive: bool,
    auth_session,
    already_sensitive: frozenset[str] = frozenset(),
) -> tuple[ManagerPermissionGroup | None, set[str], list[str]]:
    """Validate the owner's selection. Returns (template, codes to grant, sensitive codes).

    Newly selected Sensitive permissions need confirm_sensitive and a recent owner step-up;
    keeping already granted ones needs neither."""
    group = _group(permission_group)
    explicit = set(permissions or [])
    found = _validate_codes(explicit)
    sensitive = sorted(c for c, p in found.items() if p.sensitivity == "SENSITIVE")
    if set(sensitive) - set(already_sensitive):
        if not confirm_sensitive:
            raise ValidationError(
                {"confirm_sensitive": ["Confirm explicitly to grant sensitive permissions."]}
            )
        _require_owner_step_up(auth_session)
    return group, _normal_codes(group) | explicit, sensitive


def grantable(codes) -> set[str]:
    """Re-check stored selections at use: active, delegable permissions only."""
    return set(
        ManagerPermission.objects.filter(code__in=list(codes), is_active=True)
        .exclude(sensitivity=ManagerPermission.Sensitivity.OWNER_ONLY)
        .values_list("code", flat=True)
    )


def record_permission_change(a, by, change: dict, previous: dict) -> None:
    """Separate history rows for granted and revoked permissions (DR-2026-11-20-O-1)."""
    if change["granted"]:
        _history(a, "PERMISSIONS_GRANTED", by, previous, {"permissions": change["granted"]})
    if change["revoked"]:
        _history(a, "PERMISSIONS_REVOKED", by, previous, {"permissions": change["revoked"]})
