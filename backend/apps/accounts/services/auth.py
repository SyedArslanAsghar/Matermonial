"""Registration, login, sessions and logout (FR-ACC-001, FR-ACC-005; TR-01, doc 06 §22.1–§22.2).

Rules implemented here:
- Registration never reveals whether a phone is registered: the caller always answers the same.
  A new account starts with ``is_phone_verified = False`` and is sent a VERIFY_PHONE code.
- Login failures are a generic ``invalid_credentials``; an unknown phone still costs a password
  hash (timing parity). Correct credentials then pass the account-state gate.
- Web: Django ``login()`` rotates the session key (fixation); the server-side session data holds
  ``auth_session_id`` -> AuthSession. No session key or hash of one is stored.
- Mobile: an opaque access/refresh pair, stored as SHA-256 hashes only.
- Lock order (doc 06 §22.1 amendment): ``User FOR SHARE`` first, then session and token rows.
- Every login and revocation writes security events; a new sign-in queues a security notice in
  the same transaction (delivery: Phase 12).
- Deletion recovery (no FULL session while PENDING_RECOVERY) and restrictions join the gate
  with their phases (15 and 6).
"""

import uuid
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.functional import SimpleLazyObject

from common.api.auth_errors import AccountUnavailable, InvalidCredentials
from common.crypto.keys import ring
from common.db.locking import LockLevel, lock_plan, lock_rows_for_share, lock_rows_for_update
from common.events.services import emit

from ..managers import normalize_email, normalize_phone_number
from ..models import AuthSession, AuthToken, User
from .pseudonyms import pseudonym_for
from .security_events import record_security_event
from .tokens import random_pair, token_hash

_DUMMY_HASH = SimpleLazyObject(lambda: make_password("matermonial-timing-parity-dummy"))


@dataclass(frozen=True)
class MobileCredentials:
    session: AuthSession
    access_token: str
    refresh_token: str
    access_expires_at: object


def _seconds(name: str) -> timedelta:
    return timedelta(seconds=getattr(settings, name))


# --- Registration -------------------------------------------------------------------------


def register(*, phone_number: str, password: str, email: str | None = None) -> User | None:
    """Create an unverified account and send its VERIFY_PHONE code. Returns None when the phone
    (or email) is already used; the caller must respond identically either way."""
    phone = normalize_phone_number(phone_number)
    email = normalize_email(email)
    validate_password(password, User(phone_number=phone, email=email))
    if User.objects.filter(phone_number=phone).exists():
        return None
    if email and User.objects.filter(email=email).exists():
        email = None  # don't reveal the other account; the email can be added later
    try:
        with transaction.atomic():
            user = User.objects.create_user(phone_number=phone, password=password, email=email)
    except IntegrityError:  # a concurrent registration of the same phone won
        return None
    from apps.verification.services.otp import send_code

    send_code(phone_number=phone, purpose="VERIFY_PHONE", user=user)
    return user


# --- Login --------------------------------------------------------------------------------


def authenticate_credentials(*, phone_number: str, password: str, request_id=None) -> User:
    try:
        phone = normalize_phone_number(phone_number)
    except ValidationError:
        check_password(password, str(_DUMMY_HASH))
        raise InvalidCredentials() from None
    user = User.objects.filter(phone_number=phone).first()
    if user is None:
        check_password(password, str(_DUMMY_HASH))  # timing parity (T-AUTH-002)
        record_security_event(
            "LOGIN_FAILED",
            "FAILURE",
            actor_type="ANONYMOUS",
            unknown_subject_phone=phone,
            reason_code="UNKNOWN_SUBJECT",
            request_id=request_id,
        )
        raise InvalidCredentials()
    if not user.check_password(password):
        record_security_event(
            "LOGIN_FAILED",
            "FAILURE",
            actor_type="SELF",
            subject_user_id=user.id,
            reason_code="BAD_PASSWORD",
            request_id=request_id,
        )
        raise InvalidCredentials()
    if not user.is_active:
        record_security_event(
            "LOGIN_DENIED_ACCOUNT_STATE",
            "FAILURE",
            actor_type="SELF",
            subject_user_id=user.id,
            reason_code="DEACTIVATED" if user.deactivated else "INACTIVE",
            request_id=request_id,
        )
        raise AccountUnavailable()
    return user


