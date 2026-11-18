"""G5 Phase 2e-1: authentication rate limits (doc 06 §22.1 §8.4; T-AUTH-040)."""

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import AccountSecurityEvent, User

PHONE, PASSWORD = "+923001234567", "Correct-Horse-Battery-9"
pytestmark = pytest.mark.django_db


def login(phone=PHONE, password="wrong-password-0", ip="198.51.100.7", client="mobile"):
    return APIClient(REMOTE_ADDR=ip).post(
        "/api/v1/auth/login/",
        {"phone_number": phone, "password": password, "client": client},
        format="json",
    )


def test_login_is_limited_per_phone_and_ip_with_retry_after():
    User.objects.create_user(phone_number=PHONE, password=PASSWORD)
    codes = [login().status_code for _ in range(5)]
    blocked = login()
    assert codes == [401] * 5
    assert blocked.status_code == 429 and int(blocked["Retry-After"]) > 0
    assert blocked.json()["error"]["code"] == "throttled"
    assert login(password=PASSWORD).status_code == 429  # no bypass with the right password
    assert login(ip="203.0.113.9", password=PASSWORD).status_code == 200  # other IP: no lockout


def test_login_is_limited_per_ip_across_phones():
    statuses = [login(phone=f"+9230012345{i:02d}").status_code for i in range(21)]
    assert statuses[:20] == [401] * 20 and statuses[20] == 429


def test_one_rate_limit_event_per_window():
    for _ in range(8):
        login()
    assert AccountSecurityEvent.objects.filter(event_type="RATE_LIMIT_TRIGGERED").count() == 1


def test_register_is_limited_per_ip():
    statuses = [
        APIClient(REMOTE_ADDR="198.51.100.8")
        .post(
            "/api/v1/auth/register/", {"phone_number": f"+9230055500{i:02d}", "password": PASSWORD}
        )
        .status_code
        for i in range(11)
    ]
    assert statuses[:10] == [202] * 10 and statuses[10] == 429


def test_refresh_is_limited_per_session():
    User.objects.create_user(phone_number=PHONE, password=PASSWORD)
    refresh = login(password=PASSWORD).json()["refresh_token"]
    client = APIClient(REMOTE_ADDR="198.51.100.9")
    statuses = [
        client.post("/api/v1/auth/token/refresh/", {"refresh_token": refresh}).status_code
        for _ in range(31)
    ]
    assert statuses[:30] == [200] * 30 and statuses[30] == 429  # replays count too


def test_cache_keys_never_contain_the_phone_number():
    login()
    keys = list(getattr(cache, "_cache", {}).keys())
    assert keys and not any("923001234567" in str(key) for key in keys)
