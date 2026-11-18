"""G4 stage 8: TR-24 maintenance protocol and local registry. T-REG / T-LOG subset."""

import json
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services.pseudonyms import pseudonym_for
from apps.audit.models import AuditLog
from apps.audit.services import place_hold
from apps.platform_ops import ddl
from apps.platform_ops.models import (
    STREAM_M_KINDS,
    MaintenanceApproval,
    MaintenanceAuditLog,
    MaintenanceOperation,
    RegistryStreamHead,
    ShreddedPseudonym,
)
from apps.platform_ops.registry import EntryExists, IntegrityAlarm, LocalRegistry
from apps.platform_ops.services import maintenance
from apps.platform_ops.services.protocol import (
    NotApplied,
    PendingEntryConflict,
    ProtocolBlocked,
    run_stream_m,
)
from apps.platform_ops.services.shred_cache import record_shred
from common.db.uuid7 import uuid7

FUTURE = datetime(2031, 6, 15, tzinfo=UTC)  # partitions that don't exist yet


@pytest.fixture(autouse=True)
def registry_dir(settings, tmp_path):
    settings.COMPLIANCE_REGISTRY_LOCATION = str(tmp_path / "registry")
    return Path(settings.COMPLIANCE_REGISTRY_LOCATION)


def noop_op(kind="OPERATOR_INTERVENTION", name="t1", apply=lambda: None, verify=lambda: True):
    return run_stream_m(
        kind,
        target={"name": name},
        params={"name": name},
        summary={"name": name},
        apply=apply,
        verify=verify,
    )


@pytest.mark.django_db
class TestProtocol:
    def test_operation_completes_with_intent_and_completion_entries(self):
        op = noop_op()
        assert op.status == "COMPLETED" and (op.intent_seq, op.outcome_seq) == (1, 2)
        assert maintenance.verify_registry("M") == 2
        assert maintenance.verify_local_chain("M") == 2
        phases = list(
            MaintenanceAuditLog.objects.filter(op_id=op.op_id)
            .order_by("seq")
            .values_list("phase", flat=True)
        )
        assert phases == ["INTENT", "COMPLETED"]
        assert RegistryStreamHead.objects.get(stream="M").pending_op_id is None

    def test_operation_is_idempotent_per_kind_and_target(self):
        first, second = noop_op(), noop_op()
        assert first.op_id == second.op_id
        assert maintenance.verify_registry("M") == 2

    def test_proven_not_applied_aborts_and_frees_the_target(self):
        def refuse():
            raise NotApplied("nothing to do")

        aborted = noop_op(apply=refuse)
        assert aborted.status == "ABORTED"
        assert MaintenanceAuditLog.objects.filter(op_id=aborted.op_id, phase="ABORTED").exists()
        assert noop_op().status == "COMPLETED"  # ABORTED doesn't block the same target

    def test_uncertain_failure_blocks_for_an_operator(self):
        def explode():
            raise RuntimeError("disk full")

        with pytest.raises(RuntimeError):
            noop_op(apply=explode)
        op = MaintenanceOperation.objects.get()
        assert (op.status, op.blocked_from_status) == ("BLOCKED_OPERATOR", "INTENT_REGISTERED")
        assert op.last_error == "APPLY_FAILED:RuntimeError"
        with pytest.raises(ProtocolBlocked):
            noop_op()

    def test_failed_verification_blocks(self):
        with pytest.raises(ProtocolBlocked):
            noop_op(verify=lambda: False)
        assert MaintenanceOperation.objects.get().status == "BLOCKED_OPERATOR"

    def test_one_pending_entry_per_stream(self):
        RegistryStreamHead.objects.filter(stream="M").update(pending_op_id=uuid.uuid4())
        with pytest.raises(PendingEntryConflict):
            noop_op()
        assert MaintenanceOperation.objects.get().status == "BLOCKED_OPERATOR"

    def test_schema_rules(self):
        with pytest.raises(IntegrityError), transaction.atomic():  # no ABORTED in Stream R
            MaintenanceOperation.objects.create(
                stream="R", kind="SHRED", target_digest="a" * 64, status="ABORTED"
            )
        with pytest.raises(IntegrityError), transaction.atomic():  # kind matches stream
            MaintenanceOperation.objects.create(
                stream="R",
                kind="PARTITION_CREATE",
                target_digest="a" * 64,
                status="INTENT_PENDING",
            )
        with pytest.raises(IntegrityError), transaction.atomic():  # one live op per target
            for _ in range(2):
                MaintenanceOperation.objects.create(
                    stream="M",
                    kind="PARTITION_CREATE",
                    target_digest="b" * 64,
                    status="INTENT_PENDING",
                )

    def test_maintenance_log_is_append_only_and_holds_no_params(self):
        op = noop_op()
        with pytest.raises(DatabaseError), transaction.atomic():
            MaintenanceAuditLog.objects.filter(op_id=op.op_id).update(phase="ABORTED")
        with pytest.raises(DatabaseError), transaction.atomic():
            MaintenanceAuditLog.objects.filter(op_id=op.op_id).delete()
        assert "params" not in {f.name for f in MaintenanceAuditLog._meta.get_fields()}


