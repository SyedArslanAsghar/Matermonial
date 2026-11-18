"""DRF authentication for web sessions and mobile bearer tokens (TR-01; doc 06 §22.1).

Every authenticated request checks, in order: one credential type only; the AuthSession is
ACTIVE, belongs to the user, and neither its idle nor its absolute limit has passed; the account
is active (account-state gate). Failures flush the web session and answer ``401
session_revoked`` / ``session_expired`` / ``invalid_token``.
"""

from django.conf import settings
from django.contrib.auth import logout as django_logout
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, SessionAuthentication

from common.api.auth_errors import (
    AccountUnavailable,
    AmbiguousCredentials,
    InvalidToken,
    SessionExpired,
    SessionRevoked,
)

from .models import AuthSession, AuthToken
from .services.auth import mark_expired, session_problem, touch
from .services.tokens import ACCESS_PREFIX, looks_like, token_hash


def _bearer(request) -> str | None:
    header = request.META.get("HTTP_AUTHORIZATION", "")
    scheme, _, value = header.partition(" ")
    return value.strip() if scheme.lower() == "bearer" and value.strip() else None


def _client_ip(request) -> str | None:
    return request.META.get("REMOTE_ADDR")


def _reject_if_both(request) -> None:
    if _bearer(request) and settings.SESSION_COOKIE_NAME in request.COOKIES:
        raise AmbiguousCredentials()


class WebSessionAuthentication(SessionAuthentication):
    """Django session + AuthSession link; CSRF enforced by the parent class."""

    def authenticate(self, request):
        _reject_if_both(request)
        result = super().authenticate(request)  # enforces CSRF for authenticated sessions
        if result is None:
            return None
        user, _ = result
        raw_id = request._request.session.get("auth_session_id")
        session = AuthSession.objects.filter(pk=raw_id).first() if raw_id else None
        problem = session_problem(session, user.pk)
        if problem:
            if session is not None and problem == "expired":
                mark_expired(session)
            django_logout(request._request)
            raise SessionExpired() if problem == "expired" else SessionRevoked()
        if not user.is_active:
            django_logout(request._request)
            raise AccountUnavailable()
        touch(session, _client_ip(request))
        request._request.auth_session = session
        return user, session


class BearerTokenAuthentication(BaseAuthentication):
    """``Authorization: Bearer mat_at_…``: hashed lookup, never plaintext storage."""

    keyword = "Bearer"

    def authenticate_header(self, request):
        return self.keyword  # keeps 401 (not 403) for unauthenticated requests

    def authenticate(self, request):
        value = _bearer(request)
        if value is None:
            return None
        _reject_if_both(request)
        if not looks_like(value, ACCESS_PREFIX):
            raise InvalidToken()
        token = (
            AuthToken.objects.select_related("session__user")
            .filter(token_hash=token_hash(value), token_type="ACCESS")
            .first()
        )
        if token is None or token.revoked_at is not None:
            raise InvalidToken() if token is None else SessionRevoked()
        session, user = token.session, token.session.user
        problem = session_problem(session, user.pk)
        if problem == "revoked":
            raise SessionRevoked()
        # The access token is independent of rotation; it lives to its own expiry (doc 06 §8.3).
        if problem == "expired" or token.expires_at <= timezone.now():
            if problem == "expired":
                mark_expired(session)
            raise SessionExpired()
        if not user.is_active:
            raise AccountUnavailable()
        touch(session, _client_ip(request))
        request._request.auth_session = session
        return user, session
