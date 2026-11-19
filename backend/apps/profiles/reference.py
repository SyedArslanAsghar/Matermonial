"""Controlled vocabularies for profile and preference fields (DR-2026-11-19-P3-2, revised by
the owner's Phase 2/3 review on 2026-11-19).

- Options live in ``VocabularyOption`` rows, managed in the Django Admin by holders of
  ``profiles.change_vocabularyoption`` (audited). Adding, relabelling, reordering or deactivating
  an option needs no code change.
- ``code`` is the stable identifier stored on profiles; labels are display only, so relabelling
  never touches profile data. Codes can't be renamed or deleted (database trigger, migration
  0004). A deactivated option stays valid on rows that already hold it, but can't be chosen for
  a new value.
- Only *which* vocabularies exist is code (``VOCABULARIES``), because each backs a model field.
- Proposed options are seeded **inactive** for owner review (``PROPOSED``); nothing is offered
  until an administrator activates it. No religion, community or caste value is proposed.
"""

import re

COUNTRY = re.compile(r"^[A-Z]{2}$")  # ISO 3166-1 alpha-2
CURRENCY = re.compile(r"^[A-Z]{3}$")  # ISO 4217
LANGUAGE = re.compile(r"^[a-z]{2,3}$")  # ISO 639-1 / 639-2

# name -> identity-sensitive?
VOCABULARIES: dict[str, bool] = {
    "gender": True,
    "marital_status": True,
    "religion": True,
    "community": True,
    "caste": True,
    "residence_type": False,
    "family_type": False,
    "family_values": False,
    "employment_status": False,
    "income_frequency": False,
    "diet": False,
    "smoking_status": False,
    "drinking_status": False,
    "exercise_habit": False,
    "proficiency": False,
    "photo_type": False,
}

# Proposals for owner review, seeded INACTIVE (migration 0004 holds its own copy).
PROPOSED: dict[str, tuple[str, ...]] = {
    "gender": ("FEMALE", "MALE"),
    "marital_status": ("NEVER_MARRIED", "DIVORCED", "WIDOWED", "SEPARATED"),
    "residence_type": ("OWN_HOUSE", "RENTED", "FAMILY_HOME", "COMPANY_PROVIDED", "OTHER"),
    "family_type": ("NUCLEAR", "JOINT", "OTHER"),
    "family_values": ("TRADITIONAL", "MODERATE", "LIBERAL"),
    "employment_status": (
        "EMPLOYED",
        "SELF_EMPLOYED",
        "BUSINESS_OWNER",
        "STUDENT",
        "NOT_EMPLOYED",
        "RETIRED",
    ),
    "income_frequency": ("WEEKLY", "MONTHLY", "ANNUAL"),
    "diet": ("VEGETARIAN", "NON_VEGETARIAN", "VEGAN", "OTHER"),
    "smoking_status": ("NO", "OCCASIONALLY", "YES"),
    "drinking_status": ("NO", "OCCASIONALLY", "YES"),
    "exercise_habit": ("NEVER", "SOMETIMES", "REGULARLY"),
    "proficiency": ("BASIC", "CONVERSATIONAL", "FLUENT", "NATIVE"),
    "photo_type": ("PORTRAIT", "FULL_LENGTH", "OTHER"),
}

# Required profile fields that are vocabulary-backed: submission needs each configured.
FIELD_VOCABULARY = {
    "basic_info.gender": "gender",
    "basic_info.marital_status": "marital_status",
    "basic_info.religion": "religion",
    "basic_info.community": "community",
    "basic_info.caste_or_subcast": "caste",
    "profession.employment_status": "employment_status",
}


def allowed(vocabulary: str) -> tuple[str, ...]:
    """Active codes, in display order."""
    from .models import VocabularyOption

    return tuple(
        VocabularyOption.objects.filter(vocabulary=vocabulary, is_active=True)
        .order_by("sort_order", "code")
        .values_list("code", flat=True)
    )


def is_allowed(vocabulary: str, value: str | None, current: str | None = None) -> bool:
    """None, the value already stored (``current``), or an active option."""
    if value is None or value == current:
        return True
    from .models import VocabularyOption

    return VocabularyOption.objects.filter(
        vocabulary=vocabulary, code=value, is_active=True
    ).exists()


def choice_error(vocabulary: str) -> str:
    codes = allowed(vocabulary)
    if not codes:
        return "This field can't be set yet: its value list hasn't been configured."
    return f"Choose one of: {', '.join(codes)}."


def unconfigured(vocabularies) -> list[str]:
    """Vocabularies with no active option."""
    from .models import VocabularyOption

    active = set(
        VocabularyOption.objects.filter(
            vocabulary__in=list(vocabularies), is_active=True
        ).values_list("vocabulary", flat=True)
    )
    return sorted(set(vocabularies) - active)
