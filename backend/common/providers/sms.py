"""SMS adapters. Supported: ``mock``, ``console`` (local only), ``twilio``, ``disabled``.

Twilio (Programmable Messaging REST API): set ``SMS_PROVIDER=twilio``, ``TWILIO_ACCOUNT_SID``,
``TWILIO_AUTH_TOKEN`` and ``SMS_SENDER_ID`` (a Twilio phone number in E.164, an approved
alphanumeric sender ID, or a Messaging Service SID starting with ``MG``)."""

import base64
import logging
import sys
import uuid
from typing import Protocol

from django.conf import settings

from .base import DisabledProvider, DispatchResult, ProviderError, require_local, unknown
from .http import post

logger = logging.getLogger(__name__)
SUPPORTED = {"mock", "console", "twilio", "disabled"}


class SMSProvider(Protocol):
    def send_sms(self, *, to: str, message: str) -> DispatchResult: ...


class MockSMSProvider:
    name = "mock"
    sent: list[dict] = []

    def send_sms(self, *, to: str, message: str) -> DispatchResult:
        reference = uuid.uuid4().hex
        self.sent.append({"to": to, "message": message, "reference": reference})
        logger.info("Mock SMS accepted", extra={"provider": self.name, "reference": reference})
        return DispatchResult(provider=self.name, reference=reference)


class ConsoleSMSProvider:
    name = "console"

    def send_sms(self, *, to: str, message: str) -> DispatchResult:
        reference = uuid.uuid4().hex
        # Deliberately stdout, not logging: this is the simulated handset (local only).
        sys.stdout.write(f"[local console SMS to {to}] {message}\n")
        sys.stdout.flush()
        return DispatchResult(provider=self.name, reference=reference)


class TwilioSMSProvider:
    name = "twilio"
    API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

    def __init__(self, account_sid: str, auth_token: str, sender: str, timeout: float = 10.0):
        self.account_sid, self.auth_token, self.sender, self.timeout = (
            account_sid,
            auth_token,
            sender,
            timeout,
        )

    def send_sms(self, *, to: str, message: str) -> DispatchResult:
        form = {"To": to, "Body": message}
        if self.sender.startswith("MG"):
            form["MessagingServiceSid"] = self.sender
        else:
            form["From"] = self.sender
        token = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode()
        _, body = post(
            self.API.format(sid=self.account_sid),
            form=form,
            headers={"Authorization": f"Basic {token}"},
            timeout=self.timeout,
        )
        sid = body.get("sid")
        if not sid:
            raise ProviderError("unexpected_response", retryable=True)
        return DispatchResult(provider=self.name, reference=str(sid))


def get_sms_provider() -> SMSProvider:
    choice = getattr(settings, "SMS_PROVIDER", "disabled")
    if choice == "mock":
        return MockSMSProvider()
    if choice == "console":
        require_local("SMS_PROVIDER", choice)
        return ConsoleSMSProvider()
    if choice == "twilio":
        return TwilioSMSProvider(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
            settings.SMS_SENDER_ID,
            settings.PROVIDER_TIMEOUT_SECONDS,
        )
    if choice == "disabled":
        return DisabledProvider("SMS")
    raise unknown("SMS_PROVIDER", choice, SUPPORTED)
