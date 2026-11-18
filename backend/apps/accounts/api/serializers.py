"""Auth API serializers. Explicit field allowlists only (CC-R44)."""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.accounts.managers import normalize_phone_number
from apps.accounts.models import AuthSession, User


class RegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(max_length=128, write_only=True, trim_whitespace=False)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    def validate_phone_number(self, value):
        try:
            return normalize_phone_number(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from None


class PhoneSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)


class OtpVerifySerializer(PhoneSerializer):
    code = serializers.RegexField(r"^[0-9]{6}$")


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(max_length=128, write_only=True, trim_whitespace=False)
    client = serializers.ChoiceField(choices=["web", "mobile"], default="web")
    device_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    platform = serializers.CharField(max_length=50, required=False, allow_blank=True)
    app_version = serializers.CharField(max_length=50, required=False, allow_blank=True)


class AccountSerializer(serializers.ModelSerializer):
    """The caller's own account. Never password, staff flags or audit fields."""

    class Meta:
        model = User
        fields = [
            "id",
            "phone_number",
            "email",
            "is_phone_verified",
            "is_email_verified",
            "date_joined",
        ]
        read_only_fields = fields


def mask_ip(ip: str | None) -> str | None:
    """doc 06 §22.1: the session list shows a masked IP."""
    if not ip:
        return None
    if ":" in ip:
        return ":".join(ip.split(":")[:3]) + "::"
    parts = ip.split(".")
    return ".".join(parts[:2] + ["x", "x"])


class SessionSerializer(serializers.ModelSerializer):
    ip = serializers.SerializerMethodField()
    current = serializers.SerializerMethodField()

    class Meta:
        model = AuthSession
        fields = [
            "id",
            "client_type",
            "status",
            "created_at",
            "last_seen_at",
            "device_name",
            "platform",
            "app_version",
            "approximate_location",
            "ip",
            "current",
        ]
        read_only_fields = fields

    def get_ip(self, obj):
        return mask_ip(obj.last_ip or obj.login_ip)

    def get_current(self, obj):
        current = self.context.get("current_session")
        return current is not None and current.pk == obj.pk
