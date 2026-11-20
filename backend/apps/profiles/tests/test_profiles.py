"""G5 Phase 3b: own profile creation, sections, completion and submit-for-review
(FR-PRO-001…004, 009…013; doc 03 §3; doc 15 §2)."""

import threading
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import SubjectPseudonym, User
from apps.audit.models import AuditLog
from apps.profiles.models import (
    MatrimonialProfile,
    ProfileBasicInfo,
    ProfileProfession,
    VocabularyOption,
)
from apps.profiles.services.profiles import ProfileExists, create_profile
from apps.profiles.tests.conftest import activate

pytestmark = pytest.mark.django_db
URL, ME = "/api/v1/profiles/", "/api/v1/profiles/me/"


def make_user(n=1, verified=True) -> User:
    user = User.objects.create_user(phone_number=f"+92300500{n:04d}", password="Pw-Long-enough-9")
    if verified:
        User.objects.filter(pk=user.pk).update(is_phone_verified=True)
    return User.objects.get(pk=user.pk)


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def years_ago(years: int, days: int = 0) -> date:
    today = timezone.now().date()
    return today.replace(year=today.year - years) - timedelta(days=days)


@pytest.fixture
def sensitive_lists():
    """Stand-in codes for the owner-supplied vocabularies (tests only)."""
    activate("gender", "G1", "G2")
    activate("marital_status", "NEVER_MARRIED")
    activate("religion", "R1")
    activate("community", "C1")
    activate("caste", "K1")


@pytest.fixture
def owner():
    user = make_user()
    client = client_for(user)
    assert client.post(URL).status_code == 201
    return user, client


COMPLETE = {
    "basic_info": {
        "full_name": "Test Person",
        "date_of_birth": "1995-04-12",
        "gender": "G1",
        "marital_status": "NEVER_MARRIED",
        "religion": "R1",
        "nationality": "PK",
    },
    "location": {"country": "AE", "city": "Dubai"},
    "languages": [{"language": "ur", "proficiency": "NATIVE", "is_native": True}],
    "profession": {"employment_status": "EMPLOYED"},
}


class TestCreate:
    def test_requires_authentication(self):
        assert APIClient().post(URL).status_code == 401

    def test_requires_phone_verification(self):
        response = client_for(make_user(verified=False)).post(URL)
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "phone_verification_required"

    def test_creates_a_private_draft_with_pseudonym_and_audit(self, owner):
        user, client = owner
        body = client.get(ME).json()
        assert body["profile_status"] == "DRAFT"
        assert body["visibility_status"] == "HIDDEN"
        assert body["profile_code"].startswith("MP") and len(body["profile_code"]) == 10
        profile = MatrimonialProfile.objects.get(owner=user)
        assert SubjectPseudonym.objects.filter(
            subject_type="PROFILE", subject_id=profile.id
        ).exists()
        assert AuditLog.objects.filter(action="profile.created").count() == 1

    def test_one_profile_per_account(self, owner):
        user, client = owner
        response = client.post(URL)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "profile_exists"
        with pytest.raises(IntegrityError), transaction.atomic():
            MatrimonialProfile.objects.create(
                owner=user, profile_code="MP00000000", created_by=user, updated_by=user
            )

    def test_no_profile_yet_needs_a_selection(self):
        response = client_for(make_user()).get(ME)  # doc 04 §24.1 step 3
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "acting_profile_required"


@pytest.mark.django_db(transaction=True)
def test_concurrent_creates_make_one_profile():
    user = make_user(50)
    barrier, outcomes = threading.Barrier(4), []

    def attempt():
        try:
            barrier.wait()
            create_profile(User.objects.get(pk=user.pk))
            outcomes.append("ok")
        except ProfileExists:
            outcomes.append("exists")
        finally:
            connection.close()

    threads = [threading.Thread(target=attempt) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes) == ["exists", "exists", "exists", "ok"]
    assert MatrimonialProfile.objects.filter(owner=user).count() == 1


