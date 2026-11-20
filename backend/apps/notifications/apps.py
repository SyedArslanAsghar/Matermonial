from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """In-app notifications and push delivery (FR-NOT; owner decision DR-2026-11-20-O-7).
    Outbox handlers are registered on ready()."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    label = "notifications"

    def ready(self):
        from . import handlers  # noqa: F401 - registers the outbox handlers
