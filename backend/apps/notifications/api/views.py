"""``/api/v1/notifications/`` — the account's in-app notifications and push devices.
Account-scoped (``X-Acting-Profile`` refused); every query is filtered by the caller."""

import re

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from common.api.pagination import StandardPagination

from .. import services
from ..models import InAppNotification, PushDevice

EXPO_TOKEN = re.compile(r"^Expo(nent)?PushToken\[[A-Za-z0-9_\-]{10,200}\]$")
TAG = ["notifications"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InAppNotification
        fields = ["id", "event_type", "category", "title", "body", "data", "read_at", "created_at"]


class DeviceSerializer(serializers.Serializer):
    token = serializers.RegexField(EXPO_TOKEN, help_text="Expo push token from the app.")
    platform = serializers.ChoiceField(PushDevice.Platform.choices)


class DeviceTokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)


class DeviceResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    platform = serializers.CharField()
    is_active = serializers.BooleanField()


class CountSerializer(serializers.Serializer):
    updated = serializers.IntegerField()


class NotificationListView(APIView):
    @extend_schema(tags=TAG, responses=NotificationSerializer(many=True))
    def get(self, request):
        query = InAppNotification.objects.filter(recipient=request.user)
        if request.query_params.get("unread") == "true":
            query = query.filter(read_at__isnull=True)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(query.order_by("-created_at"), request, view=self)
        return paginator.get_paginated_response(NotificationSerializer(page, many=True).data)


class NotificationReadView(APIView):
    @extend_schema(tags=TAG, request=None, responses=NotificationSerializer)
    def post(self, request, notification_id):
        notification = InAppNotification.objects.filter(
            pk=notification_id, recipient=request.user
        ).first()
        if notification is None:
            raise NotFound()
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return Response(NotificationSerializer(notification).data)


class NotificationReadAllView(APIView):
    @extend_schema(tags=TAG, request=None, responses=CountSerializer)
    def post(self, request):
        updated = InAppNotification.objects.filter(
            recipient=request.user, read_at__isnull=True
        ).update(read_at=timezone.now())
        return Response({"updated": updated})


class DeviceRegisterView(APIView):
    @extend_schema(tags=TAG, request=DeviceSerializer, responses={201: DeviceResponseSerializer})
    def post(self, request):
        data = DeviceSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        device = services.register_device(
            request.user, data.validated_data["token"], data.validated_data["platform"]
        )
        return Response(
            {"id": str(device.pk), "platform": device.platform, "is_active": device.is_active},
            status=status.HTTP_201_CREATED,
        )


class DeviceUnregisterView(APIView):
    @extend_schema(tags=TAG, request=DeviceTokenSerializer, responses=CountSerializer)
    def post(self, request):
        data = DeviceTokenSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        removed = services.unregister_device(request.user, data.validated_data["token"])
        return Response({"updated": int(removed)})
