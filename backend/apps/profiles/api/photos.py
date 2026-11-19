"""``/profiles/{id}/photos/`` (doc 04 §3), owner only in Phase 3. No URL or storage key is ever
returned; delivery to viewers is Module 10 (Phase 6)."""

from rest_framework import serializers, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.family.context import resolve

from ..models import ProfilePhoto
from ..services import photos as service

FIELDS = (
    "id",
    "photo_type",
    "is_primary",
    "processing_status",
    "rejection_reason",
    "moderation_status",
    "mime_type",
    "size",
    "width",
    "height",
    "uploaded_at",
)


def represent(photo: ProfilePhoto) -> dict:
    return {f: (str(getattr(photo, f)) if f == "id" else getattr(photo, f)) for f in FIELDS}


class UploadSerializer(serializers.Serializer):
    image = serializers.FileField()
    photo_type = serializers.CharField(max_length=40, required=False, allow_null=True)


class PhotoUpdateSerializer(serializers.Serializer):
    is_primary = serializers.BooleanField(required=False)
    photo_type = serializers.CharField(max_length=40, required=False, allow_null=True)

    def validate(self, attrs):
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({k: ["Unknown field."] for k in sorted(unknown)})
        return attrs


class PhotoListView(APIView):
    parser_classes = [MultiPartParser]

    def get(self, request, profile_id):
        ctx = resolve(request, permission="view_profile", path_profile_id=profile_id)
        return Response([represent(p) for p in service.live_photos(ctx.profile_id)])

    def post(self, request, profile_id):
        # Identical 404 / permission errors before any upload work.
        ctx = resolve(request, permission="manage_photos", path_profile_id=profile_id)
        serializer = UploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        photo = service.upload_photo(
            ctx,
            serializer.validated_data["image"],
            serializer.validated_data.get("photo_type"),
        )
        photo.refresh_from_db()
        return Response(represent(photo), status=status.HTTP_202_ACCEPTED)


class PhotoDetailView(APIView):
    def patch(self, request, profile_id, photo_id):
        ctx = resolve(request, permission="manage_photos", path_profile_id=profile_id)
        serializer = PhotoUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        photo = service.update_photo(ctx, photo_id, serializer.validated_data)
        return Response(represent(photo))

    def delete(self, request, profile_id, photo_id):
        ctx = resolve(request, permission="manage_photos", path_profile_id=profile_id)
        service.delete_photo(ctx, photo_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
