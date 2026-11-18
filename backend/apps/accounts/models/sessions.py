"""Authentication sessions and mobile tokens (TR-01, ADR-025; TR-21 schema portion).

Specification: doc 03 §22.2, doc 06 §22.1–§22.2. The flows (login, refresh rotation,
revocation) are G5 Phase 2; G4 provides the schema and its database guarantees.

- No Django session key and no hash of one is stored: the web link runs one way, from the
  server-side session data (``auth_session_id``) to AuthSession.
- Tokens are stored only as SHA-256 hex digests; plaintext tokens are never stored or logged.
- Rows are retained after a session ends (retention per doc 13 OD-005).
"""

import uuid

from django.db import models
from django.db.models import F, Q


class AuthSession(models.Model):
    class ClientType(models.TextChoices):
        WEB = "WEB"
        MOBILE = "MOBILE"

    class Scope(models.TextChoices):
        FULL = "FULL"
        # TR-21 (schema portion): recovery-scoped session during deletion recovery. The flow
        # depends on OD-02d (OPEN) and is not implemented in G4.
        DELETION_RECOVERY = "DELETION_RECOVERY"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE"
        REVOKED = "REVOKED"
        EXPIRED = "EXPIRED"

    class RevokedReason(models.TextChoices):
        LOGOUT = "LOGOUT"
        USER_REVOKED = "USER_REVOKED"
        USER_REVOKED_ALL = "USER_REVOKED_ALL"
        PASSWORD_RESET = "PASSWORD_RESET"
        PASSWORD_CHANGED = "PASSWORD_CHANGED"
        DEACTIVATED = "DEACTIVATED"
        DELETION_REQUESTED = "DELETION_REQUESTED"
        ADMIN = "ADMIN"
        REFRESH_REUSE = "REFRESH_REUSE"
        KEY_COMPROMISE = "KEY_COMPROMISE"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # PROTECT (TR-09 rule F4): accounts are anonymised, not hard-deleted, during business
    # transactions; sessions are removed explicitly by the deletion job.
    user = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="sessions")
    client_type = models.CharField(max_length=6, choices=ClientType.choices)
    scope = models.CharField(max_length=17, choices=Scope.choices, default=Scope.FULL)
    status = models.CharField(max_length=7, choices=Status.choices, default=Status.ACTIVE)

    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField()
    idle_expires_at = models.DateTimeField()
    absolute_expires_at = models.DateTimeField()
    reauthenticated_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(
        max_length=18, choices=RevokedReason.choices, null=True, blank=True
    )
    # Mobile only: the K_rot version used for the latest rotation (key-compromise revocation).
    key_version_current = models.PositiveIntegerField(null=True, blank=True)

    device_name = models.CharField(max_length=100, blank=True)
    platform = models.CharField(max_length=50, blank=True)
    app_version = models.CharField(max_length=50, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_ip = models.GenericIPAddressField(null=True, blank=True)
    approximate_location = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "accounts_auth_session"
        indexes = [
            models.Index(fields=["user", "status"], name="auth_session_user_status"),
            models.Index(fields=["key_version_current"], name="auth_session_key_version"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(idle_expires_at__lte=F("absolute_expires_at")),
                name="auth_session_idle_within_absolute",
            ),
            # A revoked session always records when and why; other states never do.
            models.CheckConstraint(
                condition=(
                    Q(status="REVOKED", revoked_at__isnull=False, revoked_reason__isnull=False)
                    | (
                        ~Q(status="REVOKED")
                        & Q(revoked_at__isnull=True, revoked_reason__isnull=True)
                    )
                ),
                name="auth_session_revocation_consistent",
            ),
            # key_version_current is a mobile concept only.
            models.CheckConstraint(
                condition=Q(client_type="MOBILE") | Q(key_version_current__isnull=True),
                name="auth_session_key_version_mobile_only",
            ),
        ]

    def __str__(self):
        return f"{self.client_type} session {self.id} ({self.status})"


class AuthToken(models.Model):
    class TokenType(models.TextChoices):
        ACCESS = "ACCESS"
        REFRESH = "REFRESH"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(AuthSession, on_delete=models.PROTECT, related_name="tokens")
    token_type = models.CharField(max_length=7, choices=TokenType.choices)
    # SHA-256 of the presented token, lowercase hex. Never the plaintext.
    token_hash = models.CharField(max_length=64, unique=True)
    generation = models.PositiveIntegerField()
    # Soft reference to the parent refresh token (doc 03 §22.2 ``parent_id``): a self-FK
    # would block removing a whole token chain in one statement.
    parent_id = models.UUIDField(null=True, blank=True)
    key_version = models.PositiveIntegerField()
    issued_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "accounts_auth_token"
        indexes = [
            models.Index(fields=["session", "token_type"], name="auth_token_session_type"),
            models.Index(fields=["parent_id"], name="auth_token_parent"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(token_hash__regex=r"^[0-9a-f]{64}$"),
                name="auth_token_hash_is_sha256_hex",
            ),
            models.CheckConstraint(
                condition=Q(expires_at__gt=F("issued_at")), name="auth_token_expires_after_issue"
            ),
            # Only refresh tokens are "used" (rotation); access tokens expire or are revoked.
            models.CheckConstraint(
                condition=Q(token_type="REFRESH") | Q(used_at__isnull=True),
                name="auth_token_only_refresh_is_used",
            ),
            # Generation 0 is the login pair; every later generation has a parent.
            models.CheckConstraint(
                condition=Q(generation=0, parent_id__isnull=True)
                | Q(generation__gt=0, parent_id__isnull=False),
                name="auth_token_generation_parent_consistent",
            ),
        ]

    def __str__(self):
        return f"{self.token_type} token gen {self.generation}"
