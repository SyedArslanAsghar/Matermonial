"""KI-44 owner decisions of 2026-11-23 (DR-2026-11-23-K-1..4).

- K-1: the seeded identity vocabularies stay exactly as they are for the MVP.
- K-2 (KI44-1): a sub-caste that names a caste never stays beside a withheld caste.
- K-3 (KI44-2): ``GET /api/v1/profiles/vocabularies/`` serves the active options.
- K-4: identity-sensitive vocabulary changes in the admin need an owner decision reference,
  which the audit records.
"""

import importlib

import pytest
from django.contrib.admin.sites import site
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.profiles import reference
from apps.profiles.admin import VocabularyOptionAdmin
from apps.profiles.models import MatrimonialProfile, ProfileBasicInfo, VocabularyOption
from apps.profiles.tests.test_profiles import ME, URL, client_for, make_user
from apps.profiles.tests.test_vocabulary_admin import admin_and_request, option

pytestmark = pytest.mark.django_db
VOCAB_URL = "/api/v1/profiles/vocabularies/"
RELIGIONS = importlib.import_module(
    "apps.profiles.migrations.0005_approved_vocabularies_and_privacy_choices"
).APPROVED["religion"]
SEEDS = importlib.import_module("apps.profiles.migrations.0007_caste_sub_caste_vocabularies")
WITHHELD_ERROR = "would reveal the caste you chose not to share"


@pytest.fixture
def owner():
    user = make_user(70)
    client = client_for(user)
    assert client.post(URL).status_code == 201
    return client


def basic(client, **fields):
    return client.patch(ME, {"basic_info": fields}, format="json")


def stored():
    row = ProfileBasicInfo.objects.get()
    return row.caste, row.caste_prefer_not_to_say, row.sub_caste


# --- K-1: the seeded values are preserved ---------------------------------------------------


def expected_seed() -> dict[str, list[tuple]]:
    """(code, label, parent code, sort order) per list, straight from the seeding migrations."""

    def rows(options, parent=None):
        return [(code, label, parent, i * 10) for i, (code, label) in enumerate(options)]

    expected = {"religion": rows(RELIGIONS), "caste": rows(SEEDS.CASTES)}
    expected["community"] = rows(SEEDS.COMMUNITIES)
    expected["denomination"] = [
        r for religion, opts in SEEDS.DENOMINATIONS.items() for r in rows(opts, religion)
    ]
    expected["sub_caste"] = [
        r for caste, opts in SEEDS.SUB_CASTES.items() for r in rows(opts, caste)
    ]
    return expected


def test_seeded_identity_vocabularies_are_unchanged():
    expected = expected_seed()
    assert {k: len(v) for k, v in expected.items()} == {
        "religion": 12,
        "caste": 16,
        "community": 12,
        "denomination": 22,
        "sub_caste": 19,
    }
    for vocabulary, rows in expected.items():
        actual = sorted(
            VocabularyOption.objects.filter(vocabulary=vocabulary).values_list(
                "code", "label_en", "parent__code", "sort_order", "is_active", "label_ur"
            )
        )
        assert actual == sorted((*r, True, "") for r in rows), vocabulary


# --- K-2 (KI44-1): caste privacy ------------------------------------------------------------


