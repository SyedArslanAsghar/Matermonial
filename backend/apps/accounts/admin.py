from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group

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
    list_filter = ("is_active", "deactivated", "is_staff", "is_superuser")
    filter_horizontal = ()
    search_fields = ("phone_number", "email", "first_name", "last_name")
    # TR-07 / ADR-027: admin authorization comes only from the AdminRole tables. is_staff is a
    # projection written by the admin-role service and is_superuser is break-glass only, so
    # neither is editable here; Django groups and user_permissions are never used.
    readonly_fields = (
        "created_at",
        "updated_at",
        "date_joined",
        "last_login",
        "is_staff",
        "is_superuser",
    )
    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("Personal information", {"fields": ("first_name", "last_name", "email")}),
        ("Verification", {"fields": ("is_phone_verified", "is_email_verified")}),
        ("Status", {"fields": ("is_active", "deactivated", "deactivated_reason")}),
        ("Administrative access (read-only, TR-07)", {"fields": ("is_staff", "is_superuser")}),
        ("Audit", {"fields": ("created_at", "created_by", "updated_at", "updated_by")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone_number", "password1", "password2"),
            },
        ),
    )


# TR-07: Django groups are not an authorization source; hide their admin page.
if admin.site.is_registered(Group):
    admin.site.unregister(Group)