class TestEditing:
    def test_sections_round_trip_and_dob_only_for_owner(self, owner, sensitive_lists):
        _, client = owner
        response = client.patch(ME, COMPLETE, format="json")
        assert response.status_code == 200, response.json()
        body = response.json()
        assert body["basic_info"]["date_of_birth"] == "1995-04-12"
        assert body["age"] >= 18
        assert body["languages"] == [{"language": "ur", "proficiency": "NATIVE", "is_native": True}]

    @pytest.mark.parametrize("dob", ["under", "future"])
    def test_under_age_or_future_dob_is_rejected_and_not_stored(self, owner, dob):
        user, client = owner
        value = years_ago(18, -1) if dob == "under" else timezone.now().date() + timedelta(days=1)
        response = client.patch(ME, {"basic_info": {"date_of_birth": str(value)}}, format="json")
        assert response.status_code == 400
        assert ProfileBasicInfo.objects.get(profile__owner=user).date_of_birth is None

    def test_exactly_eighteen_is_accepted(self, owner):
        _, client = owner
        response = client.patch(
            ME, {"basic_info": {"date_of_birth": str(years_ago(18))}}, format="json"
        )
        assert response.status_code == 200
        assert response.json()["age"] == 18

    def test_sensitive_fields_accept_nothing_while_their_list_is_inactive(self, owner):
        _, client = owner
        # An administrator can switch a whole list off; the field then accepts no value.
        VocabularyOption.objects.filter(vocabulary="community").update(is_active=False)
        response = client.patch(ME, {"basic_info": {"community": "PUNJABI"}}, format="json")
        assert response.status_code == 400
        assert "hasn't been configured" in str(response.json())

    def test_value_lists_and_iso_codes_are_enforced(self, owner):
        _, client = owner
        for payload in (
            {"lifestyle": {"diet": "CARNIVORE"}},
            {"location": {"country": "pk"}},
            {"profession": {"income_currency": "rupees"}},
            {"languages": [{"language": "Urdu"}]},
        ):
            assert client.patch(ME, payload, format="json").status_code == 400, payload

    def test_income_is_decimal_with_currency_and_frequency(self, owner):
        user, client = owner
        bad = client.patch(ME, {"profession": {"income_amount": "1000.00"}}, format="json")
        assert bad.status_code == 400
        good = client.patch(
            ME,
            {
                "profession": {
                    "income_amount": "250000.50",
                    "income_currency": "PKR",
                    "income_frequency": "MONTHLY",
                }
            },
            format="json",
        )
        assert good.status_code == 200
        assert good.json()["profession"]["income_amount"] == "250000.50"
        row = ProfileProfession.objects.get(profile__owner=user)
        assert row.income_amount == Decimal("250000.50")
        with pytest.raises(IntegrityError), transaction.atomic():
            ProfileProfession.objects.filter(pk=row.pk).update(income_currency=None)

    def test_languages_are_unique_and_lists_replace(self, owner):
        _, client = owner
        dup = [{"language": "en"}, {"language": "en"}]
        assert client.patch(ME, {"languages": dup}, format="json").status_code == 400
        client.patch(ME, {"languages": [{"language": "en"}, {"language": "ur"}]}, format="json")
        body = client.patch(ME, {"languages": [{"language": "ar"}]}, format="json").json()
        assert [row["language"] for row in body["languages"]] == ["ar"]

    def test_state_and_ownership_fields_cannot_be_written(self, owner):
        user, client = owner
        for payload in (
            {"profile_status": "ACTIVE"},
            {"owner": str(make_user(2).pk)},
            {"verification_status": "APPROVED"},
            {"completion_percentage": 100},
        ):
            assert client.patch(ME, payload, format="json").status_code == 400, payload
        profile = MatrimonialProfile.objects.get(owner=user)
        assert (profile.profile_status, profile.verification_status) == ("DRAFT", "NOT_SUBMITTED")

    def test_closed_profile_is_read_only_and_suspension_freezes_visibility(self, owner):
        user, client = owner
        MatrimonialProfile.objects.filter(owner=user).update(
            profile_status="SUSPENDED", suspended_from_status="ACTIVE"
        )
        response = client.patch(ME, {"visibility_status": "VISIBLE_IN_MATCH_SEARCH"}, format="json")
        assert response.status_code == 400
        assert (
            client.patch(ME, {"education": [{"qualification": "BSc"}]}, format="json").status_code
            == 200
        )
        MatrimonialProfile.objects.filter(owner=user).update(
            profile_status="CLOSED", suspended_from_status=None
        )
        # A CLOSED profile is not available to act for (doc 04 §24.1 step 4).
        assert client.patch(ME, {"location": {"city": "Lahore"}}, format="json").status_code == 404

    def test_education_and_profession_stay_editable_after_submission(self, owner, sensitive_lists):
        user, client = owner
        client.patch(ME, COMPLETE, format="json")
        profile = MatrimonialProfile.objects.get(owner=user)
        assert client.post(f"{URL}{profile.id}/submit-review/").status_code == 200
        response = client.patch(
            ME,
            {"education": [{"qualification": "MSc"}], "profession": {"job_title": "Engineer"}},
            format="json",
        )
        assert response.status_code == 200


