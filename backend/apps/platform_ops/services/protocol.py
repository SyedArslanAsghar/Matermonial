"""Maintenance protocol, Stream M (TR-24; doc 09 §19.2–§19.3, §19.10).

No maintenance action runs outside this protocol. Each step is a short transaction:

    INTENT_PENDING -> INTENT_REGISTERING -> INTENT_REGISTERED -> APPLIED -> VERIFIED_LOCAL
      -> COMPLETION_REGISTERING -> COMPLETED
    INTENT_REGISTERED -> ABORT_REGISTERING -> ABORTED            (proven not applied)
    any non-terminal state -> BLOCKED_OPERATOR                   (anything uncertain)

- A job holds a session advisory lock on its stream; entry allocation takes FOR UPDATE on the
  stream head and is refused while another operation's entry is pending, so each stream has
  at most one registry write in flight.
- The local ``maintenance_audit_log`` row (header + entry_hash) is written in the same
  transaction that allocates the sequence number.
- Apply-transaction lock order: operation row -> stream head -> target objects.
- Stream R (DELETION, SHRED) is the deletion workflow of G5 Phase 15; RESUME and
  ABORT_WITH_EVIDENCE (two approvers) are G5 Phase 16 operator tools.
"""

import uuid
from collections.abc import Callable

from django.db import transaction
from django.utils import timezone

from common.crypto.keys import ring
from common.db.locking import maintenance_stream_lock
from common.db.uuid7 import uuid7

from ..models import STREAM_M_KINDS, MaintenanceAuditLog, MaintenanceOperation, RegistryStreamHead
from ..registry import (
    SCHEMA_VERSION,
    build_entry,
    get_registry,
    jcs,
    rfc3339,
    sha256_hex,
)

EXECUTOR_ROLE = "maintenance"
TERMINAL = ("COMPLETED", "ABORTED")


class NotApplied(Exception):
    """Raised by an apply step that has proven nothing was changed (allows ABORT)."""


class ProtocolBlocked(Exception):
    """The operation needs an operator (BLOCKED_OPERATOR)."""


class PendingEntryConflict(ProtocolBlocked):
    """Another operation's registry entry is still pending on this stream."""


def target_digest(target: dict) -> str:
    return sha256_hex(jcs(target))


def _set_status(op_id, status, **fields):
    MaintenanceOperation.objects.filter(op_id=op_id).update(
        status=status, updated_at=timezone.now(), **fields
    )


def _block(op: MaintenanceOperation, error_code: str) -> None:
    current = MaintenanceOperation.objects.get(op_id=op.op_id)
    if current.status in TERMINAL or current.status == "BLOCKED_OPERATOR":
        return
    _set_status(
        op.op_id, "BLOCKED_OPERATOR", blocked_from_status=current.status, last_error=error_code
    )


def _register(
    op: MaintenanceOperation,
    phase: str,
    params: dict,
    summary: dict,
    *,
    before: str,
    during: str,
    after: str,
    seq_field: str,
    hash_field: str,
) -> dict:
    """Allocate the next entry, write the local log row, then the registry entry."""
    stream = op.stream
    log_row_id = uuid7()  # generated before sequence allocation
    # Heads are seeded by the migration; recreate a missing one at genesis (never overwrite).
    RegistryStreamHead.objects.get_or_create(stream=stream)
    with transaction.atomic():
        locked = MaintenanceOperation.objects.select_for_update().get(op_id=op.op_id)
        if locked.status != before:
            raise ProtocolBlocked(f"unexpected status {locked.status}")
        head = RegistryStreamHead.objects.select_for_update().get(stream=stream)
        if head.pending_op_id and head.pending_op_id != op.op_id:
            raise PendingEntryConflict(stream)
        recorded_at = timezone.now()
        header = {
            "schema_version": SCHEMA_VERSION,
            "stream": stream,
            "seq": head.last_seq + 1,
            "prev_hash": head.last_hash,
            "registry_key_version": ring("REGISTRY").active_version,
            "op_id": str(op.op_id),
            "parent_op_id": str(op.parent_op_id) if op.parent_op_id else None,
            "kind": op.kind,
            "phase": phase,
            "log_row_id": str(log_row_id),
            "target_digest": op.target_digest,
            "companion_ref": None,
            "summary": summary,
            "executor_job_run_id": None,
            "executor_role": EXECUTOR_ROLE,
            "requested_by_pseudonym": (
                str(op.requested_by_pseudonym) if op.requested_by_pseudonym else None
            ),
            "approvals": [],
            "recorded_at": rfc3339(recorded_at),
        }
        entry = build_entry(header, params)
        h = entry["header"]
        MaintenanceAuditLog.objects.create(
            id=log_row_id,
            schema_version=h["schema_version"],
            stream=stream,
            seq=h["seq"],
            prev_hash=h["prev_hash"],
            registry_key_version=h["registry_key_version"],
            op_id=op.op_id,
            parent_op_id=op.parent_op_id,
            kind=op.kind,
            phase=phase,
            target_digest=op.target_digest,
            params_digest=h["params_digest"],
            companion_ref=None,
            summary=summary,
            executor_job_run_id=None,
            executor_role=EXECUTOR_ROLE,
            requested_by_pseudonym=op.requested_by_pseudonym,
            approvals=[],
            recorded_at=recorded_at,
            entry_hash=entry["entry_hash"],
        )
        RegistryStreamHead.objects.filter(stream=stream).update(
            last_seq=h["seq"], last_hash=entry["entry_hash"], pending_op_id=op.op_id
        )
        _set_status(op.op_id, during, **{seq_field: h["seq"], hash_field: entry["entry_hash"]})

    get_registry().put(entry)  # external write; on failure the op stays *_REGISTERING
    with transaction.atomic():
        RegistryStreamHead.objects.filter(stream=stream, pending_op_id=op.op_id).update(
            pending_op_id=None
        )
        _set_status(op.op_id, after)
    return entry


