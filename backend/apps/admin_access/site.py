"""The project's Django Admin site (TR-07, ADR-027; doc 06 §15, §22.2).

Built on django-otp's ``OTPAdminSite`` (access only for sessions verified by an OTP device), and
further restricted: the account must have administrative access from the AdminRole tables (or be
a break-glass superuser) and the request must carry a valid ADMIN AuthSession (checked by
``AdminSessionGuardMiddleware``). ``is_staff`` alone never grants access.
"""

from django.contrib.auth import logout as django_logout
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django_otp.admin import OTPAdminSite

from .selectors import has_admin_access


class MatermonialAdminSite(OTPAdminSite):
    site_header = "Matermonial administration"
    site_title = "Matermonial admin"
    index_title = "Administration"
    enable_nav_sidebar = False

    def __init__(self, name="admin"):
        super().__init__(name)

    def has_permission(self, request):
        return (
            super().has_permission(request)  # is_active, is_staff and django-otp verified
            and getattr(request, "admin_session", None) is not None
            and has_admin_access(request.user)
        )

    def get_urls(self):
        from .views import enroll_view

        return [
            path("mfa/enroll/", self.admin_view_public(enroll_view), name="mfa_enroll"),
            *super().get_urls(),
        ]

    def admin_view_public(self, view):
        def wrapped(request, *args, **kwargs):
            return view(request, self, *args, **kwargs)

        return wrapped

    def password_change(self, request, extra_context=None):
        # Passwords change only through the account service (step-up, session revocation,
        # security events; doc 06 §22.1 §8.4), never through an admin form.
        raise PermissionDenied

    def password_change_done(self, request, extra_context=None):
        raise PermissionDenied

    def login(self, request, extra_context=None):
        from .views import login_view

        return login_view(request, self)

    def logout(self, request, extra_context=None):
        if request.method != "POST":  # logout changes state: POST with CSRF only
            return HttpResponseRedirect(reverse("admin:index"))
        session = getattr(request, "admin_session", None)
        if session is not None:
            from apps.accounts.services.auth import revoke_sessions

            revoke_sessions(
                request.user,
                [session],
                "LOGOUT",
                request_id=getattr(request, "request_id", None),
            )
        django_logout(request)
        return HttpResponseRedirect(reverse("admin:login"))
