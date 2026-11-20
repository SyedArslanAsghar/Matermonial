"""KI-29, owner decision DR-2026-11-20-O-5: religion, denomination, caste, sub-caste and community
are separate, optional, admin-managed fields; "prefer not to say" is a privacy flag."""

import importlib

import pytest
from django.apps import apps as django_apps
from django.db import DatabaseError, IntegrityError, transaction

from apps.profiles.models import ProfileBasicInfo, VocabularyOption
from apps.profiles.tests.test_profiles import COMPLETE, ME, URL, client_for, make_user

pytestmark = pytest.mark.django_db
SEEDS = importlib.import_module("apps.profiles.migrations.0007_caste_sub_caste_vocabularies")


@pytest.fixture
def client():
    user = make_user(40)
    c = client_for(user)
    assert c.post(URL).status_code == 201
    return c


def basic(client, **fields):
    return client.patch(ME, {"basic_info": fields}, format="json")


def test_seeded_lists_are_separate_and_active():
    def codes(vocabulary):
        return set(
            VocabularyOption.objects.filter(vocabulary=vocabulary, is_active=True).values_list(
                "code", flat=True
            )
        )

    assert {"ISLAM", "CHRISTIANITY", "OTHER"} <= codes("religion")
    assert not {"SUNNI", "SHIA", "PREFER_NOT_TO_SAY"} & codes("religion")
    assert {"SUNNI", "SHIA", "CATHOLIC", "PROTESTANT", "THERAVADA"} <= codes("denomination")
    assert {"JUTT", "SYED", "BRAHMIN"} <= codes("caste")
    assert {"SYED_BUKHARI", "SUB_CASTE_OTHER"} <= codes("sub_caste")
    assert {"PUNJABI", "SINDHI"} <= codes("community")
    for vocabulary in ("religion", "denomination", "caste", "sub_caste", "community"):
        assert not any("PREFER" in c for c in codes(vocabulary))
    bukhari = VocabularyOption.objects.get(vocabulary="sub_caste", code="SYED_BUKHARI")
    assert bukhari.parent.code == "SYED" and bukhari.parent.vocabulary == "caste"
    # Caste options aren't tied to a religion: they have no parent.
    assert not VocabularyOption.objects.filter(vocabulary="caste", parent__isnull=False).exists()


def test_all_five_fields_are_optional(client):
    response = basic(client, full_name="Someone")
    body = response.json()["basic_info"]
    assert response.status_code == 200
    for field in ("religion", "denomination", "caste", "sub_caste", "community"):
        assert body[field] is None


def test_fields_are_independent_across_religions(client):
    # A Christian user can give a caste and a community; nothing ties them to Islam.
    response = basic(
        client,
        religion="CHRISTIANITY",
        denomination="CATHOLIC",
        caste="JUTT",
        sub_caste="JUTT_CHEEMA",
        community="PUNJABI",
    )
    assert response.status_code == 200, response.json()
    row = ProfileBasicInfo.objects.get()
    assert (row.religion, row.denomination, row.caste, row.sub_caste, row.community) == (
        "CHRISTIANITY",
        "CATHOLIC",
        "JUTT",
        "JUTT_CHEEMA",
        "PUNJABI",
    )


def test_denomination_must_belong_to_the_religion(client):
    assert basic(client, religion="CHRISTIANITY", denomination="SUNNI").status_code == 400
    assert basic(client, religion="ISLAM", denomination="SUNNI").status_code == 200


def test_sub_caste_is_optional_and_checked_against_a_given_caste(client):
    assert basic(client, caste="SYED").status_code == 200  # no sub-caste needed
    assert basic(client, sub_caste="SYED_BUKHARI").status_code == 200  # matches
    wrong = basic(client, sub_caste="JUTT_CHEEMA")
    assert wrong.status_code == 400 and "sub_caste" in str(wrong.json())
    # A sub-caste without a parent works with any caste; a sub-caste works with no caste.
    assert basic(client, sub_caste="SUB_CASTE_OTHER").status_code == 200
    assert basic(client, caste=None, sub_caste="JUTT_CHEEMA").status_code == 200


