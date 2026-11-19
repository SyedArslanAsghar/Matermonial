"""G5 Phase 2e-3: mandatory admin MFA (django-otp TOTP), enrollment and recovery, and the
separate admin session with 30 min idle / 12 h absolute limits (TR-07; doc 06 §15, §22.2)."""

import re
import time
from datetime import timedelta

import pytest
from django.conf import settings
from django.db import connection
from django.test import Client
from django.utils import timezone
from django_otp.oath import TOTP
from rest_framework.test import APIClient

from apps.accounts.models import AccountSecurityEvent, AuthSession, User
from apps.admin_access.models import AdminMfaEnrollment, AdminTotpDevice
from apps.admin_access.services import mfa
from apps.admin_access.services.catalogue import sync_catalogue
from apps.admin_access.services.roles import (
    CLI,
    Actor,
    InvalidTarget,
    NotAuthorized,
    assign_role,
    revoke_role,
)
from apps.admin_access.services.superusers import grant_superuser
from common.crypto.aead import DecryptionError

PASSWORD = "Correct-Horse-Battery-9"
LOGIN, INDEX, ENROLL = "/admin/login/", "/admin/", "/admin/mfa/enroll/"
pytestmark = pytest.mark.django_db


def make_user(n: int) -> User:
    return User.objects.create_user(phone_number=f"+92300400{n:04d}", password=PASSWORD)


def code_for(device: AdminTotpDevice, steps_ahead: int = 0) -> str:
    device.refresh_from_db()
    totp = TOTP(mfa._seed(device), device.step, 0, device.digits, device.drift)
    totp.time = time.time() + steps_ahead * device.step
    return f"{totp.token():0{device.digits}d}"


def enroll(user: User) -> AdminTotpDevice:
    code = mfa.issue_enrollment(CLI, user)
    pending = mfa.begin_enrollment(user, code)
    assert mfa.confirm_enrollment(
        user, pending.device.pk, pending.enrollment_id, code_for(pending.device)
    )
    return AdminTotpDevice.objects.get(user=user)


def admin_login(
    client: Client, user: User, device: AdminTotpDevice, steps_ahead=1, password=PASSWORD
):
    return client.post(
        LOGIN,
        {
            "phone_number": user.phone_number,
            "password": password,
            "otp_token": code_for(device, steps_ahead),
        },
    )


def events(event_type: str, reason: str | None = None):
    rows = AccountSecurityEvent.objects.filter(event_type=event_type)
    return rows.filter(reason_code=reason) if reason else rows


@pytest.fixture
def admin():
    sync_catalogue(CLI)
    user = make_user(1)
    assign_role(CLI, user, "system_admin")
    return User.objects.get(pk=user.pk)


@pytest.fixture
def enrolled(admin):
    return admin, enroll(admin)


