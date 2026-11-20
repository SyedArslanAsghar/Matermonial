"""Profile serializers with explicit field allowlists (CC-R44).

``OwnProfileSerializer`` is used only for the owner's own profile, which is the only place the
full date of birth appears (FR-PRO-003). Representations for other viewers arrive with search
and profile detail (Phase 8) and will never include it.
"""

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from rest_framework import serializers

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
from ..services.profiles import age_on


def _code(**kw):
    return serializers.CharField(max_length=40, allow_null=True, required=False, **kw)


def _country():
    return serializers.CharField(max_length=2, min_length=2, allow_null=True, required=False)


class BasicInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileBasicInfo
        fields = [
            "full_name",
            "date_of_birth",
            "gender",
            "marital_status",
            "religion",
            "religion_prefer_not_to_say",
            "denomination",
            "denomination_prefer_not_to_say",
            "community",
            "community_prefer_not_to_say",
            "caste",
            "caste_prefer_not_to_say",
            "sub_caste",
            "sub_caste_prefer_not_to_say",
            "nationality",
        ]
        extra_kwargs = {f: {"required": False} for f in fields}


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileLocation
        fields = [
            "country",
            "state_or_province",
            "city",
            "area_or_locality",
            "residence_type",
            "show_location",
        ]
        extra_kwargs = {f: {"required": False} for f in fields}


class FamilySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileFamilyDetails
        fields = [
            "father_occupation",
            "mother_occupation",
            "family_type",
            "family_values",
            "number_of_brothers",
            "number_of_sisters",
            "family_description",
        ]
        extra_kwargs = {f: {"required": False} for f in fields}


class ProfessionSerializer(serializers.ModelSerializer):
    income_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=0,
        allow_null=True,
        required=False,
        coerce_to_string=True,
    )

    class Meta:
        model = ProfileProfession
        fields = [
            "employment_status",
            "profession",
            "job_title",
            "employer_or_business_name",
            "income_amount",
            "income_currency",
            "income_frequency",
            "show_income",
            "description",
        ]
        extra_kwargs = {f: {"required": False} for f in fields}


class LifestyleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileLifestyle
        fields = [
            "height_cm",
            "diet",
            "smoking_status",
            "drinking_status",
            "exercise_habit",
            "description",
        ]
        extra_kwargs = {f: {"required": False} for f in fields}


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileLanguage
        fields = ["language", "proficiency", "is_native"]
        validators = []  # uniqueness is checked by the service across the whole list


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileEducation
        fields = [
            "qualification",
            "field_of_study",
            "institution",
            "country",
            "completion_year",
            "is_current",
            "description",
        ]


SECTION_SERIALIZERS = {
    "basic_info": BasicInfoSerializer,
    "location": LocationSerializer,
    "family": FamilySerializer,
    "profession": ProfessionSerializer,
    "lifestyle": LifestyleSerializer,
}


class ProfileUpdateSerializer(serializers.Serializer):
    """Partial update: each section is optional; lists replace the stored rows."""

    visibility_status = serializers.ChoiceField(
        choices=MatrimonialProfile.Visibility.choices, required=False
    )
    basic_info = BasicInfoSerializer(required=False)
    location = LocationSerializer(required=False)
    family = FamilySerializer(required=False)
    profession = ProfessionSerializer(required=False)
    lifestyle = LifestyleSerializer(required=False)
    languages = LanguageSerializer(many=True, required=False, max_length=20)
    education = EducationSerializer(many=True, required=False, max_length=20)

    def validate(self, attrs):
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({k: ["Unknown field."] for k in sorted(unknown)})
        return attrs


def _section(profile, name, serializer):
    try:
        row = getattr(profile, name)
    except ObjectDoesNotExist:
        return None
    return serializer(row).data


class OwnProfileSerializer(serializers.Serializer):
    """The owner's view of their own profile (allowlisted). The declared fields document the
    output for OpenAPI (KI-40); ``to_representation`` builds it (``basic_info.date_of_birth`` is
    omitted for managers without ``edit_basic_info``)."""

    id = serializers.UUIDField(read_only=True)
    profile_code = serializers.CharField(read_only=True)
    profile_status = serializers.ChoiceField(MatrimonialProfile.Status.choices, read_only=True)
    visibility_status = serializers.ChoiceField(
        MatrimonialProfile.Visibility.choices, read_only=True
    )
    verification_status = serializers.ChoiceField(
        MatrimonialProfile.VerificationStatus.choices, read_only=True
    )
    completion_percentage = serializers.IntegerField(read_only=True)
    age = serializers.IntegerField(read_only=True, allow_null=True)
    basic_info = BasicInfoSerializer(read_only=True, allow_null=True)
    location = LocationSerializer(read_only=True, allow_null=True)
    family = FamilySerializer(read_only=True, allow_null=True)
    profession = ProfessionSerializer(read_only=True, allow_null=True)
    lifestyle = LifestyleSerializer(read_only=True, allow_null=True)
    languages = LanguageSerializer(many=True, read_only=True)
    education = EducationSerializer(many=True, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, profile):
        today = timezone.now().date()
        basic = _section(profile, "basic_info", BasicInfoSerializer)
        dob = (
            getattr(getattr(profile, "basic_info", None), "date_of_birth", None) if basic else None
        )
        if basic is not None and not self.context.get("show_dob", True):
            # Managers without edit_basic_info see the age only (FR-PRO-003).
            basic = {k: v for k, v in basic.items() if k != "date_of_birth"}
        return {
            "id": str(profile.id),
            "profile_code": profile.profile_code,
            "profile_status": profile.profile_status,
            "visibility_status": profile.visibility_status,
            "verification_status": profile.verification_status,
            "completion_percentage": profile.completion_percentage,
            "age": age_on(dob, today) if dob else None,
            "basic_info": basic,
            "location": _section(profile, "location", LocationSerializer),
            "family": _section(profile, "family", FamilySerializer),
            "profession": _section(profile, "profession", ProfessionSerializer),
            "lifestyle": _section(profile, "lifestyle", LifestyleSerializer),
            "languages": LanguageSerializer(profile.languages.all(), many=True).data,
            "education": EducationSerializer(profile.education.all(), many=True).data,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }
