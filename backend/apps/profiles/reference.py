"""Code-defined value lists for profile and preference fields (DR-2026-11-19-P3-2).

The approved documents define no value lists. Following the owner decision:
- **Neutral lists** below are seeded as documented assumptions (doc 13; owner review).
- **Identity-sensitive lists** (gender, marital status, religion, community, caste) are **empty
  until the owner supplies or approves them**. An empty list accepts no value, so those fields
  stay unset and a profile can't be submitted for review until the lists exist.

Values are stable upper-case codes; display labels (English and Urdu) belong to the clients.
Changing a list is a reviewed code change. Stored codes are never deleted from the database when
a list changes; a retired code simply stops being accepted for new writes.
"""

import re

SENSITIVE: dict[str, tuple[str, ...]] = {
    # Owner-supplied (DR-2026-11-19-P3-2). Intentionally empty.
    "gender": (),
    "marital_status": (),
    "religion": (),
    "community": (),
    "caste": (),
}

NEUTRAL: dict[str, tuple[str, ...]] = {
    # Assumptions pending owner review (doc 13).
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
}

LISTS = {**SENSITIVE, **NEUTRAL}

COUNTRY = re.compile(r"^[A-Z]{2}$")  # ISO 3166-1 alpha-2
CURRENCY = re.compile(r"^[A-Z]{3}$")  # ISO 4217
LANGUAGE = re.compile(r"^[a-z]{2,3}$")  # ISO 639-1 / 639-2


def allowed(list_name: str) -> tuple[str, ...]:
    return LISTS[list_name]


def is_allowed(list_name: str, value: str | None) -> bool:
    return value is None or value in LISTS[list_name]
