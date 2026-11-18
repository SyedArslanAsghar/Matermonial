"""Staging settings: the same security and fail-closed validation as production (doc 07 §2,
doc 16 §4). Staging uses sandbox providers and separate secrets; it never uses production data.
"""

import os

os.environ.setdefault("DJANGO_ENVIRONMENT", "staging")

from .production import *  # noqa: E402, F403
