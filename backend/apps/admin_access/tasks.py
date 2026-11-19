"""Periodic admin-access jobs (CC-R53/CC-R54: idempotent, bounded retries)."""

from celery import shared_task


@shared_task(name="admin_access.sync_expired_assignments")
def sync_expired_assignments() -> int:
    from .services.roles import sync_expired_assignments as run

    return run()


@shared_task(name="admin_access.expire_recovery_requests")
def expire_recovery_requests() -> int:
    from .services.recovery import expire_recovery_requests as run

    return run()
