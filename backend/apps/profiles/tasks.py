"""Media processing (CC-R53). Idempotent: only a QUARANTINED row is processed (TR-10).
An unavailable scanner is retried a bounded number of times (PHOTO_SCAN_MAX_ATTEMPTS)."""

from celery import shared_task
from django.conf import settings


@shared_task(name="profiles.process_photo")
def process_photo(photo_id: str) -> str:
    from .services.photos import process_photo as run

    result = run(photo_id)
    if result == "retry":
        process_photo.apply_async(args=[photo_id], countdown=settings.PHOTO_SCAN_RETRY_SECONDS)
    return result
