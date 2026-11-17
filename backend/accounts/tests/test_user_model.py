import pytest
from django.core.exceptions import ValidationError

from accounts.models import User


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


@pytest.mark.django_db
def test_create_user_without_password_gets_unusable_password():
    user = User.objects.create_user(phone_number="+923001234568")

    assert user.has_usable_password() is False


@pytest.mark.django_db
def test_invalid_phone_format_is_rejected():
    with pytest.raises(ValidationError):
        User.objects.create_user(phone_number="03001234567", password="password")
