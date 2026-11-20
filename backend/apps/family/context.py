"""Acting-profile resolution: the immutable ``ActorContext`` (doc 04 §24.1 TR-02; ADR-026
direction adopted by DR-2026-11-18-G4; doc 14 §6).

``X-Acting-Profile`` *selects* a profile; it never proves authorization. Every profile-scoped
request is resolved fresh (never cached):

1. The account is already authenticated (DRF), including the account-state gate.
2. Profile selection: the header (a UUID, else 400 ``invalid``), or a profile ID in the URL, or
   the caller's own personal profile; with none, 400 ``acting_profile_required``. A header that
   disagrees with the URL profile is treated as not available.
3. The profile must exist and not be CLOSED.
4. Owner → full owner capabilities.
5. Otherwise an ACTIVE authorization for (profile, caller) whose ``expires_at`` hasn't passed is
   required (runtime check, regardless of the expiry job). PAUSED, PENDING, EXPIRED, REVOKED and
   REJECTED all deny [DECIDED]. Steps 3–5 fail with one identical 404
   ``acting_profile_not_available``.
6. The owner account must be active (manager path): else 403 ``acting_profile_unavailable``.
7. The endpoint's permission must be granted and active: else 403 ``permission_not_granted``.
   Owner-only permissions are never delegated.

Step 10 (TR-16, owner decision DR-2026-11-20-O-3): a manager's use of a granted Sensitive
permission needs a fresh step-up with the manager's **own authenticator** for that exact action
(``services/step_up.py``). The request carries ``X-Step-Up-Verification: <id>``; the
verification must belong to this manager, profile, authorization and action, be at most 5
minutes old and unused, and it is consumed atomically inside the business transaction (single
use). Missing, expired, reused or mismatched verifications fail with 403 ``step_up_required``;
a manager without an enrolled authenticator can't obtain one. A grant never bypasses this. The
owner is notified after each Sensitive action. One Sensitive action per request. Not
implemented: H tier and per-share approval (OD-05d), restrictions and eligibility (Phase 6),
billing (later phases; ``billing_account`` is already the owner).

Writes re-verify inside their transaction with ``lock_authorization_for_write`` (doc 04 §24.1
step 13): the authorization row FOR SHARE (lock level 1), then the same checks.
"""

import uuid
from dataclasses import dataclass, field

from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from apps.accounts.models import User
from apps.profiles.models import MatrimonialProfile
from common.db.locking import LockLevel, lock_rows_for_share

from .models import AuthorizationPermission, ProfileAccessHistory, ProfileManagerAuthorization

HEADER = "HTTP_X_ACTING_PROFILE"


