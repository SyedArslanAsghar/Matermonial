"""``/api/v1/auth/mfa/`` — the account authenticator (TOTP) used for manager step-up (TR-16).

Account-scoped (``X-Acting-Profile`` is refused by the middleware). Setting up or removing it
needs a recent password step-up (``POST /api/v1/auth/reauthenticate/``)."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.services import mfa


class MfaStatusSerializer(serializers.Serializer):
    enrolled = serializers.BooleanField()


class MfaEnrollmentSerializer(serializers.Serializer):
    secret = serializers.CharField(help_text="Base32 secret, shown once to the account holder.")
    otpauth_uri = serializers.CharField(help_text="otpauth:// URI for a QR code, shown once.")


class MfaCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=10)


def _session(request):
    return getattr(request._request, "auth_session", None)


def _request_id(request):
    return getattr(request._request, "request_id", None)


class MfaStatusView(APIView):
    @extend_schema(tags=["auth"], responses=MfaStatusSerializer)
    def get(self, request):
        return Response({"enrolled": mfa.is_enrolled(request.user)})


class MfaEnrollView(APIView):
    @extend_schema(tags=["auth"], request=None, responses=MfaEnrollmentSerializer)
    def post(self, request):
        enrollment = mfa.begin_enrollment(request.user, _session(request))
        response = Response(
            {"secret": enrollment.secret_base32, "otpauth_uri": enrollment.otpauth_uri}
        )
        response["Cache-Control"] = "no-store"
        return response


class MfaConfirmView(APIView):
    @extend_schema(tags=["auth"], request=MfaCodeSerializer, responses=MfaStatusSerializer)
    def post(self, request):
        data = MfaCodeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        mfa.confirm_enrollment(request.user, data.validated_data["code"], _request_id(request))
        return Response({"enrolled": True})


class MfaRemoveView(APIView):
    @extend_schema(tags=["auth"], request=MfaCodeSerializer, responses=MfaStatusSerializer)
    def post(self, request):
        data = MfaCodeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        mfa.remove(
            request.user, data.validated_data["code"], _session(request), _request_id(request)
        )
        return Response({"enrolled": False})
