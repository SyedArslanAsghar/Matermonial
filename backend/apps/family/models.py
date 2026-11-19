"""Family management (doc 03 §6, §22.5; doc 05 §2; doc 14 §1–§8; doc 15 §4).

- An authorization is scoped to one profile and one manager account; the owner invites, the
  manager accepts [DECIDED]. At most one PENDING/ACTIVE/PAUSED authorization per pair (partial
  unique index).
- Only ACTIVE authorizations whose ``expires_at`` hasn't passed grant anything [DECIDED];
  expiry is optional and absent by default (FR-FAM-007).
- Permissions are per authorization (``AuthorizationPermission``). Sensitivity follows the
  approved doc 14 §3 levels (Normal / Sensitive / Owner-only); doc 03 §22.5's tier column is
  OD-05 (OPEN).
- History, manager action logs and profile access history are append-only (trigger).
- Every account FK is PROTECT (TR-09 F4).
"""

import uuid

from django.db import models
from django.db.models import F, Q

CODE = r"^[a-z][a-z0-9_]{1,59}$"


class ManagerPermission(models.Model):
    class Sensitivity(models.TextChoices):
        NORMAL = "NORMAL"
        SENSITIVE = "SENSITIVE"
        OWNER_ONLY = "OWNER_ONLY"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    sensitivity = models.CharField(max_length=10, choices=Sensitivity.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "family_manager_permission"
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(condition=Q(code__regex=CODE), name="manager_permission_code")
        ]

    def __str__(self):
        return self.code


class ManagerPermissionGroup(models.Model):
    """A configurable template (FR-FAM-004), not an immutable role."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_system_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    permissions = models.ManyToManyField(
        ManagerPermission, through="ManagerPermissionGroupPermission", related_name="groups"
    )

    class Meta:
        db_table = "family_permission_group"
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(condition=Q(code__regex=CODE), name="permission_group_code")
        ]

    def __str__(self):
        return self.code


class ManagerPermissionGroupPermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(ManagerPermissionGroup, on_delete=models.PROTECT)
    permission = models.ForeignKey(ManagerPermission, on_delete=models.PROTECT)

    class Meta:
        db_table = "family_permission_group_permission"
        constraints = [
            models.UniqueConstraint(fields=["group", "permission"], name="group_permission_unique")
        ]


class ProfileManagerAuthorization(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        ACTIVE = "ACTIVE"
        PAUSED = "PAUSED"
        EXPIRED = "EXPIRED"
        REVOKED = "REVOKED"
        REJECTED = "REJECTED"

    LIVE = ("PENDING", "ACTIVE", "PAUSED")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        "profiles.MatrimonialProfile",
        on_delete=models.PROTECT,
        related_name="manager_authorizations",
    )
    manager = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="managed_authorizations"
    )
    invited_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="manager_invitations_sent"
    )
    permission_group = models.ForeignKey(
        ManagerPermissionGroup, on_delete=models.PROTECT, null=True, blank=True
    )
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    invited_at = models.DateTimeField()
    # Invitation TTL is OD-05e (OPEN): no value is set until it is decided.
    invitation_expires_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    authorized_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # optional; none by default
    paused_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=40, null=True, blank=True)  # reason code
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "family_authorization"
        indexes = [
            models.Index(fields=["manager", "status"], name="family_auth_manager_status"),
            models.Index(fields=["profile", "status"], name="family_auth_profile_status"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "manager"],
                condition=Q(status__in=["PENDING", "ACTIVE", "PAUSED"]),
                name="family_auth_one_live_per_pair",
            ),
            models.CheckConstraint(
                condition=~Q(manager=F("invited_by")), name="family_auth_not_self_invited"
            ),
            models.CheckConstraint(
                condition=Q(expires_at__isnull=True) | Q(expires_at__gt=F("invited_at")),
                name="family_auth_expiry_after_invitation",
            ),
            # Status timestamps follow the state machine (doc 15 §4).
            models.CheckConstraint(
                condition=Q(status="PENDING", accepted_at__isnull=True)
                | Q(status__in=["ACTIVE", "PAUSED"], accepted_at__isnull=False)
                | Q(status__in=["EXPIRED", "REVOKED", "REJECTED"]),
                name="family_auth_accepted_consistent",
            ),
            models.CheckConstraint(
                condition=~Q(status="PAUSED") | Q(paused_at__isnull=False),
                name="family_auth_paused_has_time",
            ),
            models.CheckConstraint(
                condition=~Q(status="REVOKED") | Q(revoked_at__isnull=False),
                name="family_auth_revoked_has_time",
            ),
            models.CheckConstraint(
                condition=~Q(status="REJECTED")
                | Q(rejected_at__isnull=False, accepted_at__isnull=True),
                name="family_auth_rejected_consistent",
            ),
        ]

    def __str__(self):
        return f"{self.manager_id} → {self.profile_id} ({self.status})"


class AuthorizationPermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    authorization = models.ForeignKey(
        ProfileManagerAuthorization, on_delete=models.PROTECT, related_name="permission_grants"
    )
    permission = models.ForeignKey(ManagerPermission, on_delete=models.PROTECT)
    is_granted = models.BooleanField(default=False)
    granted_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT)
    granted_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "family_authorization_permission"
        constraints = [
            models.UniqueConstraint(
                fields=["authorization", "permission"], name="authorization_permission_unique"
            )
        ]


class ManagerAuthorizationHistory(models.Model):
    """Append-only (trigger, migration family.0001)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    authorization = models.ForeignKey(
        ProfileManagerAuthorization, on_delete=models.PROTECT, related_name="history"
    )
    action = models.CharField(max_length=40)
    performed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,  # null = system job
    )
    previous_values = models.JSONField(default=dict)
    new_values = models.JSONField(default=dict)
    reason = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "family_authorization_history"
        ordering = ["created_at"]


class ManagerActionLog(models.Model):
    """What a manager did on behalf of a profile (FR-FAM-009). Append-only."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    authorization = models.ForeignKey(ProfileManagerAuthorization, on_delete=models.PROTECT)
    profile = models.ForeignKey("profiles.MatrimonialProfile", on_delete=models.PROTECT)
    manager = models.ForeignKey("accounts.User", on_delete=models.PROTECT)
    action_type = models.CharField(max_length=60)
    target_model = models.CharField(max_length=60)
    target_id = models.UUIDField(null=True, blank=True)
    description = models.CharField(max_length=200, blank=True)  # codes only, no free text
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "family_manager_action_log"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["profile", "created_at"], name="family_action_profile")]


class ProfileAccessHistory(models.Model):
    """Every manager access to a represented profile (doc 03 §6.7). Append-only; distinct from
    the account login history."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey("profiles.MatrimonialProfile", on_delete=models.PROTECT)
    authorization = models.ForeignKey(ProfileManagerAuthorization, on_delete=models.PROTECT)
    manager = models.ForeignKey("accounts.User", on_delete=models.PROTECT)
    accessed_at = models.DateTimeField(auto_now_add=True)
    device = models.CharField(max_length=100, blank=True)
    browser = models.CharField(max_length=200, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    approximate_location = models.CharField(max_length=100, blank=True)
    access_type = models.CharField(max_length=60)

    class Meta:
        db_table = "family_profile_access_history"
        ordering = ["-accessed_at"]
        indexes = [models.Index(fields=["profile", "accessed_at"], name="family_access_profile")]
