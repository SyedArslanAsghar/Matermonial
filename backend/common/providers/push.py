"""Push adapters. Supported: ``mock``, ``console`` (local only), ``expo``, ``disabled``.

Expo Push API (matches the approved React Native/Expo app): set ``PUSH_PROVIDER=expo`` and,
when the Expo project uses enhanced push security, ``EXPO_ACCESS_TOKEN``. Device tokens are
Expo push tokens (``ExponentPushToken[...]``) registered by the app. An Expo ticket error
``DeviceNotRegistered`` is permanent: the device is deactivated."""

import logging
import sys
import uuid
from typing import Protocol

from django.conf import settings

from .base import DisabledProvider, DispatchResult, ProviderError, require_local, unknown
from .http import post

logger = logging.getLogger(__name__)
SUPPORTED = {"mock", "console", "expo", "disabled"}


class PushProvider(Protocol):
    def send_push(
        self, *, device_token: str, title: str, body: str, data: dict | None = None
    ) -> DispatchResult: ...


class MockPushProvider:
    name = "mock"
    sent: list[dict] = []

    def send_push(self, *, device_token: str, title: str, body: str, data=None) -> DispatchResult:
        reference = uuid.uuid4().hex
        self.sent.append(
            {
                "device_token": device_token,
                "title": title,
                "body": body,
                "data": data or {},
                "reference": reference,
            }
        )
        logger.info("Mock push accepted", extra={"provider": self.name, "reference": reference})
        return DispatchResult(provider=self.name, reference=reference)


class ConsolePushProvider:
    name = "console"

    def send_push(self, *, device_token: str, title: str, body: str, data=None) -> DispatchResult:
        sys.stdout.write(f"[local console push to {device_token[:18]}…] {title}: {body}\n")
        sys.stdout.flush()
        return DispatchResult(provider=self.name, reference=uuid.uuid4().hex)


class ExpoPushProvider:
    name = "expo"

    def __init__(self, url: str, access_token: str = "", timeout: float = 10.0):
        self.url, self.access_token, self.timeout = url, access_token, timeout

    def send_push(self, *, device_token: str, title: str, body: str, data=None) -> DispatchResult:
        headers = {"Authorization": f"Bearer {self.access_token}"} if self.access_token else {}
        _, response = post(
            self.url,
            json_body=[{"to": device_token, "title": title, "body": body, "data": data or {}}],
            headers=headers,
            timeout=self.timeout,
        )
        tickets = response.get("data") or []
        ticket = tickets[0] if isinstance(tickets, list) and tickets else {}
        if ticket.get("status") == "ok" and ticket.get("id"):
            return DispatchResult(provider=self.name, reference=str(ticket["id"]))
        error = (ticket.get("details") or {}).get("error") or "push_rejected"
        raise ProviderError(
            "device_not_registered" if error == "DeviceNotRegistered" else str(error)[:40],
            retryable=error in {"MessageRateExceeded", "push_rejected"},
        )


def get_push_provider() -> PushProvider:
    choice = getattr(settings, "PUSH_PROVIDER", "disabled")
    if choice == "mock":
        return MockPushProvider()
    if choice == "console":
        require_local("PUSH_PROVIDER", choice)
        return ConsolePushProvider()
    if choice == "expo":
        return ExpoPushProvider(
            settings.EXPO_PUSH_URL, settings.EXPO_ACCESS_TOKEN, settings.PROVIDER_TIMEOUT_SECONDS
        )
    if choice == "disabled":
        return DisabledProvider("push")
    raise unknown("PUSH_PROVIDER", choice, SUPPORTED)
