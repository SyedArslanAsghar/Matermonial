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
    actions = ["issue_mfa_enrollment", "request_mfa_recovery"]

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
            actions.pop("request_mfa_recovery", None)
        return actions

    @admin.action(description="Send a first MFA enrollment code by SMS")
    def issue_mfa_enrollment(self, request, queryset):
        """KI-39: the code goes only to each account holder's verified phone; the issuing
        administrator sees the outcome, never the code."""
        from apps.admin_access.services.mfa import issue_enrollment
        from apps.admin_access.services.roles import Actor, AdminAccessError

        actor = Actor(user=request.user, request_id=getattr(request, "request_id", None))
        for user in queryset:
            try:
                delivered = issue_enrollment(actor, user)
            except AdminAccessError as exc:
                self.message_user(request, f"{user}: {exc or exc.code}", messages.ERROR)
                continue
            if delivered:
                self.message_user(
                    request, f"{user}: enrollment code sent by SMS to the account holder."
                )
            else:
                self.message_user(
                    request,
                    f"{user}: SMS delivery failed; the code was revoked and not revealed. "
                    "Try again when SMS works.",
                    messages.ERROR,
                )
        return None

    @admin.action(description="Request MFA recovery (a second administrator must approve)")
    def request_mfa_recovery(self, request, queryset):
        """ADR-033 Amendment 1: creates a PENDING request; nothing is reset and no code is shown.
        An intermediate page asks for the reason code."""
        from apps.admin_access.services.recovery import request_recovery
        from apps.admin_access.services.roles import Actor, AdminAccessError

        reason = (request.POST.get("reason_code") or "").strip().upper()
        if "apply" not in request.POST:
            context = {
                **self.admin_site.each_context(request),
                "title": "Request MFA recovery",
                "queryset": queryset,
                "action_name": "request_mfa_recovery",
            }
            return TemplateResponse(request, "admin_access/request_recovery.html", context)
        actor = Actor(user=request.user, request_id=getattr(request, "request_id", None))
        for user in queryset:
            try:
                request_recovery(actor, user, reason)
                self.message_user(
                    request, f"{user}: recovery requested; awaiting a second administrator."
                )
            except AdminAccessError as exc:
                self.message_user(request, f"{user}: {exc or exc.code}", messages.ERROR)
        return None

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
