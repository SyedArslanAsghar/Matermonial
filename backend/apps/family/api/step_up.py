"""``POST /api/v1/profiles/step-up/`` (TR-16): a manager proves their own authenticator for one
Sensitive action on the profile selected with ``X-Acting-Profile``. Returns a single-use
verification valid for at most 5 minutes; send it as ``X-Step-Up-Verification`` with the
Sensitive request."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..context import resolve
from ..services import step_up


class StepUpRequestSerializer(serializers.Serializer):
    action = serializers.CharField(
        max_length=60,
        help_text="The Sensitive permission to exercise, e.g. manage_privacy_settings.",
    )
    code = serializers.CharField(
        max_length=10, help_text="Current code from your authenticator app."
    )


class StepUpResponseSerializer(serializers.Serializer):
    verification_id = serializers.UUIDField()
    action = serializers.CharField()
    expires_at = serializers.DateTimeField()


class StepUpView(APIView):
    @extend_schema(
        tags=["profiles"],
        request=StepUpRequestSerializer,
        responses={201: StepUpResponseSerializer},
        parameters=[
            OpenApiParameter(
                "X-Acting-Profile",
                str,
                OpenApiParameter.HEADER,
                required=True,
                description="The managed profile (UUID).",
            )
        ],
    )
    def post(self, request):
        ctx = resolve(request, access_type="step_up")
        data = StepUpRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        verification = step_up.create_verification(
            ctx, data.validated_data["action"], data.validated_data["code"]
        )
        return Response(
            {
                "verification_id": str(verification.pk),
                "action": verification.action,
                "expires_at": verification.expires_at,
            },
            status=status.HTTP_201_CREATED,
        )
