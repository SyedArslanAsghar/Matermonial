from django.apps import AppConfig


class ProfilesConfig(AppConfig):
    """Matrimonial profiles and their sections (Module 02; doc 03 §3, FR-PRO-001…013)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.profiles"
    label = "profiles"
