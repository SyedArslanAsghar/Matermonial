"""Authentication endpoints (doc 04 §2; TR-01). Views stay thin (CC-R16): services do the work.

Enumeration safety: register, OTP send and (Phase 2d) password forgot always answer the same,
whatever exists. Web login enforces CSRF even though the caller isn't authenticated yet.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.managers import normalize_phone_number
from apps.accounts.models import User
from apps.accounts.services import auth as auth_service
from apps.verification.services.otp import send_code, verify_code
from common.api.auth_errors import AmbiguousCredentials, InvalidCode

from .serializers import (
    AccountSerializer,
    LoginSerializer,
    OtpVerifySerializer,
    PhoneSerializer,
    RegisterSerializer,
)

ACCEPTED = {"detail": "If the details can be used, a verification code has been sent."}


def request_meta(request) -> dict:
    return {
        "login_ip": request.META.get("REMOTE_ADDR"),
        "user_agent": request.META.get("HTTP_USER_AGENT", ""),
    }


def request_id(request):
    return getattr(request._request, "request_id", None)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """GET /auth/csrf/: sets the CSRF cookie and returns the token for web login."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"csrf_token": get_token(request)})


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        data = RegisterSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            auth_service.register(**data.validated_data)
        except DjangoValidationError as exc:  # password policy or phone format
            raise ValidationError({"password": exc.messages}) from None
        return Response(ACCEPTED, status=status.HTTP_202_ACCEPTED)


class OtpSendView(APIView):
    """POST /auth/otp/send/: resend the phone-verification code of an unverified account."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        data = PhoneSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = _user_for_phone(data.validated_data["phone_number"])
        if user is not None and user.is_active and not user.is_phone_verified:
            send_code(phone_number=user.phone_number, purpose="VERIFY_PHONE", user=user)
        return Response(ACCEPTED, status=status.HTTP_202_ACCEPTED)


class OtpVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        data = OtpVerifySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = _user_for_phone(data.validated_data["phone_number"])
        if user is None:
            raise InvalidCode()
        outcome = verify_code(
            phone_number=user.phone_number,
            purpose="VERIFY_PHONE",
            code=data.validated_data["code"],
            user=user,
        )
        if not outcome.ok:
            raise InvalidCode()
        return Response({"phone_verified": True})


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if request.META.get("HTTP_AUTHORIZATION"):
            raise AmbiguousCredentials()
        data = LoginSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        if values["client"] == "web":
            return self._web(request, values)
        user = auth_service.authenticate_credentials(
            phone_number=values["phone_number"],
            password=values["password"],
            request_id=request_id(request),
        )
        meta = {
            **request_meta(request),
            **{k: values.get(k, "") for k in ("device_name", "platform", "app_version")},
        }
        creds = auth_service.login_mobile(user, meta, request_id(request))
        return Response(
            {
                "token_type": "Bearer",
                "access_token": creds.access_token,
                "refresh_token": creds.refresh_token,
                "access_expires_at": creds.access_expires_at,
                "session_id": str(creds.session.id),
                "account": AccountSerializer(user).data,
            }
        )

    def _web(self, request, values):
        # T-AUTH-004: web login requires CSRF even though nobody is authenticated yet.
        SessionAuthentication().enforce_csrf(request)
        user = auth_service.authenticate_credentials(
            phone_number=values["phone_number"],
            password=values["password"],
            request_id=request_id(request),
        )
        auth_service.login_web(request._request, user, request_meta(request), request_id(request))
        return Response({"account": AccountSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        auth_service.logout(request._request, request.auth, request_id(request))
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(AccountSerializer(request.user).data)


def _user_for_phone(phone_number: str) -> User | None:
    try:
        phone = normalize_phone_number(phone_number)
    except DjangoValidationError:
        return None
    return User.objects.filter(phone_number=phone).first()
