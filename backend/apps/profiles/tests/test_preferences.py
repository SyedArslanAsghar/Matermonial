"""G5 Phase 3c: partner preferences (FR-PREF-001…003; doc 03 §4; doc 04 §4)."""

import pytest
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.profiles.models import MatrimonialProfile, PartnerPreference
from apps.profiles.tests.conftest import activate

pytestmark = pytest.mark.django_db
URL = "/api/v1/profiles/me/partner-preferences/"


@pytest.fixture
def client():
    user = User.objects.create_user(phone_number="+923006000001", password="Pw-Long-enough-9")
    User.objects.filter(pk=user.pk).update(is_phone_verified=True)
    api = APIClient()
    api.force_authenticate(User.objects.get(pk=user.pk))
    assert api.post("/api/v1/profiles/").status_code == 201
    return api


def test_needs_a_profile_and_authentication():
    assert APIClient().get(URL).status_code == 401
    user = User.objects.create_user(phone_number="+923006000002")
    api = APIClient()
    api.force_authenticate(user)
    assert api.get(URL).status_code == 404


def test_empty_preferences_read_as_no_preference(client):
    body = client.get(URL).json()
    assert body["own_house"] is None and body["minimum_age"] is None
    assert body["locations"] == [] and body["religions"] == []


def test_nullable_booleans_keep_three_states(client):
    body = client.patch(
        URL, {"own_house": True, "job": False, "business": None}, format="json"
    ).json()
    assert (body["own_house"], body["job"], body["business"]) == (True, False, None)
    stored = PartnerPreference.objects.get()
    assert stored.business is None  # null is not false
    body = client.patch(URL, {"job": None}, format="json").json()
    assert (body["own_house"], body["job"]) == (True, None)


@pytest.mark.parametrize(
    "payload",
    [
        {"minimum_age": 17},
        {"maximum_age": 101},
        {"minimum_age": 40, "maximum_age": 30},
        {
            "minimum_earning": 5000,
            "maximum_earning": 1000,
            "earning_currency": "PKR",
            "earning_frequency": "MONTHLY",
        },
        {"minimum_earning": 1000},  # no currency or frequency
        {"earning_currency": "rupee"},
        {"residence_type": "CASTLE"},
        {"nationality": "Pakistan"},
        {"locations": [{"country": "PK"}, {"country": "PK"}]},
        {"languages": [{"language": "English"}]},
        {"profile": "x"},
    ],
)
def test_invalid_input_is_rejected(client, payload):
    assert client.patch(URL, payload, format="json").status_code == 400


def test_patch_checks_the_merged_range(client):
    assert (
        client.patch(URL, {"minimum_age": 25, "maximum_age": 35}, format="json").status_code == 200
    )
    assert client.patch(URL, {"minimum_age": 40}, format="json").status_code == 400
    assert PartnerPreference.objects.get().minimum_age == 25


def test_sensitive_preferences_wait_for_owner_lists(client):
    assert client.patch(URL, {"religions": [{"religion": "R1"}]}, format="json").status_code == 400
    activate("religion", "R1", "R2")
    body = client.patch(
        URL, {"religions": [{"religion": "R1"}, {"religion": "R2"}]}, format="json"
    ).json()
    assert body["religions"] == [{"religion": "R1"}, {"religion": "R2"}]


def test_put_replaces_and_patch_merges(client):
    client.put(
        URL,
        {
            "minimum_age": 25,
            "maximum_age": 35,
            "own_house": True,
            "locations": [{"country": "PK", "city": "Lahore"}],
            "languages": [{"language": "ur"}],
            "minimum_earning": 100000,
            "earning_currency": "PKR",
            "earning_frequency": "MONTHLY",
        },
        format="json",
    )
    body = client.patch(URL, {"education": [{"qualification": "MBA"}]}, format="json").json()
    assert body["minimum_age"] == 25 and body["languages"] == [{"language": "ur"}]
    body = client.put(URL, {"maximum_age": 40}, format="json").json()
    assert body["minimum_age"] is None and body["own_house"] is None
    assert body["locations"] == [] and body["education"] == [] and body["minimum_earning"] is None


def test_database_rejects_inverted_ranges(client):
    client.patch(URL, {"minimum_age": 20, "maximum_age": 30}, format="json")
    with pytest.raises(IntegrityError), transaction.atomic():
        PartnerPreference.objects.update(minimum_age=50)
    with pytest.raises(IntegrityError), transaction.atomic():
        PartnerPreference.objects.update(minimum_earning=10)  # no currency


def test_closed_profile_preferences_are_read_only(client):
    MatrimonialProfile.objects.update(profile_status="CLOSED")
    assert client.patch(URL, {"job": True}, format="json").status_code == 409
