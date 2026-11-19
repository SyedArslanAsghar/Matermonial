"""Create, edit and submit the caller's own profile (FR-PRO-001…004, 009…013; doc 15 §2).

Rules:
- One personal profile per account (unique ``owner``; a race ends in the same 409).
- Creating a profile needs an active, phone-verified account. This is the stricter reading of
  FR-008 / FR-PRO-001, and it is compatible with OD-02a (OPEN) as proposed.
- The date of birth must make the person 18 or older and can't be in the future [DECIDED].
  An under-age date is rejected and not stored. Its further handling (generic message, security
  event) is OD-04b (OPEN) and isn't implemented.
- Value-list fields accept active controlled-vocabulary codes (``reference.py``); a code already
  stored stays valid after it is deactivated. Countries, currencies and languages are ISO codes.
- Submission is refused while a vocabulary behind a required field has no active option.
- Education and profession stay editable whatever the verification state (FR-PRO-004). No field
  is identity-locked yet: which fields are locked is OD-04a (OPEN, FR-PRO-005 BLOCKED).
- A CLOSED profile can't be edited through an ordinary endpoint; a SUSPENDED one can't change its
  visibility (doc 15 §2).
- Completion is recomputed in the same transaction as every change.
- Lock order (doc 12 §5): the acting User FOR SHARE (level 2), then the profile FOR UPDATE
  (level 3, the state anchor), then section writes (level 8).

Phase 3 serves only the owner. Manager access (ActorContext, TR-02) arrives with Phase 4, and
viewing other profiles with Phase 8.
"""

import secrets
from datetime import date

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, ValidationError

from apps.accounts.models import User
from apps.accounts.services.pseudonyms import create_subject, pseudonym_for
from apps.audit.services import record_audit
from common.db.locking import LockLevel, lock_plan, lock_rows_for_share, lock_rows_for_update

from .. import reference
from ..models import (
    MatrimonialProfile,
    ProfileBasicInfo,
    ProfileEducation,
    ProfileFamilyDetails,
    ProfileLanguage,
    ProfileLifestyle,
    ProfileLocation,
    ProfileProfession,
)
from .completion import (
    completion_percentage,
    missing_required,
    unconfigured_required_vocabularies,
)

ADULT_AGE = 18
CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

SINGLE_SECTIONS = {
    "basic_info": ProfileBasicInfo,
    "location": ProfileLocation,
    "family": ProfileFamilyDetails,
    "profession": ProfileProfession,
    "lifestyle": ProfileLifestyle,
}
# field -> value list (reference.py) for every code field
CODE_FIELDS = {
    "basic_info": {
        "gender": "gender",
        "marital_status": "marital_status",
        "religion": "religion",
        "community": "community",
        "caste_or_subcast": "caste",
        "denomination": "denomination",
    },
    "location": {"residence_type": "residence_type"},
    "family": {"family_type": "family_type", "family_values": "family_values"},
    "profession": {
        "employment_status": "employment_status",
        "income_frequency": "income_frequency",
    },
    "lifestyle": {
        "diet": "diet",
        "smoking_status": "smoking_status",
        "drinking_status": "drinking_status",
        "exercise_habit": "exercise_habit",
    },
    "languages": {"proficiency": "proficiency"},
}
COUNTRY_FIELDS = {"basic_info": ["nationality"], "location": ["country"], "education": ["country"]}


