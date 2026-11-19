"""Media processing (CC-R53). Idempotent: only a QUARANTINED row is processed (TR-10)."""

from celery import shared_task


@shared_task(name="profiles.process_photo")
def process_photo(photo_id: str) -> str:
    from .services.photos import process_photo as run

    return run(photo_id)
