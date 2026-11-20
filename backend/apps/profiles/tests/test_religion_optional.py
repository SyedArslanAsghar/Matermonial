"""DR-2026-11-20-P-1: religion is optional for submission and new profiles start with the
privacy choice "prefer not to say" (a flag, never a vocabulary value)."""

import pytest

from apps.profiles.models import MatrimonialProfile, ProfileBasicInfo, VocabularyOption
from apps.profiles.tests.test_profiles import ME, URL, client_for, make_user

pytestmark = pytest.mark.django_db

REQUIRED_WITHOUT_IDENTITY = {
    "basic_info": {
        "full_name": "Test Person",
        "date_of_birth": "1995-04-12",
        "gender": "FEMALE",
        "marital_status": "NEVER_MARRIED",
        "nationality": "PK",
    },
    "location": {"country": "PK", "city": "Lahore"},
    "languages": [{"language": "ur", "is_native": True}],
    "profession": {"employment_status": "EMPLOYED"},
}
IDENTITY = ("religion", "denomination", "caste", "sub_caste", "community")


@pytest.fixture
def owner():
    user = make_user(50)
    client = client_for(user)
    created = client.post(URL)
    assert created.status_code == 201
    return user, client, created.json()


def basic(client, **fields):
    return client.patch(ME, {"basic_info": fields}, format="json")


def submit(client, user):
    profile = MatrimonialProfile.objects.get(owner=user)
    return client.post(f"{URL}{profile.id}/submit-review/")


def test_new_profile_defaults_to_prefer_not_to_say(owner):
    user, _, body = owner
    info = body["basic_info"]
    assert info["religion"] is None and info["religion_prefer_not_to_say"] is True
    assert info["denomination"] is None and info["denomination_prefer_not_to_say"] is False
    row = ProfileBasicInfo.objects.get(profile__owner=user)
    assert row.religion is None and row.religion_prefer_not_to_say is True
    # The flag is not a vocabulary value, and no religion is chosen for the user.
    assert not VocabularyOption.objects.filter(vocabulary="religion", code__icontains="PREFER")


def test_complete_profile_submits_without_religion(owner):
    user, client, _ = owner
    assert client.patch(ME, REQUIRED_WITHOUT_IDENTITY, format="json").status_code == 200
    response = submit(client, user)
    assert response.status_code == 200, response.json()
    row = ProfileBasicInfo.objects.get(profile__owner=user)
    assert row.religion is None and row.religion_prefer_not_to_say is True


def test_submits_without_any_of_the_five_fields_even_without_the_flag(owner):
    user, client, _ = owner
    payload = {
        **REQUIRED_WITHOUT_IDENTITY,
        "basic_info": {
            **REQUIRED_WITHOUT_IDENTITY["basic_info"],
            "religion_prefer_not_to_say": False,
        },
    }
    assert client.patch(ME, payload, format="json").status_code == 200
    row = ProfileBasicInfo.objects.get(profile__owner=user)
    assert all(getattr(row, f) is None for f in IDENTITY)
    assert row.religion_prefer_not_to_say is False  # empty is not read as any religion
    profile = MatrimonialProfile.objects.get(owner=user)
    completion = client.get(f"{URL}{profile.id}/completion/").json()
    assert completion["missing_required"] == []
    assert submit(client, user).status_code == 200


def test_choosing_a_religion_clears_the_flag_and_scopes_denominations(owner):
    _, client, _ = owner
    body = basic(client, religion="CHRISTIANITY", denomination="CATHOLIC").json()["basic_info"]
    assert body["religion"] == "CHRISTIANITY" and body["religion_prefer_not_to_say"] is False
    assert body["denomination"] == "CATHOLIC"
    wrong = basic(client, denomination="SUNNI")  # belongs to Islam
    assert wrong.status_code == 400
    switch = basic(client, religion="ISLAM")  # the Christian denomination no longer fits
    assert switch.status_code == 400


def test_prefer_not_to_say_clears_religion_and_denomination(owner):
    user, client, _ = owner
    basic(client, religion="ISLAM", denomination="SHIA")
    body = basic(client, religion_prefer_not_to_say=True).json()["basic_info"]
    assert body["religion"] is None and body["denomination"] is None
    assert body["religion_prefer_not_to_say"] is True
    row = ProfileBasicInfo.objects.get(profile__owner=user)
    assert (row.religion, row.denomination, row.religion_prefer_not_to_say) == (None, None, True)


def test_editing_other_fields_never_changes_the_religion_choice(owner):
    user, client, _ = owner
    basic(client, religion="SIKHISM")
    basic(client, full_name="Renamed")
    client.patch(ME, {"location": {"country": "AE", "city": "Dubai"}}, format="json")
    row = ProfileBasicInfo.objects.get(profile__owner=user)
    assert row.religion == "SIKHISM" and row.religion_prefer_not_to_say is False
    basic(client, religion_prefer_not_to_say=True)
    basic(client, full_name="Again")
    assert ProfileBasicInfo.objects.get(profile__owner=user).religion_prefer_not_to_say is True


def test_existing_profiles_keep_their_values(owner):
    """Profiles created before this decision aren't changed: no row is created or altered."""
    user = make_user(51)
    legacy = MatrimonialProfile.objects.create(
        owner=user, profile_code="MP0000ABCD", created_by=user, updated_by=user
    )
    assert not ProfileBasicInfo.objects.filter(profile=legacy).exists()
    client = client_for(user)
    assert client.get(ME).json()["basic_info"] is None
    basic(client, full_name="Legacy Person")
    row = ProfileBasicInfo.objects.get(profile=legacy)
    assert row.religion is None and row.religion_prefer_not_to_say is False  # not set silently


class TestNoNewDisclosure:
    def test_other_accounts_see_nothing_and_no_public_profile_endpoints_exist(self, owner):
        user, client, body = owner
        basic(client, religion="ISLAM", denomination="SUNNI")
        stranger = client_for(make_user(52))
        profile_id = body["id"]
        for path in (f"{URL}{profile_id}/completion/", f"{URL}{profile_id}/photos/"):
            assert stranger.get(path).status_code == 404
        stranger.credentials(HTTP_X_ACTING_PROFILE=profile_id)
        assert stranger.get(ME).status_code == 404
        # Search, recommendations, previews, public views and exports don't exist yet (Phases
        # 6, 8, 15); the API exposes no endpoint that returns another person's profile.
        from django.urls import get_resolver

        routes = {str(p) for p in get_resolver().reverse_dict.keys() if isinstance(p, str)}
        for word in ("search", "recommend", "preview", "public", "export"):
            assert not any(word in r for r in routes), word

    def test_managers_see_the_privacy_choice_not_a_value(self, owner):
        from apps.family.tests.test_family import active

        user, client, body = owner
        manager = make_user(53)
        active(user, manager)
        view = client_for(manager)
        view.credentials(HTTP_X_ACTING_PROFILE=body["id"])
        info = view.get(ME).json()["basic_info"]
        assert info["religion"] is None and info["religion_prefer_not_to_say"] is True
        assert info["denomination"] is None
