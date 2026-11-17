from .base import *

DEBUG = False
SECRET_KEY = "test-only-secret-key"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Tests run on PostgreSQL (TR-13, approved 2026-11-17; CLAUDE.md CC-R58). The database comes from
# DATABASE_URL via base.py; pytest-django creates and drops a separate "test_<name>" database.
# The previous in-memory SQLite override was removed (known issue KI-4).