def _device(meta: dict) -> dict:
    allowed = ("device_name", "platform", "app_version", "user_agent", "login_ip")
    values = {k: (meta.get(k) or "") for k in allowed if k != "login_ip"}
    values["user_agent"] = values["user_agent"][:512]
    values["login_ip"] = values["last_ip"] = meta.get("login_ip") or None
    return values


def _create_session(user: User, client_type: str, meta: dict, request_id=None) -> AuthSession:
    now = timezone.now()
    if client_type == AuthSession.ClientType.WEB:
        idle, absolute = _seconds("AUTH_WEB_IDLE_SECONDS"), _seconds("AUTH_WEB_ABSOLUTE_SECONDS")
        key_version = None
    else:
        idle = _seconds("AUTH_MOBILE_REFRESH_IDLE_SECONDS")
        absolute = _seconds("AUTH_MOBILE_ABSOLUTE_SECONDS")
        key_version = ring("ROT").active_version
    session = AuthSession.objects.create(
        user=user,
        client_type=client_type,
        last_seen_at=now,
        idle_expires_at=min(now + idle, now + absolute),
        absolute_expires_at=now + absolute,
        key_version_current=key_version,
        **_device(meta),
    )
    context = {"ip": meta.get("login_ip"), "user_agent": (meta.get("user_agent") or "")[:200]}
    for event_type in ("LOGIN_SUCCEEDED", "SESSION_CREATED"):
        record_security_event(
            event_type,
            "SUCCESS",
            actor_type="SELF",
            subject_user_id=user.id,
            reason_code=client_type,
            request_id=request_id,
            actor_context=context,
            subject_linkable={"session_id": str(session.id)},
        )
    emit(
        "security.new_sign_in",
        event_class="NOTIFICATION",
        category="SECURITY",
        aggregate_type="AuthSession",
        recipient_pseudonym=pseudonym_for("ACCOUNT", user.id),
        payload={"session_id": str(session.id), "client_type": client_type},
        dedupe_identity=f"new-sign-in:{session.id}",
    )
    return session


def login_web(request, user: User, meta: dict, request_id=None) -> AuthSession:
    with transaction.atomic(), lock_plan("auth.login.web", [LockLevel.ACCOUNT]):
        lock_rows_for_share(User.objects.filter(pk=user.pk), LockLevel.ACCOUNT)
        session = _create_session(user, AuthSession.ClientType.WEB, meta, request_id)
    django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session["auth_session_id"] = str(session.id)
    return session


def login_mobile(user: User, meta: dict, request_id=None) -> MobileCredentials:
    access, refresh = random_pair()
    now = timezone.now()
    access_expires = now + _seconds("AUTH_MOBILE_ACCESS_SECONDS")
    with transaction.atomic(), lock_plan("auth.login.mobile", [LockLevel.ACCOUNT]):
        lock_rows_for_share(User.objects.filter(pk=user.pk), LockLevel.ACCOUNT)
        session = _create_session(user, AuthSession.ClientType.MOBILE, meta, request_id)
        common = {
            "session": session,
            "generation": 0,
            "key_version": session.key_version_current,
            "issued_at": now,
        }
        AuthToken.objects.create(
            token_type="ACCESS", token_hash=token_hash(access), expires_at=access_expires, **common
        )
        AuthToken.objects.create(
            token_type="REFRESH",
            token_hash=token_hash(refresh),
            expires_at=session.idle_expires_at,
            **common,
        )
    return MobileCredentials(session, access, refresh, access_expires)


# --- Session validation and revocation ----------------------------------------------------


def session_problem(session: AuthSession | None, user_id) -> str | None:
    """None when usable, else 'revoked' or 'expired' (checked on every request)."""
    now = timezone.now()
    if session is None or session.user_id != user_id or session.status == "REVOKED":
        return "revoked"
    if (
        session.status == "EXPIRED"
        or now >= session.idle_expires_at
        or now >= session.absolute_expires_at
    ):
        return "expired"
    if session.scope != AuthSession.Scope.FULL:
        return "revoked"  # recovery-scoped sessions get their own endpoints (TR-21, Phase 15)
    return None


def mark_expired(session: AuthSession) -> None:
    AuthSession.objects.filter(pk=session.pk, status="ACTIVE").update(status="EXPIRED")


