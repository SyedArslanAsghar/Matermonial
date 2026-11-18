from django.apps import AppConfig


class IdempotencyConfig(AppConfig):
    """IdempotencyRecord (TR-11; DR-2026-11-18-G4-6)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "common.idempotency"
    label = "idempotency"
