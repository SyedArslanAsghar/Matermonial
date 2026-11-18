"""G5 Phase 2c: refresh rotation, reuse detection, session management, step-up (T-AUTH 020-034)."""

import base64
import threading
from datetime import timedelta
from unittest import mock

import pytest
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AccountSecurityEvent, AuthSession, AuthToken, User
from apps.accounts.services import auth as auth_service
from common.api.auth_errors import StepUpRequired
from common.crypto.keys import dev_key
from common.events.models import OutboxEvent

PHONE, PASSWORD = "+923001234567", "Correct-Horse-Battery-9"
REFRESH_URL = "/api/v1/auth/token/refresh/"


def login():
    response = APIClient().post(
        "/api/v1/auth/login/",
        {"phone_number": PHONE, "password": PASSWORD, "client": "mobile"},
        format="json",
    )
    body = response.json()
    return body["access_token"], body["refresh_token"]


def do_refresh(token):
    return APIClient().post(REFRESH_URL, {"refresh_token": token}, format="json")


def me(access):
    return APIClient(HTTP_AUTHORIZATION=f"Bearer {access}").get("/api/v1/auth/me/")


def age_parent_use(seconds):
    AuthToken.objects.filter(used_at__isnull=False).update(
        used_at=timezone.now() - timedelta(seconds=seconds)
    )


@pytest.fixture
def user(db):
    return User.objects.create_user(phone_number=PHONE, password=PASSWORD)


