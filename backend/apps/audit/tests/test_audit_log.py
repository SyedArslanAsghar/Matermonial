"""G4 stage 6: AuditLog, holds and partition maintenance (ADR-022, TR-23). T-LOG subset."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from apps.accounts.models import SubjectPseudonym, User
from apps.accounts.services.pseudonyms import open_envelope, pseudonym_for
from apps.audit.models import AuditLog, AuditLogHold, AuditLogHoldLink
from apps.audit.services import UnsafeAuditData, place_hold, record_audit
from common.db.uuid7 import uuid7

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user():
    return User.objects.create_user(phone_number="+923001110000", password="Strong-pass-123!")


@pytest.fixture
def member():
    return User.objects.create_user(phone_number="+923002220000", password="Strong-pass-123!")


def audit(admin_user, member, **extra):
    values = dict(
        action="session.revoke",
        resource_type="accounts.auth_session",
        actor_type="ADMIN",
        result="SUCCESS",
        category="ADMINISTRATIVE",
        actor_user_id=admin_user.id,
        subject_user_id=member.id,
        metadata={"reason_code": "ADMIN", "count": 1},
        actor_context={"ip": "203.0.113.50"},
        subject_linkable={"session_id": str(uuid.uuid4())},
    )
    values.update(extra)
    return record_audit(**values)


def sql(statement, params=None):
    with connection.cursor() as cursor:
        cursor.execute(statement, params or [])
        return cursor.fetchall() if cursor.description else None


def test_audit_entry_uses_pseudonyms_and_one_envelope_per_subject(admin_user, member):
    entry = audit(admin_user, member)
    assert entry.actor_pseudonym == pseudonym_for("ACCOUNT", admin_user.id)
    assert entry.subject_pseudonym == pseudonym_for("ACCOUNT", member.id)
    assert {e["pseudonym"] for e in entry.enc_parts} == {
        str(entry.actor_pseudonym),
        str(entry.subject_pseudonym),
    }
    actor_env = next(e for e in entry.enc_parts if e["pseudonym"] == str(entry.actor_pseudonym))
    assert open_envelope(entry.id, actor_env) == {"ip": "203.0.113.50"}
    [(row,)] = sql("SELECT row_to_json(a)::text FROM audit_log a WHERE id=%s", [entry.id])
    assert str(member.id) not in row and "203.0.113.50" not in row


@pytest.mark.parametrize(
    "metadata",
    [{"note": "customer said hello"}, {"BadKey": 1}, {"nested": {"a": 1}}],
)
def test_metadata_allowlist_rejects_free_text(admin_user, member, metadata):
    with pytest.raises(UnsafeAuditData):
        audit(admin_user, member, metadata=metadata)


def test_action_must_be_a_code_in_service_and_database(admin_user, member):
    with pytest.raises(UnsafeAuditData):
        audit(admin_user, member, action="Revoke Session!")
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditLog.objects.create(
            occurred_at=timezone.now(),
            actor_type="SYSTEM",
            action="Bad Action",
            resource_type="x.y",
            result="SUCCESS",
            category="SYSTEM",
        )


def test_audit_log_is_append_only(admin_user, member):
    entry = audit(admin_user, member)
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditLog.objects.filter(pk=entry.pk).update(result="FAILURE")
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditLog.objects.filter(pk=entry.pk).delete()


def test_log_001_partitions_exist_for_current_and_next_three_months():
    names = {
        r[0]
        for r in sql(
            "SELECT c.relname FROM pg_inherits i JOIN pg_class c ON c.oid=i.inhrelid "
            "WHERE i.inhparent='audit_log'::regclass"
        )
    }
    month = datetime.now(UTC).replace(day=1)
    for _ in range(4):
        assert f"audit_log_{month:%Y_%m}" in names
        month = (month + timedelta(days=32)).replace(day=1)


def test_log_002_partition_creation_is_idempotent():
    assert sql("SELECT ensure_uuid7_partitions('audit_log', 'month', 3)")[0][0] == 0


def _past_partition_with_events():
    sql(
        "CREATE TABLE audit_log_2020_01 PARTITION OF audit_log FOR VALUES FROM "
        "(uuid_v7_lower('2020-01-01 00:00:00+00')) TO (uuid_v7_lower('2020-02-01 00:00:00+00'))"
    )
    ms = int(datetime(2020, 1, 15, tzinfo=UTC).timestamp() * 1000)
    held, plain = uuid7(ms), uuid7(ms + 1)
    for event_id in (held, plain):
        AuditLog.objects.create(
            id=event_id,
            occurred_at=datetime(2020, 1, 15, tzinfo=UTC),
            actor_type="SYSTEM",
            action="system.check",
            resource_type="system",
            result="SUCCESS",
            category="SYSTEM",
        )
    return held, plain


def test_log_003_dropping_a_past_partition_keeps_only_held_events():
    held, plain = _past_partition_with_events()
    case = uuid.uuid4()
    place_hold([held], case)
    moved = sql(
        "SELECT archive_and_drop_audit_partition('audit_log_2020_01', now() - interval '1 day')"
    )[0][0]
    assert moved == 1
    assert sql("SELECT to_regclass('audit_log_2020_01')")[0][0] is None
    rows = dict(sql("SELECT id, held FROM audit_log_all WHERE id IN (%s, %s)", [held, plain]))
    assert rows == {held: True}


def test_log_004_release_deletes_only_unlinked_unprotected_expired_rows(member):
    held, _ = _past_partition_with_events()
    case = uuid.uuid4()
    place_hold([held], case)
    sql("SELECT archive_and_drop_audit_partition('audit_log_2020_01', now() - interval '1 day')")
    assert sql("SELECT release_held_events(%s)", [case])[0][0] == 1
    assert not AuditLogHold.objects.filter(id=held).exists()
    assert not AuditLogHoldLink.objects.filter(hold_case_id=case).exists()


def test_log_005_rows_under_another_pseudonym_hold_survive_release(member):
    pseudonym = pseudonym_for("ACCOUNT", member.id)
    held, _ = _past_partition_with_events()
    sql(
        "INSERT INTO audit_log_hold (id, occurred_at, actor_type, subject_pseudonym, action, "
        "resource_type, result, category, retain_until) VALUES (%s, now(), 'SYSTEM', %s, "
        "'system.check', 'system', 'SUCCESS', 'SYSTEM', now() - interval '1 day')",
        [uuid7(), pseudonym],
    )
    SubjectPseudonym.objects.filter(pk=pseudonym).update(hold_ref="LEGAL-HOLD-1")
    assert sql("SELECT release_held_events(%s)", [uuid.uuid4()])[0][0] == 0


def test_log_006_archive_refuses_current_partitions_and_other_tables():
    current = f"audit_log_{datetime.now(UTC):%Y_%m}"
    with pytest.raises(DatabaseError), transaction.atomic():
        sql(f"SELECT archive_and_drop_audit_partition('{current}', now())")
    with pytest.raises(DatabaseError), transaction.atomic():
        sql("SELECT archive_and_drop_audit_partition('accounts_user', now())")


def test_log_007_held_rows_cannot_be_updated():
    held, _ = _past_partition_with_events()
    place_hold([held], uuid.uuid4())
    sql("SELECT archive_and_drop_audit_partition('audit_log_2020_01', NULL)")
    with pytest.raises(DatabaseError), transaction.atomic():
        AuditLogHold.objects.filter(id=held).update(result="FAILURE")


def test_log_008_maintenance_functions_are_not_executable_by_public():
    rows = sql(
        "SELECT proname, proacl::text FROM pg_proc WHERE proname IN "
        "('release_held_events', 'archive_and_drop_audit_partition')"
    )
    assert len(rows) == 2
    for _, acl in rows:
        assert acl is not None and not any(
            item.startswith("=") for item in acl.strip("{}").split(",")
        )
