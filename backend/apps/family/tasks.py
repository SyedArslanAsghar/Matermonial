"""Family-management jobs (CC-R53/CC-R54: idempotent)."""

from celery import shared_task


@shared_task(name="family.expire_authorizations")
def expire_authorizations() -> int:
    from .services.authorizations import expire_due

    return expire_due()
