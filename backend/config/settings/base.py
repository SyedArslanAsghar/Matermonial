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
    # Django Admin with the project's site: MFA (django-otp) and AdminRole authorization
    # (TR-07, ADR-027). Same app label "admin".
    "apps.admin_access.admin_config.MatermonialAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "django_otp",
    # Project domain apps (backend/apps/, DR-2026-11-17-G3-3)
    "apps.accounts",
    "apps.admin_access",
    "apps.audit",
    "apps.platform_ops",
    "apps.profiles",
    "apps.verification",
    # Shared kernel infrastructure (common/, DR-2026-11-18-G4-6)
    "common.events",
    "common.idempotency",
]

MIDDLEWARE = [
    "common.middleware.RequestIDMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Django's SessionMiddleware with a separate admin session cookie (doc 06 §22.2).
    "apps.admin_access.middleware.AdminAwareSessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "apps.admin_access.middleware.AdminSessionGuardMiddleware",
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
# The only backend (TR-07): ModelBackend password checks; permissions only from AdminRole tables.
AUTHENTICATION_BACKENDS = ["apps.admin_access.backends.AdminRoleBackend"]
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
    # TR-01: web = Django session linked to AuthSession; mobile = hashed bearer tokens.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # Bearer first: unauthenticated requests then get 401 with WWW-Authenticate.
        "apps.accounts.authentication.BearerTokenAuthentication",
        "apps.accounts.authentication.WebSessionAuthentication",
    ],
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
# Upload malware scanner (TR-10): "mock" locally and in tests, "disabled" (uploads refused)
# until a real scanner is approved.
MALWARE_SCANNER = env("MALWARE_SCANNER", default="disabled")

