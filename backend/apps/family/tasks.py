"""Family-management jobs (CC-R53/CC-R54: idempotent)."""

from celery import shared_task
from django.db import OperationalError


@shared_task(name="family.expire_authorizations")
def expire_authorizations() -> int:
    from .services.authorizations import expire_due

    return expire_due()


@shared_task(
    name="family.resolve_manager_invitation",
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    max_retries=5,
)
def resolve_manager_invitation(invitation_id: str) -> bool:
    """Resolve one invitation to an eligible account (KI-34). Idempotent; bounded retries on
    database contention. Returns whether an authorization was created."""
    from .services.authorizations import resolve_invitation

    return resolve_invitation(invitation_id) is not None


@shared_task(
    name="family.resolve_manager_request",
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    max_retries=5,
)
def resolve_manager_request(request_id: str) -> bool:
    """Deliver one request to manage a profile to its owner, if eligible (Flow B). Idempotent;
    bounded retries on database contention."""
    from .services.requests import resolve_request

    return resolve_request(request_id) is not None
