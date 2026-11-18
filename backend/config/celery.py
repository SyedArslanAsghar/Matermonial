"""Celery application (approved dependency list, DR-2026-11-17-G3-4).

Settings use the ``CELERY_`` namespace (config/settings/base.py). Tasks are discovered in
each app's ``tasks.py``. The deployment entry point defaults to production settings; set
DJANGO_SETTINGS_MODULE=config.settings.local for a local worker.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("matermonial", task_cls="common.tasks:BaseTask")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
