"""Flow B: an account asks to manage another person's profile (owner decision
DR-2026-11-20-O-1; ADR-034 applied to requests).

- The requester identifies the profile owner by phone number. Every valid request is recorded
  and answered the same way; ``resolve_request`` (background task) finds the owner's personal
  profile and notifies the owner only if the owner and the requester are eligible. The requester
  learns nothing about the number until the owner accepts or declines.
- Only the profile owner answers. When accepting, the owner selects the permissions (same rules
  as invitations); the authorization is created ACTIVE with exactly those permissions.
- A pending request expires 30 days after it was sent if it isn't accepted. The requester can
  cancel it while pending. A request is always made by the requester's own account for
  themselves: nobody can request or accept on another person's behalf.
- Lock order: accounts (2) → profile (3) → request (domain) → inserts.
"""

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError

from apps.accounts.models import User
from common.api.throttles import allow
from common.db.locking import LockLevel, lock_plan, lock_rows_for_share, lock_rows_for_update

from ..models import ManagerRequest, ProfileManagerAuthorization
from .base import (
    EXPIRY_REASON,
    AlreadyManaging,
    AlreadyRequested,
    InvalidAuthorizationState,
    InvitationExpired,
    InvitationRateLimited,
    _apply_grants,
    _audit,
    _history,
    _snapshot,
    acceptance_deadline,
    audit_subject,
    normalize_or_400,
    notify_event,
    phone_digest,
    phone_hint,
    select_permissions,
)

Req = ManagerRequest.Status
Status = ProfileManagerAuthorization.Status
LEVELS = [LockLevel.ACCOUNT, LockLevel.PROFILE, LockLevel.DOMAIN, LockLevel.INSERT]


