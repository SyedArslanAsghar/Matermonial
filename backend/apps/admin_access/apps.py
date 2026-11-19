from django.apps import AppConfig


class AdminAccessConfig(AppConfig):
    """Administrative authorization from a single source (TR-07, ADR-027; doc 03 §16.2-16.5,
    §22.15). Separate from end-user accounts and family-manager authorization."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admin_access"
    label = "admin_access"
