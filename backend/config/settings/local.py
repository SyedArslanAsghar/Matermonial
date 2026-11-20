"""Local development settings: native setup, mock providers, no Docker required (CC-R21, CC-R23)."""

from .base import *  # noqa: F403
from .base import LOGGING, env

ENVIRONMENT = "local"
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

API_DOCS_ENABLED = env.bool("API_DOCS_ENABLED", default=True)
LOCK_TRACKER_ENABLED = env.bool("LOCK_TRACKER_ENABLED", default=True)
SMS_PROVIDER = env("SMS_PROVIDER", default="mock")
PUSH_PROVIDER = env("PUSH_PROVIDER", default="mock")
EMAIL_PROVIDER = env("EMAIL_PROVIDER", default="console")
EMAIL_BACKEND = env("EMAIL_BACKEND", default=EMAIL_BACKENDS.get(EMAIL_PROVIDER, ""))  # noqa: F405
MALWARE_SCANNER = env("MALWARE_SCANNER", default="mock")
# Redis and a Celery worker are optional locally: tasks run inline unless disabled.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)

LOGGING["handlers"]["console"]["formatter"] = env("DJANGO_LOG_FORMAT", default="text")