def touch(session: AuthSession, ip: str | None = None) -> None:
    """Extend the idle window on activity, written at most once a minute (doc 06 §22.2)."""
    now = timezone.now()
    if (now - session.last_seen_at).total_seconds() < settings.AUTH_SEEN_WRITE_INTERVAL_SECONDS:
        return
    values = {"last_seen_at": now, "last_ip": ip or session.last_ip}
    if session.client_type == "WEB":
        # Mobile idle is the refresh window, extended only by a successful refresh (doc 06 §22.2).
        idle = _seconds("AUTH_WEB_IDLE_SECONDS")
        values["idle_expires_at"] = min(now + idle, session.absolute_expires_at)
    AuthSession.objects.filter(pk=session.pk, status="ACTIVE").update(**values)


def revoke_sessions(
    user: User,
    sessions,
    reason: str,
    *,
    actor_type: str = "SELF",
    actor_user_id: uuid.UUID | None = None,
    request_id=None,
) -> int:
    """Revoke the given ACTIVE sessions of ``user`` and all their tokens. Idempotent."""
    now = timezone.now()
    with transaction.atomic(), lock_plan("auth.revoke", [LockLevel.ACCOUNT, LockLevel.DOMAIN]):
        lock_rows_for_share(User.objects.filter(pk=user.pk), LockLevel.ACCOUNT)
        locked = lock_rows_for_update(
            AuthSession.objects.filter(user=user, status="ACTIVE", pk__in=[s.pk for s in sessions]),
            LockLevel.DOMAIN,
        )
        for session in locked:
            session.status, session.revoked_at, session.revoked_reason = "REVOKED", now, reason
            session.save(update_fields=["status", "revoked_at", "revoked_reason"])
            AuthToken.objects.filter(session=session, revoked_at__isnull=True).update(
                revoked_at=now
            )
            record_security_event(
                "SESSION_REVOKED",
                "INFO",
                actor_type=actor_type,
                subject_user_id=user.id,
                actor_user_id=actor_user_id,
                reason_code=reason,
                request_id=request_id,
                subject_linkable={"session_id": str(session.id)},
            )
        return len(locked)


def logout(request, session: AuthSession, request_id=None) -> None:
    revoke_sessions(
        session.user, [session], AuthSession.RevokedReason.LOGOUT, request_id=request_id
    )
    if session.client_type == "WEB":
        django_logout(request)


# --- Step-up and session management -------------------------------------------------------
# Step-up is password-only: OD-04c (password + OTP) is OPEN (DR-2026-11-18-G4A; CC-R25). The
# per-action windows are TR-16 (Phase 4); until then AUTH_STEP_UP_WINDOW_SECONDS (default 5 min).


def reauthenticate(user: User, session: AuthSession, password: str, request_id=None) -> bool:
    ok = user.check_password(password)
    record_security_event(
        "STEP_UP_SUCCEEDED" if ok else "STEP_UP_FAILED",
        "SUCCESS" if ok else "FAILURE",
        actor_type="SELF",
        subject_user_id=user.id,
        request_id=request_id,
        subject_linkable={"session_id": str(session.id)},
    )
    if ok:
        AuthSession.objects.filter(pk=session.pk).update(reauthenticated_at=timezone.now())
    return ok


def require_recent_step_up(session: AuthSession, window_seconds: int | None = None) -> None:
    from common.api.auth_errors import StepUpRequired

    window = window_seconds or settings.AUTH_STEP_UP_WINDOW_SECONDS
    current = AuthSession.objects.filter(pk=session.pk).values_list("reauthenticated_at", flat=True)
    stamp = current.first()
    if stamp is None or timezone.now() - stamp > timedelta(seconds=window):
        raise StepUpRequired()


def revoke_one(user: User, session_id, request_id=None) -> bool:
    """Revoke one of the caller's sessions. False (-> identical 404) when it isn't theirs."""
    session = AuthSession.objects.filter(pk=session_id, user=user).first()
    if session is None:
        return False
    revoke_sessions(user, [session], AuthSession.RevokedReason.USER_REVOKED, request_id=request_id)
    return True


def revoke_others(user: User, current: AuthSession, request_id=None) -> int:
    others = AuthSession.objects.filter(user=user, status="ACTIVE").exclude(pk=current.pk)
    return revoke_sessions(
        user, list(others), AuthSession.RevokedReason.USER_REVOKED, request_id=request_id
    )
