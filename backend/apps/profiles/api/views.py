"""Owner-only profile endpoints for Phase 3 (doc 04 §3). Views stay thin (CC-R16)."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

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


class ProfileCreateView(APIView):
    def post(self, request):
        profile = service.create_profile(request.user, _rid(request))
        return Response(OwnProfileSerializer(profile).data, status=status.HTTP_201_CREATED)


class OwnProfileView(APIView):
    def get(self, request):
        return Response(OwnProfileSerializer(service.own_profile(request.user)).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = service.update_profile(request.user, serializer.validated_data, _rid(request))
        return Response(OwnProfileSerializer(_reload(profile)).data)


class ProfileCompletionView(APIView):
    def get(self, request, profile_id):
        profile = service.own_profile_by_id(request.user, profile_id)
        return Response(
            {
                "completion_percentage": completion_percentage(profile),
                "missing_required": missing_required(profile),
                "unconfigured_vocabularies": unconfigured_required_vocabularies(),
            }
        )


class SubmitForReviewView(APIView):
    def post(self, request, profile_id):
        profile = service.submit_for_review(request.user, profile_id, _rid(request))
        return Response(OwnProfileSerializer(profile).data)
