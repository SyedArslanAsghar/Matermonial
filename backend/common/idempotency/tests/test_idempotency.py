"""G4 stage 7: idempotency records (CC-R39, CC-R52; TR-11)."""

import threading
import time
from datetime import timedelta

import pytest
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.accounts.models import User
from common.idempotency.models import IdempotencyRecord
from common.idempotency.services import (
    IdempotencyConflict,
    fingerprint,
    purge_expired,
    run_idempotent,
)

KEY = "6f1d6a1e-key-0001"


def make_user(phone="+923001234567"):
    return User.objects.create_user(phone_number=phone, password="Strong-pass-123!")


def counter_operation(calls):
    def operation():
        calls.append(1)
        return 201, {"purchase": "p-1"}

    return operation


def run(user, calls, body=None, scope="credits.purchase", key=KEY):
    return run_idempotent(
        account_id=user.id,
        key=key,
        scope=scope,
        request_fingerprint=fingerprint("POST", "/api/v1/credits/purchases/", body or {"pack": 1}),
        operation=counter_operation(calls),
    )


@pytest.mark.django_db
class TestIdempotency:
    def test_retry_replays_the_stored_response_without_rerunning(self):
        user, calls = make_user(), []
        first, second = run(user, calls), run(user, calls)
        assert (first.status, first.body, first.replayed) == (201, {"purchase": "p-1"}, False)
        assert (second.status, second.body, second.replayed) == (201, {"purchase": "p-1"}, True)
        assert len(calls) == 1

    @pytest.mark.parametrize("change", [{"body": {"pack": 2}}, {"scope": "credits.refund"}])
    def test_same_key_for_a_different_request_is_a_conflict(self, change):
        user, calls = make_user(), []
        run(user, calls)
        with pytest.raises(IdempotencyConflict):
            run(user, calls, **change)
        assert len(calls) == 1

    def test_failed_operation_leaves_no_record_so_retry_runs_again(self):
        user = make_user()

        def failing():
            raise RuntimeError("payment provider down")

        with pytest.raises(RuntimeError):
            run_idempotent(
                account_id=user.id,
                key=KEY,
                scope="s",
                request_fingerprint="a" * 64,
                operation=failing,
            )
        assert not IdempotencyRecord.objects.exists()
        calls = []
        assert run(user, calls).replayed is False and len(calls) == 1

    def test_keys_are_scoped_per_account(self):
        calls = []
        run(make_user(), calls)
        run(make_user("+923001234568"), calls)
        assert len(calls) == 2

    def test_expired_record_frees_the_key(self):
        user, calls = make_user(), []
        run(user, calls)
        IdempotencyRecord.objects.update(
            created_at=timezone.now() - timedelta(days=2),
            expires_at=timezone.now() - timedelta(days=1),
        )
        assert run(user, calls).replayed is False and len(calls) == 2

    def test_purge_removes_only_expired_records(self):
        user = make_user()
        run(user, [])
        run(user, [], key="6f1d6a1e-key-0002")
        IdempotencyRecord.objects.filter(key=KEY).update(
            created_at=timezone.now() - timedelta(days=2),
            expires_at=timezone.now() - timedelta(days=1),
        )
        assert purge_expired() == 1
        assert IdempotencyRecord.objects.get().key == "6f1d6a1e-key-0002"

    @pytest.mark.parametrize(
        ("field", "value"), [("key", "bad key with spaces"), ("request_fingerprint", "xyz")]
    )
    def test_database_validates_key_and_fingerprint(self, field, value):
        user = make_user()
        values = dict(
            account=user,
            key=KEY,
            scope="s",
            request_fingerprint="a" * 64,
            response_status=200,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        values[field] = value
        with pytest.raises(IntegrityError), transaction.atomic():
            IdempotencyRecord.objects.create(**values)


@pytest.mark.django_db(transaction=True)
def test_concurrent_identical_requests_run_the_operation_once():
    user = make_user()
    calls, results = [], []
    barrier = threading.Barrier(2)

    def slow_operation():
        calls.append(1)
        time.sleep(0.3)  # keep the first transaction open while the second arrives
        return 201, {"purchase": "p-1"}

    def worker():
        try:
            barrier.wait()
            results.append(
                run_idempotent(
                    account_id=user.id,
                    key=KEY,
                    scope="credits.purchase",
                    request_fingerprint="b" * 64,
                    operation=slow_operation,
                )
            )
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(calls) == 1
    assert sorted(r.replayed for r in results) == [False, True]
    assert {(r.status, str(r.body)) for r in results} == {(201, str({"purchase": "p-1"}))}
