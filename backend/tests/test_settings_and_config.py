import base64
import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db import models

from common.config import deployed_settings_errors, validate_deployed_settings
from common.crypto.keys import PURPOSES, dev_keyring

# Non-dev test keys (distinct per purpose); deployed environments must not use dev-only keys.
KEY_ENV = {
    f"{purpose}_KEYS": "1:" + base64.b64encode(bytes([i + 1]) * 32).decode()
    for i, purpose in enumerate(PURPOSES)
}
KEY_SETTINGS = {
    **KEY_ENV,
    **{f"{purpose}_ACTIVE_VERSION": 1 for purpose in PURPOSES},
    "COMPLIANCE_REGISTRY_BACKEND": "external",
    "CACHES": {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache"}},
}

GOOD_DEPLOYED = {
    "DEBUG": False,
    "SECRET_KEY": "x" * 64,
    "ALLOWED_HOSTS": ["api.example.test"],
    "SMS_PROVIDER": "disabled",
    "PUSH_PROVIDER": "disabled",
    "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
    "STORAGE_BACKEND": "local",
    **KEY_SETTINGS,
}
GOOD_ENV = {
    "DATABASE_URL": "postgresql://u:p@db.example.test:5432/app",
    "CELERY_BROKER_URL": "redis://broker.example.test:6379/0",
    **KEY_ENV,
}


def test_tests_run_on_postgresql():
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"


def test_cookie_and_header_security_defaults():
    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert settings.CSRF_COOKIE_HTTPONLY is False  # same-origin client reads the CSRF token
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"
    assert settings.X_FRAME_OPTIONS == "DENY"
    assert "common.middleware.RequestIDMiddleware" in settings.MIDDLEWARE
    assert "django.middleware.csrf.CsrfViewMiddleware" in settings.MIDDLEWARE


def test_api_foundation_settings():
    rf = settings.REST_FRAMEWORK
    assert rf["EXCEPTION_HANDLER"] == "common.api.exceptions.exception_handler"
    assert rf["DEFAULT_PAGINATION_CLASS"] == "common.api.pagination.StandardPagination"
    assert rf["DEFAULT_PERMISSION_CLASSES"] == ["rest_framework.permissions.IsAuthenticated"]
    assert "DEFAULT_THROTTLE_RATES" not in rf  # rates come with their endpoints (KI-6)


def test_custom_user_model_is_discoverable():
    user_model = get_user_model()
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert user_model.__module__.startswith("apps.accounts.models")  # models/ package (G4)
    assert user_model._meta.app_label == "accounts"
    assert user_model._meta.db_table == "accounts_user"
    assert user_model.USERNAME_FIELD == "phone_number"
    assert isinstance(user_model._meta.pk, models.UUIDField)  # CC-R32
    for name in ("created_by", "updated_by"):  # doc 12 §5.5 F4 (TR-09)
        assert user_model._meta.get_field(name).remote_field.on_delete is models.PROTECT


def test_valid_deployed_configuration_passes():
    assert deployed_settings_errors(GOOD_DEPLOYED, GOOD_ENV) == []
    validate_deployed_settings(GOOD_DEPLOYED, GOOD_ENV)


@pytest.mark.parametrize(
    ("override", "env", "fragment"),
    [
        ({"DEBUG": True}, GOOD_ENV, "DEBUG"),
        ({"SECRET_KEY": "unsafe-local-only-key-change-me"}, GOOD_ENV, "DJANGO_SECRET_KEY"),
        ({"SECRET_KEY": "short"}, GOOD_ENV, "DJANGO_SECRET_KEY"),
        ({"ALLOWED_HOSTS": []}, GOOD_ENV, "DJANGO_ALLOWED_HOSTS"),
        ({}, {}, "DATABASE_URL"),
        ({"SMS_PROVIDER": "mock"}, GOOD_ENV, "SMS_PROVIDER"),
        ({"PUSH_PROVIDER": "mock"}, GOOD_ENV, "PUSH_PROVIDER"),
        (
            {"EMAIL_BACKEND": "django.core.mail.backends.console.EmailBackend"},
            GOOD_ENV,
            "EMAIL_BACKEND",
        ),
        ({"STORAGE_BACKEND": "s3"}, GOOD_ENV, "STORAGE_BACKEND"),
        # G4 (DR-2026-11-18-G4): key rings and the compliance registry (TR-23, TR-11, TR-24).
        ({}, {**GOOD_ENV, "KEK_KEYS": ""}, "KEK_KEYS must be set explicitly"),
        ({"QUEUE_KEYS": dev_keyring("QUEUE")}, GOOD_ENV, "QUEUE_KEYS contains a dev-only key"),
        ({"DEDUPE_KEYS": "1:not-base64!"}, GOOD_ENV, "DEDUPE_KEYS: Key version 1"),
        ({"SUBJECT_HASH_ACTIVE_VERSION": 2}, GOOD_ENV, "SUBJECT_HASH_KEYS: SUBJECT_HASH"),
        ({"COMPLIANCE_REGISTRY_BACKEND": "local"}, GOOD_ENV, "COMPLIANCE_REGISTRY_BACKEND"),
        (
            {"CACHES": {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}},
            GOOD_ENV,
            "CACHE_URL must point to Redis",
        ),
    ],
)
def test_deployed_configuration_fails_closed(override, env, fragment):
    with pytest.raises(ImproperlyConfigured, match=fragment):
        validate_deployed_settings({**GOOD_DEPLOYED, **override}, env)


# --- D-1: the Celery broker must be explicit in deployed environments (DR-2026-11-17-G3C-1) ---

SECRET_LOOKING_PASSWORD = "s3cr3t-broker-pa55word"


@pytest.mark.parametrize(
    "broker_env",
    [
        {"CELERY_BROKER_URL": "redis://broker.example.test:6379/0"},
        {"REDIS_URL": "redis://cache.example.test:6379/0"},
        {"CELERY_BROKER_URL": "rediss://b.example.test:6380/0", "REDIS_URL": "redis://c:6379/1"},
    ],
)
def test_explicit_broker_configuration_passes(broker_env):
    env = {"DATABASE_URL": GOOD_ENV["DATABASE_URL"], **KEY_ENV, **broker_env}
    assert deployed_settings_errors(GOOD_DEPLOYED, env) == []


@pytest.mark.parametrize("broker_env", [{}, {"CELERY_BROKER_URL": ""}, {"REDIS_URL": ""}])
def test_missing_broker_fails_closed(broker_env):
    env = {"DATABASE_URL": GOOD_ENV["DATABASE_URL"], **KEY_ENV, **broker_env}
    with pytest.raises(ImproperlyConfigured, match="CELERY_BROKER_URL or REDIS_URL"):
        validate_deployed_settings(GOOD_DEPLOYED, env)


def test_configuration_errors_never_contain_values():
    env = {"DATABASE_URL": f"postgresql://app:{SECRET_LOOKING_PASSWORD}@db:5432/app"}
    insecure = {**GOOD_DEPLOYED, "DEBUG": True, "SECRET_KEY": SECRET_LOOKING_PASSWORD}
    with pytest.raises(ImproperlyConfigured) as excinfo:
        validate_deployed_settings(insecure, env)
    assert SECRET_LOOKING_PASSWORD not in str(excinfo.value)


def test_key_errors_never_contain_key_material():
    bad = {**GOOD_DEPLOYED, "KEK_KEYS": KEY_ENV["KEK_KEYS"] + ",2:short"}
    message = "\n".join(deployed_settings_errors(bad, GOOD_ENV))
    assert "KEK_KEYS" in message
    assert KEY_ENV["KEK_KEYS"].split(":", 1)[1] not in message and "short" not in message


def _load_settings_in_subprocess(module: str, extra_env: dict) -> subprocess.CompletedProcess:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "DJANGO_SETTINGS_MODULE": module,
        "DJANGO_SECRET_KEY": "k" * 64,
        "DJANGO_ALLOWED_HOSTS": "api.example.test",
        "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "DATABASE_URL": f"postgresql://app:{SECRET_LOOKING_PASSWORD}@db.example.test:5432/app",
        "COMPLIANCE_REGISTRY_BACKEND": "external",
        "CACHE_URL": "redis://cache.example.test:6379/1",
        **KEY_ENV,
        **extra_env,
    }
    code = "import django; django.setup(); from django.conf import settings; print(settings.CELERY_BROKER_URL)"
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parent.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize("module", ["config.settings.production", "config.settings.staging"])
def test_deployed_settings_modules_refuse_missing_broker(module):
    result = _load_settings_in_subprocess(module, {})
    assert result.returncode != 0
    assert "CELERY_BROKER_URL or REDIS_URL must be set explicitly" in result.stderr
    assert SECRET_LOOKING_PASSWORD not in result.stderr + result.stdout


@pytest.mark.parametrize("module", ["config.settings.production", "config.settings.staging"])
def test_deployed_settings_modules_load_with_explicit_broker(module):
    result = _load_settings_in_subprocess(
        module, {"REDIS_URL": "redis://broker.example.test:6379/0"}
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "redis://broker.example.test:6379/0"


def test_local_settings_keep_documented_broker_behaviour():
    # Local development keeps its documented behaviour: no broker variable is required, the
    # default broker is a local Redis, and tasks run inline (eager).
    env = {"PATH": os.environ.get("PATH", ""), "DJANGO_SETTINGS_MODULE": "config.settings.local"}
    code = (
        "import django; django.setup(); from django.conf import settings as s; "
        "print(s.CELERY_BROKER_URL, s.CELERY_TASK_ALWAYS_EAGER)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parent.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["redis://127.0.0.1:6379/0", "True"]
