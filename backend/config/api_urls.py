"""Routes under /api/v1/ (CLAUDE.md CC-R51; ADR-010). Domain apps add their URLs here."""

from django.urls import path

from common.api.health import LivenessView, ReadinessView

urlpatterns = [
    path("health/", LivenessView.as_view(), name="api-health"),
    path("health/ready/", ReadinessView.as_view(), name="api-health-ready"),
]
