"""``/family-management/`` (doc 04 §6, plus ``renew``, invitations and requests).

Account-scoped: X-Acting-Profile is refused (doc 04 §24.1 step 2), so a manager can never act
here *for* the profile they manage. Owners act on their own personal profile's invitations,
requests and authorizations; managers see and answer what is addressed to their own account.
Anything else gets the same 404. Request and response schemas are declared explicitly
(``serializers.py``) and match what the views return (KI-40).
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.profiles.models import MatrimonialProfile

from ..context import ActorContext, reject_header
from ..models import (
    ManagerActionLog,
    ManagerInvitation,
    ManagerPermission,
    ManagerPermissionGroup,
    ManagerRequest,
    ProfileAccessHistory,
    ProfileManagerAuthorization,
)
from ..services import authorizations as service
from ..services import requests as request_service
from . import serializers as s

TAG = ["family-management"]


def _mask(phone: str) -> str:
    return f"{phone[:4]}{'•' * max(len(phone) - 6, 0)}{phone[-2:]}"


def _display(user) -> str:
    return user.first_name or _mask(user.phone_number)


def _granted(a) -> list[str]:
    # Owner-only permissions are never effective, even if a row exists (DR-2026-11-20-O-4).
    return sorted(
        a.permission_grants.filter(is_granted=True)
        .exclude(permission__sensitivity="OWNER_ONLY")
        .values_list("permission__code", flat=True)
    )


def _as_owner(a) -> dict:
    return {
        "id": str(a.pk),
        "manager": {"display": _display(a.manager)},
        "status": a.status,
        "permission_group": a.permission_group.code if a.permission_group_id else None,
        "permissions": _granted(a),
        "expires_at": a.expires_at,
        "invited_at": a.invited_at,
        "accepted_at": a.accepted_at,
        "paused_at": a.paused_at,
        "revoked_at": a.revoked_at,
    }


def _as_invitation(i: ManagerInvitation) -> dict:
    """The owner's view of an invitation: only what the owner typed or chose, plus the status.
    Never the invitee's name or any account detail (KI-34)."""
    return {
        "id": str(i.pk),
        "phone_hint": i.phone_hint,
        "status": i.status,
        "permission_group": i.permission_group.code if i.permission_group_id else None,
        "requested_permissions": list(i.requested_permissions),
        "requested_expires_at": i.requested_expires_at,
        "invited_at": i.invited_at,
        "expires_at": i.expires_at,
        "responded_at": i.responded_at,
        "cancelled_at": i.cancelled_at,
        "expired_at": i.expired_at,
        # Shown once the invitee accepted: the authorization is then visible to the owner.
        "authorization_id": (
            str(i.authorization_id) if i.status == ManagerInvitation.Status.ACCEPTED else None
        ),
    }


def _as_sent_request(r: ManagerRequest) -> dict:
    """The requester's view: only what they typed and the status (nothing about the owner
    until the owner answers)."""
    answered = r.status in (ManagerRequest.Status.ACCEPTED, ManagerRequest.Status.DECLINED)
    return {
        "id": str(r.pk),
        "phone_hint": r.owner_phone_hint,
        "status": r.status,
        "requested_at": r.requested_at,
        "expires_at": r.expires_at,
        "responded_at": r.responded_at,
        "cancelled_at": r.cancelled_at,
        "expired_at": r.expired_at,
        "profile_code": r.profile.profile_code if answered and r.profile_id else None,
        "authorization_id": str(r.authorization_id) if r.authorization_id else None,
    }


def _as_received_request(r: ManagerRequest) -> dict:
    return {
        "id": str(r.pk),
        "requester": {"display": _display(r.requester)},
        "status": r.status,
        "requested_at": r.requested_at,
        "expires_at": r.expires_at,
        "responded_at": r.responded_at,
        "authorization_id": str(r.authorization_id) if r.authorization_id else None,
    }


