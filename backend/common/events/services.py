"""Outbox: emit in the business transaction, then two-phase processing (TR-11; doc 12 §6).

- ``emit`` must run inside the business operation's transaction (approved core, FR-NOT-005):
  the event commits or rolls back with it. It is never a Celery-only substitute.
- ``claim_batch`` is Tx-C: short, committed on its own, ``FOR UPDATE SKIP LOCKED``; it locks
  only outbox rows and never waits for them.
- ``process_claimed`` runs one handler transaction. The handler does its business work in
  global lock order; the event's own row is locked **last** (level 9, OWN_OUTBOX) and marked
  DONE only if this worker still holds the lease. A lost lease rolls everything back.
- A handler error leaves the claim to expire, so the next claim retries it; after
  ``MAX_ATTEMPTS`` the event becomes DEAD. An undecryptable payload (queue key unavailable)
  becomes DEAD_UNDECRYPTABLE; financial obligations then follow the two-stage resolution of
  doc 05 §25.6, implemented with the ledger (G5 Phase 7/9).
- ``redact_and_purge`` applies the retention rules of doc 03 §22.12.
"""

import logging
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from common.crypto.aead import DecryptionError, keyed_hash, open_json, seal_json
from common.crypto.keys import KeyConfigurationError, ring
from common.db.locking import LockLevel, lock_plan, record_lock

from .models import TERMINAL_STATUSES, OutboxEvent

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 8


class LeaseLost(Exception):
    """Another worker re-claimed the event after this worker's lease expired."""


class NoHandler(Exception):
    pass


@dataclass(frozen=True)
class Handler:
    func: Callable[[OutboxEvent, dict], None]
    lock_levels: frozenset = field(default_factory=frozenset)


HANDLERS: dict[str, Handler] = {}


def register_handler(event_type: str, lock_levels: Iterable[LockLevel] = ()):
    """Register the handler for ``event_type``; ``lock_levels`` is its LOCK_PLAN (doc 12 §5)."""

    def decorator(func):
        HANDLERS[event_type] = Handler(func, frozenset(lock_levels))
        return func

    return decorator


def _aad(event_id: uuid.UUID) -> bytes:
    return b"matermonial:outbox:" + event_id.bytes


def _in_business_transaction() -> bool:
    """True inside an application atomic block (test-case wrappers don't count)."""
    blocks = transaction.get_connection().atomic_blocks
    return any(not getattr(block, "_from_testcase", False) for block in blocks)


def dedupe_key(identity: str) -> str:
    return keyed_hash(ring("DEDUPE").active_key, identity)


def emit(
    event_type: str,
    *,
    event_class: str,
    category: str,
    aggregate_type: str,
    payload: dict,
    recipient_pseudonym: uuid.UUID | None = None,
    dedupe_identity: str | None = None,
) -> OutboxEvent:
    """Queue an event in the caller's transaction. A live duplicate (same dedupe identity)
    is returned instead of creating a second event."""
    if not _in_business_transaction():
        raise RuntimeError("emit() must run inside the business transaction (FR-NOT-005).")
    queue = ring("QUEUE")
    event_id = OutboxEvent._meta.pk.default()
    nonce, ciphertext = seal_json(queue.active_key, payload, _aad(event_id))
    key = dedupe_key(dedupe_identity) if dedupe_identity else None
    try:
        with transaction.atomic():
            return OutboxEvent.objects.create(
                id=event_id,
                event_type=event_type,
                event_class=event_class,
                category=category,
                aggregate_type=aggregate_type,
                recipient_pseudonym=recipient_pseudonym,
                dedupe_key=key,
                payload_enc=nonce + ciphertext,
                queue_key_version=queue.active_version,
                obligation_resolution=(
                    OutboxEvent.ObligationResolution.PENDING
                    if event_class == OutboxEvent.EventClass.FINANCIAL_OBLIGATION
                    else None
                ),
            )
    except IntegrityError:
        if key is None:
            raise
        return OutboxEvent.objects.exclude(status__in=["DEAD_UNDECRYPTABLE", "CANCELLED"]).get(
            dedupe_key=key
        )


def decrypt_payload(event: OutboxEvent) -> dict:
    raw = bytes(event.payload_enc)
    key = ring("QUEUE").key(event.queue_key_version)
    return open_json(key, raw[:12], raw[12:], _aad(event.id))


def claim_batch(limit: int = 50) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """Tx-C: claim up to ``limit`` due events; returns (event_id, lease_token) pairs."""
    now = timezone.now()
    token = uuid.uuid4()
    # durable=True: Tx-C must never run inside another transaction (Django raises if nested).
    with transaction.atomic(durable=True), lock_plan("outbox.claim", [LockLevel.OWN_OUTBOX]):
        record_lock(LockLevel.OWN_OUTBOX, "events.OutboxEvent (claim, SKIP LOCKED)")
        due = (
            OutboxEvent.objects.filter(
                Q(status=OutboxEvent.Status.PENDING)
                | Q(status=OutboxEvent.Status.CLAIMED, lease_expires_at__lt=now)
            )
            .order_by("id")
            .select_for_update(skip_locked=True)
            .values_list("id", flat=True)[:limit]
        )
        ids = list(due)
        OutboxEvent.objects.filter(id__in=ids).update(
            status=OutboxEvent.Status.CLAIMED,
            lease_token=token,
            lease_expires_at=now + timedelta(seconds=settings.OUTBOX_LEASE_SECONDS),
            attempts=F("attempts") + 1,
        )
    return [(event_id, token) for event_id in ids]


