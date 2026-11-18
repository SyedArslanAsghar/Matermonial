"""Mobile refresh-token rotation (TR-01; doc 06 §22.1 §8.3, §22.2 §10.4).

One transaction with the lock order of doc 06 §22.1 (amendment): ``User FOR SHARE`` ->
``AuthSession FOR UPDATE`` -> parent ``AuthToken FOR UPDATE``. Concurrent refreshes therefore
serialise and receive the same pair; no extra generation is created.

Parent state -> result:
- valid and unused -> mark used, insert the derived child pair, extend the rolling window
  (never past the absolute limit), return the pair;
- used <= grace (15 s) ago and its child refresh unused -> recompute the identical pair;
- used > grace ago, or its child already used -> reuse: revoke the session (REFRESH_REUSE),
  REFRESH_REUSE_DETECTED event, security notice, ``401 session_revoked``; >= 2 reuses in 24 h
  also records SUSPICIOUS_ACTIVITY (no automatic lockout);
- expired or session not ACTIVE -> ``401 session_expired`` / ``session_revoked``; unknown ->
  ``401 invalid_token``.
"""

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from common.api.auth_errors import InvalidToken, SessionExpired, SessionRevoked
from common.crypto.keys import ring
from common.db.locking import LockLevel, lock_plan, lock_rows_for_share, lock_rows_for_update
from common.events.services import emit

from ..models import AccountSecurityEvent, AuthSession, AuthToken, User
from .pseudonyms import pseudonym_for
from .security_events import record_security_event
from .tokens import REFRESH_PREFIX, derived_pair, looks_like, token_hash


@dataclass(frozen=True)
class RefreshResult:
    access_token: str
    refresh_token: str
    access_expires_at: object
    replayed: bool


class _Reuse(Exception):
    pass


def refresh(refresh_token: str, request_id=None) -> RefreshResult:
    if not looks_like(refresh_token, REFRESH_PREFIX):
        raise InvalidToken()
    found = (
        AuthToken.objects.filter(token_hash=token_hash(refresh_token), token_type="REFRESH")
        .select_related("session")
        .first()
    )
    if found is None:
        raise InvalidToken()
    user_id = found.session.user_id
    try:
        with transaction.atomic(), lock_plan("auth.refresh", [LockLevel.ACCOUNT, LockLevel.DOMAIN]):
            lock_rows_for_share(User.objects.filter(pk=user_id), LockLevel.ACCOUNT)
            [session] = lock_rows_for_update(
                AuthSession.objects.filter(pk=found.session_id), LockLevel.DOMAIN
            )
            [parent] = lock_rows_for_update(AuthToken.objects.filter(pk=found.pk), LockLevel.DOMAIN)
            return _rotate(session, parent, refresh_token, request_id)
    except _Reuse:
        _handle_reuse(found.session_id, request_id)
        raise SessionRevoked() from None


def _rotate(session: AuthSession, parent: AuthToken, presented: str, request_id) -> RefreshResult:
    now = timezone.now()
    if session.status == "REVOKED" or parent.revoked_at is not None:
        raise SessionRevoked()
    if (
        session.status != "ACTIVE"
        or now >= session.absolute_expires_at
        or now >= session.idle_expires_at
        or now >= parent.expires_at
    ):
        AuthSession.objects.filter(pk=session.pk, status="ACTIVE").update(status="EXPIRED")
        raise SessionExpired()
    if not session.user.is_active:
        raise SessionRevoked()

    children = AuthToken.objects.filter(parent_id=parent.id)
    if parent.used_at is not None:
        child_refresh = children.filter(token_type="REFRESH").first()
        grace = timedelta(seconds=settings.AUTH_REFRESH_GRACE_SECONDS)
        if (
            child_refresh is None
            or child_refresh.used_at is not None
            or now - parent.used_at > grace
        ):
            raise _Reuse()
        # Idempotent replay: recompute the identical pair from the presented parent.
        access, refresh_value = derived_pair(
            presented, parent.generation + 1, child_refresh.key_version
        )
        child_access = children.get(token_type="ACCESS")
        if token_hash(refresh_value) != child_refresh.token_hash:
            raise _Reuse()
        return RefreshResult(access, refresh_value, child_access.expires_at, True)

    version = ring("ROT").active_version
    generation = parent.generation + 1
    access, refresh_value = derived_pair(presented, generation, version)
    access_expires = now + timedelta(seconds=settings.AUTH_MOBILE_ACCESS_SECONDS)
    idle_until = min(
        now + timedelta(seconds=settings.AUTH_MOBILE_REFRESH_IDLE_SECONDS),
        session.absolute_expires_at,
    )
    parent.used_at = now
    parent.save(update_fields=["used_at"])
    common = {
        "session": session,
        "generation": generation,
        "parent_id": parent.id,
        "key_version": version,
        "issued_at": now,
    }
    AuthToken.objects.create(
        token_type="ACCESS", token_hash=token_hash(access), expires_at=access_expires, **common
    )
    AuthToken.objects.create(
        token_type="REFRESH", token_hash=token_hash(refresh_value), expires_at=idle_until, **common
    )
    session.idle_expires_at, session.key_version_current, session.last_seen_at = (
        idle_until,
        version,
        now,
    )
    session.save(update_fields=["idle_expires_at", "key_version_current", "last_seen_at"])
    return RefreshResult(access, refresh_value, access_expires, False)


def _handle_reuse(session_id, request_id) -> None:
    """Revoke the session and record the event, in its own transaction (the refresh one rolled
    back)."""
    from .auth import revoke_sessions

    session = AuthSession.objects.select_related("user").get(pk=session_id)
    user = session.user
    with transaction.atomic():
        revoke_sessions(
            user,
            [session],
            AuthSession.RevokedReason.REFRESH_REUSE,
            actor_type="SYSTEM",
            request_id=request_id,
        )
        record_security_event(
            "REFRESH_REUSE_DETECTED",
            "FAILURE",
            actor_type="ANONYMOUS",
            subject_user_id=user.id,
            request_id=request_id,
            subject_linkable={"session_id": str(session.id)},
        )
        recent = AccountSecurityEvent.objects.filter(
            event_type="REFRESH_REUSE_DETECTED",
            subject_pseudonym=pseudonym_for("ACCOUNT", user.id),
            occurred_at__gte=timezone.now() - timedelta(hours=24),
        ).count()
        if recent >= 2:
            record_security_event(
                "SUSPICIOUS_ACTIVITY",
                "INFO",
                actor_type="SYSTEM",
                subject_user_id=user.id,
                reason_code="REPEATED_REFRESH_REUSE",
                request_id=request_id,
            )
        emit(
            "security.session_ended_for_protection",
            event_class="NOTIFICATION",
            category="SECURITY",
            aggregate_type="AuthSession",
            recipient_pseudonym=pseudonym_for("ACCOUNT", user.id),
            payload={"session_id": str(session.id), "reason": "REFRESH_REUSE"},
            dedupe_identity=f"refresh-reuse:{session.id}",
        )
