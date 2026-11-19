"""AccountSecurityEvent: append-only, partitioned security history (TR-17, TR-23; ADR-032).

Specification: doc 03 §22.2, doc 06 §22.3. The table is created by raw SQL in accounts.0001
(monthly RANGE partitions on the UUIDv7 ``id``; append-only and envelope triggers), so the
model is unmanaged. Rows hold pseudonyms, never user IDs; IP address, user agent, location
and linkable IDs live only inside ``enc_parts`` envelopes.
"""

from django.db import models

from common.db.uuid7 import uuid7

EVENT_TYPES = (
    "LOGIN_SUCCEEDED",
    "LOGIN_FAILED",
    "LOGIN_DENIED_ACCOUNT_STATE",
    "SESSION_CREATED",
    "SESSION_REVOKED",
    "REFRESH_REUSE_DETECTED",
    "PASSWORD_RESET_REQUESTED",
    "PASSWORD_RESET_COMPLETED",
    "PASSWORD_RESET_FAILED",
    "PASSWORD_CHANGED",
    "PASSWORD_CHANGE_FAILED",
    "OTP_VERIFICATION_FAILED",
    "OTP_ATTEMPTS_EXHAUSTED",
    "OTP_RATE_LIMITED",
    "STEP_UP_SUCCEEDED",
    "STEP_UP_FAILED",
    "PHONE_CHANGED",
    "EMAIL_CHANGED",
    "ADMIN_MFA_ENROLLED",
    "ADMIN_MFA_REMOVED",
    # ADR-033 Amendment 1 (DR-2026-11-19-O-8, A1-5)
    "ADMIN_MFA_RECOVERY_REQUESTED",
    "ADMIN_MFA_RECOVERY_DECIDED",
    "ADMIN_MFA_EMERGENCY_RECOVERY",
    "DEACTIVATED",
    "REACTIVATED",
    "DELETION_REQUESTED",
    "DELETION_CANCELLED",
    "SUSPICIOUS_ACTIVITY",
    "RATE_LIMIT_TRIGGERED",
)


class AccountSecurityEvent(models.Model):
    class Result(models.TextChoices):
        SUCCESS = "SUCCESS"
        FAILURE = "FAILURE"
        INFO = "INFO"

    class ActorType(models.TextChoices):
        SELF = "SELF"
        ADMIN = "ADMIN"
        SYSTEM = "SYSTEM"
        ANONYMOUS = "ANONYMOUS"

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    event_type = models.CharField(max_length=40, choices=[(t, t) for t in EVENT_TYPES])
    result = models.CharField(max_length=7, choices=Result.choices)
    reason_code = models.CharField(max_length=40, null=True, blank=True)
    actor_type = models.CharField(max_length=9, choices=ActorType.choices)
    request_id = models.CharField(max_length=64, null=True, blank=True)
    occurred_at = models.DateTimeField()
    subject_pseudonym = models.UUIDField(null=True, blank=True)
    actor_pseudonym = models.UUIDField(null=True, blank=True)
    # HMAC of the normalised phone, only when no subject resolves (90-day retention).
    subject_hash = models.CharField(max_length=64, null=True, blank=True)
    enc_parts = models.JSONField(default=list)

    class Meta:
        managed = False
        db_table = "account_security_event"

    def __str__(self):
        return f"{self.event_type} {self.result} {self.id}"
