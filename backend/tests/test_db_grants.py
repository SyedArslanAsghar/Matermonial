"""D-11: the application role can't bypass append-only rules or the maintenance domain.

A throwaway role is created inside the test transaction and rolled back (CREATE ROLE is
transactional in PostgreSQL), so nothing persists in the disposable database.
"""

import uuid

import pytest
from django.db import DatabaseError, connection, transaction

from common.db.grants import application_grants

ROLE = "g4_grant_test_app"


@pytest.fixture
def as_app_role():
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE ROLE {ROLE} NOLOGIN")
        for statement in application_grants(ROLE):
            cursor.execute(statement)

    def run(sql, params=None):
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(f"SET LOCAL ROLE {ROLE}")
            cursor.execute(sql, params or [])
            return cursor.fetchall() if cursor.description else None

    return run


INSERT_AUDIT = (
    "INSERT INTO audit_log (occurred_at, actor_type, action, resource_type, result, category) "
    "VALUES (now(), 'SYSTEM', 'system.check', 'system', 'SUCCESS', 'SYSTEM') RETURNING id"
)


@pytest.mark.django_db
class TestApplicationRole:
    def test_can_read_and_append_logs(self, as_app_role):
        [(event_id,)] = as_app_role(INSERT_AUDIT)
        assert as_app_role("SELECT count(*) FROM audit_log WHERE id = %s", [event_id]) == [(1,)]

    @pytest.mark.parametrize(
        "statement",
        [
            "UPDATE audit_log SET result = 'FAILURE'",
            "DELETE FROM account_security_event",
            "TRUNCATE audit_log",  # triggers can't stop TRUNCATE; privileges do
            "DELETE FROM audit_log_hold",
            "SELECT count(*) FROM maintenance_operation",
            "UPDATE registry_stream_head SET last_seq = 0",
            "SELECT release_held_events('00000000-0000-4000-8000-000000000000')",
            "SELECT ensure_uuid7_partitions('audit_log', 'month', 12)",
        ],
    )
    def test_is_denied(self, as_app_role, statement):
        with pytest.raises(DatabaseError):
            as_app_role(statement)

    def test_can_place_a_hold_but_not_remove_one(self, as_app_role):
        event_id, case = uuid.uuid4(), uuid.uuid4()
        as_app_role(
            "INSERT INTO audit_log_hold_link (event_id, hold_case_id) VALUES (%s, %s)",
            [event_id, case],
        )
        with pytest.raises(DatabaseError):
            as_app_role("DELETE FROM audit_log_hold_link")
