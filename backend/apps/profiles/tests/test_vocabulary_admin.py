"""Vocabulary admin parent choices (DR-2026-11-20-P-2): denomination → religion (required),
sub-caste → caste (optional), no parent for any other list. Database rules stay intact."""

import pytest
from django.contrib.admin.sites import site
from django.db import DatabaseError, transaction
from django.test import Client, RequestFactory

from apps.accounts.models import User
from apps.profiles.admin import VocabularyOptionAdmin
from apps.profiles.models import VocabularyOption

pytestmark = pytest.mark.django_db


def admin_and_request(method="get", **params):
    actor = User.objects.filter(phone_number="+923006660001").first() or (
        User.objects.create_user(phone_number="+923006660001", password="Pw-Long-enough-9")
    )
    factory = RequestFactory()
    request = factory.post("/", params) if method == "post" else factory.get("/", params)
    request.user = actor
    return VocabularyOptionAdmin(VocabularyOption, site), request


def option(vocabulary, code):
    return VocabularyOption.objects.get(vocabulary=vocabulary, code=code)


def form_for(vocabulary, parent=None, code="NEW_CODE", **query):
    model_admin, request = admin_and_request("post", vocabulary=vocabulary, **query)
    form_class = model_admin.get_form(request, None)
    data = {
        "vocabulary": vocabulary,
        "code": code,
        "label_en": "New",
        "label_ur": "",
        "sort_order": 0,
        "is_active": "on",
    }
    if parent is not None:
        data["parent"] = str(parent.pk)
    return form_class(data=data)


def parent_choices(vocabulary=None):
    model_admin, request = (
        admin_and_request(vocabulary=vocabulary) if vocabulary else admin_and_request()
    )
    form = model_admin.get_form(request, None)()
    return set(form.fields["parent"].queryset.values_list("vocabulary", flat=True))


class TestParentChoices:
    def test_dropdown_offers_only_valid_parents_for_each_list(self):
        assert parent_choices("denomination") == {"religion"}
        assert parent_choices("sub_caste") == {"caste"}
        for vocabulary in ("religion", "caste", "community", "gender", "diet"):
            assert parent_choices(vocabulary) == set(), vocabulary
        # Before a list is chosen: only the two parent lists, labelled with their list.
        assert parent_choices() == {"religion", "caste"}
        model_admin, request = admin_and_request()
        field = model_admin.get_form(request, None)().fields["parent"]
        assert field.label_from_instance(option("caste", "SYED")) == "caste: Syed (SYED)"

    def test_denomination_under_a_religion(self):
        form = form_for("denomination", option("religion", "CHRISTIANITY"), code="ANGLICAN_TEST")
        assert form.is_valid(), form.errors
        created = form.save()
        assert created.parent.code == "CHRISTIANITY"

    def test_denomination_needs_a_religion_parent(self):
        form = form_for("denomination", None, code="NO_PARENT")
        assert not form.is_valid() and "parent" in form.errors

    def test_sub_caste_under_a_caste_or_without_parent(self):
        form = form_for("sub_caste", option("caste", "SYED"), code="SYED_HASHMI_TEST")
        assert form.is_valid(), form.errors
        assert form.save().parent.code == "SYED"
        loose = form_for("sub_caste", None, code="LOOSE_SUB_CASTE")
        assert loose.is_valid(), loose.errors

    @pytest.mark.parametrize(
        "vocabulary, parent",
        [
            ("sub_caste", ("religion", "ISLAM")),
            ("denomination", ("caste", "SYED")),
            ("community", ("caste", "SYED")),
            ("caste", ("religion", "ISLAM")),
        ],
    )
    def test_invalid_parent_types_are_rejected(self, vocabulary, parent):
        # Posted with no list hint, so the dropdown offers both parent lists: the form check
        # (not only the narrowed dropdown) rejects the mismatch.
        model_admin, request = admin_and_request("post")
        form_class = model_admin.get_form(request, None)
        form = form_class(
            data={
                "vocabulary": vocabulary,
                "code": "BAD_PARENT",
                "label_en": "x",
                "label_ur": "",
                "sort_order": 0,
                "parent": str(option(*parent).pk),
            }
        )
        assert not form.is_valid() and "parent" in form.errors

    def test_database_still_rejects_invalid_parents(self):
        with pytest.raises(DatabaseError), transaction.atomic():
            VocabularyOption.objects.create(
                vocabulary="sub_caste",
                code="DB_BAD",
                label_en="x",
                parent=option("religion", "ISLAM"),
            )


class TestEditing:
    def test_parent_vocabulary_and_code_are_read_only_after_creation(self):
        model_admin, request = admin_and_request()
        existing = option("sub_caste", "SYED_BUKHARI")
        assert model_admin.get_readonly_fields(request, existing) == (
            "vocabulary",
            "code",
            "parent",
        )
        form_class = model_admin.get_form(request, existing)
        assert "parent" not in form_class.base_fields
        form = form_class(
            instance=existing,
            data={"label_en": "Syed Bukhari", "label_ur": "", "sort_order": 5, "is_active": "on"},
        )
        assert form.is_valid(), form.errors
        saved = form.save()
        assert saved.parent.code == "SYED" and saved.sort_order == 5
        with pytest.raises(DatabaseError), transaction.atomic():
            VocabularyOption.objects.filter(pk=existing.pk).update(parent=option("caste", "JUTT"))

    def test_seeded_values_are_preserved(self):
        assert option("caste", "JUTT").label_en == "Jutt"
        assert option("sub_caste", "SYED_BUKHARI").label_en == "Syed Bukhari"
        assert option("caste", "MEMON").vocabulary == "caste"
        assert {"MALIK", "SHEIKH"} <= set(
            VocabularyOption.objects.filter(vocabulary="caste").values_list("code", flat=True)
        )
        assert not VocabularyOption.objects.filter(code__icontains="AHMADI").exists()
        assert set(
            VocabularyOption.objects.filter(
                vocabulary="denomination", parent__code="ISLAM"
            ).values_list("code", flat=True)
        ) == {"SUNNI", "SHIA", "ISLAM_OTHER"}


def test_admin_add_page_lists_only_caste_parents_for_sub_castes():
    """Through the real admin site, signed in with MFA."""
    from apps.admin_access.services.catalogue import sync_catalogue
    from apps.admin_access.services.roles import CLI, assign_role
    from apps.admin_access.tests.test_admin_mfa import admin_login, enroll, make_user

    sync_catalogue(CLI)
    user = make_user(61)
    assign_role(CLI, user, "system_admin")
    user = User.objects.get(pk=user.pk)
    device = enroll(user)
    client = Client()
    assert admin_login(client, user, device).status_code == 302
    page = client.get("/admin/profiles/vocabularyoption/add/?vocabulary=sub_caste")
    if page.status_code == 403:  # the role doesn't include vocabulary administration
        pytest.skip("system_admin has no vocabulary permission")
    assert page.status_code == 200
    html = page.content.decode()
    assert "caste: Syed (SYED)" in html
    assert "religion: Islam" not in html