@pytest.mark.django_db
class TestRegistry:
    def test_entries_are_write_once(self, registry_dir):
        noop_op()
        entry = LocalRegistry().get("M", 1)
        with pytest.raises(EntryExists):
            LocalRegistry().put(entry)

    @pytest.mark.parametrize("tamper", ["summary", "signature", "params"])
    def test_tampering_is_detected(self, registry_dir, tamper):
        noop_op()
        path = registry_dir / "M" / f"{1:012d}.json"
        entry = json.loads(path.read_text())
        if tamper == "summary":
            entry["header"]["summary"]["name"] = "changed"
        elif tamper == "signature":
            entry["signature"] = "0" * 64
        else:
            entry["params"]["name"] = "changed"
        path.write_text(json.dumps(entry))
        with pytest.raises(IntegrityAlarm):
            maintenance.verify_registry("M")

    def test_a_missing_entry_breaks_the_chain(self, registry_dir):
        noop_op(name="a")
        noop_op(name="b")
        (registry_dir / "M" / f"{2:012d}.json").rename(registry_dir / "M" / "moved.json")
        with pytest.raises(IntegrityAlarm):
            # entry 3 is now reachable only as a gap; re-link it as entry 2 to prove the check
            path = registry_dir / "M" / f"{3:012d}.json"
            path.rename(registry_dir / "M" / f"{2:012d}.json")
            maintenance.verify_registry("M")

    def test_local_chain_detects_a_disagreeing_head(self):
        noop_op()
        RegistryStreamHead.objects.filter(stream="M").update(last_seq=99)
        with pytest.raises(IntegrityAlarm):
            maintenance.verify_local_chain("M")

    def test_checkpoint_records_the_stream_r_head(self):
        op = maintenance.write_checkpoint()
        assert op.status == "COMPLETED"
        entry = LocalRegistry().get("M", 1)
        assert entry["header"]["summary"]["stream"] == "R"
        assert entry["header"]["kind"] == "REGISTRY_CHECKPOINT"
        assert maintenance.write_checkpoint().op_id == op.op_id  # once per day and head