class TestEnrollment:
    def test_seed_is_encrypted_and_bound_to_the_account(self, enrolled):
        admin, device = enrolled
        seed = mfa._seed(device)
        assert len(seed) == mfa.SEED_BYTES
        assert seed not in bytes(device.key_ciphertext)
        assert device.confirmed
        # Copying the ciphertext to another account's row doesn't decrypt.
        other = make_user(2)
        clone = AdminTotpDevice(
            user=other,
            key_version=device.key_version,
            key_nonce=device.key_nonce,
            key_ciphertext=device.key_ciphertext,
        )
        with pytest.raises(DecryptionError):
            mfa._seed(clone)
        assert events("ADMIN_MFA_ENROLLED").count() == 1

    def test_enrollment_code_is_hashed_single_use_and_expires(self, admin):
        code = mfa.issue_enrollment(CLI, admin)
        row = AdminMfaEnrollment.objects.get(user=admin)
        assert code.replace("-", "") not in row.code_hash and re.fullmatch(
            r"[0-9a-f]{64}", row.code_hash
        )
        pending = mfa.begin_enrollment(admin, code)
        assert mfa.confirm_enrollment(
            admin, pending.device.pk, pending.enrollment_id, code_for(pending.device)
        )
        with pytest.raises(mfa.EnrollmentInvalid):  # used
            mfa.begin_enrollment(admin, code)
        other = make_user(3)
        assign_role(CLI, other, "system_admin")
        code = mfa.issue_enrollment(CLI, other)
        AdminMfaEnrollment.objects.filter(user=other).update(
            created_at=timezone.now() - timedelta(days=2),
            expires_at=timezone.now() - timedelta(days=1),
        )
        with pytest.raises(mfa.EnrollmentInvalid):  # expired
            mfa.begin_enrollment(other, code)

    def test_wrong_confirmation_code_leaves_the_device_unconfirmed(self, admin):
        code = mfa.issue_enrollment(CLI, admin)
        pending = mfa.begin_enrollment(admin, code)
        assert not mfa.confirm_enrollment(admin, pending.device.pk, pending.enrollment_id, "000000")
        assert not AdminTotpDevice.objects.get(user=admin).confirmed
        assert events("LOGIN_FAILED", "ADMIN_ENROLLMENT_CONFIRM_FAILED").count() == 1

    def test_codes_only_for_admins_and_never_self_issued(self, admin):
        with pytest.raises(InvalidTarget):
            mfa.issue_enrollment(CLI, make_user(4))  # no administrative access
        with pytest.raises(NotAuthorized):
            mfa.issue_enrollment(Actor(user=admin), admin)
        with pytest.raises(NotAuthorized):
            mfa.issue_enrollment(Actor(user=make_user(5)), admin)  # no reset permission

    def test_enrollment_through_the_admin_pages(self, admin):
        code = mfa.issue_enrollment(CLI, admin)
        client = Client()
        page = client.post(
            ENROLL,
            {"phone_number": admin.phone_number, "password": PASSWORD, "enrollment_code": code},
        )
        assert page.status_code == 200
        secret = page.context["secret"]
        # Nothing secret is kept in the session data.
        from django.contrib.sessions.backends.db import SessionStore

        admin_cookie = client.cookies[settings.ADMIN_SESSION_COOKIE_NAME].value
        stored = SessionStore(admin_cookie)[mfa_pending_key()]
        assert set(stored) == {"user_id", "device_id", "enrollment_id"}
        device = AdminTotpDevice.objects.get(user=admin)
        assert secret == mfa.pending_secret(admin, device.pk)[0]
        done = client.post(ENROLL, {"otp_token": code_for(device)})
        assert done.context["done"] is True
        assert AdminTotpDevice.objects.get(user=admin).confirmed

    def test_enrollment_page_rejects_a_wrong_password(self, admin):
        code = mfa.issue_enrollment(CLI, admin)
        page = Client().post(
            ENROLL,
            {"phone_number": admin.phone_number, "password": "wrong", "enrollment_code": code},
        )
        assert "secret" not in page.context
        assert not AdminTotpDevice.objects.filter(user=admin).exists()


def mfa_pending_key():
    from apps.admin_access.views import PENDING_KEY

    return PENDING_KEY


