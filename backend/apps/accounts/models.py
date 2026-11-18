import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=16, unique=True, db_index=True)
    email = models.EmailField(max_length=254, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)

    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    deactivated = models.BooleanField(default=False)
    deactivated_reason = models.TextField(blank=True)

    date_joined = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    # Audit FKs use PROTECT: doc 12 §5.5 rule F4 (TR-09, approved) forbids cascading or
    # SET NULL deletes on hot referenced rows; accounts are anonymised, never hard-deleted
    # during business transactions. Implicit-lock class B2 (common/db/fk_inventory.py).
    created_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="users_created",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="users_updated",
    )

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "accounts_user"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active", "deactivated"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.phone_number

    def save(self, *args, **kwargs):
        # Normalize/validate before persistence, including admin and service writes.
        from .managers import normalize_phone_number

        self.phone_number = normalize_phone_number(self.phone_number)
        if self.deactivated:
            self.is_active = False
        super().save(*args, **kwargs)
