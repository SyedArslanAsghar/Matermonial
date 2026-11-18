"""Celery task conventions (CLAUDE.md CC-R53, CC-R54; doc 02 §16).

Every task inherits ``BaseTask`` (set as the app's task class in config/celery.py):
- Tasks must be idempotent, because retries and redelivery happen (acks_late).
- Retries are bounded: at most 3, exponential backoff with jitter, capped at 10 minutes.
  Each task opts in to retry with ``autoretry_for`` for the transient errors it expects.
- Failures are recorded in the logs with task name and ID only. Arguments aren't logged,
  because they may identify a person.
- Running a task doesn't prove that an external delivery succeeded.
"""

import logging

from celery import Task

logger = logging.getLogger(__name__)


class BaseTask(Task):
    acks_late = True
    reject_on_worker_lost = True
    max_retries = 3
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "Task failed",
            extra={"task": self.name, "task_id": task_id, "error_type": type(exc).__name__},
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)
