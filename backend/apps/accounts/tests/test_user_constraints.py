"""G4 stage 1: database-level guarantees on the User table (CC-R19, CC-R35; TR-07 / D-4 A').

QuerySet.update() bypasses User.save(), so these tests prove the database itself enforces
each rule, not just the Python validation.
"""

import pytest
from django.contrib.auth.models import Group, Permission
from django.db import IntegrityError, InternalError, ProgrammingError, transaction

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def make_user(phone="+923001234567", **extra):
    return User.objects.create_user(phone_number=phone, password="Strong-password-123!", **extra)


def test_database_rejects_non_e164_phone_written_around_save():
    user = make_user()
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=user.pk).update(phone_number="03001234567")


def test_database_rejects_deactivated_user_that_is_still_active():
    user = make_user()
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=user.pk).update(deactivated=True, is_active=True)


def test_deactivated_user_is_saved_inactive_and_reason_is_nullable():
    user = make_user()
    assert user.deactivated_reason is None
    user.deactivated = True
    user.save()
    user.refresh_from_db()
    assert user.is_active is False


def test_email_is_normalised_and_unique_case_insensitively():
    user = make_user(email="  Person@Example.COM ")
    assert user.email == "person@example.com"
    with pytest.raises(IntegrityError), transaction.atomic():
        # Written around save() so the database constraint, not normalisation, is tested.
        other = make_user(phone="+923001234568")
        User.objects.filter(pk=other.pk).update(email="PERSON@example.com")


def test_blank_email_is_stored_as_null_so_many_accounts_can_omit_it():
    first = make_user(email="")
    second = make_user(phone="+923001234568", email="   ")
    assert first.email is None and second.email is None


@pytest.mark.parametrize("relation", ["groups", "user_permissions"])
def test_django_permission_link_tables_reject_rows(relation):
    """TR-07: AdminRole tables are the only permission source (D-4 A')."""
    user = make_user()
    target = (
        Group.objects.create(name="should-not-be-used")
        if relation == "groups"
        else Permission.objects.first()
    )
    with pytest.raises((InternalError, ProgrammingError)), transaction.atomic():
        getattr(user, relation).add(target)
    assert getattr(user, relation).count() == 0