@pytest.mark.django_db
class TestPartitions:
    def test_missing_partitions_are_created_through_the_protocol(self):
        created = maintenance.ensure_log_partitions(now=FUTURE)
        assert "audit_log_2031_06" in created and "account_security_event_2031_09" in created
        assert "maintenance_audit_log_2031" in created
        assert all(ddl.relation_exists(name) for name in created)
        assert MaintenanceOperation.objects.filter(
            kind="PARTITION_CREATE", status="COMPLETED"
        ).count() == len(created)
        assert maintenance.verify_registry("M") == 2 * len(created)
        assert maintenance.ensure_log_partitions(now=FUTURE) == []  # idempotent

    def test_registry_summaries_never_contain_pseudonyms(self):
        user = User.objects.create_user(phone_number="+923001234567")
        maintenance.ensure_log_partitions(now=FUTURE)
        pseudonym = str(pseudonym_for("ACCOUNT", user.id))
        text = "".join(json.dumps(e) for e in LocalRegistry().entries("M"))
        assert pseudonym not in text and str(user.id) not in text

    def test_dropping_an_audit_partition_keeps_held_events(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "CREATE TABLE audit_log_2020_03 PARTITION OF audit_log FOR VALUES FROM "
                "(uuid_v7_lower('2020-03-01 00:00:00+00')) TO "
                "(uuid_v7_lower('2020-04-01 00:00:00+00'))"
            )
        ms = int(datetime(2020, 3, 10, tzinfo=UTC).timestamp() * 1000)
        held, plain = uuid7(ms), uuid7(ms + 1)
        for event_id in (held, plain):
            AuditLog.objects.create(
                id=event_id,
                occurred_at=datetime(2020, 3, 10, tzinfo=UTC),
                actor_type="SYSTEM",
                action="system.check",
                resource_type="system",
                result="SUCCESS",
                category="SYSTEM",
            )
        place_hold([held], uuid.uuid4())
        assert maintenance.drop_audit_partition("audit_log_2020_03", None) == 1
        assert not ddl.relation_exists("audit_log_2020_03")
        op = MaintenanceOperation.objects.get(kind="PARTITION_DROP")
        assert op.status == "COMPLETED"

    def test_dropping_something_else_is_aborted_not_applied(self):
        maintenance.drop_audit_partition("accounts_user", None)
        assert MaintenanceOperation.objects.get(kind="PARTITION_DROP").status == "ABORTED"
        assert ddl.relation_exists("accounts_user")


@pytest.mark.django_db
class TestApprovalsAndShredCache:
    def test_requester_cannot_approve_their_own_operation(self):
        requester = User.objects.create_user(phone_number="+923001112222")
        other = User.objects.create_user(phone_number="+923003334444")
        op = MaintenanceOperation.objects.create(
            stream="M",
            kind="OPERATOR_INTERVENTION",
            target_digest="c" * 64,
            status="BLOCKED_OPERATOR",
            blocked_from_status="APPLIED",
            requested_by_pseudonym=pseudonym_for("ACCOUNT", requester.id),
        )
        with pytest.raises(DatabaseError), transaction.atomic():
            MaintenanceApproval.objects.create(
                operation=op, approver=requester, permission_code="maintenance.approve_intervention"
            )
        MaintenanceApproval.objects.create(
            operation=op, approver=other, permission_code="maintenance.approve_intervention"
        )

    def test_shred_cache_reapply_and_integrity_alarm(self):
        values = dict(
            pseudonym=uuid.uuid4(),
            subject_type="ACCOUNT",
            keys_digest="d" * 64,
            op_id=uuid7(),
            intent_seq=1,
            intent_entry_hash="e" * 64,
            shredded_at=timezone.now(),
        )
        assert record_shred(**values) is True
        assert record_shred(**values) is False
        with pytest.raises(IntegrityAlarm):
            record_shred(**{**values, "keys_digest": "f" * 64})
        with pytest.raises(DatabaseError), transaction.atomic():
            ShreddedPseudonym.objects.filter(pseudonym=values["pseudonym"]).update(intent_seq=2)


def test_every_maintenance_command_is_in_the_catalogue():
    """doc 09 §19.10: no maintenance action outside the protocol (startup check)."""
    commands_dir = Path(maintenance.__file__).resolve().parents[1] / "management" / "commands"
    commands = {p.stem for p in commands_dir.glob("*.py") if p.stem != "__init__"}
    read_only = {"verify_registry"}
    assert commands - read_only == set(maintenance.MAINTENANCE_COMMANDS)
    assert set(maintenance.MAINTENANCE_COMMANDS.values()) <= set(STREAM_M_KINDS)


@pytest.mark.django_db(transaction=True)
def test_concurrent_maintenance_jobs_never_share_a_sequence_number():
    errors = []

    def worker(name):
        try:
            noop_op(name=name)
        except Exception as exc:  # pragma: no cover - reported below
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(f"job-{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert maintenance.verify_registry("M") == 8
    assert maintenance.verify_local_chain("M") == 8
