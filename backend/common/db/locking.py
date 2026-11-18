"""Lock helpers and the LOCK_PLAN tracker (doc 12 §5; TR-09 and TR-22, approved 2026-11-17).

Services take every explicit lock through these helpers inside a declared ``lock_plan``.
When ``settings.LOCK_TRACKER_ENABLED`` is true (local and test), the tracker raises
``LockOrderViolation`` on:

- a lock taken outside a declared plan, or at a level the plan doesn't declare;
- a lock at a lower level than one already taken (levels may be skipped, never revisited;
  doc 12 §5.3);
- a second exclusive state anchor in one transaction (doc 12 §5.2).

What the tracker can't see (implicit FK checks, plain UPDATE/DELETE, unique-index waits,
triggers, raw SQL) is covered by design rules and PostgreSQL tests (doc 12 §5.6).
"""

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import IntEnum
from hashlib import blake2b

from django.conf import settings
from django.db import connections, transaction


class LockLevel(IntEnum):
    """Global lock order, doc 12 §5.3."""

    AUTHORIZATION = 1
    ACCOUNT = 2
    PROFILE = 3
    PAIR = 4
    WALLET = 5
    ALLOWANCE = 6
    DOMAIN = 7
    INSERT = 8
    OWN_OUTBOX = 9


class LockOrderViolation(AssertionError):
    """A lock acquisition broke the declared plan or the global order."""


@dataclass
class _PlanState:
    name: str
    levels: frozenset[LockLevel]
    acquired: list[tuple[LockLevel, str]] = field(default_factory=list)
    anchors: int = 0


_current_plan: ContextVar[_PlanState | None] = ContextVar("lock_plan", default=None)


@contextmanager
def lock_plan(name: str, levels: Iterable[LockLevel]) -> Iterator[None]:
    """Declare a service's LOCK_PLAN for the duration of one transaction."""
    token = _current_plan.set(_PlanState(name=name, levels=frozenset(levels)))
    try:
        yield
    finally:
        _current_plan.reset(token)


def record_lock(level: LockLevel, label: str, *, anchor: bool = False) -> None:
    """Check one explicit lock acquisition against the active plan (no-op when disabled)."""
    if not getattr(settings, "LOCK_TRACKER_ENABLED", False):
        return
    state = _current_plan.get()
    if state is None:
        raise LockOrderViolation(f"Lock {label!r} taken outside a declared lock_plan.")
    if level not in state.levels:
        raise LockOrderViolation(
            f"{state.name}: level {level.name} ({label!r}) isn't in the declared plan."
        )
    if state.acquired:
        highest = max(lvl for lvl, _ in state.acquired)
        if level < highest:
            raise LockOrderViolation(
                f"{state.name}: {label!r} at level {level.name} after level "
                f"{LockLevel(highest).name}; levels can be skipped, never revisited."
            )
    if anchor:
        if state.anchors:
            raise LockOrderViolation(f"{state.name}: a transaction holds at most one anchor.")
        state.anchors += 1
    state.acquired.append((level, label))


def _require_atomic(using: str) -> None:
    if not transaction.get_connection(using).in_atomic_block:
        raise RuntimeError("Row and advisory locks must be taken inside transaction.atomic().")


def lock_rows_for_update(
    queryset, level: LockLevel, *, label: str | None = None, anchor: bool = False
) -> list:
    """SELECT … FOR UPDATE in ascending primary-key order; returns the model instances."""
    _require_atomic(queryset.db)
    record_lock(level, label or queryset.model._meta.label, anchor=anchor)
    return list(queryset.order_by("pk").select_for_update())


def lock_rows_for_share(queryset, level: LockLevel, *, label: str | None = None) -> list:
    """SELECT … FOR SHARE in ascending primary-key order; returns the locked primary keys.

    Django has no FOR SHARE API, so the ordered primary-key query is compiled and suffixed.
    This is the only sanctioned place for this SQL (lint rule: no raw SQL in services).
    """
    _require_atomic(queryset.db)
    record_lock(level, label or queryset.model._meta.label)
    sql, params = queryset.order_by("pk").values_list("pk", flat=True).query.sql_with_params()
    with connections[queryset.db].cursor() as cursor:
        cursor.execute(f"{sql} FOR SHARE", params)
        return [row[0] for row in cursor.fetchall()]


def pair_key(first, second) -> int:
    """Order-independent signed 32-bit key for a profile pair (doc 05 §25.1: least ‖ greatest)."""
    low, high = sorted((str(first), str(second)))
    digest = blake2b(f"{low}|{high}".encode(), digest_size=4).digest()
    return int.from_bytes(digest, "big", signed=True)


def pair_advisory_lock(
    namespace: int, first, second, *, shared: bool = False, using: str = "default"
) -> None:
    """Transaction-level pair advisory lock (doc 12 §5.3 level 4)."""
    _require_atomic(using)
    record_lock(LockLevel.PAIR, f"pair:{namespace}")
    function = "pg_advisory_xact_lock_shared" if shared else "pg_advisory_xact_lock"
    with connections[using].cursor() as cursor:
        cursor.execute(f"SELECT {function}(%s, %s)", [namespace, pair_key(first, second)])
