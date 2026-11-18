"""Celery entry points for the outbox (CC-R53, CC-R54). The outbox rows are the source of
truth; these tasks only drive processing and retention, and are idempotent."""

from celery import shared_task

from common.idempotency.services import purge_expired

from . import services


@shared_task(name="events.process_outbox")
def process_outbox(limit: int = 50) -> dict:
    return services.process_due(limit)


@shared_task(name="events.redact_and_purge_outbox")
def redact_and_purge_outbox() -> dict:
    redacted, purged = services.redact_and_purge()
    return {"redacted": redacted, "purged": purged}


@shared_task(name="idempotency.purge_expired")
def purge_expired_idempotency_records() -> int:
    return purge_expired()
