"""Profile endpoints (doc 04 §3). Profile-scoped endpoints resolve an ``ActorContext`` on every
request (owner, or a manager with the endpoint's permission; doc 04 §24.1). Views stay thin."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.family.context import reject_header, resolve

from ..services import profiles as service
from ..services.completion import (
    completion_percentage,
    missing_required,
    unconfigured_required_vocabularies,
)
from .serializers import OwnProfileSerializer, ProfileUpdateSerializer


def _rid(request):
    return getattr(request._request, "request_id", None)


def _reload(profile):
    return type(profile).objects.get(pk=profile.pk)


def represent(profile, ctx=None):
    # The full DOB is shown to the owner, and to a manager only when they may edit basic info.
    show_dob = ctx is None or ctx.is_owner or ctx.has("edit_basic_info")
    return OwnProfileSerializer(profile, context={"show_dob": show_dob}).data


class ProfileCreateView(APIView):
    def post(self, request):
        reject_header(request)  # creating one's own profile is account-scoped
        profile = service.create_profile(request.user, _rid(request))
        return Response(represent(profile), status=status.HTTP_201_CREATED)


class OwnProfileView(APIView):
    """``/profiles/me/``: the caller's own profile, or the one selected with X-Acting-Profile."""

    def get(self, request):
        ctx = resolve(request, permission="view_profile")
        return Response(represent(ctx.represented_profile, ctx))

    def patch(self, request):
        ctx = resolve(request, permission="view_profile")
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = service.update_profile(ctx, serializer.validated_data, _rid(request))
        return Response(represent(_reload(profile), ctx))


class ProfileCompletionView(APIView):
    def get(self, request, profile_id):
        ctx = resolve(request, permission="view_profile", path_profile_id=profile_id)
        profile = ctx.represented_profile
        return Response(
            {
                "completion_percentage": completion_percentage(profile),
                "missing_required": missing_required(profile),
                "unconfigured_vocabularies": unconfigured_required_vocabularies(),
            }
        )


class SubmitForReviewView(APIView):
    def post(self, request, profile_id):
        ctx = resolve(request, path_profile_id=profile_id, any_of=service.EDIT_PERMISSIONS)
        profile = service.submit_for_review(ctx, _rid(request))
        return Response(represent(profile, ctx))
