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
    """Append-only (trigger, migration family.0001). One row per change to an authorization,
    an invitation or a request (doc 05 §2; owner decision DR-2026-11-20-O-1). Rows linked to an
    invitation or a request record only what its sender may see (created, cancelled, expired,
    answered); the background resolution of an invitation is recorded on the authorization
    only, so invitation history never reveals whether a number has an account (ADR-034)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    authorization = models.ForeignKey(
        ProfileManagerAuthorization,
        on_delete=models.PROTECT,
        related_name="history",
        null=True,
        blank=True,
    )
    invitation = models.ForeignKey(
        "ManagerInvitation",
        on_delete=models.PROTECT,
        related_name="history",
        null=True,
        blank=True,
    )
    request = models.ForeignKey(
        "ManagerRequest",
        on_delete=models.PROTECT,
        related_name="history",
        null=True,
        blank=True,
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
        constraints = [
            models.CheckConstraint(
                condition=Q(authorization__isnull=False)
                | Q(invitation__isnull=False)
                | Q(request__isnull=False),
                name="family_history_has_subject",
            )
        ]


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


class ManagerInvitation(models.Model):
    """The owner's record of one invitation, created for **every** accepted invite request
    whether or not the phone number belongs to an eligible account (KI-34). The owner sees only
    what they typed (a masked hint) and this record's status, so an invitation never reveals
    whether an account exists, is verified or is eligible. A background task links a real
    ``ProfileManagerAuthorization`` when the number resolves to an eligible account; the owner
    learns about the account only when the invitee accepts or declines.

    - The phone number is not stored: ``phone_digest`` is a keyed hash (SUBJECT_HASH ring) used
      to refuse duplicate pending invitations, ``phone_hint`` is the masked display.
    - ``invitee`` is internal only (never serialized to the owner).
    - A pending invitation expires ``FAMILY_INVITATION_TTL_DAYS`` (30) days after it was sent
      if it isn't accepted (OD-05e, owner decision DR-2026-11-20-O-2), the same way whether or
      not it was resolved to an account.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING"
        ACCEPTED = "ACCEPTED"
        DECLINED = "DECLINED"
        CANCELLED = "CANCELLED"
        EXPIRED = "EXPIRED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        "profiles.MatrimonialProfile", on_delete=models.PROTECT, related_name="manager_invitations"
    )
    invited_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="+")
    phone_digest = models.CharField(max_length=64)
    phone_hint = models.CharField(max_length=24)
    invitee = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    permission_group = models.ForeignKey(
        ManagerPermissionGroup, on_delete=models.PROTECT, null=True, blank=True
    )
    requested_permissions = models.JSONField(default=list, blank=True)
    requested_expires_at = models.DateTimeField(null=True, blank=True)
    authorization = models.OneToOneField(
        ProfileManagerAuthorization,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="invitation",
    )
    status = models.CharField(max_length=9, choices=Status.choices, default=Status.PENDING)
    invited_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "family_invitation"
        indexes = [
            models.Index(fields=["profile", "status"], name="family_invitation_profile"),
            models.Index(fields=["status", "expires_at"], name="family_invitation_expiry"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "phone_digest"],
                condition=Q(status="PENDING"),
                name="family_invitation_one_pending_per_number",
            ),
            models.CheckConstraint(
                condition=~Q(invitee=F("invited_by")), name="family_invitation_not_self"
            ),
            models.CheckConstraint(
                condition=Q(status__in=["PENDING", "CANCELLED", "EXPIRED"])
                | Q(authorization__isnull=False, responded_at__isnull=False),
                name="family_invitation_response_consistent",
            ),
            models.CheckConstraint(
                condition=~Q(status="CANCELLED") | Q(cancelled_at__isnull=False),
                name="family_invitation_cancelled_has_time",
            ),
            models.CheckConstraint(
                condition=~Q(status="EXPIRED") | Q(expired_at__isnull=False),
                name="family_invitation_expired_has_time",
            ),
            models.CheckConstraint(
                condition=Q(expires_at__gt=F("invited_at")),
                name="family_invitation_expiry_after_sending",
            ),
        ]


