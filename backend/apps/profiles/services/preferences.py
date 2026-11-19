"""Partner preferences of the caller's own profile (FR-PREF-001…003; doc 03 §4; doc 04 §4).

- ``own_house``, ``job`` and ``business`` keep three states: true, false and null (no
  preference). Null is never turned into false (FR-019).
- Age bounds are 18–100 and the minimum can't exceed the maximum; the same applies to earnings,
  which also need a currency and a frequency (FR-020). Ranges are checked on the merged result,
  so a PATCH can't create an inverted range with one bound.
- Value-list fields accept active controlled-vocabulary codes; stored codes stay valid after
  deactivation (``reference.py``).
- Strict criteria (OD-10b) and matching (Phase 8) aren't implemented; preferences are stored
  as optional criteria only.
- ``replace=True`` (PUT) resets every omitted field to null and every omitted list to empty.
- Lock order: User FOR SHARE → profile FOR UPDATE → preference rows.
"""

from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.models import User
from common.db.locking import LockLevel, lock_plan, lock_rows_for_share, lock_rows_for_update

from .. import reference
from ..models import (
    MatrimonialProfile,
    PartnerPreference,
    PartnerPreferenceEducation,
    PartnerPreferenceLanguage,
    PartnerPreferenceLocation,
    PartnerPreferenceReligion,
)
from .profiles import InvalidProfileState

SCALAR_FIELDS = (
    "minimum_age",
    "maximum_age",
    "preferred_gender",
    "preferred_marital_status",
    "community",
    "caste_or_subcast",
    "nationality",
    "own_house",
    "job",
    "business",
    "minimum_earning",
    "maximum_earning",
    "earning_currency",
    "earning_frequency",
    "residence_type",
    "additional_requirements",
)
CODE_LISTS = {
    "preferred_gender": "gender",
    "preferred_marital_status": "marital_status",
    "community": "community",
    "caste_or_subcast": "caste",
    "earning_frequency": "income_frequency",
    "residence_type": "residence_type",
}
LISTS = {
    "locations": (PartnerPreferenceLocation, ("country", "state_or_province", "city")),
    "education": (PartnerPreferenceEducation, ("qualification",)),
    "languages": (PartnerPreferenceLanguage, ("language",)),
    "religions": (PartnerPreferenceReligion, ("religion",)),
}


def _code_error(list_name: str) -> str:
    return reference.choice_error(list_name)


def _validate(merged: dict, lists: dict, current=None, current_religions=frozenset()) -> dict:
    errors: dict = {}
    for field, list_name in CODE_LISTS.items():
        stored = getattr(current, field, None) if current is not None else None
        if not reference.is_allowed(list_name, merged.get(field), current=stored):
            errors[field] = [_code_error(list_name)]
    if merged.get("nationality") and not reference.COUNTRY.fullmatch(merged["nationality"]):
        errors["nationality"] = ["Use an ISO 3166-1 alpha-2 country code."]
    currency = merged.get("earning_currency")
    if currency and not reference.CURRENCY.fullmatch(currency):
        errors["earning_currency"] = ["Use an ISO 4217 currency code."]
    for field in ("minimum_age", "maximum_age"):
        value = merged.get(field)
        if value is not None and not 18 <= value <= 100:
            errors[field] = ["Ages must be between 18 and 100."]
    lo, hi = merged.get("minimum_age"), merged.get("maximum_age")
    if lo is not None and hi is not None and lo > hi:
        errors["minimum_age"] = ["The minimum age can't exceed the maximum age."]
    lo, hi = merged.get("minimum_earning"), merged.get("maximum_earning")
    if lo is not None and hi is not None and lo > hi:
        errors["minimum_earning"] = ["The minimum earning can't exceed the maximum earning."]
    if (lo is not None or hi is not None) and not (currency and merged.get("earning_frequency")):
        errors["earning_currency"] = ["Give the currency and frequency with an earning range."]

    for name, rows in lists.items():
        keys = [tuple(row.get(f) for f in LISTS[name][1]) for row in rows]
        if len(keys) != len(set(keys)):
            errors[name] = ["Each entry can be listed once."]
        for i, row in enumerate(rows):
            if name == "locations" and not reference.COUNTRY.fullmatch(row.get("country") or ""):
                errors[f"{name}.{i}.country"] = ["Use an ISO 3166-1 alpha-2 country code."]
            if name == "languages" and not reference.LANGUAGE.fullmatch(row.get("language") or ""):
                errors[f"{name}.{i}.language"] = ["Use an ISO 639 language code."]
            religion = row.get("religion")
            if (
                name == "religions"
                and religion not in current_religions
                and not reference.is_allowed("religion", religion)
            ):
                errors[f"{name}.{i}.religion"] = [_code_error("religion")]
    return errors


def get_preferences(user: User) -> PartnerPreference | None:
    profile = MatrimonialProfile.objects.filter(owner_id=user.pk).first()
    if profile is None:
        raise NotFound()
    return PartnerPreference.objects.filter(profile=profile).first()


def save_preferences(user: User, data: dict, *, replace: bool) -> PartnerPreference:
    with (
        transaction.atomic(),
        lock_plan("profiles.preferences", [LockLevel.ACCOUNT, LockLevel.PROFILE, LockLevel.INSERT]),
    ):
        lock_rows_for_share(User.objects.filter(pk=user.pk), LockLevel.ACCOUNT)
        locked = lock_rows_for_update(
            MatrimonialProfile.objects.filter(owner_id=user.pk), LockLevel.PROFILE, anchor=True
        )
        if not locked:
            raise NotFound()
        profile = locked[0]
        if profile.profile_status == MatrimonialProfile.Status.CLOSED:
            raise InvalidProfileState()
        current = PartnerPreference.objects.filter(profile=profile).first()

        scalars = {f: data[f] for f in SCALAR_FIELDS if f in data}
        if replace:
            merged = {f: scalars.get(f) for f in SCALAR_FIELDS}
        else:
            merged = {f: scalars.get(f, getattr(current, f, None)) for f in SCALAR_FIELDS}
        lists = {
            name: data.get(name, [] if replace else None)
            for name in LISTS
            if replace or name in data
        }
        kept = (
            frozenset(current.religions.values_list("religion", flat=True))
            if current
            else frozenset()
        )
        errors = _validate(merged, {k: v for k, v in lists.items() if v is not None}, current, kept)
        if errors:
            raise ValidationError(errors)

        preference, _ = PartnerPreference.objects.update_or_create(profile=profile, defaults=merged)
        for name, rows in lists.items():
            model, fields = LISTS[name]
            model.objects.filter(preference=preference).delete()
            model.objects.bulk_create(
                model(preference=preference, **{f: row.get(f) for f in fields}) for row in rows
            )
        profile.updated_by = user
        profile.save(update_fields=["updated_by", "updated_at"])
    return preference
