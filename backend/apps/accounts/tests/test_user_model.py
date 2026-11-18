"""User-model database tests.

These 3 tests are deferred to G4 (KI-14; DR-2026-11-18-G3A): they need the initial `accounts`
migration to create the test database. `deferred_g4_ki14` reports them as skipped with that
reason (backend/conftest.py), never as passed. Remove the marker when G4 adds the migration.
"""

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User


@pytest.mark.deferred_g4_ki14
@pytest.mark.django_db
def test_create_user_stores_e164_phone_and_hashed_password():
    user = User.objects.create_user(
        phone_number=" +923001234567 ",
        password="Strong-password-123!",
    )

    assert user.phone_number == "+923001234567"
    assert user.check_password("Strong-password-123!")
    assert user.password != "Strong-password-123!"
    assert user.is_active is True
    assert user.deactivated is False


@pytest.mark.deferred_g4_ki14
@pytest.mark.django_db
def test_create_user_without_password_gets_unusable_password():
    user = User.objects.create_user(phone_number="+923001234568")

    assert user.has_usable_password() is False


@pytest.mark.deferred_g4_ki14
@pytest.mark.django_db
def test_invalid_phone_format_is_rejected():
    with pytest.raises(ValidationError):
        User.objects.create_user(phone_number="03001234567", password="password")
