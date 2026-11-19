"""Matrimonial profile and its sections (doc 03 §3, §22.3; FR-PRO-001…013; doc 15 §2).

- One personal profile per account: ``owner`` is unique (database constraint) [DECIDED].
- Lifecycle (``profile_status``) and visibility are separate fields [DECIDED, FR-PRO-006/009].
- The full date of birth is private: only the owner's own endpoint returns it (FR-PRO-003).
- Income uses Decimal with an explicit currency and frequency (FR-PRO-011, CC-R33).
- Value-list fields store codes from ``reference.py``; the database checks formats, not values,
  because the lists are reviewed code (DR-2026-11-19-P3-2).
- Every FK to the account uses PROTECT (TR-09 F4); section rows go with their profile only
  through the deletion job (Phase 15), never through an ordinary endpoint.
"""

import uuid

from django.db import models
from django.db.models import Q

CODE = r"^[A-Z][A-Z0-9_]{0,39}$"
COUNTRY = r"^[A-Z]{2}$"


def code_field(**kwargs):
    return models.CharField(max_length=40, null=True, blank=True, **kwargs)


def code_check(field: str, name: str) -> models.CheckConstraint:
    return models.CheckConstraint(
        condition=Q(**{f"{field}__isnull": True}) | Q(**{f"{field}__regex": CODE}), name=name
    )


def country_check(field: str, name: str) -> models.CheckConstraint:
    return models.CheckConstraint(
        condition=Q(**{f"{field}__isnull": True}) | Q(**{f"{field}__regex": COUNTRY}), name=name
    )


