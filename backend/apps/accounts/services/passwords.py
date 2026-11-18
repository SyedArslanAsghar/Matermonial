"""Password reset and change (doc 06 §22.1 §8.4; FR-ACC-005).

- Forgot: the caller always answers the same; an OTP (purpose PASSWORD_RESET) is sent only to
  an existing, active account (cooldown and hourly limits of the OTP service apply).
- Reset: the new password is validated first (a weak password doesn't consume the code), then
  the code is verified and, in the same transaction, the password is set and **every** session is
  revoked (PASSWORD_RESET). No automatic login. A security notice is queued.
- Change: current password + recent step-up; **other** sessions are revoked (PASSWORD_CHANGED);
  the current web session stays valid (``update_session_auth_hash``).
"""

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from common.events.services import emit

from ..managers import normalize_phone_number
from ..models import AuthSession, User
from .auth import require_recent_step_up, revoke_sessions
from .pseudonyms import pseudonym_for
from .security_events import record_security_event


def _user_for(phone_number: str) -> tuple[str | None, User | None]:
    try:
        phone = normalize_phone_number(phone_number)
    except ValidationError:
        return None, None
    return phone, User.objects.filter(phone_number=phone).first()


def _notify(user: User, event_type: str) -> None:
    emit(
        event_type,
        event_class="NOTIFICATION",
        category="SECURITY",
        aggregate_type="User",
        recipient_pseudonym=pseudonym_for("ACCOUNT", user.id),
        payload={"account": "self"},
    )


def forgot(phone_number: str, request_id=None) -> None:
    from apps.verification.services.otp import send_code

    phone, user = _user_for(phone_number)
    if phone is None:
        return
    record_security_event(
        "PASSWORD_RESET_REQUESTED",
        "INFO",
        actor_type="ANONYMOUS",
        subject_user_id=user.id if user else None,
        unknown_subject_phone=None if user else phone,
        request_id=request_id,
    )
    if user is not None and user.is_active:
        send_code(phone_number=phone, purpose="PASSWORD_RESET", user=user)


def reset(phone_number: str, code: str, new_password: str, request_id=None) -> bool:
    """True when the password was reset. Raises ValidationError for a weak password."""
    from apps.verification.services.otp import verify_code

    phone, user = _user_for(phone_number)
    validate_password(new_password, user or User(phone_number=phone or ""))
    if user is None or not user.is_active:
        return False
    with transaction.atomic():
        outcome = verify_code(phone_number=phone, purpose="PASSWORD_RESET", code=code, user=user)
        if not outcome.ok:
            record_security_event(
                "PASSWORD_RESET_FAILED",
                "FAILURE",
                actor_type="ANONYMOUS",
                subject_user_id=user.id,
                reason_code=outcome.reason,
                request_id=request_id,
            )
            return False
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        revoke_sessions(
            user,
            list(AuthSession.objects.filter(user=user, status="ACTIVE")),
            AuthSession.RevokedReason.PASSWORD_RESET,
            request_id=request_id,
        )
        record_security_event(
            "PASSWORD_RESET_COMPLETED",
            "SUCCESS",
            actor_type="SELF",
            subject_user_id=user.id,
            request_id=request_id,
        )
        _notify(user, "security.password_reset")
    return True


def change(
    request, user: User, session: AuthSession, current: str, new: str, request_id=None
) -> bool:
    """True when changed; False for a wrong current password. Raises StepUpRequired /
    ValidationError."""
    require_recent_step_up(session)
    if not user.check_password(current):
        record_security_event(
            "PASSWORD_CHANGE_FAILED",
            "FAILURE",
            actor_type="SELF",
            subject_user_id=user.id,
            reason_code="BAD_PASSWORD",
            request_id=request_id,
        )
        return False
    validate_password(new, user)
    with transaction.atomic():
        user.set_password(new)
        user.save(update_fields=["password", "updated_at"])
        others = AuthSession.objects.filter(user=user, status="ACTIVE").exclude(pk=session.pk)
        revoke_sessions(
            user, list(others), AuthSession.RevokedReason.PASSWORD_CHANGED, request_id=request_id
        )
        record_security_event(
            "PASSWORD_CHANGED",
            "SUCCESS",
            actor_type="SELF",
            subject_user_id=user.id,
            request_id=request_id,
        )
        _notify(user, "security.password_changed")
    if session.client_type == "WEB":
        update_session_auth_hash(request, user)  # keep the current session; others end
    return True