class ManagerRequest(models.Model):
    """Flow B (owner decision DR-2026-11-20-O-1): an account asks to manage another person's
    profile, identified by the owner's phone number. Enumeration-safe like invitations
    (ADR-034): every valid request is recorded and answered the same way; a background task
    resolves the number to an eligible owner's personal profile and notifies that owner. The
    requester learns about the owner only when the owner accepts or declines. The owner chooses
    the permissions when accepting; the authorization is then ACTIVE (both sides consented: the
    requester by asking, the owner by accepting). Expires after 30 days if not answered.

    - The phone number isn't stored: ``owner_phone_digest`` (HMAC) and ``owner_phone_hint``.
    - ``owner`` and ``profile`` are internal until the owner answers.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING"
        ACCEPTED = "ACCEPTED"
        DECLINED = "DECLINED"
        CANCELLED = "CANCELLED"
        EXPIRED = "EXPIRED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requester = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="+")
    owner_phone_digest = models.CharField(max_length=64)
    owner_phone_hint = models.CharField(max_length=24)
    owner = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    profile = models.ForeignKey(
        "profiles.MatrimonialProfile",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="manager_requests",
    )
    authorization = models.OneToOneField(
        ProfileManagerAuthorization,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="request",
    )
    status = models.CharField(max_length=9, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "family_manager_request"
        indexes = [
            models.Index(fields=["profile", "status"], name="family_request_profile"),
            models.Index(fields=["requester", "status"], name="family_request_requester"),
            models.Index(fields=["status", "expires_at"], name="family_request_expiry"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["requester", "owner_phone_digest"],
                condition=Q(status="PENDING"),
                name="family_request_one_pending_per_number",
            ),
            models.CheckConstraint(
                condition=~Q(owner=F("requester")), name="family_request_not_self"
            ),
            models.CheckConstraint(
                condition=~Q(status="ACCEPTED")
                | Q(authorization__isnull=False, responded_at__isnull=False),
                name="family_request_accepted_consistent",
            ),
            models.CheckConstraint(
                condition=~Q(status="DECLINED") | Q(responded_at__isnull=False),
                name="family_request_declined_has_time",
            ),
            models.CheckConstraint(
                condition=~Q(status="CANCELLED") | Q(cancelled_at__isnull=False),
                name="family_request_cancelled_has_time",
            ),
            models.CheckConstraint(
                condition=~Q(status="EXPIRED") | Q(expired_at__isnull=False),
                name="family_request_expired_has_time",
            ),
            models.CheckConstraint(
                condition=Q(expires_at__gt=F("requested_at")),
                name="family_request_expiry_after_sending",
            ),
        ]


class SensitiveActionVerification(models.Model):
    """TR-16 step-up for a manager's Sensitive action (doc 03 §6.8; owner decision
    DR-2026-11-20-O-3). Created only after the manager proves their own authenticator (TOTP);
    bound to that manager, the represented profile, the authorization and one action
    (the Sensitive permission exercised); valid for ``FAMILY_STEP_UP_TTL_SECONDS`` (300);
    consumed once, atomically, inside the business transaction of that action."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manager = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="+")
    profile = models.ForeignKey(
        "profiles.MatrimonialProfile", on_delete=models.PROTECT, related_name="+"
    )
    authorization = models.ForeignKey(
        ProfileManagerAuthorization, on_delete=models.PROTECT, related_name="verifications"
    )
    action = models.CharField(max_length=60)
    method = models.CharField(max_length=8, default="TOTP")
    verified_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "family_sensitive_action_verification"
        indexes = [models.Index(fields=["manager", "profile"], name="family_stepup_lookup")]
        constraints = [
            models.CheckConstraint(
                condition=Q(expires_at__gt=F("verified_at")), name="family_stepup_expiry"
            ),
            models.CheckConstraint(condition=Q(method="TOTP"), name="family_stepup_method"),
            models.CheckConstraint(
                condition=Q(consumed_at__isnull=True) | Q(consumed_at__gte=F("verified_at")),
                name="family_stepup_consumed_after_verify",
            ),
        ]
