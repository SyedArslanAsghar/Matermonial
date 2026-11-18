"""Whole-transaction retry on lock contention (doc 12 §5.3; TR-09, approved).

``@retry_on_contention`` goes on service entry points. It opens the transaction, sets
``lock_timeout`` (settings.DB_LOCK_TIMEOUT_MS, default 5 s), and retries the whole
transaction on SQLSTATE 40P01 (deadlock), 40001 (serialization failure) and 55P03 (lock
not available): up to 3 attempts with jittered backoff of 50–400 ms. When retries are
exhausted it raises ``TemporarilyUnavailable`` (503 with Retry-After). Retrying is safe
because every side effect is inside the transaction.
"""

import functools
import logging
import random
import time

from django.conf import settings
from django.db import DatabaseError, connections, transaction

from common.api.exceptions import TemporarilyUnavailable

logger = logging.getLogger(__name__)

RETRYABLE_SQLSTATES = frozenset({"40P01", "40001", "55P03"})
DEFAULT_ATTEMPTS = 3
BACKOFF_SECONDS = (0.05, 0.4)


def sqlstate_of(exc: BaseException) -> str | None:
    cause = exc.__cause__ or exc.__context__
    return getattr(cause, "sqlstate", None) or getattr(exc, "sqlstate", None)


def _set_lock_timeout(using: str) -> None:
    timeout_ms = int(getattr(settings, "DB_LOCK_TIMEOUT_MS", 5000))
    with connections[using].cursor() as cursor:
        cursor.execute("SELECT set_config('lock_timeout', %s, true)", [f"{timeout_ms}ms"])


def retry_on_contention(func=None, *, attempts: int = DEFAULT_ATTEMPTS, using: str = "default"):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if transaction.get_connection(using).in_atomic_block:
                raise RuntimeError(
                    f"{fn.__qualname__}: @retry_on_contention must open the outermost transaction."
                )
            for attempt in range(1, attempts + 1):
                try:
                    with transaction.atomic(using=using):
                        _set_lock_timeout(using)
                        return fn(*args, **kwargs)
                except DatabaseError as exc:
                    state = sqlstate_of(exc)
                    if state not in RETRYABLE_SQLSTATES:
                        raise
                    if attempt == attempts:
                        logger.warning(
                            "Lock contention retries exhausted",
                            extra={"operation": fn.__qualname__, "sqlstate": state},
                        )
                        raise TemporarilyUnavailable() from exc
                    logger.info(
                        "Retrying transaction after lock contention",
                        extra={"operation": fn.__qualname__, "sqlstate": state, "attempt": attempt},
                    )
                    time.sleep(random.uniform(*BACKOFF_SECONDS))

        return wrapper

    return decorator(func) if func is not None else decorator
