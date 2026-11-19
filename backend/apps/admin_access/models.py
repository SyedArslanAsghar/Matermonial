"""Admin roles, permissions and MFA: the only source of administrative authorization (TR-07).

Specification: doc 03 §16.2-16.5 and §22.15, ADR-027, doc 06 §15 and §22.2.

- Django groups and ``user_permissions`` are never used (a trigger keeps their link tables empty,
  accounts.0001). ``User.is_staff`` is a projection of "has a live role or is a break-glass
  superuser", written only by ``services.roles.refresh_staff_projection``.
- ``is_superuser`` is break-glass only: at most two accounts (database trigger, 0001), granted
  and revoked only through ``services.superusers`` (audited) and protected by MFA.
- MFA uses django-otp. ``AdminTotpDevice`` stores its TOTP seed encrypted (AES-256-GCM with the
  ADMIN_MFA key ring), never in plaintext. Enrollment needs a single-use code issued out of band
  (``AdminMfaEnrollment``), stored only as a keyed hash.
"""

import uuid

from django.db import models
from django.db.models import F, Q
from django_otp.models import Device, ThrottlingMixin, TimestampMixin

CODE = r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_.]*$"
ROLE_CODE = r"^[a-z][a-z0-9_]{1,59}$"


class AdminPermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # "<app_label>.<codename>": Django admin model permissions (e.g. "accounts.view_user") and
    # custom ones (e.g. "admin_access.manage_roles").
    code = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_sensitive = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "admin_permission"
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(condition=Q(code__regex=CODE), name="admin_permission_code")
        ]

    def __str__(self):
        return self.code


class AdminRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    permissions = models.ManyToManyField(
        AdminPermission, through="AdminRolePermission", related_name="roles"
    )

    class Meta:
        db_table = "admin_role"
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(condition=Q(code__regex=ROLE_CODE), name="admin_role_code")
        ]

    def __str__(self):
        return self.code


class AdminRolePermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Role definitions are reference data managed by the catalogue sync; a role is retired
    # (is_active = False), never deleted, so PROTECT keeps assignment history intact.
    role = models.ForeignKey(AdminRole, on_delete=models.PROTECT)
    permission = models.ForeignKey(AdminPermission, on_delete=models.PROTECT)

    class Meta:
        db_table = "admin_role_permission"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"], name="admin_role_permission_unique"
            )
        ]


class AdminUserRole(models.Model):
    """One assignment of a role to an account. Rows are never deleted (history); revocation
    sets ``revoked_at``. A row whose ``expires_at`` has passed grants nothing."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="admin_roles")
    role = models.ForeignKey(AdminRole, on_delete=models.PROTECT, related_name="assignments")
    # Null only for assignments made by an operator through a management command (break-glass
    # bootstrap); the audit log records the channel.
    assigned_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="admin_roles_assigned",
    )
    assigned_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "admin_user_role"
        indexes = [models.Index(fields=["user", "revoked_at"], name="admin_user_role_user_live")]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"],
                condition=Q(revoked_at__isnull=True),
                name="admin_user_role_one_live",
            ),
            models.CheckConstraint(
                condition=Q(expires_at__isnull=True) | Q(expires_at__gt=F("assigned_at")),
                name="admin_user_role_expiry_after_assignment",
            ),
            models.CheckConstraint(
                condition=Q(revoked_at__isnull=True) | Q(revoked_at__gte=F("assigned_at")),
                name="admin_user_role_revoked_after_assignment",
            ),
            # Nobody grants themselves a role (privilege escalation).
            models.CheckConstraint(
                condition=Q(assigned_by__isnull=True) | ~Q(user=F("assigned_by")),
                name="admin_user_role_not_self_assigned",
            ),
        ]


class AdminTotpDevice(TimestampMixin, ThrottlingMixin, Device):
    """A django-otp TOTP device whose seed is stored encrypted (services.mfa).

    The primary key is an integer: django-otp resolves a session's verified device from
    ``"<app>.<model>/<int id>"`` (``Device.from_persistent_id``), so a UUID key would make every
    session unverifiable. This internal table is never exposed through the API. One device per
    account; a reset deletes it (the security log keeps ADMIN_MFA_ENROLLED / ADMIN_MFA_REMOVED).
    """

    id = models.BigAutoField(primary_key=True)
    # Overrides django-otp's CASCADE (TR-09 rule F4: accounts are anonymised, not deleted).
    user = models.OneToOneField(
        "accounts.User", on_delete=models.PROTECT, related_name="admin_totp_device"
    )
    key_version = models.PositiveIntegerField()
    key_nonce = models.BinaryField()
    key_ciphertext = models.BinaryField()
    digits = models.PositiveSmallIntegerField(default=6)
    step = models.PositiveSmallIntegerField(default=30)
    tolerance = models.PositiveSmallIntegerField(default=1)
    drift = models.SmallIntegerField(default=0)
    # Time step of the last accepted token: a token is never accepted twice (replay).
    last_t = models.BigIntegerField(default=-1)

    class Meta:
        db_table = "admin_totp_device"
        constraints = [
            models.CheckConstraint(condition=Q(digits__in=[6, 8]), name="admin_totp_digits"),
            models.CheckConstraint(condition=Q(step__gte=15), name="admin_totp_step"),
            models.CheckConstraint(condition=Q(tolerance__lte=2), name="admin_totp_tolerance"),
        ]

    def get_throttle_factor(self):
        from django.conf import settings

        return settings.ADMIN_MFA_THROTTLE_FACTOR

    def verify_token(self, token):
        from .services.mfa import verify_device_token

        return verify_device_token(self, token)


class AdminMfaEnrollment(models.Model):
    """A single-use, short-lived code that lets an account enroll its TOTP device.

    Enrollment needs the password **and** this code, which is delivered out of band, so a stolen
    password alone can't register an attacker's authenticator.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="admin_mfa_enrollments"
    )
    # Null when issued by an operator through a management command.
    issued_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="admin_mfa_enrollments_issued",
    )
    code_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "admin_mfa_enrollment"
        constraints = [
            models.CheckConstraint(
                condition=Q(code_hash__regex=r"^[0-9a-f]{64}$"), name="admin_mfa_enrollment_hash"
            ),
            models.CheckConstraint(
                condition=Q(expires_at__gt=F("created_at")), name="admin_mfa_enrollment_expiry"
            ),
            models.CheckConstraint(
                condition=Q(used_at__isnull=True) | Q(revoked_at__isnull=True),
                name="admin_mfa_enrollment_used_or_revoked",
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(used_at__isnull=True, revoked_at__isnull=True),
                name="admin_mfa_enrollment_one_open",
            ),
            models.CheckConstraint(
                condition=Q(issued_by__isnull=True) | ~Q(user=F("issued_by")),
                name="admin_mfa_enrollment_not_self_issued",
            ),
        ]
