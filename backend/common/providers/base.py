"""Shared provider types and selection rules (CC-R55, CC-R56; owner decision DR-2026-11-20-O-7).

Every channel has the same choices model:
- ``mock`` keeps messages in memory (tests); ``console`` prints them (local development only);
- ``disabled`` refuses to send, so nothing silently pretends to deliver;
- a real adapter (Twilio SMS, SMTP email, Expo push, ClamAV scanning) is selected by name and
  configured through environment variables. Deployed settings refuse ``mock`` and ``console``
  and refuse a real adapter whose required configuration is missing (``common.config``).

Acceptance by a provider isn't proof of delivery (doc 15 §12; CC-R54). Message bodies, codes and
credentials are never logged.
"""

from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class ProviderDisabledError(RuntimeError):
    """The provider for this channel is disabled in the current environment."""


class ProviderError(RuntimeError):
    """A provider call failed. ``retryable`` is True for timeouts, connection errors, rate
    limits and server errors; False for rejected requests (bad number, invalid token).
    ``code`` is a short machine-readable reason, never a secret or a message body."""

    def __init__(self, code: str, *, retryable: bool):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class DispatchResult:
    """The provider accepted the request. Acceptance is not proof of delivery."""

    provider: str
    reference: str


class DisabledProvider:
    name = "disabled"

    def __init__(self, channel: str):
        self.channel = channel

    def _refuse(self, **_kwargs) -> DispatchResult:
        raise ProviderDisabledError(f"The {self.channel} provider is disabled in this environment.")

    send_sms = _refuse
    send_push = _refuse
    send_email = _refuse


def require_local(setting_name: str, choice: str) -> None:
    if getattr(settings, "ENVIRONMENT", None) != "local":
        raise ImproperlyConfigured(
            f"{setting_name} {choice!r} is allowed only in local development."
        )


def unknown(setting_name: str, choice: str, supported) -> ImproperlyConfigured:
    return ImproperlyConfigured(
        f"Unknown {setting_name} {choice!r}; supported: {', '.join(sorted(supported))}."
    )
