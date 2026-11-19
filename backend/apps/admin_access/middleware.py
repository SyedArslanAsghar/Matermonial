"""Separate admin session and its per-request checks (doc 06 §22.2: "A separate admin session",
30 min idle, 12 h absolute, MFA at login; TR-07).

``AdminAwareSessionMiddleware`` replaces Django's ``SessionMiddleware``. Under the admin URL
prefix it reads and writes ``ADMIN_SESSION_COOKIE_NAME`` instead of the user web session cookie,
so signing in to the admin never replaces or reuses a user web session (and the reverse).

``AdminSessionGuardMiddleware`` runs after ``OTPMiddleware`` on admin paths. An authenticated
admin request is kept only when all hold; otherwise the admin session is ended:
- the Django session points to an ACTIVE ``AuthSession`` of type ADMIN owned by the user, within
  its idle and absolute limits;
- the account still has administrative access (live role or break-glass superuser);
- the session was verified by a confirmed django-otp device.
"""

import time

from django.conf import settings
from django.contrib.auth import logout as django_logout
from django.contrib.sessions.backends.base import UpdateError
from django.contrib.sessions.exceptions import SessionInterrupted
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.cache import patch_vary_headers
from django.utils.http import http_date

from apps.accounts.models import AuthSession
from apps.accounts.services.auth import mark_expired, session_problem, touch

from .selectors import has_admin_access


def admin_prefix() -> str:
    return "/" + settings.ADMIN_URL_PATH.strip("/") + "/"


def is_admin_path(path: str) -> bool:
    return path.startswith(admin_prefix())


def cookie_name_for(request) -> str:
    if is_admin_path(request.path_info):
        return settings.ADMIN_SESSION_COOKIE_NAME
    return settings.SESSION_COOKIE_NAME


class AdminAwareSessionMiddleware(SessionMiddleware):
    """Django's SessionMiddleware with the cookie name chosen per URL area."""

    def process_request(self, request):
        request.session_cookie_name = cookie_name_for(request)
        request.session = self.SessionStore(request.COOKIES.get(request.session_cookie_name))

    def process_response(self, request, response):
        # Mirrors django.contrib.sessions.middleware.SessionMiddleware.process_response
        # (Django 5.2) with the per-area cookie name.
        name = getattr(request, "session_cookie_name", settings.SESSION_COOKIE_NAME)
        try:
            accessed = request.session.accessed
            modified = request.session.modified
            empty = request.session.is_empty()
        except AttributeError:
            return response
        if name in request.COOKIES and empty:
            response.delete_cookie(
                name,
                path=settings.SESSION_COOKIE_PATH,
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
            need_vary_cookie = True
        else:
            need_vary_cookie = accessed
            if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty:
                if request.session.get_expire_at_browser_close():
                    max_age = expires = None
                else:
                    max_age = request.session.get_expiry_age()
                    expires = http_date(time.time() + max_age)
                if response.status_code < 500:
                    try:
                        request.session.save()
                    except UpdateError:
                        raise SessionInterrupted(
                            "The request's session was deleted before the request completed."
                        ) from None
                    response.set_cookie(
                        name,
                        request.session.session_key,
                        max_age=max_age,
                        expires=expires,
                        domain=settings.SESSION_COOKIE_DOMAIN,
                        path=settings.SESSION_COOKIE_PATH,
                        secure=settings.SESSION_COOKIE_SECURE or None,
                        httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                        samesite=settings.SESSION_COOKIE_SAMESITE,
                    )
                    need_vary_cookie = True
        if need_vary_cookie:
            patch_vary_headers(response, ("Cookie",))
        return response


def admin_session_problem(request) -> str | None:
    """None when the authenticated admin request may proceed, else a reason code."""
    user = request.user
    raw_id = request.session.get("auth_session_id")
    session = AuthSession.objects.filter(pk=raw_id).first() if raw_id else None
    problem = session_problem(session, user.pk)
    if problem is None and session.client_type != AuthSession.ClientType.ADMIN:
        problem = "revoked"
    if problem == "expired" and session is not None:
        mark_expired(session)
    if problem:
        return problem
    if not has_admin_access(user):
        return "no_access"
    if not user.is_verified():
        return "mfa_unverified"
    request.admin_session = session
    touch(session, request.META.get("REMOTE_ADDR"))
    return None


class AdminSessionGuardMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.admin_session = None
        if is_admin_path(request.path_info) and request.user.is_authenticated:
            problem = admin_session_problem(request)
            if problem:
                if problem == "no_access":
                    from .services.roles import CLI, revoke_admin_sessions

                    revoke_admin_sessions(request.user, CLI)
                django_logout(request)  # flushes the admin session; the site asks to sign in
        return self.get_response(request)
