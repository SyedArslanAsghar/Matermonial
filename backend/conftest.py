"""Shared pytest fixtures and conventions.

- Unit tests that don't touch the database carry no marker and run anywhere.
- Tests that need the database use ``@pytest.mark.django_db`` and run on PostgreSQL (TR-13).
  They need the first migration (G4) before they can create the test database (KI-14).
- Concurrency tests follow doc 12 §8 (``django_db(transaction=True)``, one connection per
  thread); they are added with the features that need them.
- ``@pytest.mark.deferred_g4_ki14`` marks exactly the 3 User-model database tests that need the
  initial ``accounts`` migration (KI-14, carried forward to G4 by DR-2026-11-18-G3A). They are
  reported as skipped with a DEFERRED reason, never as passed. Once that migration exists the
  marker is stale, and the run stops with an error until it is removed.
"""

from pathlib import Path

import pytest
from rest_framework.test import APIClient

from common.providers import MockPushProvider, MockSMSProvider

DEFERRED_G4_MARKER = "deferred_g4_ki14"
DEFERRED_G4_REASON = (
    "DEFERRED to G4 (KI-14, DR-2026-11-18-G3A): needs the initial accounts migration, "
    "which doesn't exist yet. Not run, not passed."
)
ACCOUNTS_MIGRATIONS = Path(__file__).resolve().parent / "apps" / "accounts" / "migrations"


def pytest_collection_modifyitems(config, items):
    deferred = [item for item in items if item.get_closest_marker(DEFERRED_G4_MARKER)]
    if not deferred:
        return
    if any(ACCOUNTS_MIGRATIONS.glob("0001_*.py")):
        raise pytest.UsageError(
            f"The initial accounts migration exists, so the '{DEFERRED_G4_MARKER}' marker is stale: "
            "remove it from the KI-14 tests so they run (KI-14)."
        )
    for item in deferred:
        item.add_marker(pytest.mark.skip(reason=DEFERRED_G4_REASON))


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture(autouse=True)
def _reset_mock_providers():
    MockSMSProvider.sent.clear()
    MockPushProvider.sent.clear()
    yield
    MockSMSProvider.sent.clear()
    MockPushProvider.sent.clear()
