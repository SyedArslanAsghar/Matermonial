"""Settings shared by every environment (doc 07 §2, doc 16).

Environment-specific modules (local, test, staging, production) override only what differs.
Values come from environment variables; a developer's backend/.env (never committed) is read
for local convenience. No secret value is stored in source code.
"""

from pathlib import Path

import environ

from common.crypto.keys import dev_keyring
from common.logs import build_logging_config

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, []),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env")

ENVIRONMENT = env("DJANGO_ENVIRONMENT", default="local")

# The insecure default only works locally; staging/production refuse it (common/config.py).
SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-local-only-key-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    # Project domain apps (backend/apps/, DR-2026-11-17-G3-3)
    "apps.accounts",
    "apps.audit",
    "apps.platform_ops",
    # Shared kernel infrastructure (common/, DR-2026-11-18-G4-6)
    "common.events",
    "common.idempotency",
]

MIDDLEWARE = [
    "common.middleware.RequestIDMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Database: one authoritative PostgreSQL database (CC-R14) ---
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgresql://matrimonial_app:password@127.0.0.1:5432/matrimonial_db",
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)
# lock_timeout per transaction for @retry_on_contention (doc 12 §5.3, TR-09)
DB_LOCK_TIMEOUT_MS = env.int("DB_LOCK_TIMEOUT_MS", default=5000)
# LOCK_PLAN tracker (doc 12 §5.6, TR-22): enabled in local and test settings only
LOCK_TRACKER_ENABLED = env.bool("LOCK_TRACKER_ENABLED", default=False)

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", default="Asia/Karachi")
USE_I18N = True
USE_TZ = True  # timestamps are stored in UTC (CC-R34)

# --- Static and media (private media is never served by Django; CC-R46) ---
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))
STORAGE_BACKEND = env("STORAGE_BACKEND", default="local")
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": MEDIA_ROOT},
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- API (CC-R51; doc 02 §8; doc 04 §16) ---
# Authentication: Django sessions with CSRF for the same-origin web client (TR-12).
# Mobile token authentication is TR-01 (PROPOSED, due before G4) and isn't configured here.
# Per-endpoint rate limits are added with their features (CC-R49; doc 06).
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "common.api.pagination.StandardPagination",
    "PAGE_SIZE": env.int("API_PAGE_SIZE", default=20),
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "EXCEPTION_HANDLER": "common.api.exceptions.exception_handler",
}
API_MAX_PAGE_SIZE = env.int("API_MAX_PAGE_SIZE", default=100)
# OpenAPI schema and Swagger UI are served only where enabled (local by default; KI-7)
API_DOCS_ENABLED = env.bool("API_DOCS_ENABLED", default=False)

SPECTACULAR_SETTINGS = {
    "TITLE": "Matermonial API",
    "DESCRIPTION": "Versioned API for the Matermonial platform.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --- Security headers and cookies ---
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
# The same-origin web client (TR-12) must read the CSRF token from its cookie, so the CSRF
# cookie isn't HttpOnly. The session cookie stays HttpOnly (KI-5; baseline v4 §18).
CSRF_COOKIE_HTTPONLY = False

# --- Providers (CC-R55, CC-R56; doc 16 §5) ---
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
SMS_PROVIDER = env("SMS_PROVIDER", default="disabled")
PUSH_PROVIDER = env("PUSH_PROVIDER", default="disabled")

# --- Encryption, pseudonymisation and registry keys (TR-23, TR-11, TR-24; doc 16 §10) ---
# Each ring is "<version>:<base64 32-byte key>,..." plus its active version. The defaults are
# DEV-ONLY keys derived from a public label (common.crypto.keys): fine for local development and
# tests, never for real data. Staging and production refuse them (common.config).
for _purpose in ("KEK", "QUEUE", "DEDUPE", "SUBJECT_HASH", "REGISTRY"):
    globals()[f"{_purpose}_KEYS"] = env(f"{_purpose}_KEYS", default=dev_keyring(_purpose))
    globals()[f"{_purpose}_ACTIVE_VERSION"] = env.int(f"{_purpose}_ACTIVE_VERSION", default=1)
# Compliance registry (TR-24): "local" writes hash-chained JSON files under
# COMPLIANCE_REGISTRY_LOCATION; deployed environments need the approved external store.
COMPLIANCE_REGISTRY_BACKEND = env("COMPLIANCE_REGISTRY_BACKEND", default="local")
COMPLIANCE_REGISTRY_LOCATION = env(
    "COMPLIANCE_REGISTRY_LOCATION", default=str(BASE_DIR / "var" / "compliance_registry")
)
# Outbox (TR-11; doc 16 §10.1).
OUTBOX_LEASE_SECONDS = env.int("OUTBOX_LEASE_SECONDS", default=300)
OUTBOX_REDACT_AFTER_DAYS = env.int("OUTBOX_REDACT_AFTER_DAYS", default=7)
OUTBOX_PURGE_AFTER_DAYS = env.int("OUTBOX_PURGE_AFTER_DAYS", default=30)
# Periodic kernel jobs (run by celery beat when a worker is used; doc 12 §6, CC-R53).
CELERY_BEAT_SCHEDULE = {
    "process-outbox": {"task": "events.process_outbox", "schedule": 10.0},
    "redact-and-purge-outbox": {"task": "events.redact_and_purge_outbox", "schedule": 3600.0},
    "purge-idempotency-records": {"task": "idempotency.purge_expired", "schedule": 3600.0},
    "ensure-log-partitions": {"task": "platform_ops.ensure_log_partitions", "schedule": 86400.0},
    "registry-checkpoint": {"task": "platform_ops.write_registry_checkpoint", "schedule": 86400.0},
}

# --- Celery and Redis (DR-2026-11-17-G3-4; CC-R53, CC-R54) ---
REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=None)
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT", default=300)
CELERY_TASK_SOFT_TIME_LIMIT = env.int("CELERY_TASK_SOFT_TIME_LIMIT", default=270)
CELERY_TIMEZONE = "UTC"

# --- Logging (doc 07 §17) ---
LOGGING = build_logging_config(
    level=env("DJANGO_LOG_LEVEL", default="INFO"),
    fmt=env("DJANGO_LOG_FORMAT", default="json"),
)