# --- Encryption, pseudonymisation and registry keys (TR-23, TR-11, TR-24; doc 16 §10) ---
# Each ring is "<version>:<base64 32-byte key>,..." plus its active version. The defaults are
# DEV-ONLY keys derived from a public label (common.crypto.keys): fine for local development and
# tests, never for real data. Staging and production refuse them (common.config).
for _purpose in ("KEK", "QUEUE", "DEDUPE", "SUBJECT_HASH", "REGISTRY", "OTP", "ROT", "ADMIN_MFA"):
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
# Session and token lifetimes (TR-01; doc 06 §22.2; all configurable).
AUTH_WEB_IDLE_SECONDS = env.int("AUTH_WEB_IDLE_SECONDS", default=2 * 3600)
AUTH_WEB_ABSOLUTE_SECONDS = env.int("AUTH_WEB_ABSOLUTE_SECONDS", default=7 * 86400)
AUTH_MOBILE_ACCESS_SECONDS = env.int("AUTH_MOBILE_ACCESS_SECONDS", default=15 * 60)
AUTH_MOBILE_REFRESH_IDLE_SECONDS = env.int("AUTH_MOBILE_REFRESH_IDLE_SECONDS", default=30 * 86400)
AUTH_MOBILE_ABSOLUTE_SECONDS = env.int("AUTH_MOBILE_ABSOLUTE_SECONDS", default=90 * 86400)
AUTH_REFRESH_GRACE_SECONDS = env.int("AUTH_REFRESH_GRACE_SECONDS", default=15)
AUTH_STEP_UP_WINDOW_SECONDS = env.int("AUTH_STEP_UP_WINDOW_SECONDS", default=300)  # TR-16 later
AUTH_SEEN_WRITE_INTERVAL_SECONDS = 60  # idle extension written at most once a minute
SESSION_COOKIE_AGE = AUTH_WEB_ABSOLUTE_SECONDS  # cookie Max-Age = absolute limit (doc 06 §22.2)
# Django Admin (doc 06 §22.2; TR-07): separate session, 30 min idle / 12 h absolute, TOTP MFA.
ADMIN_URL_PATH = env("ADMIN_URL_PATH", default="admin/")
ADMIN_SESSION_COOKIE_NAME = env("ADMIN_SESSION_COOKIE_NAME", default="mat_admin_session")
ADMIN_SESSION_IDLE_SECONDS = env.int("ADMIN_SESSION_IDLE_SECONDS", default=30 * 60)
ADMIN_SESSION_ABSOLUTE_SECONDS = env.int("ADMIN_SESSION_ABSOLUTE_SECONDS", default=12 * 3600)
ADMIN_MFA_ENROLLMENT_TTL_SECONDS = env.int("ADMIN_MFA_ENROLLMENT_TTL_SECONDS", default=86400)
ADMIN_MFA_THROTTLE_FACTOR = env.int("ADMIN_MFA_THROTTLE_FACTOR", default=1)  # 1, 2, 4, 8 … s
OTP_TOTP_ISSUER = env("OTP_TOTP_ISSUER", default="Matermonial")
# Authentication rate limits, "<count>/<seconds>" (doc 06 §22.1 §8.4; common/api/throttles.py).
AUTH_RATE_LIMITS = {
    "login_phone_ip": env("RATE_LOGIN_PHONE_IP", default="5/900"),
    "login_ip": env("RATE_LOGIN_IP", default="20/900"),
    "register_ip": env("RATE_REGISTER_IP", default="10/3600"),
    "otp_ip": env("RATE_OTP_IP", default="10/3600"),
    "password_ip": env("RATE_PASSWORD_IP", default="10/3600"),
    "refresh_session": env("RATE_REFRESH_SESSION", default="30/3600"),
    "admin_login_phone_ip": env("RATE_ADMIN_LOGIN_PHONE_IP", default="5/900"),
    "admin_login_ip": env("RATE_ADMIN_LOGIN_IP", default="20/900"),
    "admin_enroll_phone_ip": env("RATE_ADMIN_ENROLL_PHONE_IP", default="5/3600"),
    "admin_enroll_ip": env("RATE_ADMIN_ENROLL_IP", default="10/3600"),
}
# Cache: rate limits and flood control. Local/test: in-process; deployed: Redis (validated).
CACHES = {"default": env.cache("CACHE_URL", default="locmemcache://")}
# One-time codes (doc 03 §2.5, doc 06 §3; configurable defaults).
OTP_VALIDITY_SECONDS = env.int("OTP_VALIDITY_SECONDS", default=300)
OTP_RESEND_COOLDOWN_SECONDS = env.int("OTP_RESEND_COOLDOWN_SECONDS", default=60)
OTP_MAX_ATTEMPTS = env.int("OTP_MAX_ATTEMPTS", default=5)
OTP_MAX_SENDS_PER_HOUR = env.int("OTP_MAX_SENDS_PER_HOUR", default=5)
# Periodic kernel jobs (run by celery beat when a worker is used; doc 12 §6, CC-R53).
CELERY_BEAT_SCHEDULE = {
    "process-outbox": {"task": "events.process_outbox", "schedule": 10.0},
    "redact-and-purge-outbox": {"task": "events.redact_and_purge_outbox", "schedule": 3600.0},
    "purge-idempotency-records": {"task": "idempotency.purge_expired", "schedule": 3600.0},
    "ensure-log-partitions": {"task": "platform_ops.ensure_log_partitions", "schedule": 86400.0},
    "registry-checkpoint": {"task": "platform_ops.write_registry_checkpoint", "schedule": 86400.0},
    "admin-role-expiry": {"task": "admin_access.sync_expired_assignments", "schedule": 300.0},
}

# --- Profiles (FR-008; doc 15 §2). Required fields gate DRAFT -> PENDING_REVIEW; the default
# is the assumption in DR-2026-11-19-P3-3 (owner confirmation pending). Photos join with TR-10.
PROFILE_REQUIRED_FIELDS = [
    "basic_info.full_name",
    "basic_info.date_of_birth",
    "basic_info.gender",
    "basic_info.marital_status",
    "basic_info.religion",
    "basic_info.nationality",
    "location.country",
    "location.city",
    "languages",
    "profession.employment_status",
]
PROFILE_OPTIONAL_FIELDS = [
    "location.state_or_province",
    "education",
    "profession.profession",
    "family.family_type",
    "lifestyle.height_cm",
    "lifestyle.diet",
]

# Photo pipeline (TR-10; DR-2026-11-19-P3-1). Defaults are documented assumptions.
PHOTO_MAX_UPLOAD_BYTES = env.int("PHOTO_MAX_UPLOAD_BYTES", default=10 * 1024 * 1024)
PHOTO_MAX_PIXELS = env.int("PHOTO_MAX_PIXELS", default=40_000_000)  # decompression-bomb guard
PHOTO_MAX_EDGE = env.int("PHOTO_MAX_EDGE", default=2048)  # stored long edge, pixels
PHOTO_MIN_EDGE = env.int("PHOTO_MIN_EDGE", default=200)
PHOTO_MAX_PER_PROFILE = env.int("PHOTO_MAX_PER_PROFILE", default=6)

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
