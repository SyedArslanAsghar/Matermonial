"""TR-24 maintenance-protocol tables (doc 03 §22.15, doc 09 §19; TR-23 shred cache and rewrap log).

None of these tables holds personal data except pseudonyms where the specification names them
(``shredded_pseudonym``, ``requested_by_pseudonym``); registry ``summary`` objects never contain
pseudonyms. ``maintenance_audit_log`` is created by raw SQL (yearly UUIDv7 partitions,
append-only), so its model is unmanaged.
"""

from django.db import models
from django.db.models import Q

from common.db.uuid7 import uuid7

STREAM_R_KINDS = ("DELETION", "SHRED")
STREAM_M_KINDS = (
    "PARTITION_CREATE",
    "PARTITION_DROP",
    "HOLD_RELEASE",
    "HOLD_RETENTION_PURGE",
    "KEK_ROTATE",
    "KEK_DESTROY",
    "QUEUE_KEY_ROTATE",
    "QUEUE_KEY_DESTROY",
    "RESTORE_RECONCILE",
    "REGISTRY_CHECKPOINT",
    "MAINT_LOG_PARTITION_DROP",
    "OPERATOR_INTERVENTION",
)
# doc 09 §19.3 state machines (Stream R has no APPLYING-less path and no ABORTED).
STATUSES = (
    "INTENT_PENDING",
    "INTENT_REGISTERING",
    "INTENT_REGISTERED",
    "APPLYING",
    "APPLIED",
    "VERIFIED_LOCAL",
    "COMPLETION_REGISTERING",
    "COMPLETED",
    "ABORT_REGISTERING",
    "ABORTED",
    "BLOCKED_OPERATOR",
)
HEX64 = r"^[0-9a-f]{64}$"


class MaintenanceOperation(models.Model):
    op_id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    stream = models.CharField(max_length=1, choices=[("R", "R"), ("M", "M")])
    kind = models.CharField(
        max_length=30, choices=[(k, k) for k in STREAM_R_KINDS + STREAM_M_KINDS]
    )
    target_digest = models.CharField(max_length=64)
    status = models.CharField(max_length=22, choices=[(s, s) for s in STATUSES])
    blocked_from_status = models.CharField(
        max_length=22, choices=[(s, s) for s in STATUSES], null=True, blank=True
    )
    parent_op_id = models.UUIDField(null=True, blank=True)
    requested_by_pseudonym = models.UUIDField(null=True, blank=True)
    intent_seq = models.BigIntegerField(null=True, blank=True)
    intent_hash = models.CharField(max_length=64, null=True, blank=True)
    outcome_seq = models.BigIntegerField(null=True, blank=True)
    outcome_hash = models.CharField(max_length=64, null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=200, null=True, blank=True)  # codes, no personal data
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "maintenance_operation"
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "target_digest"],
                condition=~Q(status="ABORTED"),
                name="maintenance_operation_once_per_target",
            ),
            models.CheckConstraint(
                condition=~Q(stream="R", status__in=["ABORTED", "ABORT_REGISTERING"]),
                name="maintenance_operation_no_abort_in_stream_r",
            ),
            models.CheckConstraint(
                condition=Q(stream="R", kind__in=STREAM_R_KINDS)
                | Q(stream="M", kind__in=STREAM_M_KINDS),
                name="maintenance_operation_kind_matches_stream",
            ),
            models.CheckConstraint(
                condition=Q(target_digest__regex=HEX64), name="maintenance_operation_target_hex"
            ),
            models.CheckConstraint(
                condition=Q(status="BLOCKED_OPERATOR", blocked_from_status__isnull=False)
                | (~Q(status="BLOCKED_OPERATOR") & Q(blocked_from_status__isnull=True)),
                name="maintenance_operation_blocked_remembers_state",
            ),
        ]

    def __str__(self):
        return f"{self.kind} {self.status} {self.op_id}"


class RegistryStreamHead(models.Model):
    """One row per stream (doc 09 §19.2). Natural key by specification: ``stream``."""

    stream = models.CharField(max_length=1, primary_key=True)
    last_seq = models.BigIntegerField(default=0)
    last_hash = models.CharField(max_length=64, default="0" * 64)
    pending_op_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "registry_stream_head"
        constraints = [
            models.CheckConstraint(condition=Q(stream__in=["R", "M"]), name="registry_head_stream"),
            models.CheckConstraint(condition=Q(last_seq__gte=0), name="registry_head_seq"),
        ]


class MaintenanceAuditLog(models.Model):
    """Local copy of every registry entry header (+ entry_hash). Partitioned yearly."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)  # log_row_id
    schema_version = models.PositiveSmallIntegerField()
    stream = models.CharField(max_length=1)
    seq = models.BigIntegerField()
    prev_hash = models.CharField(max_length=64)
    registry_key_version = models.PositiveIntegerField()
    op_id = models.UUIDField()
    parent_op_id = models.UUIDField(null=True)
    kind = models.CharField(max_length=30)
    phase = models.CharField(max_length=12)
    target_digest = models.CharField(max_length=64)
    params_digest = models.CharField(max_length=64)
    companion_ref = models.JSONField(null=True)
    summary = models.JSONField(default=dict)
    executor_job_run_id = models.CharField(max_length=100, null=True)
    executor_role = models.CharField(max_length=50)
    requested_by_pseudonym = models.UUIDField(null=True)
    approvals = models.JSONField(default=list)
    recorded_at = models.DateTimeField()
    entry_hash = models.CharField(max_length=64)
    restored_from_registry = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = "maintenance_audit_log"


class MaintenanceApproval(models.Model):
    pk = models.CompositePrimaryKey("operation", "approver")
    operation = models.ForeignKey(
        MaintenanceOperation, on_delete=models.PROTECT, db_column="op_id", related_name="approvals"
    )
    approver = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, db_column="approver_user_id"
    )
    approved_at = models.DateTimeField(auto_now_add=True)
    permission_code = models.CharField(max_length=100)

    class Meta:
        db_table = "maintenance_approval"


class ShreddedPseudonym(models.Model):
    """Local cache of the registry's SHRED entries (TR-23). No automatic expiry."""

    pseudonym = models.UUIDField(primary_key=True)
    subject_type = models.CharField(max_length=7)
    keys_digest = models.CharField(max_length=64)
    op_id = models.UUIDField()
    intent_seq = models.BigIntegerField()
    intent_entry_hash = models.CharField(max_length=64)
    shredded_at = models.DateTimeField()

    class Meta:
        db_table = "shredded_pseudonym"


class KekRewrapLog(models.Model):
    """Append-only record of KEK_ROTATE rewraps (TR-23)."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    key_id = models.UUIDField()
    from_version = models.PositiveIntegerField()
    to_version = models.PositiveIntegerField()
    rotate_op_id = models.UUIDField()
    rewrapped_at = models.DateTimeField()

    class Meta:
        db_table = "kek_rewrap_log"
