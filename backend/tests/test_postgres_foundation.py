"""PostgreSQL foundation tests for G3 (owner decision DR-2026-11-17-G3C-3; TR-13).

They exercise the G3 foundation against a real, disposable PostgreSQL database:
readiness, advisory locks, lock_timeout, and the contention retry (doc 12 §5.3).

Safety rules:
- The database comes only from MATERMONIAL_TEST_POSTGRES_URL. Without it these tests skip.
- Port 5432 and local Unix sockets are refused, so the owner's local PostgreSQL server can't
  be reached by accident. Use a throwaway container on another port.
- No pytest-django test database is created and no migration runs. The tests use temporary
  connection aliases and touch no table; they only call SELECT and advisory-lock functions.
- Teardown checks that no table was created and no advisory lock is left behind.

Tests that need application tables belong to G4 (KI-14).
"""

import os
import threading
import time
from contextlib import contextmanager
from unittest import mock

import environ
import pytest
from django.db import DatabaseError, connections, transaction

from common.api.exceptions import TemporarilyUnavailable
from common.db import retry as retry_module
from common.db.locking import LockLevel, lock_plan, pair_advisory_lock, pair_key
from common.db.retry import retry_on_contention, sqlstate_of

pytestmark = pytest.mark.postgres

URL_ENV = "MATERMONIAL_TEST_POSTGRES_URL"
HOLDER, CONTENDER, OBSERVER = "g3_pg_holder", "g3_pg_contender", "g3_pg_observer"
UNREACHABLE = "g3_pg_unreachable"
NAMESPACE = 4242
PROFILE_A = "6f1d6a1e-0000-4000-8000-0000000000a1"
PROFILE_B = "6f1d6a1e-0000-4000-8000-0000000000b2"


def _disposable_config() -> dict:
    url = os.environ.get(URL_ENV)
    if not url:
        pytest.skip(f"{URL_ENV} is not set; PostgreSQL foundation tests need a disposable database")
    config = environ.Env.db_url_config(url)
    host, port = str(config.get("HOST") or ""), str(config.get("PORT") or "5432")
    if config["ENGINE"] != "django.db.backends.postgresql":
        pytest.fail(f"{URL_ENV} must point to PostgreSQL")
    if port == "5432" or not host or host.startswith("/"):
        pytest.fail(
            f"Refusing {URL_ENV}: port 5432 or a local socket could be the owner's PostgreSQL "
            "server. Use a disposable container published on another port."
        )
    return config


def _register(alias: str, config: dict) -> None:
    # configure_settings() fills in Django's per-connection defaults; it insists on a "default"
    # entry, so the disposable config is passed under both names and only `alias` is kept.
    filled = connections.configure_settings({"default": dict(config), alias: dict(config)})
    connections.settings[alias] = filled[alias]


def _unregister(alias: str) -> None:
    if alias in connections.settings:
        try:
            connections[alias].close()
        finally:
            try:
                del connections[alias]
            except AttributeError:
                pass
            del connections.settings[alias]


def _scalar(alias: str, sql: str, params=None):
    with connections[alias].cursor() as cursor:
        cursor.execute(sql, params or [])
        return cursor.fetchone()[0]


def _public_table_count(alias: str) -> int:
    return _scalar(
        alias, "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
    )


def _advisory_locks(alias: str, pid: int | None = None) -> int:
    if pid is None:
        return _scalar(alias, "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory'")
    return _scalar(
        alias, "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND pid = %s", [pid]
    )


@pytest.fixture
def pg(django_db_blocker, settings):
    """Three connections to the disposable database (+ one deliberately unreachable alias)."""
    config = _disposable_config()
    settings.LOCK_TRACKER_ENABLED = True
    with django_db_blocker.unblock():
        for alias in (HOLDER, CONTENDER, OBSERVER):
            _register(alias, config)
        _register(UNREACHABLE, {**config, "HOST": "127.0.0.1", "PORT": "1"})
        tables_before = _public_table_count(OBSERVER)
        try:
            yield
        finally:
            try:
                for alias in (HOLDER, CONTENDER):
                    connections[alias].close()
                assert _public_table_count(OBSERVER) == tables_before, "a table was created"
                assert _advisory_locks(OBSERVER) == 0, "an advisory lock was left behind"
            finally:
                for alias in (HOLDER, CONTENDER, OBSERVER, UNREACHABLE):
                    _unregister(alias)


@contextmanager
def held_pair_lock(alias: str, *, shared: bool = False):
    """Hold the test pair's advisory lock in an open transaction on `alias`."""
    with transaction.atomic(using=alias), lock_plan("test_holder", [LockLevel.PAIR]):
        pair_advisory_lock(NAMESPACE, PROFILE_A, PROFILE_B, shared=shared, using=alias)
        yield _scalar(alias, "SELECT pg_backend_pid()")


def _try_lock(alias: str, *, shared: bool) -> bool:
    function = "pg_try_advisory_lock_shared" if shared else "pg_try_advisory_lock"
    acquired = _scalar(
        alias, f"SELECT {function}(%s, %s)", [NAMESPACE, pair_key(PROFILE_A, PROFILE_B)]
    )
    if acquired:  # release the session-level probe lock immediately
        unlock = "pg_advisory_unlock_shared" if shared else "pg_advisory_unlock"
        _scalar(alias, f"SELECT {unlock}(%s, %s)", [NAMESPACE, pair_key(PROFILE_A, PROFILE_B)])
    return acquired


