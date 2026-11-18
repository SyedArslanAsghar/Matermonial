from django.apps import AppConfig


class VerificationConfig(AppConfig):
    """Phone and identity verification (D03, D06; Module 04). Phone OTP: G5 Phase 2."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.verification"
    label = "verification"