class TestCompletionAndReview:
    def test_completion_is_computed_by_the_backend(self, owner, sensitive_lists):
        user, client = owner
        profile = MatrimonialProfile.objects.get(owner=user)
        before = client.get(f"{URL}{profile.id}/completion/").json()
        assert before["completion_percentage"] == 0
        assert "basic_info.gender" in before["missing_required"]
        client.patch(ME, COMPLETE, format="json")
        after = client.get(f"{URL}{profile.id}/completion/").json()
        assert after["missing_required"] == []
        assert 0 < after["completion_percentage"] < 100
        assert (
            MatrimonialProfile.objects.get(pk=profile.pk).completion_percentage
            == after["completion_percentage"]
        )

    def test_submit_needs_required_fields_and_draft(self, owner, sensitive_lists):
        user, client = owner
        profile = MatrimonialProfile.objects.get(owner=user)
        incomplete = client.post(f"{URL}{profile.id}/submit-review/")
        assert incomplete.status_code == 400
        assert incomplete.json()["error"]["code"] == "profile_incomplete"
        client.patch(ME, COMPLETE, format="json")
        done = client.post(f"{URL}{profile.id}/submit-review/")
        assert done.json()["profile_status"] == "PENDING_REVIEW"
        again = client.post(f"{URL}{profile.id}/submit-review/")
        assert again.status_code == 409
        assert AuditLog.objects.filter(action="profile.submitted_for_review").count() == 1

    def test_other_profiles_get_an_identical_404(self, owner):
        user, client = owner
        other = make_user(3)
        client_for(other).post(URL)
        theirs = MatrimonialProfile.objects.get(owner=other)
        import uuid

        for target in (theirs.id, uuid.uuid4()):
            for method, suffix in (("get", "completion/"), ("post", "submit-review/")):
                response = getattr(client, method)(f"{URL}{target}/{suffix}")
                assert response.status_code == 404
                assert response.json()["error"]["code"] == "acting_profile_not_available"
        assert MatrimonialProfile.objects.get(pk=theirs.pk).profile_status == "DRAFT"


def test_is_active_cannot_drift_from_status(owner):
    user, _ = owner
    with pytest.raises(IntegrityError), transaction.atomic():
        MatrimonialProfile.objects.filter(owner=user).update(is_active=True)


class TestVocabularies:
    def test_submission_is_unavailable_until_required_vocabularies_exist(self, owner):
        user, client = owner
        VocabularyOption.objects.filter(
            vocabulary__in=["gender", "marital_status", "religion"]
        ).update(is_active=False)
        profile = MatrimonialProfile.objects.get(owner=user)
        completion = client.get(f"{URL}{profile.id}/completion/").json()
        # Religion is optional (DR-2026-11-20-P-1): only required lists block submission.
        assert completion["unconfigured_vocabularies"] == ["gender", "marital_status"]
        response = client.post(f"{URL}{profile.id}/submit-review/")
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "vocabulary_not_configured"

    def test_deactivated_option_stays_on_existing_profiles_but_cannot_be_chosen(
        self, owner, sensitive_lists
    ):
        user, client = owner
        client.patch(ME, COMPLETE, format="json")
        VocabularyOption.objects.filter(vocabulary="gender", code="G1").update(is_active=False)
        kept = client.patch(
            ME, {"basic_info": {**COMPLETE["basic_info"], "full_name": "New"}}, format="json"
        )
        assert kept.status_code == 200 and kept.json()["basic_info"]["gender"] == "G1"
        other_client = client_for(make_user(9))
        other_client.post(URL)
        assert (
            other_client.patch(ME, {"basic_info": {"gender": "G1"}}, format="json").status_code
            == 400
        )

    def test_relabelling_never_touches_profile_data(self, owner, sensitive_lists):
        user, client = owner
        client.patch(ME, COMPLETE, format="json")
        VocabularyOption.objects.filter(vocabulary="gender", code="G1").update(label_en="Renamed")
        assert ProfileBasicInfo.objects.get(profile__owner=user).gender == "G1"

    def test_codes_are_immutable_and_options_never_deleted(self):
        option = VocabularyOption.objects.get(vocabulary="diet", code="VEGAN")
        with pytest.raises(DatabaseError), transaction.atomic():
            VocabularyOption.objects.filter(pk=option.pk).update(code="PLANT_BASED")
        with pytest.raises(DatabaseError), transaction.atomic():
            VocabularyOption.objects.filter(pk=option.pk).delete()
        with pytest.raises(IntegrityError), transaction.atomic():
            VocabularyOption.objects.create(vocabulary="unknown_list", code="X", label_en="X")

    def test_new_options_need_no_code_change(self, owner):
        _, client = owner
        assert (
            client.patch(ME, {"lifestyle": {"diet": "PESCATARIAN"}}, format="json").status_code
            == 400
        )
        activate("diet", "PESCATARIAN")
        assert (
            client.patch(ME, {"lifestyle": {"diet": "PESCATARIAN"}}, format="json").status_code
            == 200
        )


