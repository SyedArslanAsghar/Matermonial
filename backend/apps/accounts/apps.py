from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Accounts domain (D01–D03). Lives in apps/accounts (DR-2026-11-17-G3-3).

    The app label stays "accounts" so that AUTH_USER_MODEL = "accounts.User" and the
    database table name are unchanged by the move.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"

    def ready(self):
        from . import schema  # noqa: F401 - registers the OpenAPI authentication extensions
