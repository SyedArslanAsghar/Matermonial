"""G4 stage 7: transactional outbox (FR-NOT-005; TR-11 / ADR-028). T-OUT subset + concurrency."""

import base64
import threading
import uuid
from datetime import timedelta

import pytest
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from apps.accounts.models import User
from common.crypto.keys import dev_key
from common.db.uuid7 import is_uuid7
from common.events import services
from common.events.models import OutboxEvent

HANDLED: list = []


@services.register_handler("test.noop")
def _noop(event, payload):
    HANDLED.append(payload)


@services.register_handler("test.fails")
def _fails(event, payload):
    raise RuntimeError("handler failure")


def emit(**extra):
    event_type = extra.pop("event_type", "test.noop")
    values = dict(
        event_class="NOTIFICATION",
        category="ACCOUNT",
        aggregate_type="Test",
        payload={"aggregate_id": "a-1", "phone": "+923001234567"},
    )
    values.update(extra)
    with transaction.atomic():
        return services.emit(event_type, **values)


def raw_row(event_id) -> str:
    with connection.cursor() as cursor:
        cursor.execute("SELECT row_to_json(o)::text FROM outbox_event o WHERE id=%s", [event_id])
        return cursor.fetchone()[0]


def force(event_id, **values):
    """Write columns directly (e.g. to age a row). Goes through the guard trigger."""
    OutboxEvent.objects.filter(id=event_id).update(**values)


@pytest.mark.django_db
class TestEmit:
    def test_emit_requires_the_business_transaction(self):
        with pytest.raises(RuntimeError):
            services.emit(
                "test.noop",
                event_class="NOTIFICATION",
                category="ACCOUNT",
                aggregate_type="Test",
                payload={},
            )

    def test_payload_is_encrypted_and_ids_are_v7(self):
        event = emit()
        assert is_uuid7(event.id)
        row = raw_row(event.id)
        assert "923001234567" not in row and "a-1" not in row
        assert services.decrypt_payload(event) == {"aggregate_id": "a-1", "phone": "+923001234567"}

    def test_event_rolls_back_with_the_business_transaction(self):
        with pytest.raises(RuntimeError), transaction.atomic():
            event = services.emit(
                "test.noop",
                event_class="NOTIFICATION",
                category="ACCOUNT",
                aggregate_type="Test",
                payload={},
            )
            raise RuntimeError("business step failed")
        assert not OutboxEvent.objects.filter(id=event.id).exists()

    def test_dedupe_returns_the_live_event_and_stores_only_an_hmac(self):
        first = emit(dedupe_identity="request:42:expired")
        second = emit(dedupe_identity="request:42:expired")
        assert first.id == second.id
        assert first.dedupe_key == services.dedupe_key("request:42:expired")
        assert "request:42" not in raw_row(first.id)

    def test_cancelled_events_free_their_dedupe_key(self):
        first = emit(dedupe_identity="x")
        force(first.id, status="CANCELLED", terminal_at=timezone.now())
        assert emit(dedupe_identity="x").id != first.id

    def test_financial_obligations_start_pending_resolution(self):
        event = emit(event_class="FINANCIAL_OBLIGATION", category="FINANCIAL")
        assert event.obligation_resolution == "PENDING"


@pytest.mark.django_db
class TestProcessing:
    def setup_method(self):
        HANDLED.clear()

    def test_claim_is_its_own_transaction(self):
        with pytest.raises(RuntimeError), transaction.atomic():
            services.claim_batch()

    def test_handler_runs_and_marks_done(self):
        event = emit()
        assert services.process_due() == {"DONE": 1}
        event.refresh_from_db()
        assert event.status == "DONE" and event.terminal_at and event.lease_token is None
        assert HANDLED == [{"aggregate_id": "a-1", "phone": "+923001234567"}]

    def test_failure_is_retried_after_lease_expiry_then_dead(self, settings):
        event = emit(event_type="test.fails")
        assert services.process_due() == {"CLAIMED": 1}
        assert services.process_due() == {}  # lease still held
        for _ in range(services.MAX_ATTEMPTS):
            force(event.id, lease_expires_at=timezone.now() - timedelta(seconds=1))
            services.process_due()
        event.refresh_from_db()
        assert event.status == "DEAD" and event.attempts == services.MAX_ATTEMPTS

    def test_lost_lease_rolls_back_the_handler_work(self):
        event = emit(event_type="test.creates_user")
        [(event_id, token)] = services.claim_batch()

        @services.register_handler("test.creates_user")
        def creates_user(evt, payload):
            User.objects.create_user(phone_number="+923007770000")
            # Meanwhile another worker re-claimed the event after the lease expired.
            OutboxEvent.objects.filter(id=evt.id).update(lease_token=uuid.uuid4())

        assert services.process_claimed(event_id, token) == "CLAIMED"
        assert not User.objects.filter(phone_number="+923007770000").exists()
        assert OutboxEvent.objects.get(id=event.id).status == "CLAIMED"

    def test_unknown_queue_key_makes_the_event_undecryptable(self, settings):
        event = emit()
        other = base64.b64encode(dev_key("QUEUE", 9)).decode()
        settings.QUEUE_KEYS = f"1:{other}"
        assert services.process_due() == {"DEAD_UNDECRYPTABLE": 1}
        event.refresh_from_db()
        assert event.status == "DEAD_UNDECRYPTABLE" and HANDLED == []