def test_proposals_are_seeded_inactive_and_invent_no_religion_community_or_caste():
    import importlib

    from django.apps import apps as django_apps

    from apps.profiles import reference

    migration = importlib.import_module("apps.profiles.migrations.0004_controlled_vocabularies")
    assert not {"religion", "community", "caste"} & set(migration.PROPOSED)
    assert migration.PROPOSED == reference.PROPOSED
    migration.seed_inactive(django_apps, None)  # get_or_create: never activates anything
    assert VocabularyOption.objects.filter(vocabulary="gender").count() == 2
    # Religion values come only from the owner's approval (0005); community, caste and
    # sub-caste values only from the owner's decision DR-2026-11-20-O-5 (0007).
    seeded = importlib.import_module("apps.profiles.migrations.0007_caste_sub_caste_vocabularies")
    allowed = {
        "community": {c for c, _ in seeded.COMMUNITIES},
        "caste": {c for c, _ in seeded.CASTES},
    }
    for vocabulary, codes in allowed.items():
        assert (
            set(
                VocabularyOption.objects.filter(vocabulary=vocabulary).values_list(
                    "code", flat=True
                )
            )
            == codes
        )


def test_vocabulary_admin_changes_are_audited():
    from django.contrib.admin.sites import site
    from django.test import RequestFactory

    from apps.profiles.admin import VocabularyOptionAdmin

    actor = make_user(77)
    option = VocabularyOption.objects.get(vocabulary="diet", code="VEGAN")
    request = RequestFactory().post("/")
    request.user = actor
    model_admin = VocabularyOptionAdmin(VocabularyOption, site)
    assert model_admin.get_readonly_fields(request, option) == ("vocabulary", "code", "parent")
    assert not model_admin.has_delete_permission(request, option)
    option.is_active = False

    class Form:
        changed_data = ["is_active"]

    model_admin.save_model(request, option, Form(), change=True)
    entry = AuditLog.objects.get(action="profiles.vocabulary_option_changed")
    assert entry.safe_metadata == {
        "vocabulary": "diet",
        "code": "VEGAN",
        "is_active": False,
        "changed": "is_active",
    }


