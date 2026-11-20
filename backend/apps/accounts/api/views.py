"""Authentication endpoints (doc 04 §2; TR-01). Views stay thin (CC-R16): services do the work.

Enumeration safety: register, OTP send and (Phase 2d) password forgot always answer the same,
whatever exists. Web login enforces CSRF even though the caller isn't authenticated yet.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiResponse, PolymorphicProxySerializer, extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.managers import normalize_phone_number
from apps.accounts.models import AuthSession, User
from apps.accounts.services import auth as auth_service
from apps.accounts.services import passwords
from apps.accounts.services.refresh import refresh as refresh_tokens
from apps.verification.services.otp import send_code, verify_code
from common.api.auth_errors import AmbiguousCredentials, InvalidCode, InvalidPassword
from common.api.pagination import StandardPagination
from common.api.schema import PAGE_PARAMETERS, DetailSerializer
from common.api.throttles import (
    LoginIpThrottle,
    LoginPhoneIpThrottle,
    OtpIpThrottle,
    PasswordIpThrottle,
    RefreshSessionThrottle,
    RegisterIpThrottle,
)

from . import schema_serializers as docs
from .serializers import (
    AccountSerializer,
    LoginSerializer,
    OtpVerifySerializer,
    PasswordChangeSerializer,
    PasswordResetSerializer,
    PhoneSerializer,
    RegisterSerializer,
    SessionSerializer,
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

    @extend_schema(tags=["auth"], responses=docs.CsrfResponse)
    def get(self, request):
        return Response({"csrf_token": get_token(request)})


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [RegisterIpThrottle]

    @extend_schema(tags=["auth"], request=RegisterSerializer, responses={202: DetailSerializer})
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
    throttle_classes = [OtpIpThrottle]

    @extend_schema(tags=["auth"], request=PhoneSerializer, responses={202: DetailSerializer})
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
    throttle_classes = [OtpIpThrottle]

    @extend_schema(tags=["auth"], request=OtpVerifySerializer, responses=docs.PhoneVerifiedResponse)
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
    throttle_classes = [LoginPhoneIpThrottle, LoginIpThrottle]

    @extend_schema(
        tags=["auth"],
        request=LoginSerializer,
        responses=PolymorphicProxySerializer(
            component_name="LoginResponse",
            serializers=[docs.WebLoginResponse, docs.MobileLoginResponse],
            resource_type_field_name=None,
        ),
        description="client=web sets the session cookie; client=mobile returns tokens.",
    )
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

    @extend_schema(
        tags=["auth"], request=None, responses={204: OpenApiResponse(description="Logged out")}
    )
    def post(self, request):
        auth_service.logout(request._request, request.auth, request_id(request))
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["auth"], responses=AccountSerializer)
    def get(self, request):
        return Response(AccountSerializer(request.user).data)


def _user_for_phone(phone_number: str) -> User | None:
    try:
        phone = normalize_phone_number(phone_number)
    except DjangoValidationError:
        return None
    return User.objects.filter(phone_number=phone).first()


class RefreshView(APIView):
    """POST /auth/token/refresh/ (mobile): rotation with a 15 s idempotent grace."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [RefreshSessionThrottle]

    @extend_schema(tags=["auth"], request=docs.RefreshRequest, responses=docs.RefreshResponse)
    def post(self, request):
        token = request.data.get("refresh_token")
        if not isinstance(token, str):
            raise ValidationError({"refresh_token": ["This field is required."]})
        result = refresh_tokens(token, request_id(request))
        return Response(
            {
                "token_type": "Bearer",
                "access_token": result.access_token,
                "refresh_token": result.refresh_token,
                "access_expires_at": result.access_expires_at,
            }
        )


class SessionListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["auth"], parameters=PAGE_PARAMETERS, responses=docs.SessionPage)
    def get(self, request):
        sessions = AuthSession.objects.filter(user=request.user).order_by("-created_at", "-id")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(sessions, request, view=self)
        data = SessionSerializer(page, many=True, context={"current_session": request.auth}).data
        return paginator.get_paginated_response(data)


class SessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["auth"], responses={204: OpenApiResponse(description="Session revoked")})
    def delete(self, request, session_id):
        if not auth_service.revoke_one(request.user, session_id, request_id(request)):
            from rest_framework.exceptions import NotFound

            raise NotFound()  # identical for missing and other people's sessions
        if request.auth is not None and str(request.auth.pk) == str(session_id):
            if request.auth.client_type == "WEB":
                from django.contrib.auth import logout as django_logout

                django_logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RevokeOthersView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["auth"], request=None, responses=docs.RevokedResponse)
    def post(self, request):
        count = auth_service.revoke_others(request.user, request.auth, request_id(request))
        return Response({"revoked": count})


class ReauthenticateView(APIView):
    """POST /auth/reauthenticate/: password step-up (OD-04c OPEN: no OTP yet)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["auth"], request=docs.ReauthenticateRequest, responses=docs.ReauthenticatedResponse
    )
    def post(self, request):
        password = request.data.get("password")
        if not isinstance(password, str) or not password:
            raise ValidationError({"password": ["This field is required."]})
        if not auth_service.reauthenticate(
            request.user, request.auth, password, request_id(request)
        ):
            raise InvalidPassword()
        return Response({"reauthenticated": True})


class PasswordForgotView(APIView):
    """POST /auth/password/forgot/: always 202 (no account enumeration)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordIpThrottle]

    @extend_schema(tags=["auth"], request=PhoneSerializer, responses={202: DetailSerializer})
    def post(self, request):
        data = PhoneSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        passwords.forgot(data.validated_data["phone_number"], request_id(request))
        return Response(ACCEPTED, status=status.HTTP_202_ACCEPTED)


class PasswordResetView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordIpThrottle]

    @extend_schema(
        tags=["auth"], request=PasswordResetSerializer, responses=docs.PasswordResetResponse
    )
    def post(self, request):
        data = PasswordResetSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        try:
            ok = passwords.reset(
                values["phone_number"], values["code"], values["new_password"], request_id(request)
            )
        except DjangoValidationError as exc:
            raise ValidationError({"new_password": exc.messages}) from None
        if not ok:
            raise InvalidCode()
        return Response({"password_reset": True})


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["auth"], request=PasswordChangeSerializer, responses=docs.PasswordChangedResponse
    )
    def post(self, request):
        data = PasswordChangeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            ok = passwords.change(
                request._request,
                request.user,
                request.auth,
                data.validated_data["current_password"],
                data.validated_data["new_password"],
                request_id(request),
            )
        except DjangoValidationError as exc:
            raise ValidationError({"new_password": exc.messages}) from None
        if not ok:
            raise InvalidPassword()
        return Response({"password_changed": True})
