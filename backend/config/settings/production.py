"""Production settings (AWS EC2 with Docker; doc 09). Fail closed on unsafe configuration."""

import os

from common.config import validate_deployed_settings

from .base import *  # noqa: F403

ENVIRONMENT = os.environ.get("DJANGO_ENVIRONMENT", "production")
DEBUG = False

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# __Host- cookies (doc 06 §22.2 / §10.3): Secure, Path=/, no Domain. Local HTTP can't use them.
SESSION_COOKIE_NAME = "__Host-mat_session"
CSRF_COOKIE_NAME = "__Host-mat_csrf"
ADMIN_SESSION_COOKIE_NAME = "__Host-mat_admin_session"
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
SESSION_COOKIE_PATH = "/"
CSRF_COOKIE_PATH = "/"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

validate_deployed_settings(globals(), os.environ)
