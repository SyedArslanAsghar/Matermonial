import json
import logging
from unittest import mock

from django.http import Http404, HttpResponse
from django.test import RequestFactory
from rest_framework import exceptions
from rest_framework.test import APIRequestFactory

from common.api.exceptions import TemporarilyUnavailable, exception_handler
from common.api.pagination import StandardPagination
from common.logs import JSONFormatter, RequestIDFilter, request_id_var
from common.middleware import REQUEST_ID_HEADER, RequestIDMiddleware


def _envelope(response):
    assert response.data["success"] is False
    return response.data["error"]


# --- Health (liveness needs no database) ---


def test_liveness(api_client):
    response = api_client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "matermonial-api", "api_version": "v1"}
    assert len(response[REQUEST_ID_HEADER]) >= 8


def test_readiness_reports_unavailable_database_without_details(api_client):
    with mock.patch("common.api.health.connection") as conn:
        conn.cursor.side_effect = RuntimeError("connection refused: secret-host")
        response = api_client.get("/api/v1/health/ready/")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "checks": {"database": "unavailable"}}


def test_readiness_ok_when_database_answers(api_client):
    with mock.patch("common.api.health.connection") as conn:
        response = api_client.get("/api/v1/health/ready/")
    assert response.status_code == 200
    assert response.json()["checks"] == {"database": "ok"}
    conn.cursor.return_value.__enter__.return_value.execute.assert_called_once_with("SELECT 1")


def test_unknown_api_route_returns_404(api_client):
    response = api_client.get("/api/v1/does-not-exist/")
    assert response.status_code == 404


def test_api_docs_served_when_enabled(api_client):
    assert api_client.get("/api/schema/").status_code == 200


# --- Error envelope (doc 02 §8) ---


def test_validation_error_envelope():
    response = exception_handler(exceptions.ValidationError({"phone_number": ["Required."]}), {})
    error = _envelope(response)
    assert response.status_code == 400
    assert error["code"] == "invalid"
    assert error["details"] == {"phone_number": ["Required."]}


def test_authentication_and_permission_envelopes():
    assert _envelope(exception_handler(exceptions.NotAuthenticated(), {}))["code"] == (
        "not_authenticated"
    )
    response = exception_handler(exceptions.PermissionDenied(), {})
    assert response.status_code == 403
    assert _envelope(response)["code"] == "permission_denied"


def test_django_404_is_converted():
    response = exception_handler(Http404(), {})
    assert response.status_code == 404
    assert _envelope(response)["code"] == "not_found"


def test_unhandled_exception_hides_internals(caplog):
    with caplog.at_level(logging.ERROR):
        response = exception_handler(ValueError("database password is hunter2"), {})
    error = _envelope(response)
    assert response.status_code == 500
    assert error == {"code": "server_error", "message": "A server error occurred.", "details": {}}


def test_temporarily_unavailable_has_retry_after():
    response = exception_handler(TemporarilyUnavailable(wait=2), {})
    assert response.status_code == 503
    assert response["Retry-After"] == "2"
    assert _envelope(response)["code"] == "temporarily_unavailable"


def test_throttled_keeps_retry_after():
    response = exception_handler(exceptions.Throttled(wait=30), {})
    assert response.status_code == 429
    assert response["Retry-After"] == "30"
    assert _envelope(response)["code"] == "throttled"


# --- Pagination (doc 04 §16) ---


def test_pagination_shape_and_maximum(settings):
    settings.API_MAX_PAGE_SIZE = 5
    request = APIRequestFactory().get("/items/", {"page_size": 50})
    from rest_framework.request import Request

    paginator = StandardPagination()
    page = paginator.paginate_queryset(list(range(12)), Request(request))
    assert page == [0, 1, 2, 3, 4]  # capped at the maximum
    data = paginator.get_paginated_response(page).data
    assert set(data) == {"count", "next", "previous", "results"}
    assert data["count"] == 12


# --- Request correlation and structured logs (doc 07 §17) ---


def _run_middleware(header=None):
    seen = {}

    def view(request):
        seen["request_id"] = request_id_var.get()
        return HttpResponse("ok")

    headers = {"HTTP_X_REQUEST_ID": header} if header is not None else {}
    response = RequestIDMiddleware(view)(RequestFactory().get("/", **headers))
    return response, seen["request_id"]


def test_request_id_generated_when_missing():
    response, inside = _run_middleware()
    assert response[REQUEST_ID_HEADER] == inside
    assert len(inside) == 32
    assert request_id_var.get() is None  # reset after the request


def test_valid_incoming_request_id_is_kept():
    response, inside = _run_middleware("abc12345-request")
    assert inside == "abc12345-request" == response[REQUEST_ID_HEADER]


def test_malformed_incoming_request_id_is_replaced():
    response, inside = _run_middleware("<script>alert(1)</script>")
    assert inside != "<script>alert(1)</script>"
    assert len(inside) == 32


def test_json_log_line_carries_request_id():
    token = request_id_var.set("req-12345678")
    try:
        record = logging.LogRecord(
            "app", logging.INFO, __file__, 1, "Payment confirmed", None, None
        )
        RequestIDFilter().filter(record)
        line = json.loads(JSONFormatter().format(record))
    finally:
        request_id_var.reset(token)
    assert line["request_id"] == "req-12345678"
    assert line["message"] == "Payment confirmed"
    assert {"timestamp", "level", "logger", "module"} <= set(line)
