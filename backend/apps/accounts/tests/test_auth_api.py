"""G5 Phase 2b: registration, OTP endpoints, login, logout, session checks (TR-01; T-AUTH)."""

import logging
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AccountSecurityEvent, AuthSession, AuthToken, User
from apps.accounts.services.auth import revoke_sessions
from common.events.models import OutboxEvent
from common.providers import MockSMSProvider

PHONE, PASSWORD = "+923001234567", "Correct-Horse-Battery-9"
pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(phone_number=PHONE, password=PASSWORD)


def csrf_client() -> tuple[APIClient, str]:
    client = APIClient(enforce_csrf_checks=True)
    token = client.get("/api/v1/auth/csrf/").json()["csrf_token"]
    return client, token


def web_login(phone=PHONE, password=PASSWORD):
    client, token = csrf_client()
    response = client.post(
        "/api/v1/auth/login/",
        {"phone_number": phone, "password": password},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    return client, response, token


def mobile_login(phone=PHONE, password=PASSWORD):
    return APIClient().post(
        "/api/v1/auth/login/",
        {"phone_number": phone, "password": password, "client": "mobile", "platform": "android"},
        format="json",
    )


def error_code(response):
    return response.json()["error"]["code"]


class TestRegistration:
    def test_new_account_is_unverified_and_gets_a_code(self, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            response = APIClient().post(
                "/api/v1/auth/register/",
                {"phone_number": PHONE, "password": PASSWORD, "email": "A@Example.com"},
                format="json",
            )
        assert response.status_code == 202
        user = User.objects.get(phone_number=PHONE)
        assert user.is_phone_verified is False and user.email == "a@example.com"
        assert user.check_password(PASSWORD) and len(MockSMSProvider.sent) == 1

    def test_existing_phone_gets_the_identical_answer_and_nothing_happens(
        self, user, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            response = APIClient().post(
                "/api/v1/auth/register/",
                {"phone_number": PHONE, "password": PASSWORD},
                format="json",
            )
        assert response.status_code == 202
        assert response.json() == {
            "detail": "If the details can be used, a verification code has been sent."
        }
        assert User.objects.count() == 1 and MockSMSProvider.sent == []

    @pytest.mark.parametrize(
        ("payload", "field"),
        [({"password": "password"}, "password"), ({"phone_number": "0300123"}, "phone_number")],
    )
    def test_weak_password_and_bad_phone_are_rejected(self, payload, field):
        body = {"phone_number": PHONE, "password": PASSWORD, **payload}
        response = APIClient().post("/api/v1/auth/register/", body, format="json")
        assert response.status_code == 400 and field in response.json()["error"]["details"]
        assert not User.objects.exists()


class TestOtpEndpoints:
    def code(self):
        return MockSMSProvider.sent[-1]["message"].split("code is ")[1][:6]

    def test_verify_marks_the_phone_verified(self, user, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            APIClient().post("/api/v1/auth/otp/send/", {"phone_number": PHONE}, format="json")
        response = APIClient().post(
            "/api/v1/auth/otp/verify/", {"phone_number": PHONE, "code": self.code()}, format="json"
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_phone_verified

    def test_wrong_and_unknown_get_the_same_error(self, user, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            APIClient().post("/api/v1/auth/otp/send/", {"phone_number": PHONE}, format="json")
        wrong = "000000" if self.code() != "000000" else "111111"
        a = APIClient().post("/api/v1/auth/otp/verify/", {"phone_number": PHONE, "code": wrong})
        b = APIClient().post(
            "/api/v1/auth/otp/verify/", {"phone_number": "+923009999999", "code": wrong}
        )
        assert a.status_code == b.status_code == 400 and a.json() == b.json()
        assert error_code(a) == "invalid_code"

    def test_send_is_silent_for_unknown_or_verified_phones(self, user):
        User.objects.filter(pk=user.pk).update(is_phone_verified=True)
        for phone in (PHONE, "+923009999999"):
            response = APIClient().post("/api/v1/auth/otp/send/", {"phone_number": phone})
            assert response.status_code == 202
        assert MockSMSProvider.sent == []


class TestWebLogin:
    def test_login_requires_csrf(self, user):
        client = APIClient(enforce_csrf_checks=True)
        response = client.post(
            "/api/v1/auth/login/", {"phone_number": PHONE, "password": PASSWORD}, format="json"
        )
        assert response.status_code == 403
        assert not AuthSession.objects.exists()

    def test_login_links_a_rotated_session_and_records_events(self, user):
        client, token = csrf_client()
        before = client.cookies.get("sessionid")
        response = client.post(
            "/api/v1/auth/login/",
            {"phone_number": PHONE, "password": PASSWORD},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 200 and response.json()["account"]["phone_number"] == PHONE
        session_key = client.cookies["sessionid"].value
        assert before is None or before.value != session_key  # rotated (fixation)
        auth_session = AuthSession.objects.get()
        assert auth_session.client_type == "WEB" and auth_session.status == "ACTIVE"
        assert session_key not in str(AuthSession.objects.values().get())  # T-AUTH-012
        types = set(AccountSecurityEvent.objects.values_list("event_type", flat=True))
        assert {"LOGIN_SUCCEEDED", "SESSION_CREATED"} <= types
        assert OutboxEvent.objects.filter(event_type="security.new_sign_in").count() == 1
        assert client.get("/api/v1/auth/me/").json()["phone_number"] == PHONE

    def test_failures_are_generic_and_recorded(self, user):
        _, wrong, _ = web_login(password="wrong-password-1")
        _, unknown, _ = web_login(phone="+923009999999")
        assert wrong.status_code == unknown.status_code == 401
        assert wrong.json() == unknown.json() and error_code(wrong) == "invalid_credentials"
        failed = AccountSecurityEvent.objects.filter(event_type="LOGIN_FAILED")
        assert failed.filter(subject_hash__isnull=False).count() == 1  # the unknown phone
        assert not AuthSession.objects.exists()

    def test_deactivated_account_is_denied(self, user):
        user.deactivated = True
        user.save()
        _, response, _ = web_login()
        assert response.status_code == 403 and error_code(response) == "account_unavailable"
        assert AccountSecurityEvent.objects.filter(event_type="LOGIN_DENIED_ACCOUNT_STATE").exists()

    def test_revoked_session_is_rejected_on_the_next_request(self, user):
        client, _, _ = web_login()
        revoke_sessions(user, AuthSession.objects.all(), "USER_REVOKED")
        response = client.get("/api/v1/auth/me/")
        assert response.status_code == 401 and error_code(response) == "session_revoked"
        assert client.get("/api/v1/auth/me/").status_code == 401  # session was flushed

    def test_idle_expiry_ends_the_session(self, user):
        client, _, _ = web_login()
        AuthSession.objects.update(idle_expires_at=timezone.now() - timedelta(seconds=1))
        response = client.get("/api/v1/auth/me/")
        assert response.status_code == 401 and error_code(response) == "session_expired"
        assert AuthSession.objects.get().status == "EXPIRED"

    def test_mismatched_auth_session_is_rejected(self, user):
        client, _, _ = web_login()
        other = User.objects.create_user(phone_number="+923001234568", password=PASSWORD)
        _, _, _ = web_login(phone="+923001234568")
        foreign = AuthSession.objects.get(user=other)
        session = client.session
        session["auth_session_id"] = str(foreign.id)
        session.save()
        assert client.get("/api/v1/auth/me/").status_code == 401  # T-AUTH-010

    def test_logout_revokes_and_is_idempotent(self, user):
        client, _, old_token = web_login()
        token = client.cookies["csrftoken"].value  # Django rotates the CSRF token at login
        assert token != old_token
        assert client.post("/api/v1/auth/logout/", HTTP_X_CSRFTOKEN=old_token).status_code == 403
        response = client.post("/api/v1/auth/logout/", HTTP_X_CSRFTOKEN=token)
        assert response.status_code == 204
        assert AuthSession.objects.get().revoked_reason == "LOGOUT"
        assert client.get("/api/v1/auth/me/").status_code == 401

    def test_unauthenticated_requests_get_401(self):
        response = APIClient().get("/api/v1/auth/me/")
        assert response.status_code == 401 and response["WWW-Authenticate"] == "Bearer"


class TestMobileLogin:
    def test_tokens_are_returned_once_and_stored_as_hashes(self, user, caplog):
        with caplog.at_level(logging.DEBUG):
            body = mobile_login().json()
        access, refresh = body["access_token"], body["refresh_token"]
        assert access.startswith("mat_at_") and refresh.startswith("mat_rt_")
        stored = str(list(AuthToken.objects.values()))
        assert access not in stored and refresh not in stored
        assert access not in caplog.text and refresh not in caplog.text  # T-AUTH-042
        assert AuthSession.objects.get().key_version_current == 1

    def test_bearer_authentication_and_logout(self, user):
        access = mobile_login().json()["access_token"]
        client = APIClient(HTTP_AUTHORIZATION=f"Bearer {access}")
        assert client.get("/api/v1/auth/me/").status_code == 200
        assert client.post("/api/v1/auth/logout/").status_code == 204
        assert not AuthToken.objects.filter(revoked_at__isnull=True).exists()
        response = client.get("/api/v1/auth/me/")
        assert response.status_code == 401 and error_code(response) == "session_revoked"

    def test_bad_and_expired_tokens(self, user):
        bad = APIClient(HTTP_AUTHORIZATION="Bearer mat_at_" + "x" * 43).get("/api/v1/auth/me/")
        assert bad.status_code == 401 and error_code(bad) == "invalid_token"
        access = mobile_login().json()["access_token"]
        AuthToken.objects.filter(token_type="ACCESS").update(
            issued_at=timezone.now() - timedelta(hours=1), expires_at=timezone.now()
        )
        expired = APIClient(HTTP_AUTHORIZATION=f"Bearer {access}").get("/api/v1/auth/me/")
        assert expired.status_code == 401 and error_code(expired) == "session_expired"

    def test_cookie_and_bearer_together_are_rejected(self, user):
        client, _, _ = web_login()
        access = mobile_login().json()["access_token"]
        response = client.get("/api/v1/auth/me/", HTTP_AUTHORIZATION=f"Bearer {access}")
        assert response.status_code == 400 and error_code(response) == "ambiguous_credentials"

    def test_deactivation_blocks_existing_tokens(self, user):
        access = mobile_login().json()["access_token"]
        user.deactivated = True
        user.save()
        response = APIClient(HTTP_AUTHORIZATION=f"Bearer {access}").get("/api/v1/auth/me/")
        assert response.status_code == 403 and error_code(response) == "account_unavailable"