class TestLogin:
    def test_login_needs_password_role_and_totp(self, enrolled):
        admin, device = enrolled
        client = Client()
        response = admin_login(client, admin, device)
        assert response.status_code == 302 and response.url == INDEX
        assert client.get(INDEX).status_code == 200
        session = AuthSession.objects.get(user=admin, client_type="ADMIN")
        assert session.status == "ACTIVE"
        assert events("LOGIN_SUCCEEDED", "ADMIN").count() == 1

    def test_separate_cookie_from_the_user_web_session(self, enrolled):
        admin, device = enrolled
        client = Client()
        response = admin_login(client, admin, device)
        assert settings.ADMIN_SESSION_COOKIE_NAME in response.cookies
        assert settings.SESSION_COOKIE_NAME not in response.cookies
        # The admin cookie is not a session for the API.
        api = APIClient()
        api.cookies[settings.SESSION_COOKIE_NAME] = response.cookies[
            settings.ADMIN_SESSION_COOKIE_NAME
        ].value
        assert api.get("/api/v1/auth/me/").status_code == 401

    @pytest.mark.parametrize("field", ["password", "otp_token"])
    def test_wrong_factor_fails_generically(self, enrolled, field):
        admin, device = enrolled
        data = {
            "phone_number": admin.phone_number,
            "password": PASSWORD,
            "otp_token": code_for(device, 1),
        }
        data[field] = "000000" if field == "otp_token" else "wrong-password"
        client = Client()
        response = client.post(LOGIN, data)
        assert response.status_code == 200
        assert (
            "Enter a correct phone number, password and authentication code"
            in response.content.decode()
        )
        assert not AuthSession.objects.filter(client_type="ADMIN").exists()
        assert client.get(INDEX).status_code == 302

    def test_account_without_a_device_cannot_sign_in(self, admin):
        response = Client().post(
            LOGIN, {"phone_number": admin.phone_number, "password": PASSWORD, "otp_token": "123456"}
        )
        assert response.status_code == 200
        assert events("LOGIN_FAILED", "ADMIN_MFA_NOT_ENROLLED").count() == 1

    def test_superuser_still_needs_mfa(self):
        boss = make_user(10)
        grant_superuser(CLI, boss, reason_code="BOOTSTRAP")
        response = Client().post(
            LOGIN, {"phone_number": boss.phone_number, "password": PASSWORD, "otp_token": "123456"}
        )
        assert response.status_code == 200
        assert not AuthSession.objects.filter(client_type="ADMIN").exists()

    def test_user_without_role_is_refused_even_with_a_device_and_is_staff(self, enrolled):
        admin, device = enrolled
        revoke_role(CLI, admin, "system_admin")
        User.objects.filter(pk=admin.pk).update(is_staff=True)  # forged projection
        response = admin_login(Client(), admin, device)
        assert response.status_code == 200
        assert events("LOGIN_FAILED", "ADMIN_NOT_AUTHORIZED").count() == 1

    def test_a_code_is_accepted_once(self, enrolled):
        admin, device = enrolled
        code = code_for(device, 1)
        data = {"phone_number": admin.phone_number, "password": PASSWORD, "otp_token": code}
        assert Client().post(LOGIN, data).status_code == 302
        assert Client().post(LOGIN, data).status_code == 200  # replay
        assert events("LOGIN_FAILED", "ADMIN_MFA_INVALID").count() == 1

    def test_failed_codes_throttle_the_device(self, enrolled):
        admin, device = enrolled
        for _ in range(2):
            Client().post(
                LOGIN,
                {"phone_number": admin.phone_number, "password": PASSWORD, "otp_token": "000000"},
            )
        device.refresh_from_db()
        assert device.throttling_failure_count >= 1
        # While throttled, even the right code is refused.
        assert admin_login(Client(), admin, device).status_code == 200

    def test_login_is_rate_limited(self, enrolled, settings):
        admin, _ = enrolled
        settings.AUTH_RATE_LIMITS = {**settings.AUTH_RATE_LIMITS, "admin_login_phone_ip": "2/900"}
        data = {"phone_number": admin.phone_number, "password": "wrong", "otp_token": "000000"}
        statuses = [Client().post(LOGIN, data).status_code for _ in range(3)]
        assert statuses == [200, 200, 429]
        assert events("RATE_LIMIT_TRIGGERED").count() == 1

    def test_logout_requires_post_and_revokes(self, enrolled):
        admin, device = enrolled
        client = Client()
        admin_login(client, admin, device)
        assert client.get("/admin/logout/").status_code == 302
        assert AuthSession.objects.get(client_type="ADMIN").status == "ACTIVE"
        client.post("/admin/logout/")
        session = AuthSession.objects.get(client_type="ADMIN")
        assert (session.status, session.revoked_reason) == ("REVOKED", "LOGOUT")
        assert client.get(INDEX).status_code == 302

    def test_admin_password_change_page_is_disabled(self, enrolled):
        admin, device = enrolled
        client = Client()
        admin_login(client, admin, device)
        assert client.get("/admin/password_change/").status_code == 403


