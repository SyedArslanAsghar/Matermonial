"""G4 stage 4: AuthSession / AuthToken schema guarantees (TR-01; TR-21 schema portion).

Flow tests (T-AUTH 001-042) arrive with the authentication flows in G5 Phase 2.
"""

import hashlib
from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.accounts.models import AuthSession, AuthToken, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(phone_number="+923001234567", password="Strong-pass-123!")


def make_session(user, **extra):
    now = timezone.now()
    values = {
        "user": user,
        "client_type": AuthSession.ClientType.MOBILE,
        "last_seen_at": now,
        "idle_expires_at": now + timedelta(days=30),
        "absolute_expires_at": now + timedelta(days=90),
    }
    values.update(extra)
    return AuthSession.objects.create(**values)


def token_hash(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def make_token(session, label="t0", **extra):
    now = timezone.now()
    values = {
        "session": session,
        "token_type": AuthToken.TokenType.REFRESH,
        "token_hash": token_hash(label),
        "generation": 0,
        "key_version": 1,
        "issued_at": now,
        "expires_at": now + timedelta(days=30),
    }
    values.update(extra)
    return AuthToken.objects.create(**values)


def test_new_session_defaults_to_active_full_scope(user):
    session = make_session(user)
    assert session.status == "ACTIVE" and session.scope == "FULL"


def test_recovery_scope_is_a_valid_value(user):
    assert make_session(user, scope=AuthSession.Scope.DELETION_RECOVERY).scope == (
        "DELETION_RECOVERY"
    )


def test_idle_expiry_cannot_exceed_absolute_expiry(user):
    now = timezone.now()
    with pytest.raises(IntegrityError), transaction.atomic():
        make_session(user, idle_expires_at=now + timedelta(days=2), absolute_expires_at=now)


@pytest.mark.parametrize(
    "values",
    [
        {"status": "REVOKED"},  # no time or reason
        {"status": "REVOKED", "revoked_at": "now"},  # no reason
        {"status": "ACTIVE", "revoked_reason": "LOGOUT"},  # reason without revocation
    ],
)
def test_revocation_fields_must_match_status(user, values):
    if values.get("revoked_at") == "now":
        values["revoked_at"] = timezone.now()
    with pytest.raises(IntegrityError), transaction.atomic():
        make_session(user, **values)


def test_revoked_session_with_time_and_reason_is_valid(user):
    session = make_session(
        user, status="REVOKED", revoked_at=timezone.now(), revoked_reason="LOGOUT"
    )
    assert session.revoked_reason == "LOGOUT"


def test_key_version_is_mobile_only(user):
    with pytest.raises(IntegrityError), transaction.atomic():
        make_session(user, client_type=AuthSession.ClientType.WEB, key_version_current=1)


def test_token_hash_must_be_unique_sha256_hex(user):
    session = make_session(user)
    make_token(session)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_token(session)  # same hash
    with pytest.raises(IntegrityError), transaction.atomic():
        make_token(session, token_hash="mat_rt_plaintext-token-value")


def test_only_refresh_tokens_are_marked_used(user):
    session = make_session(user)
    with pytest.raises(IntegrityError), transaction.atomic():
        make_token(session, token_type=AuthToken.TokenType.ACCESS, used_at=timezone.now())


def test_generation_and_parent_are_consistent(user):
    session = make_session(user)
    parent = make_token(session)
    child = make_token(session, label="t1", generation=1, parent_id=parent.id)
    assert child.parent_id == parent.id
    with pytest.raises(IntegrityError), transaction.atomic():
        make_token(session, label="t2", generation=2)  # missing parent
    with pytest.raises(IntegrityError), transaction.atomic():
        make_token(session, label="t3", generation=0, parent_id=parent.id)


def test_sessions_and_tokens_are_never_deleted_by_cascade(user):
    session = make_session(user)
    make_token(session)
    with pytest.raises(ProtectedError):
        user.delete()
    with pytest.raises(ProtectedError):
        session.delete()


def test_no_session_key_column_exists():
    """TR-01: no Django session key and no hash of one is stored in AuthSession."""
    names = {f.name for f in AuthSession._meta.get_fields()}
    assert not {n for n in names if "session_key" in n or "key_hash" in n}
