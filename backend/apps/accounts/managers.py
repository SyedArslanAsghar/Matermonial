import re

from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ValidationError

# Same pattern in Python and in the database CHECK constraint (accounts_user_phone_e164).
E164_REGEX = r"^\+[1-9][0-9]{7,14}$"
E164_PATTERN = re.compile(E164_REGEX)


def normalize_phone_number(phone_number: str) -> str:
    value = (phone_number or "").strip()
    if not E164_PATTERN.fullmatch(value):
        raise ValidationError("Enter a valid phone number in E.164 format, e.g. +923001234567.")
    return value


def normalize_email(email: str | None) -> str | None:
    """Trim and lower-case the whole address; empty means no email (FR-ACC-003).

    Email uniqueness is case-insensitive (G4 decision package), so storing one canonical
    form keeps lookups and the Lower(email) unique constraint consistent.
    """
    value = (email or "").strip().lower()
    return value or None


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("A phone number is required.")
        phone_number = normalize_phone_number(phone_number)
        if "email" in extra_fields:
            extra_fields["email"] = normalize_email(extra_fields["email"])
        user = self.model(phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(phone_number, password, **extra_fields)
