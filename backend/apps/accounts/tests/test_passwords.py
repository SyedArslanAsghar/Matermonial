"""G5 Phase 2d: password reset and change (doc 06 §22.1 §8.4; T-AUTH-032)."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AccountSecurityEvent, AuthSession, User
from common.events.models import OutboxEvent
from common.providers import MockSMSProvider

PHONE, PASSWORD, NEW = "+923001234567", "Correct-Horse-Battery-9", "Another-Long-Secret-42"
pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(phone_number=PHONE, password=PASSWORD)


def mobile_login(password=PASSWORD):
    return APIClient().post(
        "/api/v1/auth/login/",
        {"phone_number": PHONE, "password": password, "client": "mobile"},
        format="json",
    )


def forgot(capture, phone=PHONE):
    with capture(execute=True):
        return APIClient().post("/api/v1/auth/password/forgot/", {"phone_number": phone})


def code():
    return MockSMSProvider.sent[-1]["message"].split("code is ")[1][:6]


def reset(code_value, password=NEW, phone=PHONE):
    return APIClient().post(
        "/api/v1/auth/password/reset/",
        {"phone_number": phone, "code": code_value, "new_password": password},
        format="json",
    )


class TestReset:
    def test_reset_sets_the_password_and_revokes_every_session(
        self, user, django_capture_on_commit_callbacks
    ):
        access = mobile_login().json()["access_token"]
        mobile_login()
        assert forgot(django_capture_on_commit_callbacks).status_code == 202
        assert reset(code()).status_code == 200
        user.refresh_from_db()
        assert user.check_password(NEW)
        assert not AuthSession.objects.filter(status="ACTIVE").exists()  # T-AUTH-032
        assert set(AuthSession.objects.values_list("revoked_reason", flat=True)) == {
            "PASSWORD_RESET"
        }
        bearer = APIClient(HTTP_AUTHORIZATION=f"Bearer {access}")
        assert bearer.get("/api/v1/auth/me/").status_code == 401
        types = set(AccountSecurityEvent.objects.values_list("event_type", flat=True))
        assert {"PASSWORD_RESET_REQUESTED", "PASSWORD_RESET_COMPLETED"} <= types
        assert OutboxEvent.objects.filter(event_type="security.password_reset").exists()
        assert mobile_login(NEW).status_code == 200  # no automatic login; new password works

    def test_code_is_single_use(self, user, django_capture_on_commit_callbacks):
        forgot(django_capture_on_commit_callbacks)
        value = code()
        assert reset(value).status_code == 200
        assert reset(value, password="Yet-Another-Secret-77").status_code == 400

    def test_unknown_phone_is_indistinguishable(self, user, django_capture_on_commit_callbacks):
        known = forgot(django_capture_on_commit_callbacks)
        unknown = forgot(django_capture_on_commit_callbacks, phone="+923009999999")
        assert known.status_code == unknown.status_code == 202
        assert known.json() == unknown.json()
        assert len(MockSMSProvider.sent) == 1
        a, b = reset("123456", phone="+923009999999"), reset("123456")
        assert a.status_code == b.status_code == 400 and a.json() == b.json()

    def test_wrong_code_is_recorded_and_password_unchanged(
        self, user, django_capture_on_commit_callbacks
    ):
        forgot(django_capture_on_commit_callbacks)
        wrong = "000000" if code() != "000000" else "111111"
        assert reset(wrong).status_code == 400
        user.refresh_from_db()
        assert user.check_password(PASSWORD)
        assert AccountSecurityEvent.objects.filter(event_type="PASSWORD_RESET_FAILED").exists()

    def test_weak_password_does_not_consume_the_code(
        self, user, django_capture_on_commit_callbacks
    ):
        forgot(django_capture_on_commit_callbacks)
        value = code()
        weak = reset(value, password="password")
        assert weak.status_code == 400 and "new_password" in weak.json()["error"]["details"]
        assert reset(value).status_code == 200

    def test_deactivated_account_gets_no_code(self, user, django_capture_on_commit_callbacks):
        user.deactivated = True
        user.save()
        assert forgot(django_capture_on_commit_callbacks).status_code == 202
        assert MockSMSProvider.sent == []


class TestChange:
    def client_with_step_up(self):
        access = mobile_login().json()["access_token"]
        client = APIClient(HTTP_AUTHORIZATION=f"Bearer {access}")
        client.post("/api/v1/auth/reauthenticate/", {"password": PASSWORD}, format="json")
        return client

    def change(self, client, current=PASSWORD, new=NEW):
        return client.post(
            "/api/v1/auth/password/change/",
            {"current_password": current, "new_password": new},
            format="json",
        )

    def test_change_keeps_the_current_session_and_revokes_others(self, user):
        other_access = mobile_login().json()["access_token"]
        client = self.client_with_step_up()
        assert self.change(client).status_code == 200
        user.refresh_from_db()
        assert user.check_password(NEW)
        assert client.get("/api/v1/auth/me/").status_code == 200
        other = APIClient(HTTP_AUTHORIZATION=f"Bearer {other_access}")
        assert other.get("/api/v1/auth/me/").status_code == 401
        assert AccountSecurityEvent.objects.filter(event_type="PASSWORD_CHANGED").exists()

    def test_change_requires_a_recent_step_up(self, user):
        access = mobile_login().json()["access_token"]
        client = APIClient(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = self.change(client)
        assert (
            response.status_code == 403 and response.json()["error"]["code"] == "step_up_required"
        )
        client.post("/api/v1/auth/reauthenticate/", {"password": PASSWORD}, format="json")
        AuthSession.objects.update(reauthenticated_at=timezone.now() - timedelta(minutes=10))
        assert self.change(client).status_code == 403

    def test_wrong_current_password_fails(self, user):
        client = self.client_with_step_up()
        response = self.change(client, current="not-the-password")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_password"
        assert AccountSecurityEvent.objects.filter(event_type="PASSWORD_CHANGE_FAILED").exists()

    def test_web_change_keeps_the_web_session(self, user):
        client = APIClient(enforce_csrf_checks=True)
        token = client.get("/api/v1/auth/csrf/").json()["csrf_token"]
        client.post(
            "/api/v1/auth/login/",
            {"phone_number": PHONE, "password": PASSWORD},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        csrf = client.cookies["csrftoken"].value
        client.post(
            "/api/v1/auth/reauthenticate/",
            {"password": PASSWORD},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        response = client.post(
            "/api/v1/auth/password/change/",
            {"current_password": PASSWORD, "new_password": NEW},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        assert response.status_code == 200
        assert client.get("/api/v1/auth/me/").status_code == 200  # session hash updated
