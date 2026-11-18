"""G5 Phase 2a: phone OTP (FR-ACC-002; doc 03 §2.5, doc 06 §3)."""

import logging
import threading
from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone

from apps.accounts.models import AccountSecurityEvent, User
from apps.verification.models import PhoneVerification
from apps.verification.services.otp import send_code, verify_code
from common.providers import MockSMSProvider

PHONE = "+923001234567"
VERIFY = PhoneVerification.Purpose.VERIFY_PHONE


@pytest.fixture
def user():
    return User.objects.create_user(phone_number=PHONE, password="Strong-pass-123!")


def sent_code() -> str:
    return MockSMSProvider.sent[-1]["message"].split("code is ")[1][:6]


def send(user, capture, purpose=VERIFY):
    with capture(execute=True):
        return send_code(phone_number=PHONE, purpose=purpose, user=user)


def age(**delta):
    PhoneVerification.objects.update(created_at=timezone.now() - timedelta(**delta))


@pytest.mark.django_db
class TestSend:
    def test_code_is_sent_after_commit_and_stored_only_as_a_hash(
        self, user, django_capture_on_commit_callbacks
    ):
        outcome = send(user, django_capture_on_commit_callbacks)
        assert outcome.sent and len(MockSMSProvider.sent) == 1
        code = sent_code()
        row = PhoneVerification.objects.get()
        assert code not in row.code_hash and len(row.code_hash) == 64
        assert row.provider_reference == MockSMSProvider.sent[0]["reference"]
        validity = row.expires_at - row.created_at  # created_at is stamped at save
        assert timedelta(minutes=5) - timedelta(seconds=1) < validity <= timedelta(minutes=5)

    def test_resend_inside_cooldown_is_refused(self, user, django_capture_on_commit_callbacks):
        send(user, django_capture_on_commit_callbacks)
        second = send(user, django_capture_on_commit_callbacks)
        assert not second.sent and 1 <= second.retry_after <= 61
        assert len(MockSMSProvider.sent) == 1

    def test_resend_supersedes_the_previous_code(self, user, django_capture_on_commit_callbacks):
        send(user, django_capture_on_commit_callbacks)
        old = sent_code()
        age(seconds=61)
        send(user, django_capture_on_commit_callbacks)
        new = sent_code()
        assert PhoneVerification.objects.filter(status="SUPERSEDED").count() == 1
        assert PhoneVerification.objects.get(status="PENDING").resend_count == 1
        if old != new:
            assert not verify_code(phone_number=PHONE, purpose=VERIFY, code=old, user=user).ok
        assert verify_code(phone_number=PHONE, purpose=VERIFY, code=new, user=user).ok

    def test_hourly_limit_and_one_rate_limit_event(self, user, django_capture_on_commit_callbacks):
        for _ in range(5):
            assert send(user, django_capture_on_commit_callbacks).sent
            age(seconds=61)
        refused = send(user, django_capture_on_commit_callbacks)
        refused_again = send(user, django_capture_on_commit_callbacks)
        assert not refused.sent and not refused_again.sent and refused.retry_after > 0
        assert AccountSecurityEvent.objects.filter(event_type="RATE_LIMIT_TRIGGERED").count() == 1

    def test_code_never_appears_in_logs(self, user, django_capture_on_commit_callbacks, caplog):
        with caplog.at_level(logging.DEBUG):
            send(user, django_capture_on_commit_callbacks)
        assert sent_code() not in caplog.text


@pytest.mark.django_db
class TestVerify:
    def test_correct_code_verifies_the_phone_once(self, user, django_capture_on_commit_callbacks):
        send(user, django_capture_on_commit_callbacks)
        code = sent_code()
        assert verify_code(phone_number=PHONE, purpose=VERIFY, code=code, user=user).ok
        user.refresh_from_db()
        assert user.is_phone_verified is True
        again = verify_code(phone_number=PHONE, purpose=VERIFY, code=code, user=user)
        assert again == again.__class__(False, "invalid")

    def test_five_wrong_attempts_exhaust_the_code(self, user, django_capture_on_commit_callbacks):
        send(user, django_capture_on_commit_callbacks)
        code = sent_code()
        wrong = "000000" if code != "000000" else "111111"
        reasons = [
            verify_code(phone_number=PHONE, purpose=VERIFY, code=wrong, user=user).reason
            for _ in range(5)
        ]
        assert reasons == ["invalid"] * 4 + ["exhausted"]
        assert not verify_code(phone_number=PHONE, purpose=VERIFY, code=code, user=user).ok
        events = list(
            AccountSecurityEvent.objects.filter(event_type__startswith="OTP_").values_list(
                "event_type", flat=True
            )
        )
        assert events.count("OTP_VERIFICATION_FAILED") == 4
        assert events.count("OTP_ATTEMPTS_EXHAUSTED") == 1

    def test_expired_code_fails(self, user, django_capture_on_commit_callbacks):
        send(user, django_capture_on_commit_callbacks)
        PhoneVerification.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        assert not verify_code(phone_number=PHONE, purpose=VERIFY, code=sent_code(), user=user).ok

    def test_another_accounts_code_is_rejected(self, user, django_capture_on_commit_callbacks):
        send(user, django_capture_on_commit_callbacks)
        other = User.objects.create_user(phone_number="+923001234568")
        result = verify_code(phone_number=PHONE, purpose=VERIFY, code=sent_code(), user=other)
        assert not result.ok


@pytest.mark.django_db(transaction=True)
def test_concurrent_verification_consumes_a_code_once():
    user = User.objects.create_user(phone_number=PHONE)
    send_code(phone_number=PHONE, purpose=VERIFY, user=user)  # autocommit: on_commit runs now
    code = sent_code()
    barrier, results = threading.Barrier(2), []

    def attempt():
        try:
            barrier.wait()
            results.append(verify_code(phone_number=PHONE, purpose=VERIFY, code=code, user=user).ok)
        finally:
            connection.close()

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == [False, True]
