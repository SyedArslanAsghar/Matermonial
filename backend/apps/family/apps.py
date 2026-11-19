from django.apps import AppConfig


class FamilyConfig(AppConfig):
    """Family management (Module 05; doc 03 §6, doc 05 §2, doc 14, doc 15 §4; FR-FAM-001…009)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.family"
    label = "family"
