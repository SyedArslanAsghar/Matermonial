"""G4 stage 6: AccountSecurityEvent (TR-17, TR-23). T-SEC 002/003/005/006 and T-UUID-010."""

import uuid
from datetime import UTC, datetime

import pytest
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from apps.accounts.models import AccountSecurityEvent, User
from apps.accounts.services import pseudonyms
from apps.accounts.services.security_events import (
    record_rate_limit_once,
    record_security_event,
    subject_hash,
)
from common.db.uuid7 import uuid7

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(phone_number="+923001234567", password="Strong-pass-123!")


def row_text(event_id) -> str:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT row_to_json(e)::text FROM account_security_event e WHERE id=%s", [event_id]
        )
        return cursor.fetchone()[0]


def test_event_stores_pseudonyms_and_encrypts_personal_context(user):
    event = record_security_event(
        "LOGIN_SUCCEEDED",
        "SUCCESS",
        actor_type="SELF",
        subject_user_id=user.id,
        actor_context={"ip": "203.0.113.9", "user_agent": "Pixel"},
        subject_linkable={"session_id": "6f1d6a1e-0000-4000-8000-000000000001"},
    )
    pseudonym = pseudonyms.pseudonym_for("ACCOUNT", user.id)
    assert event.subject_pseudonym == event.actor_pseudonym == pseudonym
    text = row_text(event.id)
    for secret in (str(user.id), "203.0.113.9", "Pixel", "+923001234567", "6f1d6a1e-0000"):
        assert secret not in text
    [envelope] = event.enc_parts  # actor == subject: one envelope per pseudonym
    opened = pseudonyms.open_envelope(event.id, envelope)
    assert opened["ip"] == "203.0.113.9" and opened["session_id"].startswith("6f1d6a1e")


def test_unknown_phone_stores_only_a_keyed_hash():
    event = record_security_event(
        "LOGIN_FAILED", "FAILURE", actor_type="ANONYMOUS", unknown_subject_phone="+923000000000"
    )
    assert event.subject_pseudonym is None
    assert event.subject_hash == subject_hash("+923000000000")
    assert "923000000000" not in row_text(event.id)


def test_sec_002_events_are_append_only(user):
    event = record_security_event(
        "DEACTIVATED", "INFO", actor_type="SYSTEM", subject_user_id=user.id
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        AccountSecurityEvent.objects.filter(pk=event.pk).update(result="FAILURE")
    with pytest.raises(DatabaseError), transaction.atomic():
        AccountSecurityEvent.objects.filter(pk=event.pk).delete()


def test_sec_003_schema_has_no_plaintext_identity_columns():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'account_security_event'"
        )
        columns = {row[0] for row in cursor.fetchall()}
    assert not columns & {"user_id", "ip_address", "user_agent", "phone_number", "session_id"}


def test_unknown_event_type_is_rejected_by_service_and_database():
    with pytest.raises(ValueError):
        record_security_event("MADE_UP", "INFO", actor_type="SYSTEM")
    with pytest.raises(DatabaseError), transaction.atomic():
        AccountSecurityEvent.objects.create(
            event_type="MADE_UP", result="INFO", actor_type="SYSTEM", occurred_at=timezone.now()
        )


def test_hash_and_pseudonym_are_mutually_exclusive(user):
    with pytest.raises(DatabaseError), transaction.atomic():
        AccountSecurityEvent.objects.create(
            event_type="LOGIN_FAILED",
            result="FAILURE",
            actor_type="ANONYMOUS",
            occurred_at=timezone.now(),
            subject_pseudonym=pseudonyms.pseudonym_for("ACCOUNT", user.id),
            subject_hash="a" * 64,
        )


@pytest.mark.parametrize(
    "enc_parts",
    [
        {"not": "an array"},
        [{"pseudonym": "x"}],
        [
            {"pseudonym": "p", "key_id": "k", "kek_version": 1, "nonce": "n", "ciphertext": "c"},
            {"pseudonym": "p", "key_id": "k", "kek_version": 1, "nonce": "n", "ciphertext": "c"},
        ],
    ],
)
def test_envelope_column_is_validated(enc_parts):
    with pytest.raises(DatabaseError), transaction.atomic():
        AccountSecurityEvent.objects.create(
            event_type="LOGIN_FAILED",
            result="FAILURE",
            actor_type="ANONYMOUS",
            occurred_at=timezone.now(),
            enc_parts=enc_parts,
        )


def test_uuid_010_rows_route_to_the_monthly_partition_and_non_v7_ids_are_rejected():
    event = record_security_event("SUSPICIOUS_ACTIVITY", "INFO", actor_type="SYSTEM")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT tableoid::regclass::text FROM account_security_event WHERE id = %s", [event.id]
        )
        partition = cursor.fetchone()[0]
    assert partition == "account_security_event_" + datetime.now(UTC).strftime("%Y_%m")
    for bad_id in (uuid.uuid4(), uuid7(int(datetime(2001, 1, 1, tzinfo=UTC).timestamp() * 1000))):
        # uuid4: rejected by the v7 CHECK; 2001: no partition (there's no DEFAULT partition).
        with pytest.raises(DatabaseError), transaction.atomic():
            AccountSecurityEvent.objects.create(
                id=bad_id,
                event_type="LOGIN_FAILED",
                result="FAILURE",
                actor_type="ANONYMOUS",
                occurred_at=timezone.now(),
            )


def test_partitions_exist_for_current_and_next_three_months():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_inherits WHERE inhparent = 'account_security_event'::regclass"
        )
        assert cursor.fetchone()[0] >= 4


def test_sec_005_flood_control_writes_one_row_per_window(user):
    before = AccountSecurityEvent.objects.filter(event_type="RATE_LIMIT_TRIGGERED").count()
    key = f"login:{uuid.uuid4()}"
    first = record_rate_limit_once(key, actor_type="ANONYMOUS")
    second = record_rate_limit_once(key, actor_type="ANONYMOUS")
    assert first is not None and second is None
    after = AccountSecurityEvent.objects.filter(event_type="RATE_LIMIT_TRIGGERED").count()
    assert after - before == 1


def test_sec_006_events_survive_shredding_but_no_longer_identify_anyone(user):
    event = record_security_event(
        "LOGIN_SUCCEEDED",
        "SUCCESS",
        actor_type="SELF",
        subject_user_id=user.id,
        actor_context={"ip": "198.51.100.4"},
    )
    pseudonym = event.subject_pseudonym
    before = row_text(event.id)
    pseudonyms.unlink_subject(pseudonym)
    pseudonyms.destroy_subject_key(pseudonym)
    assert row_text(event.id) == before  # the log row is byte-for-byte unchanged
    assert pseudonyms.open_envelope(event.id, event.enc_parts[0]) is None
    assert pseudonyms.pseudonym_for("ACCOUNT", user.id) is None