def complete_own_event(event_id: uuid.UUID, lease_token: uuid.UUID) -> None:
    """Level 9: the last lock of a handler transaction. Marks the event DONE."""
    record_lock(LockLevel.OWN_OUTBOX, "events.OutboxEvent (own row)")
    event = OutboxEvent.objects.select_for_update().get(id=event_id)
    if event.status != OutboxEvent.Status.CLAIMED or event.lease_token != lease_token:
        raise LeaseLost(f"Lease lost for outbox event {event_id}")
    event.status = OutboxEvent.Status.DONE
    event.lease_token = None
    event.lease_expires_at = None
    event.terminal_at = timezone.now()
    event.save(update_fields=["status", "lease_token", "lease_expires_at", "terminal_at"])


def _set_terminal(event_id: uuid.UUID, lease_token: uuid.UUID, status: str) -> None:
    OutboxEvent.objects.filter(
        id=event_id, status=OutboxEvent.Status.CLAIMED, lease_token=lease_token
    ).update(status=status, lease_token=None, lease_expires_at=None, terminal_at=timezone.now())


def process_claimed(event_id: uuid.UUID, lease_token: uuid.UUID) -> str:
    """Run one claimed event's handler transaction. Returns the resulting status."""
    event = OutboxEvent.objects.get(id=event_id)
    try:
        payload = decrypt_payload(event)
    except (DecryptionError, KeyConfigurationError):
        _set_terminal(event_id, lease_token, OutboxEvent.Status.DEAD_UNDECRYPTABLE)
        logger.error("Outbox payload undecryptable", extra={"event_type": event.event_type})
        return OutboxEvent.Status.DEAD_UNDECRYPTABLE
    handler = HANDLERS.get(event.event_type)
    try:
        if handler is None:
            raise NoHandler(event.event_type)
        levels = handler.lock_levels | {LockLevel.OWN_OUTBOX}
        with transaction.atomic(), lock_plan(f"outbox:{event.event_type}", levels):
            handler.func(event, payload)
            complete_own_event(event_id, lease_token)
        return OutboxEvent.Status.DONE
    except LeaseLost:
        return OutboxEvent.Status.CLAIMED
    except Exception as exc:  # handler failure: logged, retried by lease expiry, then DEAD
        logger.warning(
            "Outbox handler failed",
            extra={"event_type": event.event_type, "error_type": type(exc).__name__},
        )
        if event.attempts >= MAX_ATTEMPTS:
            _set_terminal(event_id, lease_token, OutboxEvent.Status.DEAD)
            return OutboxEvent.Status.DEAD
        return OutboxEvent.Status.CLAIMED


def process_due(limit: int = 50) -> dict[str, int]:
    results: dict[str, int] = {}
    for event_id, token in claim_batch(limit):
        status = process_claimed(event_id, token)
        results[status] = results.get(status, 0) + 1
    return results


def redact_and_purge(now=None) -> tuple[int, int]:
    """Redact terminal rows after OUTBOX_REDACT_AFTER_DAYS and purge them after
    OUTBOX_PURGE_AFTER_DAYS (doc 03 §22.12). Returns (redacted, purged).

    FINANCIAL_OBLIGATION rows: DONE + 7 days, or DEAD_UNDECRYPTABLE with a verified
    resolution + 7 days. The database trigger enforces the same rule. The "refund verified"
    condition for DONE is established by the ledger handler before it completes the event.
    """
    now = now or timezone.now()
    redact_before = now - timedelta(days=settings.OUTBOX_REDACT_AFTER_DAYS)
    purge_before = now - timedelta(days=settings.OUTBOX_PURGE_AFTER_DAYS)
    unredacted = Q(redacted_at__isnull=True)
    notification = Q(
        event_class=OutboxEvent.EventClass.NOTIFICATION,
        status__in=TERMINAL_STATUSES,
        terminal_at__lte=redact_before,
    )
    financial = Q(event_class=OutboxEvent.EventClass.FINANCIAL_OBLIGATION) & (
        Q(status=OutboxEvent.Status.DONE, terminal_at__lte=redact_before)
        | Q(
            status=OutboxEvent.Status.DEAD_UNDECRYPTABLE,
            obligation_resolution__in=["REPLACED_VERIFIED", "OBLIGATION_SATISFIED_VERIFIED"],
            resolved_at__lte=redact_before,
        )
    )
    with transaction.atomic():
        redacted = OutboxEvent.objects.filter(unredacted & (notification | financial)).update(
            payload_enc=None, recipient_pseudonym=None, dedupe_key=None, redacted_at=now
        )
        purged, _ = OutboxEvent.objects.filter(
            redacted_at__isnull=False, terminal_at__lte=purge_before
        ).delete()
    return redacted, purged