class TestWithheldCaste:
    def test_withholding_caste_clears_a_sub_caste_that_names_a_caste(self, owner):
        assert basic(owner, caste="SYED", sub_caste="SYED_NAQVI").status_code == 200
        response = basic(owner, caste_prefer_not_to_say=True)
        assert response.status_code == 200, response.json()
        assert stored() == (None, True, None)
        body = response.json()["basic_info"]
        assert body["caste"] is None and body["sub_caste"] is None

    def test_withholding_caste_keeps_the_unparented_other_sub_caste(self, owner):
        assert basic(owner, caste="JUTT", sub_caste="SUB_CASTE_OTHER").status_code == 200
        assert basic(owner, caste_prefer_not_to_say=True).status_code == 200
        assert stored() == (None, True, "SUB_CASTE_OTHER")

    def test_a_sub_caste_that_names_a_caste_is_refused_while_caste_is_withheld(self, owner):
        assert basic(owner, caste_prefer_not_to_say=True).status_code == 200
        response = basic(owner, sub_caste="SYED_NAQVI")
        assert response.status_code == 400
        assert WITHHELD_ERROR in str(response.json())
        assert stored() == (None, True, None)

    def test_flag_and_named_sub_caste_in_one_request_are_refused(self, owner):
        response = basic(owner, caste_prefer_not_to_say=True, sub_caste="JUTT_CHEEMA")
        assert response.status_code == 400 and WITHHELD_ERROR in str(response.json())
        assert stored() == (None, False, None)

    def test_unparented_sub_caste_is_allowed_while_caste_is_withheld(self, owner):
        assert basic(owner, caste_prefer_not_to_say=True).status_code == 200
        assert basic(owner, sub_caste="SUB_CASTE_OTHER").status_code == 200
        assert stored() == (None, True, "SUB_CASTE_OTHER")

    def test_sharing_the_caste_again_allows_its_sub_caste(self, owner):
        assert basic(owner, caste_prefer_not_to_say=True).status_code == 200
        assert basic(owner, caste="SYED", sub_caste="SYED_KAZMI").status_code == 200
        assert stored() == ("SYED", False, "SYED_KAZMI")

    def test_sub_caste_given_first_then_caste_withheld(self, owner):
        # A sub-caste without a caste stays allowed (DR-2026-11-20-O-5) ...
        assert basic(owner, sub_caste="RAJPUT_BHATTI").status_code == 200
        # ... but withholding the caste afterwards clears it.
        assert basic(owner, caste_prefer_not_to_say=True).status_code == 200
        assert stored() == (None, True, None)

    def test_clearing_the_sub_caste_with_the_flag_is_accepted(self, owner):
        assert basic(owner, caste="SYED", sub_caste="SYED_NAQVI").status_code == 200
        assert basic(owner, caste_prefer_not_to_say=True, sub_caste=None).status_code == 200
        assert stored() == (None, True, None)

    def test_an_earlier_inconsistent_row_is_cleared_on_the_next_basic_info_update(self, owner):
        ProfileBasicInfo.objects.update(caste_prefer_not_to_say=True, sub_caste="SYED_RIZVI")
        assert basic(owner, full_name="Someone Else").status_code == 200
        assert stored() == (None, True, None)

    def test_a_deactivated_sub_caste_that_names_a_caste_is_still_cleared(self, owner):
        assert basic(owner, caste="SYED", sub_caste="SYED_ZAIDI").status_code == 200
        VocabularyOption.objects.filter(vocabulary="sub_caste", code="SYED_ZAIDI").update(
            is_active=False
        )
        assert basic(owner, caste_prefer_not_to_say=True).status_code == 200
        assert stored() == (None, True, None)

    def test_other_privacy_choices_are_unaffected(self, owner):
        assert basic(owner, caste="SYED", sub_caste="SYED_NAQVI").status_code == 200
        assert basic(owner, sub_caste_prefer_not_to_say=True).status_code == 200
        assert stored() == ("SYED", False, None)
        assert basic(owner, religion_prefer_not_to_say=True).status_code == 200
        assert stored() == ("SYED", False, None)

    def test_a_manager_is_held_to_the_same_rule(self):
        from apps.family.tests.test_family import active
        from apps.family.tests.test_family import client_for as acting_client
        from apps.family.tests.test_family import make_user as family_user

        owner_user, manager = family_user(71, with_profile=True), family_user(72)
        active(owner_user, manager)  # the standard group includes edit_basic_info
        profile = MatrimonialProfile.objects.get(owner=owner_user)
        client = acting_client(manager, profile.pk)
        assert basic(client, caste="SYED", sub_caste="SYED_GILANI").status_code == 200
        assert basic(client, caste_prefer_not_to_say=True).status_code == 200
        row = ProfileBasicInfo.objects.get(profile=profile)
        assert (row.caste, row.caste_prefer_not_to_say, row.sub_caste) == (None, True, None)
        response = basic(client, sub_caste="SYED_GILANI")
        assert response.status_code == 400 and WITHHELD_ERROR in str(response.json())