def run_stream_m(
    kind: str,
    *,
    target: dict,
    params: dict,
    summary: dict,
    apply: Callable[[], None],
    verify: Callable[[], bool],
    requested_by_pseudonym: uuid.UUID | None = None,
    parent_op_id: uuid.UUID | None = None,
) -> MaintenanceOperation:
    """Run one Stream M maintenance operation end to end (idempotent per kind + target)."""
    if kind not in STREAM_M_KINDS:
        raise ValueError(f"{kind} is not a Stream M kind")
    digest = target_digest(target)
    with maintenance_stream_lock("M"):
        op = (
            MaintenanceOperation.objects.filter(kind=kind, target_digest=digest)
            .exclude(status="ABORTED")
            .first()
        )
        if op is None:
            op = MaintenanceOperation.objects.create(
                stream="M",
                kind=kind,
                target_digest=digest,
                status="INTENT_PENDING",
                requested_by_pseudonym=requested_by_pseudonym,
                parent_op_id=parent_op_id,
            )
        if op.status == "COMPLETED":
            return op
        if op.status != "INTENT_PENDING":
            raise ProtocolBlocked(f"operation {op.op_id} is {op.status}; operator action needed")

        MaintenanceOperation.objects.filter(op_id=op.op_id).update(attempts=op.attempts + 1)
        try:
            _register(
                op,
                "INTENT",
                params,
                summary,
                before="INTENT_PENDING",
                during="INTENT_REGISTERING",
                after="INTENT_REGISTERED",
                seq_field="intent_seq",
                hash_field="intent_hash",
            )
        except Exception as exc:
            _block(op, f"INTENT_FAILED:{type(exc).__name__}")
            raise

        try:
            with transaction.atomic():
                MaintenanceOperation.objects.select_for_update().get(op_id=op.op_id)
                RegistryStreamHead.objects.select_for_update().get(stream="M")
                apply()
                _set_status(op.op_id, "APPLIED")
        except NotApplied:
            _set_status(op.op_id, "ABORT_REGISTERING")
            _abort(op, params, summary)
            return MaintenanceOperation.objects.get(op_id=op.op_id)
        except Exception as exc:
            _block(op, f"APPLY_FAILED:{type(exc).__name__}")
            raise

        if not verify():
            _block(op, "VERIFY_FAILED")
            raise ProtocolBlocked(f"operation {op.op_id} failed local verification")
        _set_status(op.op_id, "VERIFIED_LOCAL")
        try:
            _register(
                op,
                "COMPLETED",
                params,
                summary,
                before="VERIFIED_LOCAL",
                during="COMPLETION_REGISTERING",
                after="COMPLETED",
                seq_field="outcome_seq",
                hash_field="outcome_hash",
            )
        except Exception as exc:
            _block(op, f"COMPLETION_FAILED:{type(exc).__name__}")
            raise
        MaintenanceOperation.objects.filter(op_id=op.op_id).update(completed_at=timezone.now())
        return MaintenanceOperation.objects.get(op_id=op.op_id)


def _abort(op, params, summary):
    _register(
        op,
        "ABORTED",
        params,
        summary,
        before="ABORT_REGISTERING",
        during="ABORT_REGISTERING",
        after="ABORTED",
        seq_field="outcome_seq",
        hash_field="outcome_hash",
    )
    MaintenanceOperation.objects.filter(op_id=op.op_id).update(completed_at=timezone.now())
