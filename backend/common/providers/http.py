"""Minimal HTTPS client for provider adapters (standard library; no new dependency).

Timeouts are always set. Errors become ``ProviderError`` with a retryable flag; response bodies
are returned to the adapter but never logged here."""

import json
import urllib.error
import urllib.parse
import urllib.request

from .base import ProviderError

RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


def post(
    url: str,
    *,
    form: dict | None = None,
    json_body=None,
    headers: dict | None = None,
    timeout: float = 10.0,
) -> tuple[int, dict]:
    if not url.startswith("https://"):
        raise ProviderError("insecure_url", retryable=False)
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        content_type = "application/x-www-form-urlencoded"
    else:
        data = json.dumps(json_body).encode()
        content_type = "application/json"
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": content_type, "Accept": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - https only
            return response.status, _json(response.read())
    except urllib.error.HTTPError as exc:
        raise ProviderError(f"http_{exc.code}", retryable=exc.code in RETRYABLE_STATUS) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ProviderError("network_error", retryable=True) from None


def _json(raw: bytes) -> dict:
    try:
        value = json.loads(raw or b"{}")
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {"data": value}