def _as_manager(a) -> dict:
    return {
        "id": str(a.pk),
        "profile": {"id": str(a.profile_id), "profile_code": a.profile.profile_code},
        "status": a.status,
        "permissions": _granted(a),
        "expires_at": a.expires_at,
        "invited_at": a.invited_at,
        "invitation_expires_at": a.invitation_expires_at,
    }


def _history_rows(rows, owner_id) -> list[dict]:
    return [
        {
            "action": h.action,
            "by_owner": h.performed_by_id == owner_id,
            "by_system": h.performed_by_id is None,
            "previous": h.previous_values,
            "new": h.new_values,
            "reason": h.reason,
            "at": h.created_at,
        }
        for h in rows
    ]


def _owner_context(request) -> ActorContext:
    reject_header(request)
    profile = MatrimonialProfile.objects.filter(owner_id=request.user.pk).first()
    if profile is None or profile.profile_status == MatrimonialProfile.Status.CLOSED:
        raise NotFound()
    return ActorContext(
        request.user, profile, True, None, request_id=getattr(request._request, "request_id", None)
    )


def _session(request):
    return getattr(request._request, "auth_session", None)


class AuthorizationListView(APIView):
    @extend_schema(tags=TAG, responses=s.AuthorizationListResponse)
    def get(self, request):
        reject_header(request)
        # Owners see authorizations once accepted; before that, only their invitations (KI-34).
        owned = (
            ProfileManagerAuthorization.objects.filter(
                profile__owner_id=request.user.pk, accepted_at__isnull=False
            )
            .select_related("manager", "permission_group")
            .order_by("-invited_at")
        )
        invitations = (
            ManagerInvitation.objects.filter(profile__owner_id=request.user.pk)
            .select_related("permission_group")
            .order_by("-invited_at")[:200]
        )
        managed = (
            ProfileManagerAuthorization.objects.filter(manager_id=request.user.pk)
            .select_related("profile")
            .order_by("-invited_at")
        )
        return Response(
            {
                "as_owner": [_as_owner(a) for a in owned],
                "invitations": [_as_invitation(i) for i in invitations],
                "as_manager": [_as_manager(a) for a in managed],
            }
        )

    @extend_schema(
        tags=TAG,
        request=s.InviteSerializer,
        responses={202: s.InvitationSentResponse},
        description=(
            "Invite a manager with the permissions the owner selects. The answer is the same "
            "for every valid number (ADR-034)."
        ),
    )
    def post(self, request):
        ctx = _owner_context(request)
        data = s.InviteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        invitation = service.invite(
            ctx,
            phone_number=data.validated_data["phone_number"],
            permission_group=data.validated_data.get("permission_group"),
            permissions=data.validated_data.get("permissions"),
            expires_at=data.validated_data.get("expires_at"),
            confirm_sensitive=data.validated_data["confirm_sensitive"],
            auth_session=_session(request),
        )
        # 202 and the same body for every number (KI-34): built from the owner's input only.
        return Response(
            {"detail": s.INVITATION_SENT, "invitation": _as_invitation(invitation)},
            status=status.HTTP_202_ACCEPTED,
        )


class ManagerResponseView(APIView):
    accept = True

    @extend_schema(tags=TAG, request=None, responses=s.ManagedAuthorizationSerializer)
    def post(self, request, authorization_id):
        reject_header(request)
        operation = service.accept if self.accept else service.reject
        return Response(_as_manager(operation(request.user, authorization_id)))


class OwnerControlView(APIView):
    operation = None

    @extend_schema(tags=TAG, request=s.ReasonSerializer, responses=s.OwnerAuthorizationSerializer)
    def post(self, request, authorization_id):
        reject_header(request)
        data = s.ReasonSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        a = type(self).operation(request.user, authorization_id, data.validated_data.get("reason"))
        return Response(_as_owner(a))


class PauseView(OwnerControlView):
    operation = staticmethod(service.pause)


class ResumeView(OwnerControlView):
    operation = staticmethod(service.resume)


class RevokeView(OwnerControlView):
    operation = staticmethod(service.revoke)


