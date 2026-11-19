"""Django Admin sign-in with mandatory TOTP, and MFA enrollment (TR-07; doc 06 §22.2).

Sign-in needs phone number, password and a TOTP code in one step; every failure shows the same
message (no hint whether the password, the role or the code was wrong). Enrollment needs the
password and an out-of-band enrollment code, shows the seed once, and confirms it with a TOTP
code; the account then signs in normally. Both are rate limited per phone+IP and per IP.
"""

import django_otp
from django import forms
from django.conf import settings
from django.contrib.auth import login as django_login
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from apps.accounts.services.auth import authenticate_credentials, create_admin_session
from apps.accounts.services.security_events import record_security_event
from common.api.auth_errors import AccountUnavailable, InvalidCredentials
from common.api.throttles import allow

from .selectors import has_admin_access
from .services import mfa

GENERIC_ERROR = (
    "Enter a correct phone number, password and authentication code. "
    "Administrators without an authenticator must enroll first."
)
RATE_ERROR = "Too many attempts. Try again later."
PENDING_KEY = "admin_mfa_pending"


class AdminLoginForm(forms.Form):
    phone_number = forms.CharField(max_length=32)
    password = forms.CharField(widget=forms.PasswordInput, max_length=256, strip=False)
    otp_token = forms.CharField(
        label="Authentication code",
        max_length=8,
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric"}),
    )


class EnrollStartForm(forms.Form):
    phone_number = forms.CharField(max_length=32)
    password = forms.CharField(widget=forms.PasswordInput, max_length=256, strip=False)
    enrollment_code = forms.CharField(max_length=64)


class EnrollConfirmForm(forms.Form):
    otp_token = forms.CharField(
        label="Authentication code",
        max_length=8,
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric"}),
    )


def _ip(request) -> str:
    return request.META.get("REMOTE_ADDR") or "unknown"


def _rate_ok(request, scope_prefix: str, phone: str) -> bool:
    # Both counters always advance, so a blocked phone can't be used to probe the IP limit.
    by_phone = allow(f"{scope_prefix}_phone_ip", f"{phone.strip()}|{_ip(request)}")
    by_ip = allow(f"{scope_prefix}_ip", _ip(request))
    return by_phone and by_ip


def _first_factor(request, form) -> object | None:
    try:
        user = authenticate_credentials(
            phone_number=form.cleaned_data["phone_number"],
            password=form.cleaned_data["password"],
            request_id=getattr(request, "request_id", None),
        )
    except (InvalidCredentials, AccountUnavailable):
        return None
    if not has_admin_access(user):
        record_security_event(
            "LOGIN_FAILED",
            "FAILURE",
            actor_type="SELF",
            subject_user_id=user.pk,
            reason_code="ADMIN_NOT_AUTHORIZED",
            request_id=getattr(request, "request_id", None),
        )
        return None
    return user


def _context(site, request, **extra):
    return {**site.each_context(request), "site_header": site.site_header, **extra}


def _safe_next(request) -> str:
    target = request.POST.get("next") or request.GET.get("next") or ""
    if url_has_allowed_host_and_scheme(target, {request.get_host()}, request.is_secure()):
        return target
    return reverse("admin:index")


@sensitive_post_parameters("password", "otp_token")
@csrf_protect
@never_cache
def login_view(request, site):
    if request.method == "GET" and site.has_permission(request):
        return HttpResponseRedirect(reverse("admin:index"))
    form = AdminLoginForm(request.POST or None)
    status = 200
    if request.method == "POST" and form.is_valid():
        if not _rate_ok(request, "admin_login", form.cleaned_data["phone_number"]):
            form.add_error(None, RATE_ERROR)
            status = 429
        else:
            user = _first_factor(request, form)
            device = (
                mfa.verify_login_token(
                    user, form.cleaned_data["otp_token"], getattr(request, "request_id", None)
                )
                if user is not None
                else None
            )
            if device is not None:
                meta = {
                    "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                    "login_ip": request.META.get("REMOTE_ADDR"),
                    "device_name": "Django Admin",
                }
                session = create_admin_session(user, meta, getattr(request, "request_id", None))
                django_login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])
                request.session.set_expiry(settings.ADMIN_SESSION_ABSOLUTE_SECONDS)
                request.session["auth_session_id"] = str(session.id)
                django_otp.login(request, device)
                return HttpResponseRedirect(_safe_next(request))
            form.add_error(None, GENERIC_ERROR)
    elif request.method == "POST":
        form.add_error(None, GENERIC_ERROR)
    context = _context(site, request, form=form, title="Sign in", next=request.GET.get("next", ""))
    return TemplateResponse(request, "admin_access/login.html", context, status=status)


@sensitive_post_parameters("password", "enrollment_code", "otp_token")
@csrf_protect
@never_cache
def enroll_view(request, site):
    """Two steps in one URL: (1) password + enrollment code -> seed shown once;
    (2) TOTP code -> device confirmed. The pending state lives in the anonymous session."""
    pending = request.session.get(PENDING_KEY)
    status = 200
    if pending and request.method == "POST" and "otp_token" in request.POST:
        form = EnrollConfirmForm(request.POST)
        from apps.accounts.models import User

        user = User.objects.filter(pk=pending["user_id"]).first()
        if (
            form.is_valid()
            and user is not None
            and _rate_ok(request, "admin_enroll", user.phone_number)
        ):
            if mfa.confirm_enrollment(
                user,
                pending["device_id"],
                pending["enrollment_id"],
                form.cleaned_data["otp_token"],
                getattr(request, "request_id", None),
            ):
                request.session.flush()
                context = _context(site, request, title="Authenticator enrolled", done=True)
                return TemplateResponse(request, "admin_access/enroll.html", context)
        shown = mfa.pending_secret(user, pending["device_id"]) if user is not None else None
        if shown is None:
            request.session.flush()
            return HttpResponseRedirect(reverse("admin:mfa_enroll"))
        form = EnrollConfirmForm()
        form.add_error(None, "That code didn't match. Check the time on your device and retry.")
        context = _context(
            site,
            request,
            title="Confirm authenticator",
            confirm_form=form,
            secret=shown[0],
            uri=shown[1],
        )
        return TemplateResponse(request, "admin_access/enroll.html", context)

    form = EnrollStartForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not _rate_ok(request, "admin_enroll", form.cleaned_data["phone_number"]):
            form.add_error(None, RATE_ERROR)
            status = 429
        else:
            user = _first_factor(request, form)
            result = None
            if user is not None:
                try:
                    result = mfa.begin_enrollment(
                        user,
                        form.cleaned_data["enrollment_code"],
                        getattr(request, "request_id", None),
                    )
                except (mfa.EnrollmentInvalid, mfa.AlreadyEnrolled):
                    result = None
            if result is not None:
                request.session.cycle_key()
                request.session.set_expiry(15 * 60)
                request.session[PENDING_KEY] = {
                    "user_id": str(user.pk),
                    "device_id": result.device.pk,
                    "enrollment_id": str(result.enrollment_id),
                }
                context = _context(
                    site,
                    request,
                    title="Confirm authenticator",
                    confirm_form=EnrollConfirmForm(),
                    secret=result.secret_base32,
                    uri=result.otpauth_uri,
                )
                return TemplateResponse(request, "admin_access/enroll.html", context)
            form.add_error(None, "Enter a correct phone number, password and enrollment code.")
    context = _context(site, request, title="Enroll an authenticator", start_form=form)
    return TemplateResponse(request, "admin_access/enroll.html", context, status=status)
