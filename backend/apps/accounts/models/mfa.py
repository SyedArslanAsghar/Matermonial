"""Account authenticator (TOTP) for ordinary accounts (TR-16; owner decision DR-2026-11-20-O-3).

Optional for every account; **required** for a manager to perform a Sensitive action on behalf
of a profile (step-up, ``apps.family.services.step_up``). Same design as the admin
authenticator (ADR-033): django-otp TOTP with the seed sealed by AES-256-GCM under the
``ACCOUNT_MFA`` key ring, bound to the account by the associated data; a time step is accepted at
most once; django-otp throttling applies. One device per account. It is separate from the admin
authenticator and from phone verification.
"""

import uuid

from django.db import models
from django.db.models import Q
from django_otp.models import Device, ThrottlingMixin, TimestampMixin


class AccountTotpDevice(TimestampMixin, ThrottlingMixin, Device):
    # UUID key (CC-R32): unlike the admin device, this one is never resolved from a session's
    # persistent id, so django-otp's integer-key need doesn't apply.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Overrides django-otp's CASCADE (TR-09 rule F4: accounts are anonymised, not deleted).
    user = models.OneToOneField(
        "accounts.User", on_delete=models.PROTECT, related_name="account_totp_device"
    )
    key_version = models.PositiveIntegerField()
    key_nonce = models.BinaryField()
    key_ciphertext = models.BinaryField()
    digits = models.PositiveSmallIntegerField(default=6)
    step = models.PositiveSmallIntegerField(default=30)
    tolerance = models.PositiveSmallIntegerField(default=1)
    drift = models.SmallIntegerField(default=0)
    last_t = models.BigIntegerField(default=-1)

    class Meta:
        db_table = "account_totp_device"
        constraints = [
            models.CheckConstraint(condition=Q(digits__in=[6, 8]), name="account_totp_digits"),
            models.CheckConstraint(condition=Q(step__gte=15), name="account_totp_step"),
            models.CheckConstraint(condition=Q(tolerance__lte=2), name="account_totp_tolerance"),
        ]

    def get_throttle_factor(self):
        from django.conf import settings

        return settings.ACCOUNT_MFA_THROTTLE_FACTOR