class TestApprovedVocabulariesAndPrivacyChoices:
    """DR-2026-11-19-O-1..7."""

    def test_migration_activates_exactly_the_owner_approved_options(self):
        import importlib

        from django.apps import apps as django_apps

        migration = importlib.import_module(
            "apps.profiles.migrations.0005_approved_vocabularies_and_privacy_choices"
        )
        migration.activate_approved(django_apps, None)
        active = dict(
            VocabularyOption.objects.filter(
                vocabulary__in=["gender", "marital_status", "religion"], is_active=True
            ).values_list("code", "label_en")
        )
        assert active["FEMALE"] == "Female" and active["NEVER_MARRIED"] == "Never Married"
        assert (
            active["ZOROASTRIANISM"] == "Zoroastrianism (Parsi)"
            and active["BAHAI"] == "Baháʼí Faith"
        )
        assert len(active) == 2 + 4 + 12
        assert not {"SUNNI", "SHIA", "PREFER_NOT_TO_SAY"} & set(active)
        # Denominations are separate from religion (0007 seeds them as their own list).
        assert set(
            VocabularyOption.objects.filter(code__in=["SUNNI", "SHIA"]).values_list(
                "vocabulary", flat=True
            )
        ) == {"denomination"}

    def test_prefer_not_to_say_is_a_flag_not_a_value_and_answers_religion(
        self, owner, sensitive_lists
    ):
        user, client = owner
        payload = {**COMPLETE, "basic_info": {**COMPLETE["basic_info"]}}
        del payload["basic_info"]["religion"]
        payload["basic_info"]["religion_prefer_not_to_say"] = True
        body = client.patch(ME, payload, format="json").json()
        assert body["basic_info"]["religion"] is None
        assert body["basic_info"]["religion_prefer_not_to_say"] is True
        profile = MatrimonialProfile.objects.get(owner=user)
        assert (
            "basic_info.religion"
            not in client.get(f"{URL}{profile.id}/completion/").json()["missing_required"]
        )
        assert client.post(f"{URL}{profile.id}/submit-review/").status_code == 200
        # Giving a value later clears the flag.
        body = client.patch(ME, {"basic_info": {"religion": "R1"}}, format="json").json()
        assert body["basic_info"]["religion_prefer_not_to_say"] is False

    def test_value_and_prefer_not_to_say_together_are_rejected(self, owner, sensitive_lists):
        _, client = owner
        bad = {"basic_info": {"religion": "R1", "religion_prefer_not_to_say": True}}
        assert client.patch(ME, bad, format="json").status_code == 400
        with pytest.raises(IntegrityError), transaction.atomic():
            ProfileBasicInfo.objects.filter(profile=MatrimonialProfile.objects.first()).update(
                caste="K1", caste_prefer_not_to_say=True
            )

    def test_denomination_is_optional_separate_and_scoped_to_its_religion(
        self, owner, sensitive_lists
    ):
        user, client = owner
        activate("religion", "R2")
        r1 = VocabularyOption.objects.get(vocabulary="religion", code="R1")
        VocabularyOption.objects.create(
            vocabulary="denomination", code="D1", label_en="D1", parent=r1, is_active=True
        )
        assert client.patch(ME, COMPLETE, format="json").status_code == 200  # none given: fine
        ok = client.patch(ME, {"basic_info": {"denomination": "D1"}}, format="json")
        assert ok.status_code == 200 and ok.json()["basic_info"]["denomination"] == "D1"
        # Changing the religion leaves a denomination of the old religion: rejected.
        assert (
            client.patch(ME, {"basic_info": {"religion": "R2"}}, format="json").status_code == 400
        )
        moved = client.patch(
            ME, {"basic_info": {"religion": "R2", "denomination": None}}, format="json"
        )
        assert moved.status_code == 200
        # Withholding the religion also clears the denomination.
        client.patch(ME, {"basic_info": {"religion": "R1", "denomination": "D1"}}, format="json")
        hidden = client.patch(
            ME, {"basic_info": {"religion_prefer_not_to_say": True}}, format="json"
        )
        assert hidden.json()["basic_info"]["denomination"] is None

    def test_denomination_options_need_a_religion_parent(self):
        diet = VocabularyOption.objects.get(vocabulary="diet", code="VEGAN")
        with pytest.raises(DatabaseError), transaction.atomic():
            VocabularyOption.objects.create(
                vocabulary="denomination", code="X", label_en="X", parent=diet
            )
        with pytest.raises(IntegrityError), transaction.atomic():
            VocabularyOption.objects.create(vocabulary="denomination", code="Y", label_en="Y")

    def test_identity_fields_are_never_required(self, settings):
        from apps.profiles.reference import FIELD_VOCABULARY

        required = set(settings.PROFILE_REQUIRED_FIELDS)
        assert not required & {
            "basic_info.religion",
            "basic_info.community",
            "basic_info.caste",
            "basic_info.sub_caste",
            "basic_info.denomination",
        }
        assert required == {
            "basic_info.full_name",
            "basic_info.date_of_birth",
            "basic_info.gender",
            "basic_info.marital_status",
            "basic_info.nationality",
            "location.country",
            "location.city",
            "languages",
            "profession.employment_status",
        }
        assert FIELD_VOCABULARY["basic_info.denomination"] == "denomination"


