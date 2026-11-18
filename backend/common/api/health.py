"""Health endpoints (doc 10 G3; doc 02 §16; doc 09).

- Liveness  ``GET /api/v1/health/``: the process is serving requests. No dependencies.
- Readiness ``GET /api/v1/health/ready/``: the database answers ``SELECT 1``.

Neither endpoint returns configuration, versions of dependencies or error details.
"""

import logging

from django.db import connection
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)
SERVICE_NAME = "matermonial-api"


class LivenessView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, summary="Liveness check")
    def get(self, request):
        return Response({"status": "ok", "service": SERVICE_NAME, "api_version": "v1"})


class ReadinessView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        responses={200: OpenApiTypes.OBJECT, 503: OpenApiTypes.OBJECT}, summary="Readiness check"
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            logger.warning("Readiness check failed: database unavailable", exc_info=True)
            return Response(
                {"status": "unavailable", "checks": {"database": "unavailable"}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ok", "checks": {"database": "ok"}})
