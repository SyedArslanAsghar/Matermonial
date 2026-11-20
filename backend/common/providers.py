"""Provider abstractions for SMS and push, with mock and disabled implementations
(CLAUDE.md CC-R55, CC-R56; doc 04 §17–§22; doc 16 §5).

- ``mock``: records messages in memory for local development and tests. It never logs the
  message body (an SMS can carry an OTP; CC-R47).
- ``console`` (SMS only, ``ENVIRONMENT=local`` only): writes each SMS to this process's standard
  output, standing in for the handset so a developer can read OTPs and admin enrollment codes
  (which are delivered only by SMS, KI-39). It never goes through ``logging``. Any other
  environment refuses it at selection, and deployed settings refuse it at startup.
- ``disabled``: refuses to send. This is the default outside local and test, so a feature
  flag or missing provider never silently pretends to deliver.

Real providers are added with their feature phase. Acceptance by a provider doesn't prove
delivery (doc 15 §12; CC-R54). Email uses Django's EMAIL_BACKEND setting. Object storage
uses Django's STORAGES setting. The payment provider interface is defined with the payments
phase (Phase 13), because its contract depends on JazzCash decisions (doc 13 OD-001/003).
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class ProviderDisabledError(RuntimeError):
    """The provider for this channel is disabled in the current environment."""


@dataclass(frozen=True)
class DispatchResult:
    """The provider accepted the request. Acceptance is not proof of delivery."""

    provider: str
    reference: str


class SMSProvider(Protocol):
    def send_sms(self, *, to: str, message: str) -> DispatchResult: ...


class PushProvider(Protocol):
    def send_push(self, *, device_token: str, title: str, body: str) -> DispatchResult: ...


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
        import sys

        reference = uuid.uuid4().hex
        # Deliberately stdout, not logging: this is the simulated handset (local only).
        sys.stdout.write(f"[local console SMS to {to}] {message}\n")
        sys.stdout.flush()
        return DispatchResult(provider=self.name, reference=reference)


class MockPushProvider:
    name = "mock"
    sent: list[dict] = []

    def send_push(self, *, device_token: str, title: str, body: str) -> DispatchResult:
        reference = uuid.uuid4().hex
        self.sent.append(
            {"device_token": device_token, "title": title, "body": body, "reference": reference}
        )
        logger.info("Mock push accepted", extra={"provider": self.name, "reference": reference})
        return DispatchResult(provider=self.name, reference=reference)


class DisabledProvider:
    name = "disabled"

    def __init__(self, channel: str):
        self.channel = channel

    def _refuse(self, **_kwargs) -> DispatchResult:
        raise ProviderDisabledError(f"The {self.channel} provider is disabled in this environment.")

    send_sms = _refuse
    send_push = _refuse


def _select(setting_name: str, channel: str, mock_cls):
    choice = getattr(settings, setting_name, "disabled")
    if choice == "mock":
        return mock_cls()
    if choice == "disabled":
        return DisabledProvider(channel)
    raise ImproperlyConfigured(f"Unknown {setting_name} {choice!r}; expected 'mock' or 'disabled'.")


def get_sms_provider() -> SMSProvider:
    if getattr(settings, "SMS_PROVIDER", None) == "console":
        if getattr(settings, "ENVIRONMENT", None) != "local":
            raise ImproperlyConfigured(
                "SMS_PROVIDER 'console' is allowed only in local development."
            )
        return ConsoleSMSProvider()
    return _select("SMS_PROVIDER", "SMS", MockSMSProvider)


def get_push_provider() -> PushProvider:
    return _select("PUSH_PROVIDER", "push", MockPushProvider)


# --- Malware scanning (TR-10, DR-2026-11-19-P3-1) -----------------------------------------
# ``mock`` (local and tests) flags only the EICAR test signature. ``disabled`` refuses every
# scan, so uploads are refused rather than accepted unscanned. Deployed settings refuse
# ``mock``; a real scanner needs owner approval before production.

EICAR_MARKER = b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"


@dataclass(frozen=True)
class ScanResult:
    clean: bool
    provider: str


class MockScanner:
    name = "mock"

    def scan(self, data: bytes) -> ScanResult:
        return ScanResult(clean=EICAR_MARKER not in data, provider=self.name)


class DisabledScanner:
    name = "disabled"

    def scan(self, data: bytes) -> ScanResult:
        raise ProviderDisabledError("Malware scanning is disabled in this environment.")


def get_malware_scanner():
    choice = getattr(settings, "MALWARE_SCANNER", "disabled")
    if choice == "mock":
        return MockScanner()
    if choice == "disabled":
        return DisabledScanner()
    raise ImproperlyConfigured(
        f"Unknown MALWARE_SCANNER {choice!r}; expected 'mock' or 'disabled'."
    )
