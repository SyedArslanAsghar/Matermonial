"""Response schemas for ``/api/v1/auth/`` (KI-40). They describe exactly what the views
return; request bodies use the validating serializers in ``serializers.py``."""

from rest_framework import serializers

from common.api.schema import paginated

from .serializers import AccountSerializer, SessionSerializer


class CsrfResponse(serializers.Serializer):
    csrf_token = serializers.CharField()


class PhoneVerifiedResponse(serializers.Serializer):
    phone_verified = serializers.BooleanField()


class WebLoginResponse(serializers.Serializer):
    account = AccountSerializer()


class MobileLoginResponse(serializers.Serializer):
    token_type = serializers.CharField()
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    access_expires_at = serializers.DateTimeField()
    session_id = serializers.UUIDField()
    account = AccountSerializer()


class RefreshRequest(serializers.Serializer):
    refresh_token = serializers.CharField()


class RefreshResponse(serializers.Serializer):
    token_type = serializers.CharField()
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    access_expires_at = serializers.DateTimeField()


class RevokedResponse(serializers.Serializer):
    revoked = serializers.IntegerField()


class ReauthenticateRequest(serializers.Serializer):
    password = serializers.CharField(write_only=True)


class ReauthenticatedResponse(serializers.Serializer):
    reauthenticated = serializers.BooleanField()


class PasswordResetResponse(serializers.Serializer):
    password_reset = serializers.BooleanField()


class PasswordChangedResponse(serializers.Serializer):
    password_changed = serializers.BooleanField()


SessionPage = paginated("PaginatedSessionList", SessionSerializer)
