"""Lock-order tracker, pair keys and contention retry (doc 12 §5; TR-09, TR-22).

Row and advisory locks against real tables are exercised by the PostgreSQL concurrency
harness (doc 12 §8) once models exist (G4 onwards).
"""

from contextlib import nullcontext
from unittest import mock

import pytest
from django.db import OperationalError

from common.api.exceptions import TemporarilyUnavailable
from common.db import retry as retry_module
from common.db.locking import (
    LockLevel,
    LockOrderViolation,
    lock_plan,
    pair_key,
    record_lock,
)
from common.db.retry import retry_on_contention, sqlstate_of

PLAN = [LockLevel.AUTHORIZATION, LockLevel.ACCOUNT, LockLevel.PAIR, LockLevel.WALLET]


def test_tracker_accepts_ascending_and_skipped_levels():
    with lock_plan("create_request", PLAN):
        record_lock(LockLevel.ACCOUNT, "User share")
        record_lock(LockLevel.ACCOUNT, "User share (second account)")
        record_lock(LockLevel.PAIR, "pair")
        record_lock(LockLevel.WALLET, "wallet")


def test_tracker_rejects_revisiting_a_lower_level():
    with (
        lock_plan("create_request", PLAN),
        pytest.raises(LockOrderViolation, match="never revisited"),
    ):
        record_lock(LockLevel.WALLET, "wallet")
        record_lock(LockLevel.PAIR, "pair")


def test_tracker_rejects_undeclared_level():
    with (
        lock_plan("create_request", PLAN),
        pytest.raises(LockOrderViolation, match="declared plan"),
    ):
        record_lock(LockLevel.DOMAIN, "request row")


def test_tracker_rejects_lock_outside_a_plan():
    with pytest.raises(LockOrderViolation, match="outside a declared lock_plan"):
        record_lock(LockLevel.ACCOUNT, "User")


def test_tracker_allows_one_anchor_only():
    with lock_plan("deactivate", [LockLevel.ACCOUNT, LockLevel.PROFILE]):
        record_lock(LockLevel.ACCOUNT, "User update", anchor=True)
        with pytest.raises(LockOrderViolation, match="at most one anchor"):
            record_lock(LockLevel.PROFILE, "Profile update", anchor=True)


def test_tracker_is_a_noop_when_disabled(settings):
    settings.LOCK_TRACKER_ENABLED = False
    record_lock(LockLevel.WALLET, "anything")  # no plan, no error


def test_pair_key_is_order_independent_and_32_bit():
    a, b = "0f8a1c2e-0000-4000-8000-000000000001", "0f8a1c2e-0000-4000-8000-000000000002"
    assert pair_key(a, b) == pair_key(b, a)
    assert -(2**31) <= pair_key(a, b) < 2**31
    assert pair_key(a, b) != pair_key(a, "0f8a1c2e-0000-4000-8000-000000000003")


# --- @retry_on_contention ---


class _PgError(Exception):
    def __init__(self, sqlstate):
        super().__init__(sqlstate)
        self.sqlstate = sqlstate


def _db_error(sqlstate):
    try:
        raise OperationalError("db error") from _PgError(sqlstate)
    except OperationalError as exc:
        return exc


@pytest.fixture
def no_db_transaction():
    with (
        mock.patch.object(retry_module.transaction, "atomic", return_value=nullcontext()),
        mock.patch.object(retry_module, "_set_lock_timeout"),
        mock.patch.object(retry_module.time, "sleep") as sleep,
    ):
        yield sleep


def test_sqlstate_is_read_from_the_driver_error():
    assert sqlstate_of(_db_error("40P01")) == "40P01"


@pytest.mark.parametrize("state", ["40P01", "40001", "55P03"])
def test_retries_then_succeeds(no_db_transaction, state):
    calls = []

    @retry_on_contention
    def operation():
        calls.append(1)
        if len(calls) < 3:
            raise _db_error(state)
        return "done"

    assert operation() == "done"
    assert len(calls) == 3
    assert no_db_transaction.call_count == 2
    for call in no_db_transaction.call_args_list:
        assert 0.05 <= call.args[0] <= 0.4


def test_exhausted_retries_raise_503(no_db_transaction):
    @retry_on_contention
    def operation():
        raise _db_error("40P01")

    with pytest.raises(TemporarilyUnavailable):
        operation()


def test_non_retryable_errors_propagate_immediately(no_db_transaction):
    calls = []

    @retry_on_contention
    def operation():
        calls.append(1)
        raise _db_error("23505")  # unique violation: a real error, not contention

    with pytest.raises(OperationalError):
        operation()
    assert calls == [1]


def test_must_be_the_outermost_transaction():
    @retry_on_contention
    def operation():
        return "never"

    fake_connection = mock.Mock(in_atomic_block=True)
    with (
        mock.patch.object(retry_module.transaction, "get_connection", return_value=fake_connection),
        pytest.raises(RuntimeError, match="outermost transaction"),
    ):
        operation()
