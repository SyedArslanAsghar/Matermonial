"""In-app notifications, push devices and per-channel delivery records (DR-2026-11-20-O-7).

- ``InAppNotification`` is created exactly once per outbox event (``source_event_id`` unique),
  so a retried handler never duplicates it. Title and body come from the catalogue
  (``catalogue.py``) and never contain private profile data; ``data`` holds only opaque IDs.
- ``PushDevice`` holds an Expo push token registered by the account's app. Tokens are shown
  to nobody and deactivated when the provider says the device is gone.
- ``NotificationDelivery`` records each push attempt: PENDING → SENT (accepted by the provider;
  not proof of delivery, CC-R54) or FAILED; bounded retries.
"""

import uuid

from django.db import models
from django.db.models import Q


class InAppNotification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="notifications"
    )
    source_event_id = models.UUIDField(unique=True)
    event_type = models.CharField(max_length=60)
    category = models.CharField(max_length=20)
    title = models.CharField(max_length=120)
    body = models.CharField(max_length=300)
    data = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications_in_app"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "-created_at"], name="notif_recipient_recent"),
            models.Index(
                fields=["recipient"], condition=Q(read_at__isnull=True), name="notif_unread"
            ),
        ]


class PushDevice(models.Model):
    class Platform(models.TextChoices):
        IOS = "IOS"
        ANDROID = "ANDROID"
        WEB = "WEB"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="push_devices")
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=7, choices=Platform.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications_push_device"
        indexes = [models.Index(fields=["user", "is_active"], name="push_device_user_active")]
        constraints = [
            models.CheckConstraint(
                condition=Q(is_active=True) | Q(deactivated_at__isnull=False),
                name="push_device_inactive_has_time",
            )
        ]


class NotificationDelivery(models.Model):
    class Channel(models.TextChoices):
        PUSH = "PUSH"

    class Status(models.TextChoices):
        PENDING = "PENDING"
        SENT = "SENT"
        FAILED = "FAILED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        InAppNotification, on_delete=models.PROTECT, related_name="deliveries"
    )
    channel = models.CharField(max_length=5, choices=Channel.choices)
    device = models.ForeignKey(PushDevice, on_delete=models.PROTECT, related_name="deliveries")
    status = models.CharField(max_length=7, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    provider = models.CharField(max_length=20, blank=True)
    provider_reference = models.CharField(max_length=120, blank=True)
    last_error_code = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications_delivery"
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "channel", "device"], name="delivery_once_per_device"
            ),
            models.CheckConstraint(
                condition=~Q(status="SENT") | Q(sent_at__isnull=False),
                name="delivery_sent_has_time",
            ),
        ]