def test_prefer_not_to_say_is_a_flag_for_each_field(client):
    body = basic(client, caste_prefer_not_to_say=True, sub_caste_prefer_not_to_say=True).json()[
        "basic_info"
    ]
    assert body["caste"] is None and body["caste_prefer_not_to_say"] is True
    assert body["sub_caste"] is None and body["sub_caste_prefer_not_to_say"] is True
    both = basic(client, sub_caste="SYED_BUKHARI", sub_caste_prefer_not_to_say=True)
    assert both.status_code == 400
    with pytest.raises(IntegrityError), transaction.atomic():
        ProfileBasicInfo.objects.filter().update(sub_caste="X1", sub_caste_prefer_not_to_say=True)


def test_none_of_the_five_identity_fields_is_required(client, settings):
    # DR-2026-11-20-P-1: religion is optional too (superseding its place in DR-2026-11-19-O-7).
    assert not {
        "basic_info.religion",
        "basic_info.denomination",
        "basic_info.caste",
        "basic_info.sub_caste",
        "basic_info.community",
    } & set(settings.PROFILE_REQUIRED_FIELDS)


def test_admins_add_options_without_code_and_codes_stay_stable(client):
    VocabularyOption.objects.create(
        vocabulary="sub_caste",
        code="SYED_HASHMI",
        label_en="Syed Hashmi",
        parent=VocabularyOption.objects.get(vocabulary="caste", code="SYED"),
        is_active=True,
    )
    assert basic(client, caste="SYED", sub_caste="SYED_HASHMI").status_code == 200
    option = VocabularyOption.objects.get(vocabulary="sub_caste", code="SYED_HASHMI")
    VocabularyOption.objects.filter(pk=option.pk).update(label_en="Hashmi")  # labels editable
    with pytest.raises(DatabaseError), transaction.atomic():
        VocabularyOption.objects.filter(pk=option.pk).update(code="HASHMI")
    with pytest.raises(DatabaseError), transaction.atomic():
        VocabularyOption.objects.filter(pk=option.pk).delete()


def test_parent_rules_are_enforced_by_the_database():
    religion = VocabularyOption.objects.get(vocabulary="religion", code="ISLAM")
    with pytest.raises(DatabaseError), transaction.atomic():
        VocabularyOption.objects.create(
            vocabulary="sub_caste", code="BAD_PARENT", label_en="x", parent=religion
        )
    caste = VocabularyOption.objects.get(vocabulary="caste", code="SYED")
    with pytest.raises(DatabaseError), transaction.atomic():
        VocabularyOption.objects.create(
            vocabulary="denomination", code="BAD_DENOM", label_en="x", parent=caste
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        VocabularyOption.objects.create(
            vocabulary="community", code="WITH_PARENT", label_en="x", parent=caste
        )


def test_complete_profile_with_all_fields_still_submits(client):
    from apps.profiles.models import MatrimonialProfile

    payload = {
        **COMPLETE,
        "basic_info": {
            **COMPLETE["basic_info"],
            "gender": "FEMALE",
            "religion": "ISLAM",
            "denomination": "SHIA",
            "caste": "SYED",
            "sub_caste": "SYED_NAQVI",
            "community": "URDU_SPEAKING",
        },
        "languages": [{"language": "ur", "is_native": True}],
    }
    assert client.patch(ME, payload, format="json").status_code == 200
    profile = MatrimonialProfile.objects.get()
    assert client.post(f"{URL}{profile.id}/submit-review/").status_code == 200


def test_seed_function_is_idempotent():
    before = VocabularyOption.objects.count()
    SEEDS.seed(django_apps, None)
    assert VocabularyOption.objects.count() == before
