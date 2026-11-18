from django.apps import AppConfig


class PlatformOpsConfig(AppConfig):
    """Platform operations (ADR-023, D22): TR-24 maintenance protocol and compliance registry.

    Maintenance tables are their own lock domain: no business transaction touches them (doc 09
    §19.2). Placement: DR-2026-11-18-G4-6.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.platform_ops"
    label = "platform_ops"
