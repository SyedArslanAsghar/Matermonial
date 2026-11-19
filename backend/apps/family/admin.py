"""Configurable templates and the permission catalogue (FR-FAM-004; doc 14 §1). Sensitivity is
fixed by the approved catalogue (read-only); templates and activation are editable. Changes are
audited. Templates never grant Sensitive permissions by being applied (service rule)."""

from django.contrib import admin

from apps.audit.services import record_audit

from .models import ManagerPermission, ManagerPermissionGroup, ManagerPermissionGroupPermission


def _audit(request, action, obj):
    record_audit(
        action=action,
        resource_type="family.catalogue",
        actor_type="ADMIN",
        result="SUCCESS",
        category="ADMINISTRATIVE",
        actor_user_id=request.user.pk,
        request_id=getattr(request, "request_id", None),
        metadata={"code": obj.code, "is_active": obj.is_active},
    )


@admin.register(ManagerPermission)
class ManagerPermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "sensitivity", "is_active")
    list_filter = ("sensitivity", "is_active")
    fields = ("code", "name", "description", "sensitivity", "is_active")
    readonly_fields = ("code", "sensitivity")

    def has_add_permission(self, request):
        return False  # the catalogue is the approved doc 14 §3 list

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        _audit(request, "family.permission_changed", obj)


class GroupPermissionInline(admin.TabularInline):
    model = ManagerPermissionGroupPermission
    extra = 0


@admin.register(ManagerPermissionGroup)
class ManagerPermissionGroupAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_system_default", "is_active")
    inlines = [GroupPermissionInline]

    def get_readonly_fields(self, request, obj=None):
        return ("code", "is_system_default") if obj is not None else ("is_system_default",)

    def has_delete_permission(self, request, obj=None):
        return False  # deactivate instead; authorizations reference templates

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        _audit(request, "family.template_changed", obj)
