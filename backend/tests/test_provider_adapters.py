"""Provider adapters (DR-2026-11-20-O-7, -8): Twilio SMS, SMTP email, Expo push and ClamAV
scanning are selectable by configuration; real services are never contacted in tests (the HTTP
layer and the socket are mocked)."""

import io
import json
import struct
import urllib.error
from unittest import mock

import pytest
from django.core import mail
from django.core.exceptions import ImproperlyConfigured

from common.config import provider_configuration_errors
from common.providers import (
    ClamAVScanner,
    ExpoPushProvider,
    ProviderDisabledError,
    ProviderError,
    ScannerUnavailable,
    TwilioSMSProvider,
    get_malware_scanner,
    get_push_provider,
    get_sms_provider,
    send_email,
)


class FakeResponse(io.BytesIO):
    def __init__(self, payload, status=200):
        super().__init__(json.dumps(payload).encode())
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def http_error(code):
    return urllib.error.HTTPError("https://x", code, "err", {}, io.BytesIO(b"{}"))


# --- Selection ------------------------------------------------------------------------------


def test_real_adapters_are_selected_by_configuration(settings):
    settings.SMS_PROVIDER = "twilio"
    settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN = "AC123", "token"
    settings.SMS_SENDER_ID = "+15005550006"
    assert isinstance(get_sms_provider(), TwilioSMSProvider)
    settings.PUSH_PROVIDER = "expo"
    assert isinstance(get_push_provider(), ExpoPushProvider)
    settings.MALWARE_SCANNER, settings.CLAMAV_HOST = "clamav", "clamav.internal"
    assert isinstance(get_malware_scanner(), ClamAVScanner)


@pytest.mark.parametrize(
    "setting, choice",
    [("SMS_PROVIDER", "nexmo"), ("PUSH_PROVIDER", "fcm"), ("MALWARE_SCANNER", "virustotal")],
)
def test_unsupported_providers_are_refused(settings, setting, choice):
    setattr(settings, setting, choice)
    getter = {
        "SMS_PROVIDER": get_sms_provider,
        "PUSH_PROVIDER": get_push_provider,
        "MALWARE_SCANNER": get_malware_scanner,
    }[setting]
    with pytest.raises(ImproperlyConfigured):
        getter()


@pytest.mark.parametrize("setting", ["SMS_PROVIDER", "PUSH_PROVIDER"])
def test_console_providers_are_local_only(settings, setting):
    setattr(settings, setting, "console")
    settings.ENVIRONMENT = "production"
    getter = get_sms_provider if setting == "SMS_PROVIDER" else get_push_provider
    with pytest.raises(ImproperlyConfigured):
        getter()


def test_deployed_configuration_requires_each_selected_providers_settings():
    errors = provider_configuration_errors(
        {
            "SMS_PROVIDER": "twilio",
            "EMAIL_PROVIDER": "smtp",
            "PUSH_PROVIDER": "expo",
            "EXPO_PUSH_URL": "http://insecure",
            "MALWARE_SCANNER": "clamav",
        }
    )
    text = " ".join(errors)
    for name in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "SMS_SENDER_ID", "EMAIL_HOST"):
        assert name in text
    assert "EMAIL_SENDER" in text and "CLAMAV_HOST" in text and "https" in text
    assert provider_configuration_errors({"SMS_PROVIDER": "disabled"}) == []


# --- Twilio ---------------------------------------------------------------------------------


def test_twilio_sends_with_basic_auth_and_returns_the_message_sid():
    provider = TwilioSMSProvider("AC123", "secret-token", "+15005550006")
    with mock.patch("urllib.request.urlopen", return_value=FakeResponse({"sid": "SM1"})) as call:
        result = provider.send_sms(to="+923001234567", message="Your code is 123456")
    request = call.call_args.args[0]
    assert result.reference == "SM1" and result.provider == "twilio"
    assert request.full_url.endswith("/Accounts/AC123/Messages.json")
    assert request.get_header("Authorization").startswith("Basic ")
    body = request.data.decode()
    assert "To=%2B923001234567" in body and "From=%2B15005550006" in body


def test_twilio_messaging_service_sender():
    provider = TwilioSMSProvider("AC123", "t", "MG0123")
    with mock.patch("urllib.request.urlopen", return_value=FakeResponse({"sid": "SM2"})) as call:
        provider.send_sms(to="+923001234567", message="hi")
    assert "MessagingServiceSid=MG0123" in call.call_args.args[0].data.decode()


@pytest.mark.parametrize("code, retryable", [(400, False), (401, False), (429, True), (503, True)])
def test_twilio_errors_are_classified(code, retryable, caplog):
    provider = TwilioSMSProvider("AC123", "secret-token", "+1500")
    with mock.patch("urllib.request.urlopen", side_effect=http_error(code)):
        with pytest.raises(ProviderError) as exc:
            provider.send_sms(to="+923001234567", message="Your code is 123456")
    assert exc.value.retryable is retryable
    assert "123456" not in caplog.text and "secret-token" not in caplog.text


