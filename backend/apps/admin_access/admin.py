"""Admin pages for administrative access (TR-07).

- Roles and permissions are read-only here: they come from the reviewed code catalogue
  (``sync_admin_catalogue``), so nobody widens a role from the browser.
- Assignments are created and revoked only through ``services.roles`` (authorization,
  anti-escalation, locking, ``is_staff`` projection and audit). Rows are never edited or deleted.
- MFA devices and enrollment codes have no admin page; resets and codes are actions on accounts
  (accounts/admin.py) that call ``services.mfa``.
"""

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from apps.accounts.models import User

from .models import AdminActionApproval, AdminPermission, AdminRole, AdminUserRole
from .services.roles import Actor, AdminAccessError, assign_role, assignment_problem, revoke_role


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AdminPermission)
class AdminPermissionAdmin(ReadOnlyAdmin):
    list_display = ("code", "name", "is_sensitive", "is_active")
    list_filter = ("is_sensitive", "is_active")
    search_fields = ("code", "name")


@admin.register(AdminRole)
class AdminRoleAdmin(ReadOnlyAdmin):
    list_display = ("code", "name", "is_active")
    readonly_fields = ("code", "name", "description", "is_active", "permission_codes")
    fields = readonly_fields

    @admin.display(description="Permissions")
    def permission_codes(self, obj):
        return ", ".join(obj.permissions.order_by("code").values_list("code", flat=True))


class AssignRoleForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True, deactivated=False).order_by("phone_number"),
        to_field_name="phone_number",
        widget=forms.TextInput,
        help_text="Phone number in E.164 format.",
    )

    class Meta:
        model = AdminUserRole
        fields = ("user", "role", "expires_at")

    def __init__(self, *args, actor: Actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        self.fields["role"].queryset = AdminRole.objects.filter(is_active=True)

    def clean(self):
        data = super().clean()
        if data.get("user") and data.get("role"):
            problem = assignment_problem(self.actor, data["user"], data["role"])
            if problem is not None:
                raise ValidationError(str(problem) or "You can't make this assignment.")
        return data


@admin.register(AdminUserRole)
class AdminUserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "assigned_by", "assigned_at", "expires_at", "revoked_at")
    list_filter = ("role", ("revoked_at", admin.EmptyFieldListFilter))
    search_fields = ("user__phone_number",)
    list_select_related = ("user", "role", "assigned_by")
    actions = ["revoke_selected"]

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        actor = Actor(user=request.user, request_id=getattr(request, "request_id", None))

        class Bound(form):
            def __init__(self, *args, **kw):
                super().__init__(*args, actor=actor, **kw)

        return Bound

    form = AssignRoleForm

    def has_add_permission(self, request):
        return request.user.has_perm("admin_access.add_adminuserrole") and request.user.has_perm(
            "admin_access.manage_roles"
        )

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.has_perm("admin_access.manage_roles"):
            actions.pop("revoke_selected", None)
        return actions

    def save_model(self, request, obj, form, change):
        actor = Actor(user=request.user, request_id=getattr(request, "request_id", None))
        created = assign_role(
            actor, obj.user, obj.role.code, expires_at=form.cleaned_data.get("expires_at")
        )
        obj.pk, obj.assigned_at, obj._state.adding = created.pk, created.assigned_at, False

    @admin.action(description="Revoke selected assignments")
    def revoke_selected(self, request, queryset):
        actor = Actor(user=request.user, request_id=getattr(request, "request_id", None))
        done = 0
        for row in queryset.filter(revoked_at__isnull=True).select_related("user", "role"):
            try:
                revoke_role(actor, row.user, row.role.code)
                done += 1
            except AdminAccessError as exc:
                self.message_user(request, f"{row}: {exc or exc.code}", messages.ERROR)
        self.message_user(request, f"Revoked {done} assignment(s).", messages.SUCCESS)


@admin.register(AdminActionApproval)
class AdminActionApprovalAdmin(ReadOnlyAdmin):
    """Approval requests (ADR-033 Amendment 1). Read-only rows; decisions go through the
    recovery service, which enforces separation of duties and never reveals codes."""

    list_display = (
        "action_type",
        "resource_id",
        "status",
        "outcome",
        "requested_by",
        "requested_at",
        "approved_by",
        "rejected_by",
        "expires_at",
    )
    list_filter = ("action_type", "status")
    actions = ["approve_selected", "reject_selected"]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.has_perm("admin_access.approve_admin_mfa_recovery"):
            actions.pop("approve_selected", None)
            actions.pop("reject_selected", None)
        return actions

    def _decide(self, request, queryset, operation, done_message):
        from .services.recovery import RecoveryNotPending

        actor = Actor(user=request.user, request_id=getattr(request, "request_id", None))
        for approval in queryset:
            try:
                result = operation(actor, approval.pk)
                if result.outcome == "DELIVERY_FAILED":
                    self.message_user(
                        request,
                        "Approved, but SMS delivery failed: the code was revoked and not "
                        "revealed. Start a new request or use the emergency procedure.",
                        messages.WARNING,
                    )
                else:
                    self.message_user(request, done_message, messages.SUCCESS)
            except (AdminAccessError, RecoveryNotPending) as exc:
                self.message_user(request, f"{approval.pk}: {exc or exc.code}", messages.ERROR)

    @admin.action(description="Approve selected recovery requests")
    def approve_selected(self, request, queryset):
        from .services.recovery import approve_recovery

        self._decide(
            request,
            queryset,
            approve_recovery,
            "Approved. The replacement code is sent by SMS to the account holder only.",
        )

    @admin.action(description="Reject selected recovery requests")
    def reject_selected(self, request, queryset):
        from .services.recovery import reject_recovery

        self._decide(request, queryset, reject_recovery, "Rejected.")