class RenewView(APIView):
    @extend_schema(tags=TAG, request=s.RenewSerializer, responses=s.OwnerAuthorizationSerializer)
    def post(self, request, authorization_id):
        reject_header(request)
        data = s.RenewSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        a = service.renew(request.user, authorization_id, data.validated_data["expires_at"])
        return Response(_as_owner(a))


class AuthorizationPermissionsView(APIView):
    @extend_schema(
        tags=TAG,
        request=s.PermissionsSerializer,
        responses=s.PermissionsChangeResponse,
        description="Owner only: grant or revoke individual permissions of an authorization.",
    )
    def put(self, request, authorization_id):
        reject_header(request)
        data = s.PermissionsSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        change = service.set_permissions(
            request.user,
            authorization_id,
            permission_group=data.validated_data.get("permission_group"),
            permissions=data.validated_data["permissions"],
            confirm_sensitive=data.validated_data["confirm_sensitive"],
            auth_session=_session(request),
        )
        a = ProfileManagerAuthorization.objects.get(pk=authorization_id)
        return Response({**_as_owner(a), "change": change})


class AuthorizationHistoryView(APIView):
    """The owner (once accepted) and the authorization's manager may read its history."""

    @extend_schema(tags=TAG, responses=s.HistoryEntrySerializer(many=True))
    def get(self, request, authorization_id):
        reject_header(request)
        a = (
            ProfileManagerAuthorization.objects.filter(pk=authorization_id)
            .select_related("profile")
            .first()
        )
        is_owner = a is not None and a.profile.owner_id == request.user.pk
        if a is None or not (
            (is_owner and a.accepted_at is not None) or a.manager_id == request.user.pk
        ):
            raise NotFound()
        return Response(_history_rows(a.history.all(), a.profile.owner_id))


class InvitationCancelView(APIView):
    @extend_schema(tags=TAG, request=s.ReasonSerializer, responses=s.InvitationSerializer)
    def post(self, request, invitation_id):
        reject_header(request)
        data = s.ReasonSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        invitation = service.cancel_invitation(
            request.user, invitation_id, data.validated_data.get("reason")
        )
        return Response(_as_invitation(invitation))


class InvitationHistoryView(APIView):
    """The owner's history of one invitation: created, cancelled, expired, answered. Never the
    background resolution (ADR-034)."""

    @extend_schema(tags=TAG, responses=s.HistoryEntrySerializer(many=True))
    def get(self, request, invitation_id):
        reject_header(request)
        invitation = ManagerInvitation.objects.filter(
            pk=invitation_id, profile__owner_id=request.user.pk
        ).first()
        if invitation is None:
            raise NotFound()
        return Response(_history_rows(invitation.history.all(), request.user.pk))


class RequestListView(APIView):
    @extend_schema(tags=TAG, responses=s.RequestListResponse)
    def get(self, request):
        reject_header(request)
        sent = ManagerRequest.objects.filter(requester_id=request.user.pk).select_related("profile")
        received = ManagerRequest.objects.filter(profile__owner_id=request.user.pk).select_related(
            "requester"
        )
        return Response(
            {
                "sent": [_as_sent_request(r) for r in sent.order_by("-requested_at")[:200]],
                "received": [
                    _as_received_request(r) for r in received.order_by("-requested_at")[:200]
                ],
            }
        )

    @extend_schema(
        tags=TAG,
        request=s.ManagerRequestCreateSerializer,
        responses={202: s.RequestSentResponse},
        description=(
            "Ask to manage the profile of the account holding this phone number. The answer is "
            "the same for every valid number; the owner chooses permissions when accepting."
        ),
    )
    def post(self, request):
        reject_header(request)
        data = s.ManagerRequestCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        sent = request_service.create_request(request.user, data.validated_data["phone_number"])
        return Response(
            {"detail": s.REQUEST_SENT, "request": _as_sent_request(sent)},
            status=status.HTTP_202_ACCEPTED,
        )