class TestEmploymentStatusVocabulary:
    """KI-37: the approved employment-status options are active, so a valid profile can be
    submitted with the production (migrated) vocabularies alone."""

    APPROVED = [
        "EMPLOYED",
        "SELF_EMPLOYED",
        "BUSINESS_OWNER",
        "UNEMPLOYED",
        "STUDENT",
        "RETIRED",
        "HOMEMAKER",
        "OTHER",
    ]

    @staticmethod
    def production_state():
        """Exactly what the migrations leave: every option inactive except the owner-approved
        activations of 0005 and 0006 (undoes the test-only neutral activations)."""
        import importlib

        from django.apps import apps as django_apps

        VocabularyOption.objects.update(is_active=False)
        for name in (
            "0005_approved_vocabularies_and_privacy_choices",
            "0006_activate_employment_status",
        ):
            module = importlib.import_module(f"apps.profiles.migrations.{name}")
            (getattr(module, "activate_approved", None) or module.activate)(django_apps, None)

    def test_migrated_options_are_the_approved_list_in_order(self):
        from apps.profiles import reference

        assert list(reference.allowed("employment_status")) == self.APPROVED
        labels = dict(
            VocabularyOption.objects.filter(vocabulary="employment_status").values_list(
                "code", "label_en"
            )
        )
        assert labels["SELF_EMPLOYED"] == "Self-employed" and labels["HOMEMAKER"] == "Homemaker"
        # The earlier proposal is kept (codes are permanent) but not offered.
        assert (
            VocabularyOption.objects.get(
                vocabulary="employment_status", code="NOT_EMPLOYED"
            ).is_active
            is False
        )
        assert not VocabularyOption.objects.filter(
            vocabulary="employment_status", code__icontains="PREFER"
        ).exists()

    def test_valid_profile_submits_with_production_vocabularies_only(self, owner):
        user, client = owner
        self.production_state()
        payload = {
            "basic_info": {
                "full_name": "Test Person",
                "date_of_birth": "1995-04-12",
                "gender": "FEMALE",
                "marital_status": "NEVER_MARRIED",
                "religion": "ISLAM",
                "nationality": "PK",
            },
            "location": {"country": "PK", "city": "Lahore"},
            "languages": [{"language": "ur", "is_native": True}],
            "profession": {"employment_status": "HOMEMAKER"},
        }
        assert client.patch(ME, payload, format="json").status_code == 200
        profile = MatrimonialProfile.objects.get(owner=user)
        completion = client.get(f"{URL}{profile.id}/completion/").json()
        assert completion["unconfigured_vocabularies"] == []
        assert completion["missing_required"] == []
        response = client.post(f"{URL}{profile.id}/submit-review/")
        assert response.status_code == 200
        assert MatrimonialProfile.objects.get(pk=profile.pk).profile_status == "PENDING_REVIEW"

    def test_inactive_or_unknown_employment_status_is_rejected(self, owner):
        _, client = owner
        self.production_state()
        for code in ("NOT_EMPLOYED", "PREFER_NOT_TO_SAY", "ASTRONAUT"):
            response = client.patch(ME, {"profession": {"employment_status": code}}, format="json")
            assert response.status_code == 400, code

    def test_deactivating_the_list_blocks_submission_again(self, owner):
        user, client = owner
        self.production_state()
        client.patch(
            ME,
            {
                **COMPLETE,
                "basic_info": {
                    **COMPLETE["basic_info"],
                    "gender": "MALE",
                    "religion": "ISLAM",
                },
                "languages": [{"language": "ur", "is_native": True}],
            },
            format="json",
        )
        VocabularyOption.objects.filter(vocabulary="employment_status").update(is_active=False)
        profile = MatrimonialProfile.objects.get(owner=user)
        completion = client.get(f"{URL}{profile.id}/completion/").json()
        assert completion["unconfigured_vocabularies"] == ["employment_status"]
        response = client.post(f"{URL}{profile.id}/submit-review/")
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "vocabulary_not_configured"

    def test_migration_reverse_deactivates_and_reapply_restores(self):
        import importlib

        from django.apps import apps as django_apps

        module = importlib.import_module("apps.profiles.migrations.0006_activate_employment_status")
        module.deactivate(django_apps, None)
        assert (
            VocabularyOption.objects.filter(vocabulary="employment_status", is_active=True).count()
            == 0
        )
        module.activate(django_apps, None)
        assert (
            list(
                VocabularyOption.objects.filter(vocabulary="employment_status", is_active=True)
                .order_by("sort_order")
                .values_list("code", flat=True)
            )
            == self.APPROVED
        )