class ProfileExists(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "profile_exists"
    default_detail = "This account already has a personal profile."


class PhoneVerificationRequired(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "phone_verification_required"
    default_detail = "Verify your phone number before creating a profile."


class InvalidProfileState(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "invalid_profile_state"
    default_detail = "This action isn't possible in the profile's current state."


class VocabularyNotConfigured(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "vocabulary_not_configured"
    default_detail = (
        "Profile submission isn't available yet: required value lists aren't configured."
    )


class ProfileIncomplete(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "profile_incomplete"
    default_detail = "Complete the required profile fields first."


# --- Reads ---------------------------------------------------------------------------------


def own_profile(user) -> MatrimonialProfile:
    profile = MatrimonialProfile.objects.filter(owner_id=user.pk).first()
    if profile is None:
        raise NotFound()
    return profile


def own_profile_by_id(user, profile_id) -> MatrimonialProfile:
    """A profile ID in the URL never establishes ownership (doc 04 §3): anything other than the
    caller's own profile gets the same 404 as a missing one."""
    profile = MatrimonialProfile.objects.filter(pk=profile_id, owner_id=user.pk).first()
    if profile is None:
        raise NotFound()
    return profile


def age_on(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


# --- Create --------------------------------------------------------------------------------


def _new_code() -> str:
    return "MP" + "".join(secrets.choice(CROCKFORD) for _ in range(8))


def create_profile(user: User, request_id=None) -> MatrimonialProfile:
    if not user.is_active:
        raise APIException("This account can't be used right now.", "account_unavailable")
    if not user.is_phone_verified:
        raise PhoneVerificationRequired()
    for _ in range(5):
        try:
            with (
                transaction.atomic(),
                lock_plan("profiles.create", [LockLevel.ACCOUNT, LockLevel.INSERT]),
            ):
                lock_rows_for_share(User.objects.filter(pk=user.pk), LockLevel.ACCOUNT)
                if MatrimonialProfile.objects.filter(owner_id=user.pk).exists():
                    raise ProfileExists()
                profile = MatrimonialProfile.objects.create(
                    owner=user, profile_code=_new_code(), created_by=user, updated_by=user
                )
                pseudonym = create_subject("PROFILE", profile.id).pseudonym
                record_audit(
                    action="profile.created",
                    resource_type="profiles.profile",
                    actor_type="USER",
                    result="SUCCESS",
                    category="STATE_CHANGE",
                    actor_user_id=user.pk,
                    subject_user_id=user.pk,
                    represented_profile_pseudonym=pseudonym,
                    request_id=request_id,
                )
                return profile
        except IntegrityError as exc:
            if MatrimonialProfile.objects.filter(owner_id=user.pk).exists():
                raise ProfileExists() from None  # a concurrent create won
            if "profile_code" not in str(exc):
                raise
            # profile_code collision (2^40 space): retry with a new code
    raise APIException("Please retry.", "temporarily_unavailable")


# --- Update --------------------------------------------------------------------------------


def _check_codes(section: str, values: dict, errors: dict, prefix: str = "", current=None) -> None:
    for field, list_name in CODE_FIELDS.get(section, {}).items():
        value = values.get(field)
        stored = getattr(current, field, None) if current is not None else None
        if value is not None and not reference.is_allowed(list_name, value, current=stored):
            errors[f"{prefix}{field}"] = [reference.choice_error(list_name)]
    for field in COUNTRY_FIELDS.get(section, []):
        value = values.get(field)
        if value is not None and not reference.COUNTRY.fullmatch(value):
            errors[f"{prefix}{field}"] = ["Use an ISO 3166-1 alpha-2 country code."]


def _normalise_privacy_choices(values: dict, errors: dict) -> None:
    """ "Prefer not to say" is a flag beside the value (DR-2026-11-19-O-6): choosing it clears the
    value; giving a value clears the flag; both at once is an error."""
    for field in reference.PRIVACY_CHOICE_FIELDS:
        flag = f"{field}_prefer_not_to_say"
        if values.get(flag) is True:
            if values.get(field) is not None:
                errors[field] = ["Give a value or choose prefer not to say, not both."]
            values[field] = None
        elif values.get(field) is not None:
            values[flag] = False
    # Withholding the religion also withholds the denomination, which would reveal it.
    if values.get("religion_prefer_not_to_say") is True:
        values["denomination"] = None


def _check_denomination(values: dict, current, errors: dict) -> None:
    religion = values.get("religion", getattr(current, "religion", None))
    denomination = values.get("denomination", getattr(current, "denomination", None))
    if denomination is None:
        return
    if religion is None:
        errors["denomination"] = ["Choose a religion before a denomination or tradition."]
    elif reference.denomination_parent(denomination) != religion:
        errors["denomination"] = ["This denomination or tradition doesn't belong to the religion."]


def _check_section(section: str, values: dict, current, today: date) -> dict:
    errors: dict = {}
    if section == "basic_info":
        _normalise_privacy_choices(values, errors)
        _check_denomination(values, current, errors)
    _check_codes(section, values, errors, current=current)
    if section == "basic_info" and values.get("date_of_birth") is not None:
        dob = values["date_of_birth"]
        if dob > today or age_on(dob, today) < ADULT_AGE:
            # Not stored; deliberately no detail about why (OD-04b handling is OPEN).
            errors["date_of_birth"] = ["Enter a valid date of birth."]
    if section == "profession":
        merged = {
            f: values.get(f, getattr(current, f, None) if current else None)
            for f in ("income_amount", "income_currency", "income_frequency")
        }
        currency = merged["income_currency"]
        if currency is not None and not reference.CURRENCY.fullmatch(currency):
            errors["income_currency"] = ["Use an ISO 4217 currency code."]
        if merged["income_amount"] is not None and (
            merged["income_currency"] is None or merged["income_frequency"] is None
        ):
            errors["income_amount"] = ["Give the currency and frequency with the income."]
    return errors


def _check_list(section: str, rows: list[dict]) -> dict:
    errors: dict = {}
    for index, row in enumerate(rows):
        _check_codes(section, row, errors, prefix=f"{index}.")
        if section == "languages" and not reference.LANGUAGE.fullmatch(row.get("language", "")):
            errors[f"{index}.language"] = ["Use an ISO 639 language code."]
    if section == "languages":
        codes = [row.get("language") for row in rows]
        if len(codes) != len(set(codes)):
            errors["non_field_errors"] = ["Each language can be listed once."]
    return errors


def update_profile(user: User, data: dict, request_id=None) -> MatrimonialProfile:
    """Apply a validated partial update. ``data`` may hold ``visibility_status``, any single
    section as a dict of fields, and ``languages`` / ``education`` as complete replacement lists.
    """
    today = timezone.now().date()
    with (
        transaction.atomic(),
        lock_plan("profiles.update", [LockLevel.ACCOUNT, LockLevel.PROFILE, LockLevel.INSERT]),
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

        errors: dict = {}
        for section, model in SINGLE_SECTIONS.items():
            if section in data:
                current = model.objects.filter(profile=profile).first()
                section_errors = _check_section(section, data[section], current, today)
                if section_errors:
                    errors[section] = section_errors
        for section in ("languages", "education"):
            if section in data:
                section_errors = _check_list(section, data[section])
                if section_errors:
                    errors[section] = section_errors
        if "visibility_status" in data and profile.profile_status == "SUSPENDED":
            errors["visibility_status"] = [
                "Visibility can't change while the profile is suspended."
            ]
        if errors:
            raise ValidationError(errors)

        for section, model in SINGLE_SECTIONS.items():
            if section in data:
                model.objects.update_or_create(profile=profile, defaults=data[section])
        if "languages" in data:
            profile.languages.all().delete()
            ProfileLanguage.objects.bulk_create(
                ProfileLanguage(profile=profile, **row) for row in data["languages"]
            )
        if "education" in data:
            profile.education.all().delete()
            ProfileEducation.objects.bulk_create(
                ProfileEducation(profile=profile, position=i, **row)
                for i, row in enumerate(data["education"])
            )
        if "visibility_status" in data:
            profile.visibility_status = data["visibility_status"]
        profile.completion_percentage = completion_percentage(profile)
        profile.updated_by = user
        profile.save(
            update_fields=["visibility_status", "completion_percentage", "updated_by", "updated_at"]
        )
    return profile


# --- Lifecycle -----------------------------------------------------------------------------


def submit_for_review(user: User, profile_id, request_id=None) -> MatrimonialProfile:
    """DRAFT → PENDING_REVIEW when the required fields are complete (doc 15 §2). Activation
    (PENDING_REVIEW → ACTIVE) needs identity approval and review: Phases 5 and 14 (OD-03e)."""
    own_profile_by_id(user, profile_id)  # identical 404 for anything else
    with transaction.atomic(), lock_plan("profiles.submit", [LockLevel.ACCOUNT, LockLevel.PROFILE]):
        lock_rows_for_share(User.objects.filter(pk=user.pk), LockLevel.ACCOUNT)
        profile = lock_rows_for_update(
            MatrimonialProfile.objects.filter(pk=profile_id, owner_id=user.pk),
            LockLevel.PROFILE,
            anchor=True,
        )[0]
        if profile.profile_status != MatrimonialProfile.Status.DRAFT:
            raise InvalidProfileState()
        if unconfigured_required_vocabularies():
            raise VocabularyNotConfigured()
        if missing_required(profile):
            raise ProfileIncomplete()  # GET .../completion/ lists what is missing
        profile.profile_status = MatrimonialProfile.Status.PENDING_REVIEW
        profile.submitted_at = timezone.now()
        profile.updated_by = user
        profile.save(update_fields=["profile_status", "submitted_at", "updated_by", "updated_at"])
        record_audit(
            action="profile.submitted_for_review",
            resource_type="profiles.profile",
            actor_type="USER",
            result="SUCCESS",
            category="STATE_CHANGE",
            actor_user_id=user.pk,
            subject_user_id=user.pk,
            represented_profile_pseudonym=pseudonym_for("PROFILE", profile.id),
            request_id=request_id,
            metadata={"from_status": "DRAFT", "to_status": "PENDING_REVIEW"},
        )
    return profile