def test_network_failures_are_retryable():
    provider = TwilioSMSProvider("AC123", "t", "+1500")
    with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
        with pytest.raises(ProviderError) as exc:
            provider.send_sms(to="+923001234567", message="x")
    assert exc.value.retryable and exc.value.code == "network_error"


# --- Expo -----------------------------------------------------------------------------------


def test_expo_push_success_and_bearer_token():
    provider = ExpoPushProvider("https://exp.host/--/api/v2/push/send", "expo-secret")
    ticket = {"data": [{"status": "ok", "id": "ticket-1"}]}
    with mock.patch("urllib.request.urlopen", return_value=FakeResponse(ticket)) as call:
        result = provider.send_push(
            device_token="ExponentPushToken[abcdefghijkl]", title="t", body="b"
        )
    request = call.call_args.args[0]
    assert result.reference == "ticket-1"
    assert request.get_header("Authorization") == "Bearer expo-secret"
    assert json.loads(request.data)[0]["to"] == "ExponentPushToken[abcdefghijkl]"


def test_expo_device_not_registered_is_permanent():
    provider = ExpoPushProvider("https://exp.host/--/api/v2/push/send")
    ticket = {"data": [{"status": "error", "details": {"error": "DeviceNotRegistered"}}]}
    with mock.patch("urllib.request.urlopen", return_value=FakeResponse(ticket)):
        with pytest.raises(ProviderError) as exc:
            provider.send_push(device_token="ExponentPushToken[abcdefghijkl]", title="t", body="b")
    assert exc.value.code == "device_not_registered" and not exc.value.retryable


def test_https_is_required():
    provider = ExpoPushProvider("http://exp.host/push")
    with pytest.raises(ProviderError) as exc:
        provider.send_push(device_token="x", title="t", body="b")
    assert exc.value.code == "insecure_url"


# --- Email ----------------------------------------------------------------------------------


def test_email_uses_the_configured_backend_and_sender(settings):
    settings.DEFAULT_FROM_EMAIL = "no-reply@example.test"
    result = send_email(to="user@example.test", subject="Hello", body="Body")
    assert result.reference == "smtp"
    assert mail.outbox[0].from_email == "no-reply@example.test"


def test_disabled_email_refuses(settings):
    settings.EMAIL_BACKEND = "common.providers.email.DisabledEmailBackend"
    with pytest.raises(ProviderDisabledError):
        send_email(to="user@example.test", subject="s", body="b")


def test_smtp_connection_failure_is_retryable(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    with mock.patch("smtplib.SMTP", side_effect=ConnectionRefusedError()):
        with pytest.raises(ProviderError) as exc:
            send_email(to="user@example.test", subject="s", body="b")
    assert exc.value.retryable


# --- ClamAV ---------------------------------------------------------------------------------


class FakeClamd:
    def __init__(self, reply: bytes):
        self.reply, self.sent = reply, b""

    def settimeout(self, _):
        pass

    def sendall(self, data):
        self.sent += data

    def recv(self, _):
        reply, self.reply = self.reply, b""
        return reply

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.mark.parametrize(
    "reply, outcome, signature",
    [
        (b"stream: OK\0", "CLEAN", ""),
        (b"stream: Eicar-Test-Signature FOUND\0", "INFECTED", "Eicar-Test-Signature"),
    ],
)
def test_clamav_instream_outcomes(reply, outcome, signature):
    fake = FakeClamd(reply)
    with mock.patch("socket.create_connection", return_value=fake):
        result = ClamAVScanner("clamav.internal", 3310, 5).scan(b"x" * 70_000)
    assert (result.outcome, result.signature) == (outcome, signature)
    assert fake.sent.startswith(b"zINSTREAM\0")
    assert fake.sent.endswith(struct.pack("!L", 0))  # end-of-stream chunk
    assert struct.unpack("!L", fake.sent[10:14])[0] == ClamAVScanner.CHUNK  # chunked


@pytest.mark.parametrize("reply", [b"INSTREAM size limit exceeded. ERROR\0", b""])
def test_clamav_errors_are_failures_never_clean(reply):
    with mock.patch("socket.create_connection", return_value=FakeClamd(reply)):
        with pytest.raises(ScannerUnavailable):
            ClamAVScanner("clamav.internal", 3310, 5).scan(b"data")


def test_clamav_unreachable_is_a_failure():
    with mock.patch("socket.create_connection", side_effect=ConnectionRefusedError()):
        with pytest.raises(ScannerUnavailable) as exc:
            ClamAVScanner("clamav.internal", 3310, 5).scan(b"data")
    assert exc.value.code == "clamav_unreachable"


def test_mock_scanner_is_refused_when_deployed():
    from common.config import NON_PRODUCTION_PROVIDERS

    assert "mock" in NON_PRODUCTION_PROVIDERS
