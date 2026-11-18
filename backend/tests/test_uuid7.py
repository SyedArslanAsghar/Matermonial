"""T-UUID: UUIDv7 generation and boundaries (TR-23; baseline v4.6 §4; G4 stage 3).

Run on PostgreSQL 16 and 18: the database function takes a different path on each.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from django.db import connection

from common.db.uuid7 import is_uuid7, uuid7, uuid7_lower, uuid7_timestamp_ms


def scalar(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        return cursor.fetchone()[0]


def test_uuid_001_python_generator_sets_version_variant_and_timestamp():
    value = uuid7(1_700_000_000_123)
    assert is_uuid7(value)
    assert uuid7_timestamp_ms(value) == 1_700_000_000_123


def test_uuid_002_python_values_sort_by_millisecond():
    early, late = uuid7(1_000), uuid7(1_001)
    assert early.bytes < late.bytes


@pytest.mark.django_db
def test_uuid_003_database_function_returns_current_v7():
    before = int(datetime.now(UTC).timestamp() * 1000)
    value = scalar("SELECT uuid_v7()")
    after = int(datetime.now(UTC).timestamp() * 1000)
    assert is_uuid7(value)
    assert before - 5 <= uuid7_timestamp_ms(value) <= after + 5


@pytest.mark.django_db
def test_uuid_004_database_values_are_unique():
    assert scalar("SELECT count(DISTINCT uuid_v7()) FROM generate_series(1, 5000)") == 5000


@pytest.mark.django_db
def test_uuid_005_function_uses_the_version_specific_path():
    version = int(scalar("SHOW server_version_num"))
    body = scalar("SELECT prosrc FROM pg_proc WHERE proname = 'uuid_v7'")
    if version >= 180000:
        assert "uuidv7()" in body
    else:
        assert "gen_random_uuid" in body


@pytest.mark.django_db
@pytest.mark.parametrize(
    "moment",
    [
        datetime(2027, 1, 1, tzinfo=UTC),
        datetime(2026, 11, 18, 23, 59, 59, 999000, tzinfo=UTC),
        datetime(2030, 6, 15, 12, 0, 0, 1000, tzinfo=UTC),
    ],
)
def test_uuid_006_lower_bound_matches_python_and_is_timezone_independent(moment):
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL TIME ZONE 'Asia/Karachi'")
        cursor.execute("SELECT uuid_v7_lower(%s)", [moment])
        karachi = cursor.fetchone()[0]
        cursor.execute("SET LOCAL TIME ZONE 'UTC'")
        cursor.execute("SELECT uuid_v7_lower(%s)", [moment])
        utc = cursor.fetchone()[0]
    assert karachi == utc == uuid7_lower(moment)


def _extreme(ms: int, fill: int) -> uuid.UUID:
    raw = bytearray(ms.to_bytes(6, "big") + bytes([fill]) * 10)
    raw[6] = (raw[6] & 0x0F) | 0x70
    raw[8] = (raw[8] & 0x3F) | 0x80
    return uuid.UUID(bytes=bytes(raw))


@pytest.mark.django_db
def test_uuid_007_boundary_orders_every_v7_by_its_millisecond():
    """Every v7 with ts >= T sorts >= lower(T); every v7 with ts < T sorts below it."""
    moment = datetime(2027, 2, 1, tzinfo=UTC)
    t = int(moment.timestamp() * 1000)
    candidates = [_extreme(t, 0x00), _extreme(t, 0xFF), _extreme(t - 1, 0xFF), uuid7(t)]
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT v, v >= uuid_v7_lower(%s) FROM unnest(%s::uuid[]) AS v", [moment, candidates]
        )
        result = dict(cursor.fetchall())
    assert result[_extreme(t, 0x00)] and result[_extreme(t, 0xFF)] and result[candidates[3]]
    assert result[_extreme(t - 1, 0xFF)] is False


@pytest.mark.django_db
def test_uuid_008_lower_bound_is_immutable_and_strict():
    volatility, strict = None, None
    with connection.cursor() as cursor:
        cursor.execute("SELECT provolatile, proisstrict FROM pg_proc WHERE proname='uuid_v7_lower'")
        volatility, strict = cursor.fetchone()
    assert volatility == "i" and strict is True
    assert scalar("SELECT uuid_v7_lower(NULL) IS NULL") is True


@pytest.mark.django_db
def test_uuid_009_database_values_sort_in_time_order():
    with connection.cursor() as cursor:
        cursor.execute("SELECT uuid_v7()")
        first = cursor.fetchone()[0]
        cursor.execute("SELECT pg_sleep(0.003)")
        cursor.execute("SELECT uuid_v7()")
        second = cursor.fetchone()[0]
    assert first.bytes < second.bytes
    assert uuid7_timestamp_ms(second) - uuid7_timestamp_ms(first) >= 2


def test_uuid_naive_datetime_rejected():
    with pytest.raises(ValueError):
        uuid7_lower(datetime(2027, 1, 1) + timedelta(0))
