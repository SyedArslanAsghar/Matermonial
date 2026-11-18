from django.apps import AppConfig


class AuditConfig(AppConfig):
    """Central audit stream (ADR-022, TR-23; doc 03 §16.1 / §22.15). DR-2026-11-18-G4-6."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    label = "audit"
