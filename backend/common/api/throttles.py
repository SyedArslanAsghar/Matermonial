"""Authentication rate limits (doc 06 §22.1 §8.4; CC-R49).

| Endpoint | Limit (configurable) |
|---|---|
| login | 5 per 15 min per phone+IP, and 20 per 15 min per IP |
| register | 10 per hour per IP |
| OTP send / verify, password forgot / reset | 10 per hour per IP (plus the OTP service's per-phone rules) |
| token refresh | 30 per hour per session |

No hard account lockout; a throttled request gets ``429`` with ``Retry-After``. Cache keys are
keyed hashes (no raw phone numbers or tokens in the cache). The first rejection of each window
records one RATE_LIMIT_TRIGGERED security event (flood control, doc 06 §22.3). Production uses
Redis (deployed settings refuse a per-process cache).
"""

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle

from common.crypto.aead import keyed_hash
from common.crypto.keys import ring


def _digest(*parts: str) -> str:
    return keyed_hash(ring("SUBJECT_HASH").active_key, "\x00".join(parts))


class AuthRateThrottle(SimpleRateThrottle):
    """Rates are ``"<count>/<seconds>"`` (e.g. ``5/900``), read from ``AUTH_RATE_LIMITS``."""

    scope = ""

    def get_rate(self):
        return settings.AUTH_RATE_LIMITS[self.scope]

    def parse_rate(self, rate):
        count, seconds = rate.split("/")
        return int(count), int(seconds)

    def identity(self, request) -> str | None:  # pragma: no cover - overridden
        raise NotImplementedError

    def get_cache_key(self, request, view):
        identity = self.identity(request)
        if identity is None:
            return None
        return f"throttle:{self.scope}:{_digest(self.scope, identity)}"

    def throttle_failure(self):
        from apps.accounts.services.security_events import record_rate_limit_once

        record_rate_limit_once(self.key, actor_type="ANONYMOUS", reason_code=self.scope.upper())
        return False


def _ip(request) -> str:
    return request.META.get("REMOTE_ADDR") or "unknown"


def _phone(request) -> str:
    value = request.data.get("phone_number") if hasattr(request, "data") else None
    return str(value or "").strip()


class LoginPhoneIpThrottle(AuthRateThrottle):
    scope = "login_phone_ip"

    def identity(self, request):
        return f"{_phone(request)}|{_ip(request)}"


class LoginIpThrottle(AuthRateThrottle):
    scope = "login_ip"

    def identity(self, request):
        return _ip(request)


class RegisterIpThrottle(AuthRateThrottle):
    scope = "register_ip"

    def identity(self, request):
        return _ip(request)


class OtpIpThrottle(AuthRateThrottle):
    scope = "otp_ip"

    def identity(self, request):
        return _ip(request)


class PasswordIpThrottle(AuthRateThrottle):
    scope = "password_ip"

    def identity(self, request):
        return _ip(request)


class RefreshSessionThrottle(AuthRateThrottle):
    scope = "refresh_session"

    def identity(self, request):
        token = request.data.get("refresh_token") if hasattr(request, "data") else None
        if not isinstance(token, str) or not token:
            return _ip(request)
        from apps.accounts.models import AuthToken
        from apps.accounts.services.tokens import token_hash

        session_id = (
            AuthToken.objects.filter(token_hash=token_hash(token))
            .values_list("session_id", flat=True)
            .first()
        )
        return f"session:{session_id}" if session_id else f"ip:{_ip(request)}"