# The race the profile-row lock prevents: one update withholds the caste while another sets a
# sub-caste that names a caste. Unserialized, each would read the other's old state and both
# would succeed, leaving "SYED_NAQVI" beside a withheld caste. The interleaving is forced, not
# timed: the first update pauses inside its locked section (after reading the stored row), the
# second starts, and the test waits until PostgreSQL reports it blocked on a lock before letting
# the first finish (doc 12 §8: transaction=True, one connection per thread).
WITHHOLD = {"caste_prefer_not_to_say": True}
NAMED_SUB_CASTE = {"sub_caste": "SYED_NAQVI"}


def lock_waiters() -> int:
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_stat_activity "
            "WHERE datname = current_database() AND wait_event_type = 'Lock'"
        )
        return cursor.fetchone()[0]


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "first, second, expected_status",
    [
        (WITHHOLD, NAMED_SUB_CASTE, (200, 400)),  # the later sub-caste is refused
        (NAMED_SUB_CASTE, WITHHOLD, (200, 200)),  # the later withholding clears it
    ],
    ids=["withhold-first", "sub-caste-first"],
)
def test_concurrent_updates_never_leave_a_named_sub_caste_beside_a_withheld_caste(
    monkeypatch, first, second, expected_status
):
    import threading
    import time

    from django.db import connection

    from apps.profiles.services import profiles as service

    # Transactional tests start from an emptied database when another one ran first, so make
    # sure the two seeded options this test uses exist (same values as migration 0007).
    syed, _ = VocabularyOption.objects.get_or_create(
        vocabulary="caste", code="SYED", defaults={"label_en": "Syed", "is_active": True}
    )
    VocabularyOption.objects.get_or_create(
        vocabulary="sub_caste",
        code="SYED_NAQVI",
        defaults={"label_en": "Syed Naqvi", "parent": syed, "is_active": True},
    )
    user = make_user(79)
    assert client_for(user).post(URL).status_code == 201

    inside, release = threading.Event(), threading.Event()
    original = service._protect_withheld_caste

    def pausing(values, current, errors):
        original(values, current, errors)
        if threading.current_thread().name == "first":
            inside.set()  # the profile row is locked and the stored row has been read
            assert release.wait(30), "the test never released the first update"

    monkeypatch.setattr(service, "_protect_withheld_caste", pausing)
    statuses: dict[str, int] = {}

    def run(name, fields):
        try:
            statuses[name] = basic(client_for(user), **fields).status_code
        finally:
            connection.close()

    waiting_before = lock_waiters()
    threads = [
        threading.Thread(target=run, args=("first", first), name="first"),
        threading.Thread(target=run, args=("second", second), name="second"),
    ]
    try:
        threads[0].start()
        assert inside.wait(30), "the first update never reached its locked section"
        threads[1].start()
        deadline = time.monotonic() + 30
        while lock_waiters() <= waiting_before:  # a condition, not a fixed delay
            assert time.monotonic() < deadline, "the second update was never blocked"
            assert threads[1].is_alive(), "the second update finished without waiting"
            time.sleep(0.02)
    finally:
        release.set()
        for t in threads:
            t.join(60)
    assert not any(t.is_alive() for t in threads)

    assert (statuses["first"], statuses["second"]) == expected_status
    row = ProfileBasicInfo.objects.get(profile__owner=user)
    assert row.caste_prefer_not_to_say is True
    assert row.sub_caste is None


# --- K-3 (KI44-2): vocabulary endpoint ------------------------------------------------------


