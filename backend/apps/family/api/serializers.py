"""Request validation and response schemas for ``/family-management/`` (KI-40).

Input serializers validate requests; output serializers document exactly what the views return
(the views build the bodies; these describe them for OpenAPI and are checked by the schema
tests)."""

from rest_framework import serializers

REASON = r"^[A-Z0-9_]{3,40}$"
STATUS_AUTH = ["PENDING", "ACTIVE", "PAUSED", "EXPIRED", "REVOKED", "REJECTED"]
STATUS_INV = ["PENDING", "ACCEPTED", "DECLINED", "CANCELLED", "EXPIRED"]

INVITATION_SENT = (
    "If this number belongs to an account that can be invited, its holder will receive the "
    "invitation."
)
REQUEST_SENT = (
    "If this number belongs to a profile owner who can receive requests, they will be asked "
    "to accept."
)


# --- Input ----------------------------------------------------------------------------------


class _Selection(serializers.Serializer):
    """The owner's permission checkboxes: a template and/or individual codes."""

    permission_group = serializers.CharField(max_length=60, required=False, allow_null=True)
    permissions = serializers.ListField(
        child=serializers.CharField(max_length=60), required=False, default=list, max_length=60
    )
    confirm_sensitive = serializers.BooleanField(
        default=False, help_text="Required (with a recent owner step-up) to grant Sensitive ones."
    )


class InviteSerializer(_Selection):
    phone_number = serializers.CharField(max_length=32)
    expires_at = serializers.DateTimeField(
        required=False, allow_null=True, help_text="Optional expiry of the authorization."
    )


class PermissionsSerializer(_Selection):
    permissions = serializers.ListField(child=serializers.CharField(max_length=60), max_length=60)


class AcceptRequestSerializer(_Selection):
    pass


class ManagerRequestCreateSerializer(serializers.Serializer):
    phone_number = serializers.CharField(
        max_length=32, help_text="The phone number of the profile owner."
    )


class ReasonSerializer(serializers.Serializer):
    reason = serializers.RegexField(REASON, required=False, allow_null=True)


class RenewSerializer(serializers.Serializer):
    expires_at = serializers.DateTimeField(allow_null=True)


# --- Output ---------------------------------------------------------------------------------


class _Display(serializers.Serializer):
    display = serializers.CharField()


class _ProfileRef(serializers.Serializer):
    id = serializers.UUIDField()
    profile_code = serializers.CharField()


class OwnerAuthorizationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    manager = _Display()
    status = serializers.ChoiceField(STATUS_AUTH)
    permission_group = serializers.CharField(allow_null=True)
    permissions = serializers.ListField(child=serializers.CharField())
    expires_at = serializers.DateTimeField(allow_null=True)
    invited_at = serializers.DateTimeField()
    accepted_at = serializers.DateTimeField(allow_null=True)
    paused_at = serializers.DateTimeField(allow_null=True)
    revoked_at = serializers.DateTimeField(allow_null=True)


class ManagedAuthorizationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    profile = _ProfileRef()
    status = serializers.ChoiceField(STATUS_AUTH)
    permissions = serializers.ListField(child=serializers.CharField())
    expires_at = serializers.DateTimeField(allow_null=True)
    invited_at = serializers.DateTimeField()
    invitation_expires_at = serializers.DateTimeField(allow_null=True)


class InvitationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    phone_hint = serializers.CharField()
    status = serializers.ChoiceField(STATUS_INV)
    permission_group = serializers.CharField(allow_null=True)
    requested_permissions = serializers.ListField(child=serializers.CharField())
    requested_expires_at = serializers.DateTimeField(allow_null=True)
    invited_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField()
    responded_at = serializers.DateTimeField(allow_null=True)
    cancelled_at = serializers.DateTimeField(allow_null=True)
    expired_at = serializers.DateTimeField(allow_null=True)
    authorization_id = serializers.UUIDField(allow_null=True)


class InvitationSentResponse(serializers.Serializer):
    detail = serializers.CharField()
    invitation = InvitationSerializer()


class AuthorizationListResponse(serializers.Serializer):
    as_owner = OwnerAuthorizationSerializer(many=True)
    invitations = InvitationSerializer(many=True)
    as_manager = ManagedAuthorizationSerializer(many=True)


class _Change(serializers.Serializer):
    granted = serializers.ListField(child=serializers.CharField())
    revoked = serializers.ListField(child=serializers.CharField())


class PermissionsChangeResponse(OwnerAuthorizationSerializer):
    change = _Change()


class HistoryEntrySerializer(serializers.Serializer):
    action = serializers.CharField()
    by_owner = serializers.BooleanField()
    by_system = serializers.BooleanField()
    previous = serializers.DictField()
    new = serializers.DictField()
    reason = serializers.CharField(allow_null=True)
    at = serializers.DateTimeField()


class SentRequestSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    phone_hint = serializers.CharField()
    status = serializers.ChoiceField(STATUS_INV)
    requested_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField()
    responded_at = serializers.DateTimeField(allow_null=True)
    cancelled_at = serializers.DateTimeField(allow_null=True)
    expired_at = serializers.DateTimeField(allow_null=True)
    profile_code = serializers.CharField(allow_null=True)
    authorization_id = serializers.UUIDField(allow_null=True)


class ReceivedRequestSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    requester = _Display()
    status = serializers.ChoiceField(STATUS_INV)
    requested_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField()
    responded_at = serializers.DateTimeField(allow_null=True)
    authorization_id = serializers.UUIDField(allow_null=True)


class RequestSentResponse(serializers.Serializer):
    detail = serializers.CharField()
    request = SentRequestSerializer()


class RequestListResponse(serializers.Serializer):
    sent = SentRequestSerializer(many=True)
    received = ReceivedRequestSerializer(many=True)


class CatalogueEntrySerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    sensitivity = serializers.ChoiceField(["NORMAL", "SENSITIVE", "OWNER_ONLY"])


class PermissionGroupSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    permissions = serializers.ListField(child=serializers.CharField())
    granted_on_apply = serializers.ListField(child=serializers.CharField())


class _Access(serializers.Serializer):
    manager = serializers.CharField()
    accessed_at = serializers.DateTimeField()
    access_type = serializers.CharField()
    browser = serializers.CharField(allow_blank=True)
    device = serializers.CharField(allow_blank=True)
    approximate_location = serializers.CharField(allow_blank=True, allow_null=True)


class _Action(serializers.Serializer):
    manager = serializers.CharField()
    action_type = serializers.CharField()
    target_model = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    at = serializers.DateTimeField()


class AccessHistoryResponse(serializers.Serializer):
    accesses = _Access(many=True)
    actions = _Action(many=True)