class MatrimonialProfile(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        PENDING_REVIEW = "PENDING_REVIEW"
        ACTIVE = "ACTIVE"
        PAUSED = "PAUSED"
        SUSPENDED = "SUSPENDED"
        CLOSED = "CLOSED"

    class Visibility(models.TextChoices):
        HIDDEN = "HIDDEN"
        VISIBLE_IN_MATCH_SEARCH = "VISIBLE_IN_MATCH_SEARCH"
        LIMITED_VISIBILITY = "LIMITED_VISIBILITY"  # "visible after acceptance" (OD-03b OPEN)

    class VerificationStatus(models.TextChoices):  # written by identity verification (Phase 5)
        NOT_SUBMITTED = "NOT_SUBMITTED"
        PENDING_REVIEW = "PENDING_REVIEW"
        UNDER_REVIEW = "UNDER_REVIEW"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"
        RESUBMISSION_REQUIRED = "RESUBMISSION_REQUIRED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.OneToOneField(
        "accounts.User", on_delete=models.PROTECT, related_name="personal_profile"
    )
    profile_code = models.CharField(max_length=12, unique=True)
    profile_status = models.CharField(max_length=14, choices=Status.choices, default=Status.DRAFT)
    suspended_from_status = models.CharField(
        max_length=14, null=True, blank=True, choices=Status.choices
    )
    visibility_status = models.CharField(
        max_length=23, choices=Visibility.choices, default=Visibility.HIDDEN
    )
    verification_status = models.CharField(
        max_length=21, choices=VerificationStatus.choices, default=VerificationStatus.NOT_SUBMITTED
    )
    completion_percentage = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="profiles_created"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="profiles_updated"
    )

    class Meta:
        db_table = "profiles_profile"
        indexes = [models.Index(fields=["profile_status", "visibility_status"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(completion_percentage__lte=100), name="profile_completion_range"
            ),
            models.CheckConstraint(
                condition=Q(profile_code__regex=r"^MP[0-9A-HJKMNP-TV-Z]{8}$"),
                name="profile_code_format",
            ),
            # is_active mirrors ACTIVE so it can never drift from the lifecycle.
            models.CheckConstraint(
                condition=Q(is_active=True, profile_status="ACTIVE")
                | (Q(is_active=False) & ~Q(profile_status="ACTIVE")),
                name="profile_is_active_matches_status",
            ),
            # suspended_from_status is set exactly while SUSPENDED (doc 15 §2).
            models.CheckConstraint(
                condition=Q(
                    profile_status="SUSPENDED", suspended_from_status__in=["ACTIVE", "PAUSED"]
                )
                | (~Q(profile_status="SUSPENDED") & Q(suspended_from_status__isnull=True)),
                name="profile_suspended_from_consistent",
            ),
        ]

    def __str__(self):
        return self.profile_code


class ProfileBasicInfo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.OneToOneField(
        MatrimonialProfile, on_delete=models.PROTECT, related_name="basic_info"
    )
    full_name = models.CharField(max_length=150, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)  # private (FR-PRO-003)
    gender = code_field()
    marital_status = code_field()
    religion = code_field()
    community = code_field()
    caste_or_subcast = code_field()
    nationality = models.CharField(max_length=2, null=True, blank=True)

    class Meta:
        db_table = "profiles_basic_info"
        constraints = [
            code_check("gender", "basic_gender_code"),
            code_check("marital_status", "basic_marital_code"),
            code_check("religion", "basic_religion_code"),
            code_check("community", "basic_community_code"),
            code_check("caste_or_subcast", "basic_caste_code"),
            country_check("nationality", "basic_nationality_iso"),
            models.CheckConstraint(
                condition=Q(date_of_birth__isnull=True) | Q(date_of_birth__gte="1900-01-01"),
                name="basic_dob_plausible",
            ),
        ]


class ProfileLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.OneToOneField(
        MatrimonialProfile, on_delete=models.PROTECT, related_name="location"
    )
    country = models.CharField(max_length=2, null=True, blank=True)  # residence, not nationality
    state_or_province = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    area_or_locality = models.CharField(max_length=100, null=True, blank=True)
    residence_type = code_field()
    show_location = models.BooleanField(default=False)

    class Meta:
        db_table = "profiles_location"
        constraints = [
            country_check("country", "location_country_iso"),
            code_check("residence_type", "location_residence_code"),
        ]


class ProfileFamilyDetails(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.OneToOneField(
        MatrimonialProfile, on_delete=models.PROTECT, related_name="family"
    )
    father_occupation = models.CharField(max_length=100, null=True, blank=True)
    mother_occupation = models.CharField(max_length=100, null=True, blank=True)
    family_type = code_field()
    family_values = code_field()
    number_of_brothers = models.PositiveSmallIntegerField(null=True, blank=True)
    number_of_sisters = models.PositiveSmallIntegerField(null=True, blank=True)
    family_description = models.TextField(max_length=2000, null=True, blank=True)

    class Meta:
        db_table = "profiles_family"
        constraints = [
            code_check("family_type", "family_type_code"),
            code_check("family_values", "family_values_code"),
            models.CheckConstraint(
                condition=(Q(number_of_brothers__isnull=True) | Q(number_of_brothers__lte=30))
                & (Q(number_of_sisters__isnull=True) | Q(number_of_sisters__lte=30)),
                name="family_sibling_range",
            ),
        ]


class ProfileEducation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        MatrimonialProfile, on_delete=models.PROTECT, related_name="education"
    )
    qualification = models.CharField(max_length=150)
    field_of_study = models.CharField(max_length=150, null=True, blank=True)
    institution = models.CharField(max_length=200, null=True, blank=True)
    country = models.CharField(max_length=2, null=True, blank=True)
    completion_year = models.PositiveSmallIntegerField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(max_length=2000, null=True, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "profiles_education"
        ordering = ["position"]
        constraints = [
            country_check("country", "education_country_iso"),
            models.CheckConstraint(
                condition=Q(completion_year__isnull=True)
                | Q(completion_year__gte=1940, completion_year__lte=2100),
                name="education_year_range",
            ),
        ]


class ProfileProfession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.OneToOneField(
        MatrimonialProfile, on_delete=models.PROTECT, related_name="profession"
    )
    employment_status = code_field()
    profession = models.CharField(max_length=100, null=True, blank=True)
    job_title = models.CharField(max_length=100, null=True, blank=True)
    employer_or_business_name = models.CharField(max_length=150, null=True, blank=True)
    income_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    income_currency = models.CharField(max_length=3, null=True, blank=True)
    income_frequency = code_field()
    show_income = models.BooleanField(default=False)
    description = models.TextField(max_length=2000, null=True, blank=True)

    class Meta:
        db_table = "profiles_profession"
        constraints = [
            code_check("employment_status", "profession_employment_code"),
            code_check("income_frequency", "profession_frequency_code"),
            models.CheckConstraint(
                condition=Q(income_currency__isnull=True) | Q(income_currency__regex=r"^[A-Z]{3}$"),
                name="profession_currency_iso",
            ),
            models.CheckConstraint(
                condition=Q(income_amount__isnull=True) | Q(income_amount__gte=0),
                name="profession_income_non_negative",
            ),
            # An amount is meaningless without its currency and frequency (FR-014).
            models.CheckConstraint(
                condition=Q(income_amount__isnull=True)
                | Q(income_currency__isnull=False, income_frequency__isnull=False),
                name="profession_income_has_currency_and_frequency",
            ),
        ]


class ProfileLifestyle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.OneToOneField(
        MatrimonialProfile, on_delete=models.PROTECT, related_name="lifestyle"
    )
    height_cm = models.PositiveSmallIntegerField(null=True, blank=True)
    diet = code_field()
    smoking_status = code_field()
    drinking_status = code_field()
    exercise_habit = code_field()
    description = models.TextField(max_length=2000, null=True, blank=True)

    class Meta:
        db_table = "profiles_lifestyle"
        constraints = [
            models.CheckConstraint(
                condition=Q(height_cm__isnull=True) | Q(height_cm__gte=90, height_cm__lte=250),
                name="lifestyle_height_range",
            ),
            code_check("diet", "lifestyle_diet_code"),
            code_check("smoking_status", "lifestyle_smoking_code"),
            code_check("drinking_status", "lifestyle_drinking_code"),
            code_check("exercise_habit", "lifestyle_exercise_code"),
        ]


class ProfileLanguage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        MatrimonialProfile, on_delete=models.PROTECT, related_name="languages"
    )
    language = models.CharField(max_length=3)
    proficiency = code_field()
    is_native = models.BooleanField(default=False)

    class Meta:
        db_table = "profiles_language"
        ordering = ["language"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "language"], name="language_unique_per_profile"
            ),
            models.CheckConstraint(
                condition=Q(language__regex=r"^[a-z]{2,3}$"), name="language_iso"
            ),
            code_check("proficiency", "language_proficiency_code"),
        ]
