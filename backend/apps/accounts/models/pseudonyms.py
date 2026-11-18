"""Subject pseudonyms and data keys (TR-23, ADR-032; doc 03 §22.2, doc 06 §22.6).

Logs (AuditLog, AccountSecurityEvent, OutboxEvent recipients) never store account or profile
IDs: they store a random pseudonym, and personal context goes into envelopes encrypted with
that subject's data key. Deletion unlinks the pseudonym and destroys the key, so existing log
rows stay byte-for-byte unchanged but no longer identify anyone.

Database triggers (migration accounts.0001) make the lifecycle one-way:
- a pseudonym can be unlinked (subject_id -> NULL) but never relinked, and is never deleted;
- a data key can be destroyed (wrapped_key -> NULL) but a destroyed tombstone never changes,
  and keys are never deleted.
"""

import uuid

from django.db import models
from django.db.models import Q


class SubjectPseudonym(models.Model):
    class SubjectType(models.TextChoices):
        ACCOUNT = "ACCOUNT"
        PROFILE = "PROFILE"

    # Random (uuid4), not time-ordered: a pseudonym must reveal nothing about its subject.
    pseudonym = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject_type = models.CharField(max_length=7, choices=SubjectType.choices)
    # Soft reference (class S): NULL once unlinked at deletion PROCESSING.
    subject_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    unlinked_at = models.DateTimeField(null=True, blank=True)
    # Set while a legal or security hold defers unlinking (FR-DAT-009).
    hold_ref = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "accounts_subject_pseudonym"
        constraints = [
            # One pseudonym per subject.
            models.UniqueConstraint(
                fields=["subject_type", "subject_id"],
                condition=Q(subject_id__isnull=False),
                name="subject_pseudonym_one_per_subject",
            ),
            models.CheckConstraint(
                condition=Q(unlinked_at__isnull=True, subject_id__isnull=False)
                | Q(unlinked_at__isnull=False, subject_id__isnull=True),
                name="subject_pseudonym_unlink_consistent",
            ),
        ]

    def __str__(self):  # deliberately no subject_id
        return f"{self.subject_type} pseudonym {self.pseudonym}"


class SubjectDataKey(models.Model):
    key_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pseudonym = models.ForeignKey(
        SubjectPseudonym, on_delete=models.PROTECT, related_name="data_keys", db_column="pseudonym"
    )
    kek_version = models.PositiveIntegerField()
    # nonce || AES-GCM(KEK[kek_version], data key, aad=key_id). NULL once destroyed.
    wrapped_key = models.BinaryField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    destroyed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_subject_data_key"
        constraints = [
            # doc 03 §22.2 / doc 06 §22.6: destroyed exactly when no wrapped key remains.
            models.CheckConstraint(
                condition=Q(destroyed_at__isnull=True, wrapped_key__isnull=False)
                | Q(destroyed_at__isnull=False, wrapped_key__isnull=True),
                name="subject_data_key_destroyed_iff_no_key",
            ),
            models.UniqueConstraint(
                fields=["pseudonym"],
                condition=Q(destroyed_at__isnull=True),
                name="subject_data_key_one_live_per_pseudonym",
            ),
        ]

    def __str__(self):
        return f"data key {self.key_id} ({'destroyed' if self.destroyed_at else 'live'})"
