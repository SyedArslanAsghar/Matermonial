"""Fail-closed configuration validation for deployed environments (doc 16 §7, doc 10 G3).

Staging and production refuse to start when required configuration is missing or unsafe.
G4 (DR-2026-11-18-G4) adds the key rings and compliance-registry items of doc 16 §10
(TR-11, TR-23, TR-24): deployed environments must configure real keys and a non-local
registry. Errors name settings, never values.
"""

from collections.abc import Mapping

from django.core.exceptions import ImproperlyConfigured

from common.crypto.keys import PURPOSES, KeyConfigurationError, KeyRing, parse_keyring

INSECURE_DEFAULT_SECRET_KEY = "unsafe-local-only-key-change-me"
MIN_SECRET_KEY_LENGTH = 50
NON_PRODUCTION_PROVIDERS = {"mock", "console"}
NON_PRODUCTION_EMAIL_BACKENDS = {
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.locmem.EmailBackend",
    "django.core.mail.backends.filebased.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
}
SUPPORTED_STORAGE_BACKENDS = {"local"}
NON_PRODUCTION_REGISTRY_BACKENDS = {"local", "mock"}


def key_ring_errors(settings: Mapping, environ: Mapping) -> list[str]:
    """Key rings must be set explicitly, well formed, contain the active version and hold no
    dev-only key (TR-23, TR-11, TR-24)."""
    errors = []
    for purpose in PURPOSES:
        name = f"{purpose}_KEYS"
        if not environ.get(name):
            errors.append(f"{name} must be set explicitly (no default keys in deployment).")
            continue
        try:
            ring = KeyRing(
                purpose,
                parse_keyring(settings.get(name, "")),
                settings.get(f"{purpose}_ACTIVE_VERSION"),
            )
        except KeyConfigurationError as exc:
            errors.append(f"{name}: {exc}")
            continue
        if ring.uses_dev_keys():
            errors.append(f"{name} contains a dev-only key.")
    return errors


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
    for name in ("SMS_PROVIDER", "PUSH_PROVIDER", "MALWARE_SCANNER", "EMAIL_PROVIDER"):
        if settings.get(name) in NON_PRODUCTION_PROVIDERS:
            errors.append(f"{name} must not be a mock provider in a deployed environment.")
    errors.extend(provider_configuration_errors(settings))
    if settings.get("EMAIL_BACKEND") in NON_PRODUCTION_EMAIL_BACKENDS:
        errors.append("EMAIL_BACKEND must not be a console/local/test backend when deployed.")
    if settings.get("STORAGE_BACKEND") not in SUPPORTED_STORAGE_BACKENDS:
        errors.append(
            "STORAGE_BACKEND is not supported; object storage needs an approved dependency. "
            "Never fall back to public storage (doc 16 §7)."
        )
    errors.extend(key_ring_errors(settings, environ))
    cache_backend = (settings.get("CACHES") or {}).get("default", {}).get("BACKEND", "")
    if "redis" not in cache_backend.lower():
        errors.append(
            "CACHE_URL must point to Redis when deployed: rate limits must be shared by all "
            "workers (doc 06 §22.1)."
        )
    if settings.get("COMPLIANCE_REGISTRY_BACKEND") in NON_PRODUCTION_REGISTRY_BACKENDS:
        errors.append(
            "COMPLIANCE_REGISTRY_BACKEND must be the approved external registry when deployed "
            "(TR-24; the storage resource needs owner approval before production)."
        )
    return errors


# Variables each real provider needs (DR-2026-11-20-O-7, -8). Names only, never values.
PROVIDER_REQUIREMENTS = {
    ("SMS_PROVIDER", "twilio"): ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "SMS_SENDER_ID"),
    ("EMAIL_PROVIDER", "smtp"): ("EMAIL_HOST", "EMAIL_SENDER"),
    ("PUSH_PROVIDER", "expo"): ("EXPO_PUSH_URL",),
    ("MALWARE_SCANNER", "clamav"): ("CLAMAV_HOST",),
}


def provider_configuration_errors(settings: Mapping) -> list[str]:
    """A selected real provider must be fully configured: no silent fallback to mock,
    console or a half-configured adapter."""
    errors = []
    for (name, choice), required in PROVIDER_REQUIREMENTS.items():
        if settings.get(name) == choice:
            for variable in required:
                if not settings.get(variable):
                    errors.append(f"{variable} must be set when {name}={choice}.")
    if settings.get("PUSH_PROVIDER") == "expo" and not str(
        settings.get("EXPO_PUSH_URL", "")
    ).startswith("https://"):
        errors.append("EXPO_PUSH_URL must use https.")
    return errors


def validate_deployed_settings(settings: Mapping, environ: Mapping) -> None:
    errors = deployed_settings_errors(settings, environ)
    if errors:
        raise ImproperlyConfigured(
            "Unsafe or incomplete configuration for a deployed environment:\n- "
            + "\n- ".join(errors)
        )