class RequesterNotVerified(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "phone_verification_required"
    default_detail = "Verify your phone number before asking to manage a profile."


def _requester_eligible(user: User) -> bool:
    return user.is_active and not user.deactivated and user.is_phone_verified


def create_request(requester: User, phone_number: str) -> ManagerRequest:
    """Record a request to manage the profile of the account holding ``phone_number``.
    The answer never depends on whether that account or profile exists."""
    if not _requester_eligible(requester):
        raise RequesterNotVerified()
    if not allow("family_request_account", str(requester.pk)):
        raise InvitationRateLimited("Too many requests. Try again later.")
    phone = normalize_or_400(phone_number)
    if phone == requester.phone_number:
        raise ValidationError({"phone_number": ["You can't ask to manage your own profile."]})
    # The requester already knows the owners whose profiles they manage.
    if ProfileManagerAuthorization.objects.filter(
        manager=requester,
        status__in=[Status.ACTIVE, Status.PAUSED],
        profile__owner__phone_number=phone,
    ).exists():
        raise AlreadyManaging("You already manage this person's profile.")
    owner_id = (
        User.objects.filter(phone_number=phone)
        .exclude(pk=requester.pk)
        .values_list("pk", flat=True)
    ).first()
    now = timezone.now()
    try:
        with (
            transaction.atomic(),
            lock_plan("family.request", [LockLevel.ACCOUNT, LockLevel.INSERT]),
        ):
            lock_rows_for_share(
                User.objects.filter(pk__in=[pk for pk in (requester.pk, owner_id) if pk]),
                LockLevel.ACCOUNT,
            )
            request = ManagerRequest.objects.create(
                requester=requester,
                owner_phone_digest=phone_digest(phone),
                owner_phone_hint=phone_hint(phone),
                owner_id=owner_id,
                requested_at=now,
                expires_at=acceptance_deadline(now),
            )
            _history(
                None,
                "REQUEST_CREATED",
                requester,
                {},
                {"expires_at": request.expires_at.isoformat()},
                request=request,
            )
            audit_subject(
                "request_created",
                requester,
                requester.pk,
                None,
                "family.request",
                request_id=str(request.pk),
            )
            request_id = str(request.pk)
            transaction.on_commit(lambda: _enqueue_resolution(request_id))
    except IntegrityError:
        raise AlreadyRequested() from None
    return request


def _enqueue_resolution(request_id: str) -> None:
    from ..tasks import resolve_manager_request

    resolve_manager_request.delay(request_id)


def resolve_request(request_id) -> ManagerRequest | None:
    """Background step: attach the owner's personal profile and notify the owner when the
    number belongs to an eligible owner. Otherwise nothing visible happens. Idempotent."""
    from apps.profiles.models import MatrimonialProfile

    request = ManagerRequest.objects.filter(pk=request_id).first()
    if request is None or request.status != Req.PENDING or request.profile_id is not None:
        return None
    accounts = [request.requester_id] + ([request.owner_id] if request.owner_id else [])
    profile_id = (
        MatrimonialProfile.objects.filter(owner_id=request.owner_id)
        .values_list("pk", flat=True)
        .first()
        if request.owner_id
        else None
    )
    with transaction.atomic(), lock_plan("family.resolve_request", LEVELS):
        lock_rows_for_share(User.objects.filter(pk__in=accounts), LockLevel.ACCOUNT)
        profiles = lock_rows_for_update(
            MatrimonialProfile.objects.filter(pk=profile_id), LockLevel.PROFILE
        )
        request = lock_rows_for_update(
            ManagerRequest.objects.filter(pk=request_id), LockLevel.DOMAIN
        )[0]
        now = timezone.now()
        if request.status != Req.PENDING or request.profile_id or request.expires_at <= now:
            return None
        owner = User.objects.filter(pk=request.owner_id).first()
        requester = User.objects.get(pk=request.requester_id)
        profile = profiles[0] if profiles else None
        eligible = (
            owner is not None
            and _requester_eligible(owner)
            and phone_digest(owner.phone_number) == request.owner_phone_digest
            and profile is not None
            and profile.profile_status != MatrimonialProfile.Status.CLOSED
            and _requester_eligible(requester)
            and not ProfileManagerAuthorization.objects.filter(
                profile=profile, manager=requester, status__in=ProfileManagerAuthorization.LIVE
            ).exists()
        )
        if not eligible:
            audit_subject(
                "request_unresolved",
                None,
                request.requester_id,
                None,
                "family.request",
                request_id=str(request.pk),
            )
            return None
        request.profile = profile
        request.save(update_fields=["profile", "updated_at"])
        audit_subject(
            "request_delivered",
            None,
            owner.pk,
            profile.pk,
            "family.request",
            request_id=str(request.pk),
        )
        notify_event(owner.pk, "manager_request_received", "ManagerRequest", request.pk, now)
        return request


def _lock_for_owner(owner: User, request_id):
    """Locks in global order and returns the owner's pending request, or 404."""
    from apps.profiles.models import MatrimonialProfile

    row = (
        ManagerRequest.objects.filter(pk=request_id, profile__owner_id=owner.pk)
        .values("requester_id", "profile_id")
        .first()
    )
    if row is None:
        raise NotFound()
    lock_rows_for_share(
        User.objects.filter(pk__in=[owner.pk, row["requester_id"]]), LockLevel.ACCOUNT
    )
    profile = lock_rows_for_update(
        MatrimonialProfile.objects.filter(pk=row["profile_id"]), LockLevel.PROFILE
    )[0]
    request = lock_rows_for_update(ManagerRequest.objects.filter(pk=request_id), LockLevel.DOMAIN)[
        0
    ]
    if request.status != Req.PENDING:
        raise InvalidAuthorizationState("This request is no longer pending.")
    if request.expires_at <= timezone.now():
        raise InvitationExpired()
    return profile, request


def accept_request(
    owner: User,
    request_id,
    *,
    permission_group: str | None,
    permissions,
    confirm_sensitive: bool = False,
    auth_session=None,
) -> ProfileManagerAuthorization:
    """The owner accepts and selects the permissions; the authorization becomes ACTIVE with
    exactly those permissions."""
    group, codes, _ = select_permissions(
        permission_group,
        permissions,
        confirm_sensitive=confirm_sensitive,
        auth_session=auth_session,
    )
    try:
        with transaction.atomic(), lock_plan("family.accept_request", LEVELS):
            profile, request = _lock_for_owner(owner, request_id)
            requester = User.objects.get(pk=request.requester_id)
            if not _requester_eligible(requester):
                raise InvalidAuthorizationState("This account can't manage profiles right now.")
            now = timezone.now()
            a = ProfileManagerAuthorization.objects.create(
                profile=profile,
                manager=requester,
                invited_by=owner,
                permission_group=group,
                status=Status.ACTIVE,
                invited_at=request.requested_at,
                accepted_at=now,
                authorized_at=now,
            )
            a = ProfileManagerAuthorization.objects.select_related(
                "profile", "permission_group"
            ).get(pk=a.pk)
            change = _apply_grants(a, codes, owner, now)
            _history(
                a,
                "REQUESTED",
                requester,
                {},
                {"requested_at": request.requested_at.isoformat()},
                request=request,
            )
            _history(
                a,
                "REQUEST_ACCEPTED",
                owner,
                {},
                {**_snapshot(a), **change},
                request=request,
            )
            request.status, request.responded_at, request.authorization = Req.ACCEPTED, now, a
            request.save(update_fields=["status", "responded_at", "authorization", "updated_at"])
            _audit(
                "request_accepted",
                owner,
                a,
                permission_group=group.code if group else None,
                granted_count=len(change["granted"]),
            )
            notify_event(
                requester.pk, "manager_request_accepted", "ManagerRequest", request.pk, now
            )
            return a
    except IntegrityError:
        raise InvalidAuthorizationState("This account already has a live authorization.") from None


def decline_request(owner: User, request_id) -> ManagerRequest:
    with transaction.atomic(), lock_plan("family.decline_request", LEVELS):
        profile, request = _lock_for_owner(owner, request_id)
        now = timezone.now()
        request.status, request.responded_at = Req.DECLINED, now
        request.save(update_fields=["status", "responded_at", "updated_at"])
        _history(
            None,
            "REQUEST_DECLINED",
            owner,
            {"status": "PENDING"},
            {"status": "DECLINED"},
            request=request,
        )
        audit_subject(
            "request_declined",
            owner,
            owner.pk,
            profile.pk,
            "family.request",
            request_id=str(request.pk),
        )
        notify_event(
            request.requester_id, "manager_request_declined", "ManagerRequest", request.pk, now
        )
        return request


def cancel_request(requester: User, request_id) -> ManagerRequest:
    """The requester withdraws their own pending request."""
    with transaction.atomic(), lock_plan("family.cancel_request", LEVELS):
        if not ManagerRequest.objects.filter(pk=request_id, requester=requester).exists():
            raise NotFound()
        lock_rows_for_share(User.objects.filter(pk=requester.pk), LockLevel.ACCOUNT)
        request = lock_rows_for_update(
            ManagerRequest.objects.filter(pk=request_id), LockLevel.DOMAIN
        )[0]
        if request.status != Req.PENDING:
            raise InvalidAuthorizationState("This request is no longer pending.")
        request.status, request.cancelled_at = Req.CANCELLED, timezone.now()
        request.save(update_fields=["status", "cancelled_at", "updated_at"])
        _history(
            None,
            "REQUEST_CANCELLED",
            requester,
            {"status": "PENDING"},
            {"status": "CANCELLED"},
            request=request,
        )
        audit_subject(
            "request_cancelled",
            requester,
            requester.pk,
            request.profile_id,
            "family.request",
            request_id=str(request.pk),
        )
        return request


def expire_requests(now=None) -> int:
    """Scheduled: pending requests past their 30-day deadline become EXPIRED. Idempotent."""
    now = now or timezone.now()
    due = list(
        ManagerRequest.objects.filter(status=Req.PENDING, expires_at__lte=now).values_list(
            "pk", "requester_id", "owner_id"
        )
    )
    done = 0
    for pk, requester_id, owner_id in due:
        with transaction.atomic(), lock_plan("family.expire_request", LEVELS):
            lock_rows_for_share(
                User.objects.filter(pk__in=[p for p in (requester_id, owner_id) if p]),
                LockLevel.ACCOUNT,
            )
            rows = lock_rows_for_update(
                ManagerRequest.objects.filter(pk=pk, status=Req.PENDING, expires_at__lte=now),
                LockLevel.DOMAIN,
            )
            if not rows:
                continue
            request = rows[0]
            request.status, request.expired_at = Req.EXPIRED, now
            request.save(update_fields=["status", "expired_at", "updated_at"])
            _history(
                None,
                "REQUEST_EXPIRED",
                None,
                {"status": "PENDING"},
                {"status": "EXPIRED"},
                EXPIRY_REASON,
                request=request,
            )
            audit_subject(
                "request_expired",
                None,
                requester_id,
                request.profile_id,
                "family.request",
                request_id=str(request.pk),
                reason=EXPIRY_REASON,
            )
            notify_event(requester_id, "manager_request_expired", "ManagerRequest", pk, now)
            if request.profile_id:  # the owner had received it
                notify_event(owner_id, "manager_request_expired", "ManagerRequest", pk, now)
            done += 1
    return done
