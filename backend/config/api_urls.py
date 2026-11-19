"""Routes under /api/v1/ (CLAUDE.md CC-R51; ADR-010). Domain apps add their URLs here."""

from django.urls import include, path

from common.api.health import LivenessView, ReadinessView

urlpatterns = [
    path("health/", LivenessView.as_view(), name="api-health"),
    path("health/ready/", ReadinessView.as_view(), name="api-health-ready"),
    path("auth/", include("apps.accounts.api.urls")),
    path("profiles/", include("apps.profiles.api.urls")),
    path("family-management/", include("apps.family.api.urls")),
]
