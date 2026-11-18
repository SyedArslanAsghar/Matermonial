"""Periodic maintenance jobs (TR-24); each runs through the maintenance protocol."""

from celery import shared_task

from .services.maintenance import ensure_log_partitions, write_checkpoint


@shared_task(name="platform_ops.ensure_log_partitions")
def ensure_log_partitions_task() -> list[str]:
    return ensure_log_partitions()


@shared_task(name="platform_ops.write_registry_checkpoint")
def write_registry_checkpoint_task() -> str:
    return write_checkpoint().status
