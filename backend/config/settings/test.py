"""Test settings. Tests run on PostgreSQL (TR-13, approved 2026-11-17; CLAUDE.md CC-R58).

The database comes from DATABASE_URL via base.py; pytest-django creates and drops a separate
"test_<name>" database. The previous in-memory SQLite override was removed (KI-4).

KI-38: DATABASE_URL must be set explicitly (environment or backend/.env) and point to an approved
disposable server (loopback, port 55432 or 55418 by default; never 5432). Otherwise loading these
settings fails before any connection is attempted; base.py's development default is never used.
"""

import os
from pathlib import Path

import environ

from common.test_database import require_disposable_test_database

# A developer's backend/.env counts as explicit configuration (base.py reads it too); it never
# overrides variables already set in the environment.
environ.Env.read_env(Path(__file__).resolve().parent.parent.parent / ".env")
require_disposable_test_database(os.environ)

from .base import *  # noqa: E402, F403

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
