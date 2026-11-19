"""Test settings. Tests run on PostgreSQL (TR-13, approved 2026-11-17; CLAUDE.md CC-R58).

The database comes from DATABASE_URL via base.py; pytest-django creates and drops a separate
"test_<name>" database. The previous in-memory SQLite override was removed (KI-4).
"""

from .base import *  # noqa: F403

ENVIRONMENT = "test"
DEBUG = False
SECRET_KEY = "test-only-secret-key"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

API_DOCS_ENABLED = True
LOCK_TRACKER_ENABLED = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
SMS_PROVIDER = "mock"
PUSH_PROVIDER = "mock"
MALWARE_SCANNER = "mock"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_BROKER_URL = "memory://localhost/"
