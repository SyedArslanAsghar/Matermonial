"""Profile completion from defined fields, computed by the backend (FR-008; doc 03 §22.1 row 16).

The required set gates DRAFT → PENDING_REVIEW (doc 15 §2). It is configurable
(``PROFILE_REQUIRED_FIELDS`` / ``PROFILE_OPTIONAL_FIELDS``); the defaults are the owner-approved
baseline (DR-2026-11-19-O-7), with religion made optional by DR-2026-11-20-P-1. Religion,
denomination, caste, sub-caste and community never count toward completion, so the percentage
never pressures anyone to disclose them. Photos join the set when the upload
pipeline exists (TR-10). Items are ``"<section>.<field>"`` or a list section name ("languages",
"education"), which counts as filled when it has at least one row.
"""

from django.conf import settings

LIST_SECTIONS = {"languages", "education"}


def _filled(profile, item: str) -> bool:
    if item in LIST_SECTIONS:
        return getattr(profile, item).exists()
    section_name, field = item.split(".", 1)
    section = getattr(profile, section_name, None)
    if section is None:
        return False
    value = getattr(section, field)
    # "Prefer not to say" answers the question (DR-2026-11-19-O-6).
    if getattr(section, f"{field}_prefer_not_to_say", False):
        return True
    return value not in (None, "")


def _sections(profile):
    # Reverse one-to-one accessors raise when the row doesn't exist; normalise to None.
    from django.core.exceptions import ObjectDoesNotExist

    class View:
        def __getattr__(self, name):
            try:
                return getattr(profile, name)
            except ObjectDoesNotExist:
                return None

    return View()


def missing_required(profile) -> list[str]:
    view = _sections(profile)
    return [item for item in settings.PROFILE_REQUIRED_FIELDS if not _filled(view, item)]


def completion_percentage(profile) -> int:
    view = _sections(profile)
    items = [*settings.PROFILE_REQUIRED_FIELDS, *settings.PROFILE_OPTIONAL_FIELDS]
    if not items:
        return 100
    done = sum(1 for item in items if _filled(view, item))
    return (100 * done) // len(items)


def unconfigured_required_vocabularies() -> list[str]:
    """Vocabularies behind required fields that have no active option (submission blocked)."""
    from .. import reference

    needed = {
        reference.FIELD_VOCABULARY[item]
        for item in settings.PROFILE_REQUIRED_FIELDS
        if item in reference.FIELD_VOCABULARY
    }
    return reference.unconfigured(needed)
