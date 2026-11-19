"""``/profiles/me/partner-preferences/`` (doc 04 §4): GET, PUT (replace), PATCH (partial)."""

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import PartnerPreference
from ..services import preferences as service


def _opt_code():
    return serializers.CharField(max_length=40, allow_null=True, required=False)


class LocationItem(serializers.Serializer):
    country = serializers.CharField(max_length=2)
    state_or_province = serializers.CharField(max_length=100, allow_null=True, required=False)
    city = serializers.CharField(max_length=100, allow_null=True, required=False)


class EducationItem(serializers.Serializer):
    qualification = serializers.CharField(max_length=150)


class LanguageItem(serializers.Serializer):
    language = serializers.CharField(max_length=3)


class ReligionItem(serializers.Serializer):
    religion = serializers.CharField(max_length=40)


class PreferenceWriteSerializer(serializers.Serializer):
    minimum_age = serializers.IntegerField(allow_null=True, required=False)
    maximum_age = serializers.IntegerField(allow_null=True, required=False)
    preferred_gender = _opt_code()
    preferred_marital_status = _opt_code()
    community = _opt_code()
    caste_or_subcast = _opt_code()
    nationality = serializers.CharField(max_length=2, allow_null=True, required=False)
    # Three-state booleans: true, false or null (no preference). Never coerced (FR-019).
    own_house = serializers.BooleanField(allow_null=True, required=False)
    job = serializers.BooleanField(allow_null=True, required=False)
    business = serializers.BooleanField(allow_null=True, required=False)
    minimum_earning = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    maximum_earning = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    earning_currency = serializers.CharField(max_length=3, allow_null=True, required=False)
    earning_frequency = _opt_code()
    residence_type = _opt_code()
    additional_requirements = serializers.CharField(
        max_length=2000, allow_null=True, allow_blank=True, required=False
    )
    locations = LocationItem(many=True, required=False, max_length=20)
    education = EducationItem(many=True, required=False, max_length=20)
    languages = LanguageItem(many=True, required=False, max_length=20)
    religions = ReligionItem(many=True, required=False, max_length=20)

    def validate(self, attrs):
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({k: ["Unknown field."] for k in sorted(unknown)})
        return attrs


def represent(preference: PartnerPreference | None) -> dict:
    body = {f: getattr(preference, f, None) for f in service.SCALAR_FIELDS}
    for name, (_, fields) in service.LISTS.items():
        rows = getattr(preference, name).all() if preference else []
        body[name] = [{f: getattr(row, f) for f in fields} for row in rows]
    return body


class PartnerPreferenceView(APIView):
    def get(self, request):
        return Response(represent(service.get_preferences(request.user)))

    def put(self, request):
        return self._save(request, replace=True)

    def patch(self, request):
        return self._save(request, replace=False)

    def _save(self, request, *, replace):
        serializer = PreferenceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        preference = service.save_preferences(
            request.user, serializer.validated_data, replace=replace
        )
        return Response(represent(preference))
