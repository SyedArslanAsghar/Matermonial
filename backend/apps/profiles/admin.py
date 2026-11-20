"""Controlled-vocabulary administration (owner review 2026-11-19; reference.py).

Holders of ``profiles.add_vocabularyoption`` / ``profiles.change_vocabularyoption`` (sensitive,
admin catalogue) may add options and edit labels, order and activation. ``vocabulary``, ``code``
and ``parent`` are fixed after creation (also a database trigger) and options are never deleted.
Every change is audited. Activating a proposed option is the owner-approved step.

Parent choices (corrected 2026-11-20, DR-2026-11-20-P-2): a denomination's parent is a religion
option and is required; a sub-caste's parent is a caste option and is optional; no other list
has a parent. The dropdown offers only valid choices for the list being added (pass
``?vocabulary=<list>`` on the add page to narrow it to one list; without it, religion and caste
options are offered, labelled with their list), and the form rejects a mismatched parent before
the database trigger would. Database constraints are unchanged.
"""

from django import forms
from django.contrib import admin

from apps.audit.services import record_audit

from .models import VocabularyOption

TRACKED = ("label_en", "label_ur", "sort_order", "is_active")

# vocabulary -> (parent vocabulary, parent required)
PARENT_RULES = {"denomination": ("religion", True), "sub_caste": ("caste", False)}


class ParentChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.vocabulary}: {obj.label_en} ({obj.code})"


class VocabularyOptionForm(forms.ModelForm):
    class Meta:
        model = VocabularyOption
        fields = ("vocabulary", "code", "parent", "label_en", "label_ur", "sort_order", "is_active")

    def clean(self):
        cleaned = super().clean()
        if not self.instance._state.adding:  # vocabulary, code, parent are read-only after creation
            return cleaned
        vocabulary, parent = cleaned.get("vocabulary"), cleaned.get("parent")
        rule = PARENT_RULES.get(vocabulary)
        if rule is None:
            if parent is not None:
                self.add_error("parent", "This list has no parent.")
            return cleaned
        parent_list, required = rule
        if parent is None and required:
            self.add_error("parent", f"Choose the {parent_list} this option belongs to.")
        elif parent is not None and parent.vocabulary != parent_list:
            self.add_error("parent", f"The parent must be a {parent_list} option.")
        return cleaned


def parent_queryset(vocabulary: str | None):
    """Valid parent options for ``vocabulary`` (None: the add page before a list is chosen)."""
    if vocabulary in PARENT_RULES:
        return VocabularyOption.objects.filter(vocabulary=PARENT_RULES[vocabulary][0])
    if vocabulary:
        return VocabularyOption.objects.none()
    return VocabularyOption.objects.filter(
        vocabulary__in=[parent for parent, _ in PARENT_RULES.values()]
    )


@admin.register(VocabularyOption)
class VocabularyOptionAdmin(admin.ModelAdmin):
    list_display = (
        "vocabulary",
        "code",
        "parent",
        "label_en",
        "label_ur",
        "sort_order",
        "is_active",
    )
    list_filter = ("vocabulary", "is_active")
    list_editable = ()
    search_fields = ("code", "label_en")
    ordering = ("vocabulary", "sort_order", "code")
    fields = ("vocabulary", "code", "parent", "label_en", "label_ur", "sort_order", "is_active")
    form = VocabularyOptionForm

    def get_readonly_fields(self, request, obj=None):
        return ("vocabulary", "code", "parent") if obj is not None else ()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parent":
            vocabulary = request.POST.get("vocabulary") or request.GET.get("vocabulary")
            kwargs["queryset"] = parent_queryset(vocabulary).order_by("vocabulary", "sort_order")
            kwargs["form_class"] = ParentChoiceField
            kwargs["required"] = False
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_changeform_initial_data(self, request):
        # ?vocabulary=<list> preselects the list on the add page (and narrows the parents).
        initial = super().get_changeform_initial_data(request)
        if request.GET.get("vocabulary"):
            initial["vocabulary"] = request.GET["vocabulary"]
        return initial

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
