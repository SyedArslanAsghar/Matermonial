"""Shared pytest fixtures and conventions.

- Unit tests that don't touch the database carry no marker and run anywhere.
- Tests that need the database use ``@pytest.mark.django_db`` and run on PostgreSQL (TR-13);
  pytest-django builds the test database from the migrations.
- Concurrency tests follow doc 12 §8 (``django_db(transaction=True)``, one connection per
  thread); they are added with the features that need them.
"""

import pytest
from rest_framework.test import APIClient

from common.providers import MockPushProvider, MockSMSProvider


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture(autouse=True)
def _clear_cache():
    """Rate-limit and flood-control counters live in the cache; isolate tests."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _reset_mock_providers():
    MockSMSProvider.sent.clear()
    MockPushProvider.sent.clear()
    yield
    MockSMSProvider.sent.clear()
    MockPushProvider.sent.clear()