class HeaderNotAllowed(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "header_not_allowed"
    default_detail = "X-Acting-Profile isn't accepted by this endpoint."


class ActingProfileRequired(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "acting_profile_required"
    default_detail = "Select a profile to act for."


class ActingProfileNotAvailable(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "acting_profile_not_available"
    default_detail = "The selected profile isn't available."


class ActingProfileUnavailable(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "acting_profile_unavailable"
    default_detail = "The selected profile can't be managed right now."


class StepUpVerificationRequired(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "step_up_required"
    default_detail = "This sensitive action needs a fresh verification with your authenticator app."


class OneSensitiveActionPerRequest(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "one_sensitive_action_per_request"
    default_detail = "Send one sensitive change per request, each with its own verification."


class PermissionNotGranted(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "permission_not_granted"
    default_detail = "You don't have permission to do this for the selected profile."


@dataclass(frozen=True)
class ActorContext:
    actual_account: User
    represented_profile: MatrimonialProfile
    is_owner: bool
    authorization_id: uuid.UUID | None
    granted: frozenset[str] = field(default_factory=frozenset)
    # Granted Sensitive permissions: usable only with a step-up verification (TR-16).
    sensitive: frozenset[str] = field(default_factory=frozenset)
    step_up_id: uuid.UUID | None = None
    request_id: str | None = None
    ip: str | None = None
    user_agent: str = ""

    @property
    def profile_id(self) -> uuid.UUID:
        return self.represented_profile.pk

    @property
    def billing_account_id(self) -> uuid.UUID:
        # doc 04 §24.1 step 14: never the manager's own account.
        return self.represented_profile.owner_id

    @property
    def audit_actor_type(self) -> str:
        return "USER" if self.is_owner else "MANAGER"

    def has(self, permission: str) -> bool:
        """Read-side check (e.g. field visibility). Sensitive permissions are never implied
        without a step-up, so they count as not held here."""
        return self.is_owner or (permission in self.granted and permission not in self.sensitive)

    def require(self, *permissions: str, any_of: bool = False) -> None:
        if self.is_owner:
            return
        held = [p in self.granted for p in permissions]
        if not (any(held) if any_of else all(held)):
            raise PermissionNotGranted()
        needed = sensitive_needed(self, permissions, any_of=any_of)
        if len(needed) > 1:
            raise OneSensitiveActionPerRequest()
        if needed and self.step_up_id is None:
            raise StepUpVerificationRequired()


def reject_header(request) -> None:
    """Account-scoped endpoints refuse the header (doc 04 §24.1 step 2)."""
    if request.META.get(HEADER):
        raise HeaderNotAllowed()


def _parse(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (TypeError, ValueError):
        raise ValidationError({"X-Acting-Profile": ["Must be a profile UUID."]}) from None


def live_authorization(profile_id, manager_id, now=None):
    now = now or timezone.now()
    authorization = ProfileManagerAuthorization.objects.filter(
        profile_id=profile_id, manager_id=manager_id, status="ACTIVE"
    ).first()
    if authorization is None:
        return None
    if authorization.expires_at is not None and authorization.expires_at <= now:
        return None  # runtime expiry, whatever the job has done
    return authorization


def granted_codes(authorization_id) -> frozenset[str]:
    return frozenset(
        AuthorizationPermission.objects.filter(
            authorization_id=authorization_id,
            is_granted=True,
            permission__is_active=True,
        )
        .exclude(permission__sensitivity="OWNER_ONLY")
        .values_list("permission__code", flat=True)
    )


def sensitive_codes(authorization_id) -> frozenset[str]:
    return frozenset(
        AuthorizationPermission.objects.filter(
            authorization_id=authorization_id,
            is_granted=True,
            permission__is_active=True,
            permission__sensitivity="SENSITIVE",
        ).values_list("permission__code", flat=True)
    )


def sensitive_needed(context, permissions, *, any_of: bool = False) -> list[str]:
    """The Sensitive permissions this call relies on (none for owners). With ``any_of``, a
    Normal permission that satisfies the call means no Sensitive one is needed."""
    if context.is_owner:
        return []
    granted = [p for p in permissions if p in context.granted]
    if any_of and any(p not in context.sensitive for p in granted):
        return []
    return sorted(p for p in granted if p in context.sensitive)


STEP_UP_HEADER = "HTTP_X_STEP_UP_VERIFICATION"


def _step_up_id(request) -> uuid.UUID | None:
    value = request.META.get(STEP_UP_HEADER)
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except (TypeError, ValueError):
        raise ValidationError(
            {"X-Step-Up-Verification": ["Must be a verification UUID."]}
        ) from None


def resolve(
    request,
    *,
    permission: str | None = None,
    path_profile_id=None,
    any_of: tuple[str, ...] = (),
    access_type: str | None = None,
) -> ActorContext:
    user = request.user
    header = request.META.get(HEADER)
    selected = _parse(header) if header else None
    if path_profile_id is not None:
        if selected is not None and selected != path_profile_id:
            raise ActingProfileNotAvailable()
        selected = path_profile_id
    if selected is None:
        own = (
            MatrimonialProfile.objects.filter(owner_id=user.pk).values_list("pk", flat=True).first()
        )
        if own is None:
            raise ActingProfileRequired()
        selected = own

    profile = MatrimonialProfile.objects.select_related("owner").filter(pk=selected).first()
    if profile is None or profile.profile_status == MatrimonialProfile.Status.CLOSED:
        raise ActingProfileNotAvailable()

    meta = {
        "request_id": getattr(request, "request_id", None)
        or getattr(getattr(request, "_request", None), "request_id", None),
        "ip": request.META.get("REMOTE_ADDR"),
        "user_agent": (request.META.get("HTTP_USER_AGENT") or "")[:512],
    }
    if profile.owner_id == user.pk:
        return ActorContext(user, profile, True, None, **meta)

    authorization = live_authorization(profile.pk, user.pk)
    if authorization is None:
        raise ActingProfileNotAvailable()
    owner = profile.owner
    if not owner.is_active or owner.deactivated:
        raise ActingProfileUnavailable()
    context = ActorContext(
        user,
        profile,
        False,
        authorization.pk,
        granted_codes(authorization.pk),
        sensitive_codes(authorization.pk),
        _step_up_id(request),
        **meta,
    )
    if permission:
        context.require(permission)
    if any_of:
        context.require(*any_of, any_of=True)
    ProfileAccessHistory.objects.create(
        profile=profile,
        authorization=authorization,
        manager=user,
        ip_address=context.ip,
        browser=context.user_agent[:200],
        access_type=access_type or permission or (any_of[0] if any_of else "view_profile"),
    )
    return context


def lock_authorization_for_write(context: ActorContext, *permissions: str) -> None:
    """Inside the service transaction (lock level 1, first): re-check the manager path and the
    permissions, so a pause, revocation or permission change committed meanwhile wins."""
    if context.is_owner:
        return
    lock_rows_for_share(
        ProfileManagerAuthorization.objects.filter(pk=context.authorization_id),
        LockLevel.AUTHORIZATION,
    )
    if live_authorization(context.profile_id, context.actual_account.pk) is None:
        raise ActingProfileNotAvailable()
    current = granted_codes(context.authorization_id)
    if any(p not in current for p in permissions):
        raise PermissionNotGranted()
