"""AuditLog and its hold tables (ADR-022, TR-23; doc 03 §22.15, doc 06 §22.3, §22.6).

Tables are created by raw SQL in audit.0001 (monthly UUIDv7 RANGE partitions, append-only),
so the models are unmanaged. Actor, subject and represented-profile references are pseudonyms
with no database foreign keys; personal context and linkable IDs live in ``enc_parts``.
Read access is the auditor role only (never end users); reads use the ``audit_log_all`` view.
"""

from django.db import models

from common.db.uuid7 import uuid7


class AuditLogColumns(models.Model):
    class ActorType(models.TextChoices):
        USER = "USER"  # the account owner acting for itself
        MANAGER = "MANAGER"  # a family manager acting for a represented profile
        ADMIN = "ADMIN"
        SYSTEM = "SYSTEM"

    class Result(models.TextChoices):
        SUCCESS = "SUCCESS"
        FAILURE = "FAILURE"
        DENIED = "DENIED"

    class Category(models.TextChoices):  # retention is set per category (doc 06 §22.3)
        SYSTEM = "SYSTEM"
        FINANCIAL = "FINANCIAL"
        ADMINISTRATIVE = "ADMINISTRATIVE"
        STATE_CHANGE = "STATE_CHANGE"
        SECURITY = "SECURITY"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    occurred_at = models.DateTimeField()
    actor_type = models.CharField(max_length=7, choices=ActorType.choices)
    actor_pseudonym = models.UUIDField(null=True, blank=True)
    subject_pseudonym = models.UUIDField(null=True, blank=True)
    represented_profile_pseudonym = models.UUIDField(null=True, blank=True)
    action = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=100)
    result = models.CharField(max_length=7, choices=Result.choices)
    category = models.CharField(max_length=14, choices=Category.choices)
    request_id = models.CharField(max_length=64, null=True, blank=True)
    safe_metadata = models.JSONField(default=dict)
    enc_parts = models.JSONField(default=list)

    class Meta:
        abstract = True


class AuditLog(AuditLogColumns):
    class Meta:
        managed = False
        db_table = "audit_log"


class AuditLogHold(AuditLogColumns):
    """Held events copied out of a dropped partition (unpartitioned)."""

    retain_until = models.DateTimeField(null=True, blank=True)
    moved_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "audit_log_hold"


class AuditLogHoldLink(models.Model):
    pk = models.CompositePrimaryKey("event_id", "hold_case_id")
    event_id = models.UUIDField()
    hold_case_id = models.UUIDField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "audit_log_hold_link"