class TestVocabularyEndpoint:
    def test_requires_authentication(self):
        assert APIClient().get(VOCAB_URL).status_code == 401

    def test_returns_every_list_with_active_options_in_order(self):
        response = client_for(make_user(73)).get(VOCAB_URL)
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"vocabularies", "notices"}  # not paginated
        lists = body["vocabularies"]
        assert list(lists) == list(reference.VOCABULARIES)
        assert [o["code"] for o in lists["religion"]] == [c for c, _ in RELIGIONS]
        assert lists["religion"][6] == {
            "code": "ZOROASTRIANISM",
            "label_en": "Zoroastrianism (Parsi)",
            "label_ur": "",
            "parent": None,
        }
        for vocabulary, rows in expected_seed().items():
            assert len(lists[vocabulary]) == len(rows), vocabulary

    def test_parents_are_given_for_denominations_and_sub_castes(self):
        lists = client_for(make_user(74)).get(VOCAB_URL).json()["vocabularies"]
        by_code = {o["code"]: o for o in lists["sub_caste"]}
        assert by_code["SYED_BUKHARI"]["parent"] == {"vocabulary": "caste", "code": "SYED"}
        assert by_code["SUB_CASTE_OTHER"]["parent"] is None
        sunni = next(o for o in lists["denomination"] if o["code"] == "SUNNI")
        assert sunni["parent"] == {"vocabulary": "religion", "code": "ISLAM"}
        assert all(o["parent"] is None for o in lists["caste"] + lists["community"])

    def test_inactive_options_are_not_offered(self):
        VocabularyOption.objects.filter(vocabulary="community", code="BENGALI").update(
            is_active=False
        )
        lists = client_for(make_user(75)).get(VOCAB_URL).json()["vocabularies"]
        assert "BENGALI" not in {o["code"] for o in lists["community"]}
        # Proposals seeded inactive (e.g. NOT_EMPLOYED, KI-37) aren't offered either.
        assert "NOT_EMPLOYED" not in {o["code"] for o in lists["employment_status"]}

    def test_only_option_fields_are_exposed(self):
        lists = client_for(make_user(76)).get(VOCAB_URL).json()["vocabularies"]
        for options in lists.values():
            for o in options:
                assert set(o) == {"code", "label_en", "label_ur", "parent"}

    def test_carries_the_sub_caste_privacy_notice(self):
        notices = client_for(make_user(77)).get(VOCAB_URL).json()["notices"]
        assert notices == [{"vocabulary": "sub_caste", "text_en": reference.NOTICES["sub_caste"]}]
        assert "optional" in notices[0]["text_en"]

    def test_refuses_the_acting_profile_header(self):
        client = client_for(make_user(78))
        client.credentials(HTTP_X_ACTING_PROFILE="00000000-0000-0000-0000-000000000000")
        response = client.get(VOCAB_URL)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "header_not_allowed"


# --- K-4: admin changes need an owner decision reference ------------------------------------


def edit_form(existing, **extra):
    model_admin, request = admin_and_request()
    form_class = model_admin.get_form(request, existing)
    data = {
        "label_en": existing.label_en,
        "label_ur": existing.label_ur,
        "sort_order": existing.sort_order,
        "is_active": "on" if existing.is_active else "",
        **extra,
    }
    return model_admin, request, form_class(instance=existing, data=data)


class TestAdminDecisionReference:
    def test_identity_list_change_without_reference_is_refused(self):
        _, _, form = edit_form(option("caste", "MALIK"), label_en="Malik (title)")
        assert not form.is_valid() and "decision_reference" in form.errors

    def test_malformed_reference_is_refused(self):
        _, _, form = edit_form(option("caste", "MALIK"), decision_reference="approved by owner")
        assert not form.is_valid() and "decision_reference" in form.errors

    def test_new_identity_option_needs_a_reference(self):
        model_admin, request = admin_and_request("post", vocabulary="community")
        form = model_admin.get_form(request, None)(
            data={
                "vocabulary": "community",
                "code": "TEST_COMMUNITY",
                "label_en": "Test",
                "label_ur": "",
                "sort_order": 0,
            }
        )
        assert not form.is_valid() and "decision_reference" in form.errors

    def test_change_with_reference_is_saved_and_audited(self):
        existing = option("community", "BENGALI")
        model_admin, request, form = edit_form(
            existing, sort_order=999, decision_reference="DR-2026-11-23-K-1"
        )
        assert form.is_valid(), form.errors
        obj = form.save(commit=False)
        model_admin.save_model(request, obj, form, change=True)
        log = AuditLog.objects.filter(action="profiles.vocabulary_option_changed").latest(
            "occurred_at"
        )
        assert log.safe_metadata["decision_reference"] == "DR-2026-11-23-K-1"
        assert log.safe_metadata["code"] == "BENGALI"
        VocabularyOption.objects.filter(pk=existing.pk).update(sort_order=existing.sort_order)

    def test_non_identity_lists_need_no_reference(self):
        diet = VocabularyOption.objects.filter(vocabulary="diet").first()
        _, _, form = edit_form(diet, sort_order=diet.sort_order + 1)
        assert form.is_valid(), form.errors
        model_admin = VocabularyOptionAdmin(VocabularyOption, site)
        assert "decision_reference" in model_admin.fields
