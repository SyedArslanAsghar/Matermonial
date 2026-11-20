"""Push delivery (CC-R53/CC-R54): idempotent, bounded retries, failures recorded."""

from celery import shared_task
from django.conf import settings


@shared_task(name="notifications.deliver_push")
def deliver_push(delivery_id: str, attempt: int = 1) -> str:
    from .services import deliver

    result = deliver(delivery_id)
    if result == "retry" and attempt < settings.NOTIFICATION_PUSH_MAX_ATTEMPTS:
        deliver_push.apply_async(
            args=[delivery_id, attempt + 1], countdown=min(30 * 2**attempt, 3600)
        )
    return result
