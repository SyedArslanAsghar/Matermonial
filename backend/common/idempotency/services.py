"""Idempotent execution of retry-sensitive operations (CC-R39, CC-R52; TR-11).

``run_idempotent`` runs the operation and stores its response **in one transaction**:

1. Insert the record first, inside a savepoint. A concurrent request with the same
   (account, key) blocks on the unique index until the first transaction ends.
2. If the insert conflicts, the earlier request committed: replay its stored response when
   the scope and fingerprint match, otherwise raise ``IdempotencyConflict``.
3. If the operation raises, everything rolls back, including the record, so the client can
   retry with the same key.

The record's ``response_status``/``response_body`` are written after the operation; the insert
in step 1 uses a placeholder status that is replaced before commit (never visible outside).
"""

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import IdempotencyRecord

DEFAULT_TTL = timedelta(hours=24)
_PLACEHOLDER_STATUS = 102  # "Processing"; replaced before the transaction commits


class IdempotencyConflict(Exception):
    """The key was already used for a different operation or request body."""


@dataclass(frozen=True)
class IdempotentResult:
    status: int
    body: dict
    replayed: bool


def fingerprint(method: str, path: str, body: dict | None) -> str:
    canonical = json.dumps(
        {"method": method.upper(), "path": path, "body": body or {}},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def run_idempotent(
    *,
    account_id,
    key: str,
    scope: str,
    request_fingerprint: str,
    operation: Callable[[], tuple[int, dict]],
    ttl: timedelta = DEFAULT_TTL,
) -> IdempotentResult:
    now = timezone.now()
    with transaction.atomic():
        # Expired records free their key (purge also removes them in bulk).
        IdempotencyRecord.objects.filter(
            account_id=account_id, key=key, expires_at__lte=now
        ).delete()
        try:
            with transaction.atomic():
                record = IdempotencyRecord.objects.create(
                    account_id=account_id,
                    key=key,
                    scope=scope,
                    request_fingerprint=request_fingerprint,
                    response_status=_PLACEHOLDER_STATUS,
                    expires_at=now + ttl,
                )
        except IntegrityError:
            existing = IdempotencyRecord.objects.get(account_id=account_id, key=key)
            if existing.scope != scope or existing.request_fingerprint != request_fingerprint:
                raise IdempotencyConflict(
                    "Idempotency-Key was already used for a different request."
                ) from None
            return IdempotentResult(existing.response_status, existing.response_body, True)

        status, body = operation()
        record.response_status, record.response_body = status, body
        record.save(update_fields=["response_status", "response_body"])
        return IdempotentResult(status, body, False)


def purge_expired(now=None) -> int:
    deleted, _ = IdempotencyRecord.objects.filter(expires_at__lte=now or timezone.now()).delete()
    return deleted