class RequestAcceptView(APIView):
    @extend_schema(
        tags=TAG,
        request=s.AcceptRequestSerializer,
        responses=s.OwnerAuthorizationSerializer,
        description="Owner only: accept a request and select the manager's permissions.",
    )
    def post(self, request, request_id):
        reject_header(request)
        data = s.AcceptRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        a = request_service.accept_request(
            request.user,
            request_id,
            permission_group=data.validated_data.get("permission_group"),
            permissions=data.validated_data["permissions"],
            confirm_sensitive=data.validated_data["confirm_sensitive"],
            auth_session=_session(request),
        )
        return Response(_as_owner(a))


class RequestDeclineView(APIView):
    @extend_schema(tags=TAG, request=None, responses=s.ReceivedRequestSerializer)
    def post(self, request, request_id):
        reject_header(request)
        declined = request_service.decline_request(request.user, request_id)
        return Response(_as_received_request(declined))


class RequestCancelView(APIView):
    @extend_schema(tags=TAG, request=None, responses=s.SentRequestSerializer)
    def post(self, request, request_id):
        reject_header(request)
        cancelled = request_service.cancel_request(request.user, request_id)
        return Response(_as_sent_request(cancelled))


class RequestHistoryView(APIView):
    """The requester always; the owner once the request reached them."""

    @extend_schema(tags=TAG, responses=s.HistoryEntrySerializer(many=True))
    def get(self, request, request_id):
        reject_header(request)
        row = ManagerRequest.objects.filter(pk=request_id).select_related("profile").first()
        allowed = row is not None and (
            row.requester_id == request.user.pk
            or (row.profile_id is not None and row.profile.owner_id == request.user.pk)
        )
        if not allowed:
            raise NotFound()
        owner_id = row.profile.owner_id if row.profile_id else None
        return Response(_history_rows(row.history.all(), owner_id))


class PermissionCatalogueView(APIView):
    @extend_schema(tags=TAG, responses=s.CatalogueEntrySerializer(many=True))
    def get(self, request):
        reject_header(request)
        return Response(
            [
                {"code": p.code, "name": p.name, "sensitivity": p.sensitivity}
                for p in ManagerPermission.objects.filter(is_active=True)
            ]
        )


class PermissionGroupView(APIView):
    @extend_schema(tags=TAG, responses=s.PermissionGroupSerializer(many=True))
    def get(self, request):
        reject_header(request)
        return Response(
            [
                {
                    "code": g.code,
                    "name": g.name,
                    "permissions": sorted(
                        g.permissions.filter(is_active=True).values_list("code", flat=True)
                    ),
                    # Applying a template grants only these; sensitive ones need confirmation.
                    "granted_on_apply": sorted(
                        g.permissions.filter(is_active=True, sensitivity="NORMAL").values_list(
                            "code", flat=True
                        )
                    ),
                }
                for g in ManagerPermissionGroup.objects.filter(is_active=True)
            ]
        )


class ProfileAccessHistoryView(APIView):
    """The owner's view of manager access and actions (FR-FAM-009). IP addresses are recorded
    but not shown; device/browser and approximate location are shown where available."""

    @extend_schema(tags=TAG, responses=s.AccessHistoryResponse)
    def get(self, request):
        ctx = _owner_context(request)
        accesses = ProfileAccessHistory.objects.filter(profile_id=ctx.profile_id).select_related(
            "manager"
        )[:200]
        actions = ManagerActionLog.objects.filter(profile_id=ctx.profile_id).select_related(
            "manager"
        )[:200]
        return Response(
            {
                "accesses": [
                    {
                        "manager": _display(a.manager),
                        "accessed_at": a.accessed_at,
                        "access_type": a.access_type,
                        "browser": a.browser,
                        "device": a.device,
                        "approximate_location": a.approximate_location,
                    }
                    for a in accesses
                ],
                "actions": [
                    {
                        "manager": _display(a.manager),
                        "action_type": a.action_type,
                        "target_model": a.target_model,
                        "description": a.description,
                        "at": a.created_at,
                    }
                    for a in actions
                ],
            }
        )
