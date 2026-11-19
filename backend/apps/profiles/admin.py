"""Controlled-vocabulary administration (owner review 2026-11-19; reference.py).

Holders of ``profiles.add_vocabularyoption`` / ``profiles.change_vocabularyoption`` (sensitive,
admin catalogue) may add options and edit labels, order and activation. ``vocabulary`` and
``code`` are fixed after creation (also a database trigger) and options are never deleted.
Every change is audited. Activating a proposed option is the owner-approved step.
"""

from django.contrib import admin

from apps.audit.services import record_audit

from .models import VocabularyOption

TRACKED = ("label_en", "label_ur", "sort_order", "is_active")


@admin.register(VocabularyOption)
class VocabularyOptionAdmin(admin.ModelAdmin):
    list_display = ("vocabulary", "code", "label_en", "label_ur", "sort_order", "is_active")
    list_filter = ("vocabulary", "is_active")
    list_editable = ()
    search_fields = ("code", "label_en")
    ordering = ("vocabulary", "sort_order", "code")
    fields = ("vocabulary", "code", "label_en", "label_ur", "sort_order", "is_active")

    def get_readonly_fields(self, request, obj=None):
        return ("vocabulary", "code") if obj is not None else ()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        changed = sorted(f for f in TRACKED if f in form.changed_data) if change else ["created"]
        super().save_model(request, obj, form, change)
        record_audit(
            action="profiles.vocabulary_option_changed"
            if change
            else "profiles.vocabulary_option_added",
            resource_type="profiles.vocabulary_option",
            actor_type="ADMIN",
            result="SUCCESS",
            category="ADMINISTRATIVE",
            actor_user_id=request.user.pk,
            request_id=getattr(request, "request_id", None),
            metadata={
                "vocabulary": obj.vocabulary,
                "code": obj.code,
                "is_active": obj.is_active,
                "changed": ".".join(changed),
            },
        )