@pytest.mark.django_db
class TestRotation:
    def test_020_rotation_issues_a_new_pair_and_025_old_access_keeps_working(self, user):
        access, refresh = login()
        response = do_refresh(refresh)
        assert response.status_code == 200
        new = response.json()
        assert new["refresh_token"] != refresh and new["access_token"] != access
        assert AuthToken.objects.filter(generation=1).count() == 2
        assert me(access).status_code == 200 and me(new["access_token"]).status_code == 200

    def test_021_retry_within_grace_returns_the_identical_pair(self, user):
        _, refresh = login()
        first, second = do_refresh(refresh).json(), do_refresh(refresh).json()
        assert first["refresh_token"] == second["refresh_token"]
        assert first["access_token"] == second["access_token"]
        assert AuthToken.objects.count() == 4  # no extra generation

    def test_023_retry_after_grace_is_reuse_and_revokes(self, user):
        _, refresh = login()
        do_refresh(refresh)
        age_parent_use(16)
        response = do_refresh(refresh)
        assert response.status_code == 401 and response.json()["error"]["code"] == "session_revoked"
        session = AuthSession.objects.get()
        assert (session.status, session.revoked_reason) == ("REVOKED", "REFRESH_REUSE")
        assert not AuthToken.objects.filter(revoked_at__isnull=True).exists()
        assert AccountSecurityEvent.objects.filter(event_type="REFRESH_REUSE_DETECTED").exists()
        assert OutboxEvent.objects.filter(
            event_type="security.session_ended_for_protection"
        ).exists()

    def test_024_grandparent_reuse_revokes(self, user):
        _, refresh = login()
        child = do_refresh(refresh).json()["refresh_token"]
        assert do_refresh(child).status_code == 200  # child used
        assert do_refresh(refresh).status_code == 401  # parent whose child was used
        assert AuthSession.objects.get().status == "REVOKED"

    def test_repeated_reuse_is_flagged_suspicious(self, user):
        for _ in range(2):
            _, refresh = login()
            do_refresh(refresh)
            age_parent_use(16)
            do_refresh(refresh)
        assert AccountSecurityEvent.objects.filter(event_type="SUSPICIOUS_ACTIVITY").count() == 1

    def test_026_failure_mid_rotation_rolls_back(self, user):
        _, refresh = login()
        original = AuthToken.objects.create
        calls = {"n": 0}

        def fail_second(**kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("injected database failure")
            return original(**kwargs)

        with mock.patch.object(AuthToken.objects, "create", side_effect=fail_second):
            response = do_refresh(refresh)
        # The error envelope hides internals; the whole rotation transaction rolled back.
        assert response.status_code == 500 and response.json()["error"]["code"] == "server_error"
        assert AuthToken.objects.count() == 2
        assert AuthToken.objects.get(generation=0, token_type="REFRESH").used_at is None
        assert do_refresh(refresh).status_code == 200  # the parent is still usable

    def test_027_rotating_k_rot_keeps_chains_working(self, user, settings):
        _, refresh = login()
        v2 = base64.b64encode(dev_key("ROT", 2)).decode()
        settings.ROT_KEYS = f"{settings.ROT_KEYS},2:{v2}"
        settings.ROT_ACTIVE_VERSION = 2
        first = do_refresh(refresh).json()
        assert AuthSession.objects.get().key_version_current == 2
        assert do_refresh(refresh).json() == first  # grace replay with the child's key version
        assert do_refresh(first["refresh_token"]).status_code == 200

    def test_034_absolute_expiry_is_enforced(self, user):
        _, refresh = login()
        AuthSession.objects.update(
            created_at=timezone.now() - timedelta(days=91),
            absolute_expires_at=timezone.now() - timedelta(seconds=1),
            idle_expires_at=timezone.now() - timedelta(seconds=2),
        )
        response = do_refresh(refresh)
        assert response.status_code == 401 and response.json()["error"]["code"] == "session_expired"

    def test_refresh_extends_the_rolling_window_but_not_past_absolute(self, user):
        _, refresh = login()
        absolute = timezone.now() + timedelta(days=5)
        AuthSession.objects.update(absolute_expires_at=absolute, idle_expires_at=absolute)
        do_refresh(refresh)
        assert AuthSession.objects.get().idle_expires_at <= absolute

    @pytest.mark.parametrize("token", ["garbage", "mat_rt_" + "x" * 43])
    def test_unknown_tokens_are_invalid(self, user, token):
        response = do_refresh(token)
        assert response.status_code == 401 and response.json()["error"]["code"] == "invalid_token"

    def test_access_token_cannot_refresh(self, user):
        access, _ = login()
        assert do_refresh(access).status_code == 401


@pytest.mark.django_db(transaction=True)
def test_022_concurrent_refreshes_create_one_generation():
    User.objects.create_user(phone_number=PHONE, password=PASSWORD)
    _, refresh = login()
    barrier, results = threading.Barrier(10), []

    def worker():
        try:
            barrier.wait()
            results.append(do_refresh(refresh).json())
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len({r["refresh_token"] for r in results}) == 1
    assert AuthToken.objects.filter(generation=1).count() == 2
    assert AuthSession.objects.get().status == "ACTIVE"


@pytest.mark.django_db
class TestSessionManagement:
    def test_list_shows_own_sessions_with_masked_ip_and_no_tokens(self, user):
        access, refresh = login()
        login()
        body = APIClient(HTTP_AUTHORIZATION=f"Bearer {access}").get("/api/v1/auth/sessions/").json()
        sessions = body["results"] if "results" in body else body["data"]
        assert len(sessions) == 2 and sum(s["current"] for s in sessions) == 1
        assert all(s["ip"] in (None, "127.0.x.x") for s in sessions)
        assert access not in str(body) and refresh not in str(body)

    def test_030_031_revoke_one_and_others(self, user):
        access_a, _ = login()
        access_b, _ = login()
        access_c, _ = login()
        client_a = APIClient(HTTP_AUTHORIZATION=f"Bearer {access_a}")
        session_b = AuthSession.objects.order_by("created_at")[1]
        assert client_a.delete(f"/api/v1/auth/sessions/{session_b.id}/").status_code == 204
        assert me(access_b).status_code == 401 and me(access_a).status_code == 200
        assert client_a.post("/api/v1/auth/sessions/revoke-others/").json() == {"revoked": 1}
        assert me(access_c).status_code == 401 and me(access_a).status_code == 200

    def test_other_peoples_sessions_get_an_identical_404(self, user):
        access, _ = login()
        other = User.objects.create_user(phone_number="+923001234568", password=PASSWORD)
        foreign = AuthSession.objects.create(
            user=other,
            client_type="WEB",
            last_seen_at=timezone.now(),
            idle_expires_at=timezone.now() + timedelta(hours=1),
            absolute_expires_at=timezone.now() + timedelta(hours=2),
        )
        client = APIClient(HTTP_AUTHORIZATION=f"Bearer {access}")
        a = client.delete(f"/api/v1/auth/sessions/{foreign.id}/")
        b = client.delete("/api/v1/auth/sessions/6f1d6a1e-0000-4000-8000-000000000099/")
        assert a.status_code == b.status_code == 404 and a.json() == b.json()
        assert AuthSession.objects.get(pk=foreign.pk).status == "ACTIVE"


@pytest.mark.django_db
class TestStepUp:
    def test_wrong_password_fails_without_ending_the_session(self, user):
        access, _ = login()
        client = APIClient(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = client.post("/api/v1/auth/reauthenticate/", {"password": "nope"}, format="json")
        assert (
            response.status_code == 400 and response.json()["error"]["code"] == "invalid_password"
        )
        assert AccountSecurityEvent.objects.filter(event_type="STEP_UP_FAILED").exists()
        assert me(access).status_code == 200

    def test_step_up_window(self, user):
        access, _ = login()
        session = AuthSession.objects.get()
        with pytest.raises(StepUpRequired):
            auth_service.require_recent_step_up(session)
        client = APIClient(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = client.post(
            "/api/v1/auth/reauthenticate/", {"password": PASSWORD}, format="json"
        )
        assert response.status_code == 200
        auth_service.require_recent_step_up(session)  # within the window
        AuthSession.objects.update(reauthenticated_at=timezone.now() - timedelta(minutes=6))
        with pytest.raises(StepUpRequired):
            auth_service.require_recent_step_up(session)
