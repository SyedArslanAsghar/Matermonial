"""PhoneVerification: one-time codes (doc 03 §2.5 / §5.1, doc 06 §3; FR-ACC-002).

- Only ``code_hash = HMAC(OTP key[key_version], "<id>:<code>")`` is stored; the code itself is
  never stored or logged (CC-R47).
- Every send creates a new row; a still-pending earlier row for the same phone and purpose
  becomes SUPERSEDED, so at most one code per phone and purpose is ever usable.
"""

import uuid

from django.db import models
from django.db.models import Q


class PhoneVerification(models.Model):
    class Purpose(models.TextChoices):
        VERIFY_PHONE = "VERIFY_PHONE"  # prove ownership of the account's phone (FR-ACC-002)
        PASSWORD_RESET = "PASSWORD_RESET"  # doc 06 §22.1 password reset

    class Status(models.TextChoices):
        PENDING = "PENDING"
        VERIFIED = "VERIFIED"
        SUPERSEDED = "SUPERSEDED"
        EXHAUSTED = "EXHAUSTED"  # maximum attempts reached

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="phone_verifications",
    )
    phone_number = models.CharField(max_length=16)
    purpose = models.CharField(max_length=14, choices=Purpose.choices)
    code_hash = models.CharField(max_length=64)
    key_version = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    resend_count = models.PositiveSmallIntegerField(default=0)
    provider_reference = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "verification_phone_verification"
        indexes = [
            models.Index(fields=["phone_number", "created_at"], name="phone_verif_phone_time"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["phone_number", "purpose"],
                condition=Q(status="PENDING"),
                name="phone_verif_one_pending",
            ),
            models.CheckConstraint(
                condition=Q(code_hash__regex=r"^[0-9a-f]{64}$"), name="phone_verif_hash_hex"
            ),
            models.CheckConstraint(
                condition=Q(status="VERIFIED", verified_at__isnull=False)
                | (~Q(status="VERIFIED") & Q(verified_at__isnull=True)),
                name="phone_verif_verified_at_consistent",
            ),
            models.CheckConstraint(
                condition=Q(phone_number__regex=r"^\+[1-9][0-9]{7,14}$"),
                name="phone_verif_phone_e164",
            ),
        ]

    def __str__(self):  # never the phone number or code
        return f"{self.purpose} {self.status} {self.id}"