@pytest.mark.django_db
class TestGuardTrigger:
    def done(self, **extra):
        event = emit(**extra)
        force(event.id, status="DONE", terminal_at=timezone.now())
        return event

    def test_live_rows_cannot_be_redacted(self):
        event = emit()
        with pytest.raises(DatabaseError), transaction.atomic():
            force(event.id, payload_enc=None)

    def test_redaction_only_sets_null(self):
        event = self.done()
        with pytest.raises(DatabaseError), transaction.atomic():
            force(event.id, recipient_pseudonym=uuid.uuid4())
        force(event.id, payload_enc=None, recipient_pseudonym=None, dedupe_key=None)

    def test_terminal_status_is_final_and_identity_immutable(self):
        event = self.done()
        with pytest.raises(DatabaseError), transaction.atomic():
            force(event.id, status="PENDING", terminal_at=None)
        with pytest.raises(DatabaseError), transaction.atomic():
            force(event.id, event_type="other")

    def test_only_terminal_redacted_rows_can_be_purged(self):
        live = emit()
        with pytest.raises(DatabaseError), transaction.atomic():
            OutboxEvent.objects.filter(id=live.id).delete()
        done = self.done()
        with pytest.raises(DatabaseError), transaction.atomic():
            OutboxEvent.objects.filter(id=done.id).delete()
        force(done.id, payload_enc=None, recipient_pseudonym=None, dedupe_key=None)
        OutboxEvent.objects.filter(id=done.id).delete()

    def test_financial_obligations_wait_seven_days(self):
        event = self.done(event_class="FINANCIAL_OBLIGATION", category="FINANCIAL")
        with pytest.raises(DatabaseError), transaction.atomic():
            force(event.id, payload_enc=None)
        force(event.id, terminal_at=timezone.now() - timedelta(days=8))
        force(event.id, payload_enc=None)

    def test_undecryptable_obligation_needs_verified_resolution(self):
        event = emit(event_class="FINANCIAL_OBLIGATION", category="FINANCIAL")
        old = timezone.now() - timedelta(days=8)
        force(event.id, status="DEAD_UNDECRYPTABLE", terminal_at=old)
        with pytest.raises(DatabaseError), transaction.atomic():
            force(event.id, payload_enc=None)  # resolution still PENDING
        force(event.id, obligation_resolution="REPLACED_VERIFIED", resolved_at=old)
        force(event.id, payload_enc=None)


@pytest.mark.django_db
def test_redact_and_purge_follow_retention():
    fresh, old, ancient = emit(), emit(), emit()
    now = timezone.now()
    force(fresh.id, status="DONE", terminal_at=now)
    force(old.id, status="DONE", terminal_at=now - timedelta(days=8))
    force(ancient.id, status="DONE", terminal_at=now - timedelta(days=31))
    redacted, purged = services.redact_and_purge()
    assert (redacted, purged) == (2, 1)
    assert OutboxEvent.objects.get(id=old.id).payload_enc is None
    assert OutboxEvent.objects.get(id=fresh.id).payload_enc is not None
    assert not OutboxEvent.objects.filter(id=ancient.id).exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_claimers_get_disjoint_batches():
    with transaction.atomic():
        for _ in range(20):
            services.emit(
                "test.noop",
                event_class="NOTIFICATION",
                category="ACCOUNT",
                aggregate_type="Test",
                payload={},
            )
    barrier = threading.Barrier(2)
    claimed: list[list] = []

    def worker():
        try:
            barrier.wait()
            claimed.append([event_id for event_id, _ in services.claim_batch(15)])
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    first, second = claimed
    assert not set(first) & set(second)
    assert len(first) + len(second) == 20
