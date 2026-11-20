"""Email. Supported ``EMAIL_PROVIDER`` values: ``mock`` (in-memory), ``console`` (local only),
``smtp``, ``disabled``. Selection maps to Django's ``EMAIL_BACKEND`` in settings.

SMTP works with any provider that offers SMTP submission (for example Amazon SES, SendGrid,
Mailgun, Postmark or a mail server): set ``EMAIL_PROVIDER=smtp``, ``EMAIL_HOST``, ``EMAIL_PORT``,
``EMAIL_HOST_USER``, ``EMAIL_HOST_PASSWORD``, ``EMAIL_USE_TLS`` (or ``EMAIL_USE_SSL``) and
``EMAIL_SENDER`` (the From address). Only SMTP is implemented; provider HTTP APIs are not."""

from django.conf import settings
from django.core.mail import send_mail
from django.core.mail.backends.base import BaseEmailBackend

from .base import DispatchResult, ProviderDisabledError, ProviderError

BACKENDS = {
    "mock": "django.core.mail.backends.locmem.EmailBackend",
    "console": "django.core.mail.backends.console.EmailBackend",
    "smtp": "django.core.mail.backends.smtp.EmailBackend",
    "disabled": "common.providers.email.DisabledEmailBackend",
}


class DisabledEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        raise ProviderDisabledError("Email is disabled in this environment.")


def send_email(*, to: str, subject: str, body: str) -> DispatchResult:
    try:
        sent = send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=False)
    except ProviderDisabledError:
        raise
    except OSError:  # connection refused, timeout, TLS failure
        raise ProviderError("smtp_unavailable", retryable=True) from None
    except Exception:  # noqa: BLE001 - SMTP rejections (bad recipient, auth) are permanent
        raise ProviderError("smtp_rejected", retryable=False) from None
    if not sent:
        raise ProviderError("not_sent", retryable=True)
    return DispatchResult(provider=getattr(settings, "EMAIL_PROVIDER", "smtp"), reference="smtp")
