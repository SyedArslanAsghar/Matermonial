"""Fail-closed configuration validation for deployed environments (doc 16 §7, doc 10 G3).

Staging and production refuse to start when required configuration is missing or unsafe.
Only configuration that already exists in G3 is validated here; the compliance-registry,
KEK and queue-key items of doc 16 §10 belong to TR-11/TR-23/TR-24 (PROPOSED) and are added
when those are approved.
"""

from collections.abc import Mapping

from django.core.exceptions import ImproperlyConfigured

INSECURE_DEFAULT_SECRET_KEY = "unsafe-local-only-key-change-me"
MIN_SECRET_KEY_LENGTH = 50
NON_PRODUCTION_PROVIDERS = {"mock"}
NON_PRODUCTION_EMAIL_BACKENDS = {
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.locmem.EmailBackend",
    "django.core.mail.backends.filebased.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
}
SUPPORTED_STORAGE_BACKENDS = {"local"}


def deployed_settings_errors(settings: Mapping, environ: Mapping) -> list[str]:
    """Return every configuration problem that must stop a deployed environment from starting."""
    errors: list[str] = []
    if settings.get("DEBUG"):
        errors.append("DEBUG must be False.")
    secret_key = settings.get("SECRET_KEY") or ""
    if secret_key == INSECURE_DEFAULT_SECRET_KEY or len(secret_key) < MIN_SECRET_KEY_LENGTH:
        errors.append(
            f"DJANGO_SECRET_KEY must be set to a unique value of at least "
            f"{MIN_SECRET_KEY_LENGTH} characters."
        )
    if not settings.get("ALLOWED_HOSTS"):
        errors.append("DJANGO_ALLOWED_HOSTS must be set.")
    if not environ.get("DATABASE_URL"):
        errors.append("DATABASE_URL must be set explicitly (no default database in deployment).")
    # The Celery broker must be configured explicitly: no silent fallback to a localhost Redis
    # (owner decision DR-2026-11-17-G3C-1). Only variable names are reported, never values.
    if not (environ.get("CELERY_BROKER_URL") or environ.get("REDIS_URL")):
        errors.append(
            "CELERY_BROKER_URL or REDIS_URL must be set explicitly "
            "(no default message broker in deployment)."
        )
    for name in ("SMS_PROVIDER", "PUSH_PROVIDER"):
        if settings.get(name) in NON_PRODUCTION_PROVIDERS:
            errors.append(f"{name} must not be a mock provider in a deployed environment.")
    if settings.get("EMAIL_BACKEND") in NON_PRODUCTION_EMAIL_BACKENDS:
        errors.append("EMAIL_BACKEND must not be a console/local/test backend when deployed.")
    if settings.get("STORAGE_BACKEND") not in SUPPORTED_STORAGE_BACKENDS:
        errors.append(
            "STORAGE_BACKEND is not supported; object storage needs an approved dependency. "
            "Never fall back to public storage (doc 16 §7)."
        )
    return errors


def validate_deployed_settings(settings: Mapping, environ: Mapping) -> None:
    errors = deployed_settings_errors(settings, environ)
    if errors:
        raise ImproperlyConfigured(
            "Unsafe or incomplete configuration for a deployed environment:\n- "
            + "\n- ".join(errors)
        )
