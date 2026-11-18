import logging

import pytest
from django.core import mail
from django.core.exceptions import ImproperlyConfigured

from common.providers import (
    MockSMSProvider,
    ProviderDisabledError,
    get_push_provider,
    get_sms_provider,
)
from common.tasks import BaseTask
from config.celery import app as celery_app


def test_mock_sms_records_without_logging_the_body(caplog):
    with caplog.at_level(logging.INFO):
        result = get_sms_provider().send_sms(to="+923001234567", message="Your code is 123456")
    assert result.provider == "mock"
    assert MockSMSProvider.sent[0]["message"] == "Your code is 123456"
    assert "123456" not in caplog.text


def test_mock_push_records():
    result = get_push_provider().send_push(device_token="tok", title="t", body="b")
    assert result.provider == "mock"


def test_disabled_provider_refuses(settings):
    settings.SMS_PROVIDER = "disabled"
    with pytest.raises(ProviderDisabledError):
        get_sms_provider().send_sms(to="+923001234567", message="x")


def test_unknown_provider_is_a_configuration_error(settings):
    settings.PUSH_PROVIDER = "carrier-pigeon"
    with pytest.raises(ImproperlyConfigured):
        get_push_provider()


def test_test_email_backend_is_in_memory():
    from django.core.mail import send_mail

    send_mail("Subject", "Body", "noreply@example.test", ["user@example.test"])
    assert len(mail.outbox) == 1


def test_celery_app_uses_project_conventions():
    assert celery_app.main == "matermonial"
    assert celery_app.conf.task_always_eager is True
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert issubclass(celery_app.Task, BaseTask)


def test_task_runs_and_failures_are_logged_without_arguments(caplog):
    @celery_app.task(name="tests.add")
    def add(x, y):
        return x + y

    @celery_app.task(name="tests.fail")
    def fail(secret_argument):
        raise ValueError("boom")

    assert add.delay(2, 3).get() == 5
    assert add.max_retries == 3 and add.retry_backoff is True

    # Run the failure the way a worker does (no propagation); Celery skips on_failure when an
    # eager failure is re-raised to the caller.
    with caplog.at_level(logging.ERROR):
        result = fail.apply(args=["+923001234567"], throw=False)
    assert result.failed()
    assert "Task failed" in caplog.text
    assert "+923001234567" not in caplog.text
