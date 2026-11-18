from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import AdminUserChangeForm, AdminUserCreationForm
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm
    ordering = ("-created_at",)
    list_display = (
        "phone_number",
        "email",
        "is_phone_verified",
        "is_active",
        "deactivated",
        "is_staff",
    )
    search_fields = ("phone_number", "email", "first_name", "last_name")
    readonly_fields = ("created_at", "updated_at", "date_joined", "last_login")
    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("Personal information", {"fields": ("first_name", "last_name", "email")}),
        ("Verification", {"fields": ("is_phone_verified", "is_email_verified")}),
        ("Status", {"fields": ("is_active", "deactivated", "deactivated_reason")}),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Audit", {"fields": ("created_at", "created_by", "updated_at", "updated_by")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone_number", "password1", "password2", "is_staff", "is_superuser"),
            },
        ),
    )
