"""Standard API error envelope (doc 02 §8; CLAUDE.md CC-R51).

Every error response has the shape::

    {"success": false, "error": {"code": "...", "message": "...", "details": {...}}}

Codes are the DRF exception codes (for example ``not_authenticated``, ``permission_denied``,
``not_found``, ``throttled``, ``invalid``) or the project codes in doc 04 §24.4. Unexpected
exceptions return a generic ``server_error`` and never expose internal details.
"""

import logging

from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class TemporarilyUnavailable(APIException):
    """503 with Retry-After, e.g. when lock-contention retries are exhausted (doc 12 §5.3)."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "temporarily_unavailable"
    default_detail = "The service is temporarily unavailable. Please retry."

    def __init__(self, detail=None, code=None, wait: int = 1):
        super().__init__(detail, code)
        self.wait = wait  # DRF turns `wait` into a Retry-After header.


def error_body(code: str, message: str, details=None) -> dict:
    return {"success": False, "error": {"code": code, "message": message, "details": details or {}}}


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled exception in API view")
        return Response(
            error_body("server_error", "A server error occurred."),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, ValidationError):
        code, message, details = "invalid", "Invalid input.", response.data
    elif isinstance(exc, APIException):
        detail = exc.detail
        code = getattr(detail, "code", None) or exc.default_code
        message, details = str(detail), {}
    else:  # Django Http404 / PermissionDenied, already converted to a response by DRF
        code = "not_found" if response.status_code == 404 else "permission_denied"
        message, details = str(response.data.get("detail", "")), {}

    response.data = error_body(code, message, details)
    return response
