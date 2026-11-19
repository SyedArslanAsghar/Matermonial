"""``/family-management/`` (doc 04 §6, plus ``renew``). Account-scoped: X-Acting-Profile is
refused (doc 04 §24.1 step 2). Owners act on their own personal profile's authorizations;
managers see and answer their own invitations. Anything else gets the same 404."""

from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.profiles.models import MatrimonialProfile

from ..context import ActorContext, reject_header
from ..models import (
    ManagerActionLog,
    ManagerPermission,
    ManagerPermissionGroup,
    ProfileAccessHistory,
    ProfileManagerAuthorization,
)
from ..services import authorizations as service

REASON = r"^[A-Z0-9_]{3,40}$"


def _mask(phone: str) -> str:
    return f"{phone[:4]}{'•' * max(len(phone) - 6, 0)}{phone[-2:]}"


def _granted(a) -> list[str]:
    return sorted(
        a.permission_grants.filter(is_granted=True).values_list("permission__code", flat=True)
    )


def _as_owner(a) -> dict:
    return {
        "id": str(a.pk),
        "manager": {"display": a.manager.first_name or _mask(a.manager.phone_number)},
        "status": a.status,
        "permission_group": a.permission_group.code if a.permission_group_id else None,
        "permissions": _granted(a),
        "expires_at": a.expires_at,
        "invited_at": a.invited_at,
        "accepted_at": a.accepted_at,
        "paused_at": a.paused_at,
        "revoked_at": a.revoked_at,
    }


def _as_manager(a) -> dict:
    return {
        "id": str(a.pk),
        "profile": {"id": str(a.profile_id), "profile_code": a.profile.profile_code},
        "status": a.status,
        "permissions": _granted(a),
        "expires_at": a.expires_at,
        "invited_at": a.invited_at,
    }


def _owner_context(request) -> ActorContext:
    reject_header(request)
    profile = MatrimonialProfile.objects.filter(owner_id=request.user.pk).first()
    if profile is None or profile.profile_status == MatrimonialProfile.Status.CLOSED:
        raise NotFound()
    return ActorContext(
        request.user, profile, True, None, request_id=getattr(request._request, "request_id", None)
    )


class InviteSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=32)
    permission_group = serializers.CharField(max_length=60, required=False, allow_null=True)
    permissions = serializers.ListField(
        child=serializers.CharField(max_length=60), required=False, max_length=60
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.RegexField(REASON, required=False, allow_null=True)


class RenewSerializer(serializers.Serializer):
    expires_at = serializers.DateTimeField(allow_null=True)


class PermissionsSerializer(serializers.Serializer):
    permission_group = serializers.CharField(max_length=60, required=False, allow_null=True)
    permissions = serializers.ListField(child=serializers.CharField(max_length=60), max_length=60)
    confirm_sensitive = serializers.BooleanField(default=False)


class AuthorizationListView(APIView):
    def get(self, request):
        reject_header(request)
        owned = (
            ProfileManagerAuthorization.objects.filter(profile__owner_id=request.user.pk)
            .select_related("manager", "permission_group")
            .order_by("-invited_at")
        )
        managed = (
            ProfileManagerAuthorization.objects.filter(manager_id=request.user.pk)
            .select_related("profile")
            .order_by("-invited_at")
        )
        return Response(
            {
                "as_owner": [_as_owner(a) for a in owned],
                "as_manager": [_as_manager(a) for a in managed],
            }
        )

    def post(self, request):
        ctx = _owner_context(request)
        data = InviteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        a = service.invite(
            ctx,
            phone_number=data.validated_data["phone_number"],
            permission_group=data.validated_data.get("permission_group"),
            permissions=data.validated_data.get("permissions"),
            expires_at=data.validated_data.get("expires_at"),
        )
        return Response(_as_owner(a), status=status.HTTP_201_CREATED)


class ManagerResponseView(APIView):
    accept = True

    def post(self, request, authorization_id):
        reject_header(request)
        operation = service.accept if self.accept else service.reject
        return Response(_as_manager(operation(request.user, authorization_id)))


class OwnerControlView(APIView):
    operation = None

    def post(self, request, authorization_id):
        reject_header(request)
        data = ReasonSerializer(data=request.data)
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
    def post(self, request, authorization_id):
        reject_header(request)
        data = RenewSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        a = service.renew(request.user, authorization_id, data.validated_data["expires_at"])
        return Response(_as_owner(a))


class AuthorizationPermissionsView(APIView):
    def put(self, request, authorization_id):
        reject_header(request)
        data = PermissionsSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        change = service.set_permissions(
            request.user,
            authorization_id,
            permission_group=data.validated_data.get("permission_group"),
            permissions=data.validated_data["permissions"],
            confirm_sensitive=data.validated_data["confirm_sensitive"],
            auth_session=getattr(request._request, "auth_session", None),
        )
        a = ProfileManagerAuthorization.objects.get(pk=authorization_id)
        return Response({**_as_owner(a), "change": change})


class AuthorizationHistoryView(APIView):
    """Owner and the authorization's manager may read its history."""

    def get(self, request, authorization_id):
        reject_header(request)
        a = (
            ProfileManagerAuthorization.objects.filter(pk=authorization_id)
            .select_related("profile")
            .first()
        )
        if a is None or request.user.pk not in (a.profile.owner_id, a.manager_id):
            raise NotFound()
        return Response(
            [
                {
                    "action": h.action,
                    "by_owner": h.performed_by_id == a.profile.owner_id,
                    "by_system": h.performed_by_id is None,
                    "previous": h.previous_values,
                    "new": h.new_values,
                    "reason": h.reason,
                    "at": h.created_at,
                }
                for h in a.history.all()
            ]
        )


class PermissionCatalogueView(APIView):
    def get(self, request):
        reject_header(request)
        return Response(
            [
                {"code": p.code, "name": p.name, "sensitivity": p.sensitivity}
                for p in ManagerPermission.objects.filter(is_active=True)
            ]
        )


class PermissionGroupView(APIView):
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
                        "manager": a.manager.first_name or _mask(a.manager.phone_number),
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
                        "manager": a.manager.first_name or _mask(a.manager.phone_number),
                        "action_type": a.action_type,
                        "target_model": a.target_model,
                        "description": a.description,
                        "at": a.created_at,
                    }
                    for a in actions
                ],
            }
        )
