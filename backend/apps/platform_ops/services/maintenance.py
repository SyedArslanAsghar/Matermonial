"""Maintenance operations run through the protocol (TR-23 / TR-24; doc 09 §19.10).

- ``ensure_log_partitions``: PARTITION_CREATE for every missing current/future partition.
  (The migrations bootstrapped the first partitions before the registry existed; from then on
  every partition change is a recorded operation.)
- ``drop_audit_partition``: PARTITION_DROP, copying held events to ``audit_log_hold`` first.
- ``write_checkpoint``: REGISTRY_CHECKPOINT, the signed Stream R head written to Stream M.
- ``verify_local_chain`` / ``verify_registry``: local and external chain verification.
"""

from datetime import UTC, datetime

from django.utils import timezone

from .. import ddl
from ..models import MaintenanceAuditLog, RegistryStreamHead
from ..registry import GENESIS_HASH, IntegrityAlarm, entry_hash, get_registry, rfc3339
from .protocol import NotApplied, run_stream_m

# doc 09 §19.10: every maintenance command must map to a catalogue kind (startup check/test).
MAINTENANCE_COMMANDS = {
    "ensure_log_partitions": "PARTITION_CREATE",
    "drop_audit_partition": "PARTITION_DROP",
    "write_registry_checkpoint": "REGISTRY_CHECKPOINT",
}


def ensure_log_partitions(now: datetime | None = None) -> list[str]:
    created = []
    for plan in ddl.planned_partitions(now):
        if ddl.relation_exists(plan["partition"]):
            continue
        description = {
            "table": plan["table"],
            "partition": plan["partition"],
            "from": rfc3339(plan["from"]),
            "to": rfc3339(plan["to"]),
        }

        def apply(plan=plan):
            if ddl.relation_exists(plan["partition"]):
                raise NotApplied("partition already exists")
            ddl.create_partition(plan["table"], plan["partition"], plan["from"], plan["to"])

        op = run_stream_m(
            "PARTITION_CREATE",
            target={"table": plan["table"], "partition": plan["partition"]},
            params=description,
            summary=description,
            apply=apply,
            verify=lambda plan=plan: ddl.is_partition_of(plan["partition"], plan["table"]),
        )
        if op.status == "COMPLETED":
            created.append(plan["partition"])
    return created


def drop_audit_partition(partition: str, retain_until: datetime | None) -> int:
    """Drop a past audit_log partition, keeping held events (doc 03 §22.15)."""
    moved = {"count": 0}

    def apply():
        if not ddl.is_partition_of(partition, "audit_log"):
            raise NotApplied("not an audit_log partition")
        moved["count"] = ddl.archive_and_drop_audit_partition(partition, retain_until)

    run_stream_m(
        "PARTITION_DROP",
        target={"table": "audit_log", "partition": partition},
        params={"partition": partition},
        summary={"table": "audit_log", "partition": partition},
        apply=apply,
        verify=lambda: not ddl.relation_exists(partition),
    )
    return moved["count"]


def write_checkpoint(now: datetime | None = None):
    """Daily signed checkpoint of Stream R into Stream M (doc 06 §22.7, C-55)."""
    head = RegistryStreamHead.objects.get(stream="R")
    day = (now or timezone.now()).astimezone(UTC).date().isoformat()
    summary = {"stream": "R", "seq": head.last_seq, "head_hash": head.last_hash, "day": day}
    return run_stream_m(
        "REGISTRY_CHECKPOINT",
        target={"checkpoint_day": day, "stream": "R", "seq": head.last_seq},
        params=summary,
        summary=summary,
        apply=lambda: None,
        verify=lambda: True,
    )


def _header_from_row(row: MaintenanceAuditLog) -> dict:
    return {
        "schema_version": row.schema_version,
        "stream": row.stream,
        "seq": row.seq,
        "prev_hash": row.prev_hash,
        "registry_key_version": row.registry_key_version,
        "op_id": str(row.op_id),
        "parent_op_id": str(row.parent_op_id) if row.parent_op_id else None,
        "kind": row.kind,
        "phase": row.phase,
        "log_row_id": str(row.id),
        "target_digest": row.target_digest,
        "companion_ref": row.companion_ref,
        "summary": row.summary,
        "executor_job_run_id": row.executor_job_run_id,
        "executor_role": row.executor_role,
        "requested_by_pseudonym": (
            str(row.requested_by_pseudonym) if row.requested_by_pseudonym else None
        ),
        "approvals": row.approvals,
        "recorded_at": rfc3339(row.recorded_at),
        "params_digest": row.params_digest,
    }


def verify_local_chain(stream: str) -> int:
    """Rebuild each header from local columns, recompute entry_hash and check the chain."""
    previous_hash, previous_seq, count = GENESIS_HASH, 0, 0
    for row in MaintenanceAuditLog.objects.filter(stream=stream).order_by("seq"):
        if row.seq != previous_seq + 1 or row.prev_hash != previous_hash:
            raise IntegrityAlarm(f"local chain broken at {stream}/{row.seq}")
        if entry_hash(_header_from_row(row)) != row.entry_hash:
            raise IntegrityAlarm(f"local hash mismatch at {stream}/{row.seq}")
        previous_hash, previous_seq, count = row.entry_hash, row.seq, count + 1
    head = RegistryStreamHead.objects.get(stream=stream)
    if (head.last_seq, head.last_hash) != (previous_seq, previous_hash):
        raise IntegrityAlarm(f"stream head disagrees with the local log for {stream}")
    return count


def verify_registry(stream: str) -> int:
    return get_registry().verify_stream(stream)
