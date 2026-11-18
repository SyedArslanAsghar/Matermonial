"""OutboxEvent: a pseudonymous, encrypted work queue (TR-11, ADR-028; doc 03 §22.12).

- Written in the same transaction as the business operation (approved core, FR-NOT-005).
- Banned in the row: raw user, profile or resource IDs, names, phone numbers, message text.
  The recipient is a pseudonym; the aggregate ID and handler parameters are inside
  ``payload_enc`` (AES-GCM under the versioned queue key, ``id`` as associated data).
- ``dedupe_key = HMAC(K_dedupe, business event identity)``; unique among live rows.
- Redaction trigger (events.0001): payload_enc, recipient_pseudonym and dedupe_key may only
  change from a value to NULL, and only on a terminal row; FINANCIAL_OBLIGATION rows need the
  stricter conditions of doc 03 §22.12.
"""

from django.db import models
from django.db.models import Q

from common.db.uuid7 import uuid7

TERMINAL_STATUSES = ("DONE", "CANCELLED", "DEAD", "DEAD_UNDECRYPTABLE")


class OutboxEvent(models.Model):
    class EventClass(models.TextChoices):
        NOTIFICATION = "NOTIFICATION"
        FINANCIAL_OBLIGATION = "FINANCIAL_OBLIGATION"

    class Category(models.TextChoices):
        SECURITY = "SECURITY"
        FINANCIAL = "FINANCIAL"
        MATRIMONIAL_ACTIVITY = "MATRIMONIAL_ACTIVITY"
        ACCOUNT = "ACCOUNT"
        SYSTEM = "SYSTEM"

    class Status(models.TextChoices):
        PENDING = "PENDING"
        CLAIMED = "CLAIMED"
        DONE = "DONE"
        CANCELLED = "CANCELLED"
        DEAD = "DEAD"
        BLOCKED_INTEGRITY = "BLOCKED_INTEGRITY"
        DEAD_UNDECRYPTABLE = "DEAD_UNDECRYPTABLE"

    class ObligationResolution(models.TextChoices):
        PENDING = "PENDING"
        REPLACED_VERIFIED = "REPLACED_VERIFIED"
        OBLIGATION_SATISFIED_VERIFIED = "OBLIGATION_SATISFIED_VERIFIED"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    event_type = models.CharField(max_length=60)
    event_class = models.CharField(max_length=20, choices=EventClass.choices)
    category = models.CharField(max_length=20, choices=Category.choices)
    status = models.CharField(max_length=18, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    lease_token = models.UUIDField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    terminal_at = models.DateTimeField(null=True, blank=True)
    redacted_at = models.DateTimeField(null=True, blank=True)

    recipient_pseudonym = models.UUIDField(null=True, blank=True)
    dedupe_key = models.CharField(max_length=64, null=True, blank=True)
    aggregate_type = models.CharField(max_length=60)
    payload_enc = models.BinaryField(null=True, blank=True)
    queue_key_version = models.PositiveIntegerField()

    obligation_resolution = models.CharField(
        max_length=29, choices=ObligationResolution.choices, null=True, blank=True
    )
    replaced_by_event_id = models.UUIDField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "outbox_event"
        indexes = [
            models.Index(fields=["status", "id"], name="outbox_status_id"),
            models.Index(fields=["status", "terminal_at"], name="outbox_status_terminal"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["dedupe_key"],
                condition=~Q(status__in=["DEAD_UNDECRYPTABLE", "CANCELLED"]),
                name="outbox_dedupe_live_unique",
            ),
            models.CheckConstraint(
                condition=Q(dedupe_key__isnull=True) | Q(dedupe_key__regex=r"^[0-9a-f]{64}$"),
                name="outbox_dedupe_is_hmac_hex",
            ),
            # A claim always carries a lease; other states never do.
            models.CheckConstraint(
                condition=Q(
                    status="CLAIMED", lease_token__isnull=False, lease_expires_at__isnull=False
                )
                | (~Q(status="CLAIMED") & Q(lease_token__isnull=True)),
                name="outbox_lease_only_when_claimed",
            ),
            models.CheckConstraint(
                condition=Q(status__in=TERMINAL_STATUSES, terminal_at__isnull=False)
                | (~Q(status__in=TERMINAL_STATUSES) & Q(terminal_at__isnull=True)),
                name="outbox_terminal_at_consistent",
            ),
            # Obligation fields exist only on financial obligations.
            models.CheckConstraint(
                condition=Q(event_class="FINANCIAL_OBLIGATION")
                | Q(
                    obligation_resolution__isnull=True,
                    replaced_by_event_id__isnull=True,
                    resolved_at__isnull=True,
                ),
                name="outbox_obligation_fields_financial_only",
            ),
        ]

    def __str__(self):
        return f"{self.event_type} {self.status} {self.id}"
