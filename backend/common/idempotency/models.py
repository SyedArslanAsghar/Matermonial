"""IdempotencyRecord (CC-R39, CC-R52; TR-11; doc 03 §22.2: "Exact columns are fixed at G4").

Stores, per account and ``Idempotency-Key``, the request fingerprint and the original
response, so a retry replays the response instead of repeating the operation. The record is
written in the **same transaction** as the business operation (common.idempotency.services),
so a rolled-back operation leaves no record and can be retried.

Column decisions (G4, documented assumption):
- ``scope`` is the operation (for example ``credits.purchase``): reusing a key for another
  operation, or with a different request body, is a conflict, never a replay.
- Stored responses can contain personal data, so records expire (default 24 h) and are purged.
"""

import uuid

from django.db import models
from django.db.models import F, Q


class IdempotencyRecord(models.Model):
    class Status(models.TextChoices):
        COMPLETED = "COMPLETED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # PROTECT (TR-09 F4); the owning service already holds the account lock (class P).
    account = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="idempotency_records"
    )
    key = models.CharField(max_length=128)
    scope = models.CharField(max_length=100)
    request_fingerprint = models.CharField(max_length=64)
    status = models.CharField(max_length=9, choices=Status.choices, default=Status.COMPLETED)
    response_status = models.PositiveSmallIntegerField()
    response_body = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "idempotency_record"
        indexes = [models.Index(fields=["expires_at"], name="idempotency_expires")]
        constraints = [
            models.UniqueConstraint(fields=["account", "key"], name="idempotency_account_key"),
            # Keys are client-generated opaque tokens (UUIDs recommended).
            models.CheckConstraint(
                condition=Q(key__regex=r"^[A-Za-z0-9_.:-]{8,128}$"),
                name="idempotency_key_format",
            ),
            models.CheckConstraint(
                condition=Q(request_fingerprint__regex=r"^[0-9a-f]{64}$"),
                name="idempotency_fingerprint_sha256",
            ),
            models.CheckConstraint(
                condition=Q(response_status__gte=100, response_status__lte=599),
                name="idempotency_http_status",
            ),
            models.CheckConstraint(
                condition=Q(expires_at__gt=F("created_at")), name="idempotency_expires_later"
            ),
        ]

    def __str__(self):
        return f"{self.scope} {self.key}"
