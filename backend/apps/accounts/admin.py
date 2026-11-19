from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.template.response import TemplateResponse

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
    actions = ["issue_mfa_enrollment", "reset_admin_mfa"]

    def user_change_password(self, request, id, form_url=""):
        # Staff never set an account's password (raw state editing; doc 06 §15). Recovery is
        # the user's own password reset, which revokes sessions and records events.
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied

    def save_model(self, request, obj, form, change):
        if change:
            return super().save_model(request, obj, form, change)
        # New accounts go through the manager so the pseudonym and data key are created in the
        # same transaction (TR-23); a plain save() would skip them.
        created = User.objects.create_user(
            obj.phone_number, form.cleaned_data.get("password1"), created_by=request.user
        )
        obj.pk, obj._state.adding, obj._state.db = created.pk, False, created._state.db

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.has_perm("admin_access.reset_admin_mfa"):
            actions.pop("issue_mfa_enrollment", None)
            actions.pop("reset_admin_mfa", None)
        return actions

    def _mfa_action(self, request, queryset, operation, title):
        from apps.admin_access.services.roles import Actor, AdminAccessError

        actor = Actor(user=request.user, request_id=getattr(request, "request_id", None))
        results, errors = [], []
        for user in queryset:
            try:
                code = operation(actor, user)
            except AdminAccessError as exc:
                errors.append(f"{user}: {exc or exc.code}")
                continue
            results.append((user, code))
        for error in errors:
            self.message_user(request, error, messages.ERROR)
        if not results:
            return None
        # Codes are rendered once in this response, never stored in messages or logs.
        context = {**self.admin_site.each_context(request), "title": title, "results": results}
        response = TemplateResponse(request, "admin_access/enrollment_codes.html", context)
        response["Cache-Control"] = "no-store"
        return response

    @admin.action(description="Issue an MFA enrollment code")
    def issue_mfa_enrollment(self, request, queryset):
        from apps.admin_access.services.mfa import issue_enrollment

        return self._mfa_action(request, queryset, issue_enrollment, "MFA enrollment codes")

    @admin.action(description="Reset admin MFA and issue a new enrollment code")
    def reset_admin_mfa(self, request, queryset):
        from apps.admin_access.services.mfa import reset_mfa

        return self._mfa_action(request, queryset, reset_mfa, "MFA reset")

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