# --- 1. Connectivity and readiness ---


def test_readiness_reports_ok_against_postgresql(pg, api_client):
    assert _scalar(OBSERVER, "SHOW server_version_num").isdigit()
    with mock.patch("common.api.health.connection", connections[OBSERVER]):
        response = api_client.get("/api/v1/health/ready/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok"}}


def test_readiness_reports_unavailable_when_postgresql_is_unreachable(pg, api_client):
    with mock.patch("common.api.health.connection", connections[UNREACHABLE]):
        response = api_client.get("/api/v1/health/ready/")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "checks": {"database": "unavailable"}}


# --- 2. Advisory lock acquisition and release ---


def test_exclusive_pair_lock_is_held_until_commit(pg):
    with held_pair_lock(HOLDER) as holder_pid:
        assert _advisory_locks(OBSERVER, holder_pid) == 1
        assert _try_lock(CONTENDER, shared=False) is False
        assert _try_lock(CONTENDER, shared=True) is False
    assert _advisory_locks(OBSERVER, holder_pid) == 0
    assert _try_lock(CONTENDER, shared=False) is True


def test_shared_pair_lock_admits_shared_but_not_exclusive(pg):
    with held_pair_lock(HOLDER, shared=True) as holder_pid:
        assert _advisory_locks(OBSERVER, holder_pid) == 1
        assert _try_lock(CONTENDER, shared=True) is True
        assert _try_lock(CONTENDER, shared=False) is False
    assert _advisory_locks(OBSERVER, holder_pid) == 0


def test_pair_lock_is_symmetric_in_postgresql(pg):
    with transaction.atomic(using=HOLDER), lock_plan("test_symmetric", [LockLevel.PAIR]):
        pair_advisory_lock(NAMESPACE, PROFILE_B, PROFILE_A, using=HOLDER)  # reversed order
        assert _try_lock(CONTENDER, shared=False) is False


# --- 3. lock_timeout ---


def test_lock_timeout_is_transaction_local(pg, settings):
    settings.DB_LOCK_TIMEOUT_MS = 250

    @retry_on_contention(using=CONTENDER)
    def read_timeout():
        return _scalar(CONTENDER, "SHOW lock_timeout")

    assert read_timeout() == "250ms"
    assert _scalar(CONTENDER, "SHOW lock_timeout") == "0"  # back to the session default


def test_lock_timeout_cancels_a_blocked_wait_with_55P03(pg, settings):
    settings.DB_LOCK_TIMEOUT_MS = 200
    with held_pair_lock(HOLDER):
        started = time.monotonic()
        with pytest.raises(DatabaseError) as excinfo:
            with transaction.atomic(using=CONTENDER), lock_plan("test_wait", [LockLevel.PAIR]):
                retry_module._set_lock_timeout(CONTENDER)
                pair_advisory_lock(NAMESPACE, PROFILE_A, PROFILE_B, using=CONTENDER)
        elapsed = time.monotonic() - started
    assert sqlstate_of(excinfo.value) == "55P03"
    assert 0.15 <= elapsed < 3


# --- 4. Contention retry ---


def test_retry_exhausts_to_503_under_real_contention(pg, settings):
    settings.DB_LOCK_TIMEOUT_MS = 150
    attempts = []

    @retry_on_contention(using=CONTENDER)
    def contended_operation():
        attempts.append(1)
        with lock_plan("test_contended", [LockLevel.PAIR]):
            pair_advisory_lock(NAMESPACE, PROFILE_A, PROFILE_B, using=CONTENDER)

    with held_pair_lock(HOLDER), pytest.raises(TemporarilyUnavailable):
        contended_operation()
    assert len(attempts) == retry_module.DEFAULT_ATTEMPTS
    assert _advisory_locks(OBSERVER) == 0


def test_retry_succeeds_once_the_lock_is_released(pg, settings):
    settings.DB_LOCK_TIMEOUT_MS = 300
    attempts, outcome = [], {}
    started = threading.Event()

    @retry_on_contention(using=CONTENDER)
    def contended_operation():
        attempts.append(1)
        started.set()
        with lock_plan("test_recovering", [LockLevel.PAIR]):
            pair_advisory_lock(NAMESPACE, PROFILE_A, PROFILE_B, using=CONTENDER)
        return "done"

    def worker():
        try:
            outcome["result"] = contended_operation()
        except Exception as exc:  # reported by the assertion below
            outcome["error"] = exc
        finally:
            connections[CONTENDER].close()  # this thread's own connection

    with held_pair_lock(HOLDER):
        thread = threading.Thread(target=worker)
        thread.start()
        assert started.wait(5)
        time.sleep(0.35)  # the first attempt times out at 300 ms; then the lock is released
    thread.join(10)
    assert not thread.is_alive()
    assert outcome.get("error") is None, outcome.get("error")
    assert outcome["result"] == "done"
    assert len(attempts) >= 2
