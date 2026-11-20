"""Notification delivery (FR-NOT; DR-2026-11-20-O-7).

Channels:
- **In-app**: every catalogued outbox NOTIFICATION event becomes one ``InAppNotification`` for
  its recipient (idempotent per outbox event).
- **Push**: one ``NotificationDelivery`` per active device, sent by a Celery task after commit
  with bounded retries (``NOTIFICATION_PUSH_MAX_ATTEMPTS``). A permanent provider error fails
  the delivery; ``device_not_registered`` also deactivates the device.
- **SMS** carries one-time codes (phone OTP, admin enrollment codes) sent directly by their own
  services; **email** is available through ``common.providers.send_email`` for later features.
  Neither is used for these notices, so no notice is ever sent by SMS or email without a
  decision.

The outbox (TR-11) remains the only way notices start: handlers run in the outbox's handler
transaction, so a notice exists exactly when the business change committed.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import SubjectPseudonym, User
from common.db.locking import LockLevel, lock_rows_for_share, lock_rows_for_update
from common.providers import ProviderDisabledError, ProviderError, get_push_provider

from .catalogue import CATALOGUE, GENERIC, SAFE_DATA_KEYS
from .models import InAppNotification, NotificationDelivery, PushDevice

logger = logging.getLogger(__name__)
HANDLER_LEVELS = (LockLevel.ACCOUNT, LockLevel.DOMAIN, LockLevel.INSERT)


def recipient_for(pseudonym) -> User | None:
    if pseudonym is None:
        return None
    subject_id = (
        SubjectPseudonym.objects.filter(pseudonym=pseudonym, subject_type="ACCOUNT")
        .values_list("subject_id", flat=True)
        .first()
    )
    return User.objects.filter(pk=subject_id, is_active=True).first() if subject_id else None


def handle_event(event, payload: dict) -> InAppNotification | None:
    """Outbox handler body (inside the handler transaction). Idempotent."""
    user = recipient_for(event.recipient_pseudonym)
    if user is None:
        return None  # unknown, unlinked or inactive recipient: nothing to deliver
    lock_rows_for_share(User.objects.filter(pk=user.pk), LockLevel.ACCOUNT)
    devices = lock_rows_for_share(
        PushDevice.objects.filter(user=user, is_active=True), LockLevel.DOMAIN
    )
    title, body = CATALOGUE.get(event.event_type, GENERIC)
    notification, _ = InAppNotification.objects.get_or_create(
        source_event_id=event.id,
        defaults={
            "recipient": user,
            "event_type": event.event_type,
            "category": event.category,
            "title": title,
            "body": body,
            "data": {k: v for k, v in payload.items() if k in SAFE_DATA_KEYS},
        },
    )
    pending = []
    for device_id in devices:
        delivery, created = NotificationDelivery.objects.get_or_create(
            notification=notification,
            channel=NotificationDelivery.Channel.PUSH,
            device_id=device_id,
        )
        if created:
            pending.append(str(delivery.pk))
    if pending:
        transaction.on_commit(lambda: _enqueue(pending))
    return notification


def _enqueue(delivery_ids: list[str]) -> None:
    from .tasks import deliver_push

    for delivery_id in delivery_ids:
        deliver_push.delay(delivery_id)


def deliver(delivery_id) -> str:
    """Send one push delivery. Returns sent | failed | retry | skipped. Idempotent."""
    from common.db.locking import lock_plan

    with transaction.atomic(), lock_plan("notifications.deliver", [LockLevel.DOMAIN]):
        rows = lock_rows_for_update(
            NotificationDelivery.objects.filter(pk=delivery_id, status="PENDING"),
            LockLevel.DOMAIN,
        )
        if not rows:
            return "skipped"
        delivery = rows[0]
        device = PushDevice.objects.get(pk=delivery.device_id)
        notification = InAppNotification.objects.get(pk=delivery.notification_id)
        now = timezone.now()
        delivery.attempts += 1
        if not device.is_active:
            delivery.status, delivery.last_error_code = "FAILED", "device_inactive"
            delivery.save()
            return "failed"
        try:
            result = get_push_provider().send_push(
                device_token=device.token,
                title=notification.title,
                body=notification.body,
                data={"notification_id": str(notification.pk), **notification.data},
            )
        except ProviderDisabledError:
            delivery.status, delivery.last_error_code = "FAILED", "provider_disabled"
            delivery.save()
            return "failed"
        except ProviderError as exc:
            delivery.last_error_code = exc.code[:40]
            if exc.code == "device_not_registered":
                PushDevice.objects.filter(pk=device.pk).update(is_active=False, deactivated_at=now)
                delivery.status = "FAILED"
            elif exc.retryable and delivery.attempts < settings.NOTIFICATION_PUSH_MAX_ATTEMPTS:
                delivery.save()  # stays PENDING for the next attempt
                return "retry"
            else:
                delivery.status = "FAILED"
            delivery.save()
            logger.warning("Push delivery failed", extra={"code": delivery.last_error_code})
            return "failed"
        delivery.status, delivery.sent_at = "SENT", now
        delivery.provider, delivery.provider_reference = result.provider, result.reference[:120]
        delivery.last_error_code = ""
        delivery.save()
        return "sent"


def register_device(user: User, token: str, platform: str) -> PushDevice:
    """Register (or move to this account) a device token. A token belongs to one device, so a
    new sign-in on that device takes it over."""
    from common.db.locking import lock_plan

    with (
        transaction.atomic(),
        lock_plan("notifications.device", [LockLevel.ACCOUNT, LockLevel.DOMAIN]),
    ):
        lock_rows_for_share(User.objects.filter(pk=user.pk), LockLevel.ACCOUNT)
        existing = lock_rows_for_update(PushDevice.objects.filter(token=token), LockLevel.DOMAIN)
        if existing:
            device = existing[0]
            device.user, device.platform, device.is_active, device.deactivated_at = (
                user,
                platform,
                True,
                None,
            )
            device.save()
            return device
        return PushDevice.objects.create(user=user, token=token, platform=platform)


def unregister_device(user: User, token: str) -> bool:
    return bool(
        PushDevice.objects.filter(user=user, token=token, is_active=True).update(
            is_active=False, deactivated_at=timezone.now()
        )
    )
