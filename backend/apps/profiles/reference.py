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
  until an administrator activates it. The identity lists (religion, denomination, caste,
  sub-caste, community) aren't proposals: their owner-approved values are seeded active by
  migrations 0005 and 0007 and are kept unchanged for the MVP (DR-2026-11-20-PA-3,
  DR-2026-11-23-K-1).
- Clients read the active options from ``GET /api/v1/profiles/vocabularies/``
  (``active_options``).
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
    # Optional sub-caste (DR-2026-11-20-O-5); an option may name a parent caste.
    "sub_caste": True,
    # Optional, per-religion tradition or denomination (DR-2026-11-19-O-4). Each option has a
    # religion option as its parent; no common structure is assumed across religions.
    "denomination": True,
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

# Proposals for owner review, seeded INACTIVE (migration 0004 holds its own copy). Owner-approved
# lists are activated by later migrations: gender, marital status, religion (0005) and
# employment status (0006, KI-37; NOT_EMPLOYED stays an inactive proposal).
OWNER_ACTIVATED = ("gender", "marital_status", "religion", "employment_status")

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

# Vocabulary-backed profile fields. Only those listed in ``settings.PROFILE_REQUIRED_FIELDS``
# need a configured list before submission (``services.completion``); the five identity fields
# are optional (DR-2026-11-20-P-1).
FIELD_VOCABULARY = {
    "basic_info.gender": "gender",
    "basic_info.marital_status": "marital_status",
    "basic_info.religion": "religion",
    "basic_info.community": "community",
    "basic_info.caste": "caste",
    "basic_info.sub_caste": "sub_caste",
    "basic_info.denomination": "denomination",
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


# Fields whose answer may be the privacy response "prefer not to say" (DR-2026-11-19-O-6).
# It is stored as ``<field>_prefer_not_to_say = True`` with the value NULL, never as a code.
PRIVACY_CHOICE_FIELDS = ("religion", "denomination", "community", "caste", "sub_caste")


def parent_code(vocabulary: str, code: str) -> str | None:
    """The parent option's code (a sub-caste's caste), or None."""
    from .models import VocabularyOption

    return (
        VocabularyOption.objects.filter(vocabulary=vocabulary, code=code)
        .values_list("parent__code", flat=True)
        .first()
    )


def denomination_parent(code: str) -> str | None:
    """The religion code a denomination option belongs to."""
    from .models import VocabularyOption

    return (
        VocabularyOption.objects.filter(vocabulary="denomination", code=code)
        .values_list("parent__code", flat=True)
        .first()
    )


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


def active_options() -> dict[str, list[dict]]:
    """Every vocabulary (in ``VOCABULARIES`` order) with its active options in display order,
    exactly the values the profile services accept as new choices. A list with no active option
    is returned empty."""
    from .models import VocabularyOption

    grouped: dict[str, list[dict]] = {name: [] for name in VOCABULARIES}
    rows = (
        VocabularyOption.objects.filter(is_active=True, vocabulary__in=list(VOCABULARIES))
        .order_by("vocabulary", "sort_order", "code")
        .values("vocabulary", "code", "label_en", "label_ur", "parent__vocabulary", "parent__code")
    )
    for row in rows:
        parent = (
            {"vocabulary": row["parent__vocabulary"], "code": row["parent__code"]}
            if row["parent__code"] is not None
            else None
        )
        grouped[row["vocabulary"]].append(
            {
                "code": row["code"],
                "label_en": row["label_en"],
                "label_ur": row["label_ur"],
                "parent": parent,
            }
        )
    return grouped


# Neutral notices that clients show beside a field (KI44-1, DR-2026-11-23-K-2). English only
# until Urdu translations are approved (deferred, DR-2026-11-23-K-1).
NOTICES: dict[str, str] = {
    "sub_caste": (
        "Sharing a sub-caste is optional. A sub-caste can show your caste and may suggest your "
        "family or religious background. If you chose not to share your caste, you can't pick "
        "a sub-caste that names one."
    ),
}