class TestSessionLimits:
    def test_lifetimes_are_30_minutes_idle_and_12_hours_absolute(self, enrolled):
        admin, device = enrolled
        admin_login(Client(), admin, device)
        session = AuthSession.objects.get(client_type="ADMIN")
        idle = session.idle_expires_at - session.created_at
        absolute = session.absolute_expires_at - session.created_at
        assert abs(idle - timedelta(minutes=30)) < timedelta(seconds=5)
        assert abs(absolute - timedelta(hours=12)) < timedelta(seconds=5)

    def test_idle_timeout_ends_the_session(self, enrolled):
        admin, device = enrolled
        client = Client()
        admin_login(client, admin, device)
        AuthSession.objects.filter(client_type="ADMIN").update(
            idle_expires_at=timezone.now() - timedelta(seconds=1)
        )
        response = client.get(INDEX)
        assert response.status_code == 302 and response.url.startswith(LOGIN)
        assert AuthSession.objects.get(client_type="ADMIN").status == "EXPIRED"

    def test_absolute_timeout_ends_the_session_despite_activity(self, enrolled):
        admin, device = enrolled
        client = Client()
        admin_login(client, admin, device)
        now = timezone.now()
        AuthSession.objects.filter(client_type="ADMIN").update(
            absolute_expires_at=now - timedelta(seconds=1),
            idle_expires_at=now - timedelta(seconds=1),
        )
        assert client.get(INDEX).status_code == 302

    def test_activity_extends_idle_but_never_past_absolute(self, enrolled):
        admin, device = enrolled
        client = Client()
        admin_login(client, admin, device)
        session = AuthSession.objects.get(client_type="ADMIN")
        past = timezone.now() - timedelta(minutes=5)
        absolute = timezone.now() + timedelta(minutes=10)
        AuthSession.objects.filter(pk=session.pk).update(
            last_seen_at=past,
            idle_expires_at=timezone.now() + timedelta(minutes=2),
            absolute_expires_at=absolute,
        )
        assert client.get(INDEX).status_code == 200
        session.refresh_from_db()
        assert session.idle_expires_at == absolute  # capped by the absolute limit
        assert session.last_seen_at > past

    def test_role_revocation_ends_an_open_admin_session(self, enrolled):
        admin, device = enrolled
        client = Client()
        admin_login(client, admin, device)
        revoke_role(CLI, admin, "system_admin")
        assert client.get(INDEX).status_code == 302

    def test_expired_role_ends_the_session_on_the_next_request(self, enrolled):
        from apps.admin_access.models import AdminUserRole

        admin, device = enrolled
        client = Client()
        admin_login(client, admin, device)
        now = timezone.now()
        AdminUserRole.objects.filter(user=admin).update(
            assigned_at=now - timedelta(hours=1), expires_at=now - timedelta(seconds=1)
        )
        assert client.get(INDEX).status_code == 302
        assert AuthSession.objects.get(client_type="ADMIN").status == "REVOKED"

    def test_web_api_session_never_opens_the_admin(self, enrolled):
        admin, _ = enrolled
        api = APIClient()
        token = api.get("/api/v1/auth/csrf/").json()["csrf_token"]
        api.post(
            "/api/v1/auth/login/",
            {"phone_number": admin.phone_number, "password": PASSWORD},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert api.get("/api/v1/auth/me/").status_code == 200
        assert api.get(INDEX).status_code == 302  # a user session is not an admin session


@pytest.mark.django_db(transaction=True)
def test_concurrent_logins_with_one_code_succeed_once():
    import threading

    sync_catalogue(CLI)
    user = User.objects.create_user(phone_number="+923004009999", password=PASSWORD)
    assign_role(CLI, user, "system_admin")
    device = enroll(User.objects.get(pk=user.pk))
    code = code_for(device, 1)
    barrier, results = threading.Barrier(3), []

    def attempt():
        try:
            barrier.wait()
            results.append(mfa.verify_login_token(user, code) is not None)
        finally:
            connection.close()

    threads = [threading.Thread(target=attempt) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == [False, False, True]


def test_deployed_settings_require_a_real_admin_mfa_key():
    from common.config import key_ring_errors
    from common.crypto.keys import PURPOSES, dev_keyring

    assert "ADMIN_MFA" in PURPOSES
    dev = {f"{p}_KEYS": dev_keyring(p) for p in PURPOSES}
    dev.update({f"{p}_ACTIVE_VERSION": 1 for p in PURPOSES})
    errors = key_ring_errors(dev, {k: v for k, v in dev.items() if k != "ADMIN_MFA_KEYS"})
    assert "ADMIN_MFA_KEYS must be set explicitly (no default keys in deployment)." in errors
    assert "ADMIN_MFA_KEYS contains a dev-only key." in key_ring_errors(dev, dev)
