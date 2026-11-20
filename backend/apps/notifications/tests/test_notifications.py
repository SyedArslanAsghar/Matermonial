"""In-app notifications and push delivery from outbox events (DR-2026-11-20-O-7)."""

from unittest import mock

import pytest
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.services.pseudonyms import pseudonym_for
from apps.notifications import services
from apps.notifications.catalogue import CATALOGUE
from apps.notifications.models import InAppNotification, NotificationDelivery, PushDevice
from common.events.models import OutboxEvent
from common.events.services import emit, process_due
from common.providers import MockPushProvider, ProviderError

pytestmark = pytest.mark.django_db
TOKEN = "ExponentPushToken[abcdefghijklmnop]"


def make_user(n):
    return User.objects.create_user(phone_number=f"+92300700{n:04d}", password="Pw-Long-enough-9")


def client_for(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


def notify(user, event_type="family.permissions_changed", **payload):
    from django.db import transaction

    with transaction.atomic():
        emit(
            event_type,
            event_class="NOTIFICATION",
            category="ACCOUNT",
            aggregate_type="Test",
            recipient_pseudonym=pseudonym_for("ACCOUNT", user.pk),
            payload={"authorization_id": "a1", "secret_name": "Private Person", **payload},
            dedupe_identity=f"test:{event_type}:{user.pk}:{payload}",
        )


def run_outbox():
    with TestCase.captureOnCommitCallbacks(execute=True):
        return process_due()


def test_every_catalogued_event_has_a_handler():
    from common.events.services import HANDLERS

    assert set(CATALOGUE) <= set(HANDLERS)


def test_outbox_event_becomes_one_in_app_notification_without_private_data():
    user = make_user(1)
    notify(user)
    assert run_outbox() == {"DONE": 1}
    notification = InAppNotification.objects.get()
    assert notification.recipient == user and notification.title == "Permissions changed"
    assert notification.data == {"authorization_id": "a1"}  # only opaque ids are copied
    assert "Private" not in notification.body
    # Handler re-run (e.g. a retried event) never duplicates it.
    from django.db import transaction

    from common.db.locking import lock_plan

    event = OutboxEvent.objects.get()
    with transaction.atomic(), lock_plan("test", services.HANDLER_LEVELS):
        services.handle_event(event, {"authorization_id": "a1"})
    assert InAppNotification.objects.count() == 1


def test_push_goes_to_each_active_device_once():
    user = make_user(2)
    services.register_device(user, TOKEN, "ANDROID")
    services.register_device(user, "ExponentPushToken[zzzzzzzzzzzzzzzz]", "IOS")
    PushDevice.objects.filter(token__contains="zzz").update(
        is_active=False, deactivated_at="2026-01-01T00:00Z"
    )
    notify(user)
    run_outbox()
    delivery = NotificationDelivery.objects.get()
    assert delivery.status == "SENT" and delivery.provider == "mock" and delivery.sent_at
    assert [m["device_token"] for m in MockPushProvider.sent] == [TOKEN]
    assert services.deliver(delivery.pk) == "skipped"  # idempotent


def test_retryable_push_failures_are_bounded_then_failed(settings):
    settings.NOTIFICATION_PUSH_MAX_ATTEMPTS = 3
    user = make_user(3)
    services.register_device(user, TOKEN, "ANDROID")
    error = ProviderError("http_503", retryable=True)
    with mock.patch.object(MockPushProvider, "send_push", side_effect=error):
        notify(user)
        run_outbox()
    delivery = NotificationDelivery.objects.get()
    assert delivery.status == "FAILED" and delivery.attempts == 3
    assert delivery.last_error_code == "http_503"


def test_device_not_registered_deactivates_the_device():
    user = make_user(4)
    device = services.register_device(user, TOKEN, "ANDROID")
    error = ProviderError("device_not_registered", retryable=False)
    with mock.patch.object(MockPushProvider, "send_push", side_effect=error):
        notify(user)
        run_outbox()
    device.refresh_from_db()
    assert not device.is_active and device.deactivated_at
    assert NotificationDelivery.objects.get().status == "FAILED"


def test_disabled_push_provider_fails_without_retry(settings):
    settings.PUSH_PROVIDER = "disabled"
    user = make_user(5)
    services.register_device(user, TOKEN, "ANDROID")
    notify(user)
    run_outbox()
    delivery = NotificationDelivery.objects.get()
    assert delivery.status == "FAILED" and delivery.last_error_code == "provider_disabled"
    assert InAppNotification.objects.count() == 1  # in-app still delivered


def test_unknown_recipient_is_a_completed_event_with_nothing_delivered():
    user = make_user(6)
    notify(user)
    User.objects.filter(pk=user.pk).update(is_active=False)
    assert run_outbox() == {"DONE": 1}
    assert not InAppNotification.objects.exists()


class TestApi:
    def test_list_read_and_read_all_are_scoped_to_the_caller(self):
        user, other = make_user(7), make_user(8)
        notify(user)
        notify(user, "family.authorization_revoked")
        notify(other)
        run_outbox()
        client = client_for(user)
        body = client.get("/api/v1/notifications/").json()
        items = body["data"] if "data" in body else body["results"]
        assert len(items) == 2
        theirs = InAppNotification.objects.get(recipient=other)
        assert client.post(f"/api/v1/notifications/{theirs.pk}/read/").status_code == 404
        mine = InAppNotification.objects.filter(recipient=user).first()
        assert client.post(f"/api/v1/notifications/{mine.pk}/read/").json()["read_at"]
        assert client.post("/api/v1/notifications/read-all/").json() == {"updated": 1}
        assert InAppNotification.objects.get(pk=theirs.pk).read_at is None

    def test_device_registration_validates_and_moves_tokens(self):
        user, other = make_user(9), make_user(10)
        bad = client_for(user).post(
            "/api/v1/notifications/devices/", {"token": "nope", "platform": "IOS"}, format="json"
        )
        assert bad.status_code == 400
        ok = client_for(user).post(
            "/api/v1/notifications/devices/", {"token": TOKEN, "platform": "IOS"}, format="json"
        )
        assert ok.status_code == 201
        client_for(other).post(
            "/api/v1/notifications/devices/", {"token": TOKEN, "platform": "IOS"}, format="json"
        )
        assert PushDevice.objects.get(token=TOKEN).user == other  # one device, one account
        assert client_for(user).post(
            "/api/v1/notifications/devices/unregister/", {"token": TOKEN}, format="json"
        ).json() == {"updated": 0}
        assert client_for(other).post(
            "/api/v1/notifications/devices/unregister/", {"token": TOKEN}, format="json"
        ).json() == {"updated": 1}

    def test_acting_profile_header_is_refused(self):
        user = make_user(11)
        client = client_for(user)
        client.credentials(HTTP_X_ACTING_PROFILE="6f1d6a1e-0000-4000-8000-0000000000a1")
        assert client.get("/api/v1/notifications/").status_code == 400
