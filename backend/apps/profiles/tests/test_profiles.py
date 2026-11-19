"""G5 Phase 3b: own profile creation, sections, completion and submit-for-review
(FR-PRO-001…004, 009…013; doc 03 §3; doc 15 §2)."""

import threading
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import SubjectPseudonym, User
from apps.audit.models import AuditLog
from apps.profiles import reference
from apps.profiles.models import MatrimonialProfile, ProfileBasicInfo, ProfileProfession
from apps.profiles.services.profiles import ProfileExists, create_profile

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
def sensitive_lists(monkeypatch):
    """Stand-in values for the owner-supplied lists (tests only)."""
    for name, values in {
        "gender": ("G1", "G2"),
        "marital_status": ("NEVER_MARRIED",),
        "religion": ("R1",),
        "community": ("C1",),
        "caste": ("K1",),
    }.items():
        monkeypatch.setitem(reference.LISTS, name, values)


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

    def test_no_profile_yet_is_404(self):
        assert client_for(make_user()).get(ME).status_code == 404


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
        assert not ProfileBasicInfo.objects.filter(profile__owner=user).exists()

    def test_exactly_eighteen_is_accepted(self, owner):
        _, client = owner
        response = client.patch(
            ME, {"basic_info": {"date_of_birth": str(years_ago(18))}}, format="json"
        )
        assert response.status_code == 200
        assert response.json()["age"] == 18

    def test_sensitive_fields_accept_nothing_until_lists_are_supplied(self, owner):
        _, client = owner
        response = client.patch(ME, {"basic_info": {"gender": "G1"}}, format="json")
        assert response.status_code == 400
        assert "hasn't been provided" in str(response.json())

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
        assert client.patch(ME, {"location": {"city": "Lahore"}}, format="json").status_code == 409

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
                assert response.json()["error"]["code"] == "not_found"
        assert MatrimonialProfile.objects.get(pk=theirs.pk).profile_status == "DRAFT"


def test_is_active_cannot_drift_from_status(owner):
    user, _ = owner
    with pytest.raises(IntegrityError), transaction.atomic():
        MatrimonialProfile.objects.filter(owner=user).update(is_active=True)
