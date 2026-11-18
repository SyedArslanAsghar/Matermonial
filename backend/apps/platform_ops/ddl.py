"""Database-level helpers for maintenance operations (TR-23 / TR-24).

DDL and catalog queries live here, not in services (lint rule: no raw SQL in service modules,
doc 12 §5.6). Only the maintenance protocol (services/protocol.py) calls these.
"""

from datetime import UTC, datetime

from django.db import connection

# (parent table, period, periods ahead): doc 03 §22.15 (monthly logs 3 months ahead; the
# maintenance log yearly).
PARTITIONED_LOGS = (
    ("account_security_event", "month", 3),
    ("audit_log", "month", 3),
    ("maintenance_audit_log", "year", 1),
)


def _add_months(moment: datetime, months: int) -> datetime:
    index = moment.year * 12 + moment.month - 1 + months
    return moment.replace(year=index // 12, month=index % 12 + 1)


def planned_partitions(now: datetime | None = None) -> list[dict]:
    """Every partition that should exist now: current period plus the periods ahead."""
    now = (now or datetime.now(UTC)).astimezone(UTC)
    plans = []
    for table, period, ahead in PARTITIONED_LOGS:
        if period == "month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            for i in range(ahead + 1):
                lo, hi = _add_months(start, i), _add_months(start, i + 1)
                plans.append(_plan(table, f"{table}_{lo:%Y_%m}", lo, hi))
        else:
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            for i in range(ahead + 1):
                lo, hi = start.replace(year=start.year + i), start.replace(year=start.year + i + 1)
                plans.append(_plan(table, f"{table}_{lo:%Y}", lo, hi))
    return plans


def _plan(table, partition, lo, hi):
    return {"table": table, "partition": partition, "from": lo, "to": hi}


def relation_exists(name: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass(%s) IS NOT NULL", [name])
        return cursor.fetchone()[0]


def is_partition_of(partition: str, parent: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_inherits WHERE inhrelid = to_regclass(%s) "
            "AND inhparent = to_regclass(%s))",
            [partition, parent],
        )
        return cursor.fetchone()[0]


def create_partition(table: str, partition: str, lo: datetime, hi: datetime) -> None:
    allowed = {t for t, _, _ in PARTITIONED_LOGS}
    if table not in allowed or not partition.startswith(table + "_"):
        raise ValueError("unknown partitioned log")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT format('CREATE TABLE %%I PARTITION OF %%I FOR VALUES FROM (%%L) TO (%%L)', "
            "%s::text, %s::text, uuid_v7_lower(%s), uuid_v7_lower(%s))",
            [partition, table, lo, hi],
        )
        cursor.execute(cursor.fetchone()[0])


def archive_and_drop_audit_partition(partition: str, retain_until: datetime | None) -> int:
    with connection.cursor() as cursor:
        cursor.execute("SELECT archive_and_drop_audit_partition(%s, %s)", [partition, retain_until])
        return cursor.fetchone()[0]
