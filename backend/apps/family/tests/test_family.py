"""G5 Phase 4: family management (FR-FAM-001…009; doc 05 §2; doc 14 §1–§8; doc 15 §4;
doc 04 §24.1 acting-profile resolution)."""

import threading
import uuid
from datetime import timedelta

import pytest
from django.db import DatabaseError, connection, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AuthSession, User
from apps.audit.models import AuditLog
from apps.family.context import ActingProfileNotAvailable, resolve
from apps.family.models import (
    AuthorizationPermission,
    ManagerActionLog,
    ManagerAuthorizationHistory,
    ManagerInvitation,
    ProfileAccessHistory,
    ProfileManagerAuthorization,
)
from apps.family.services import authorizations as svc
from apps.profiles.models import MatrimonialProfile, ProfileBasicInfo
from common.events.models import OutboxEvent

pytestmark = pytest.mark.django_db
PASSWORD = "Correct-Horse-Battery-9"
FAM = "/api/v1/family-management/"
ME = "/api/v1/profiles/me/"


def make_user(n, *, verified=True, with_profile=False):
    user = User.objects.create_user(phone_number=f"+92300900{n:04d}", password=PASSWORD)
    User.objects.filter(pk=user.pk).update(is_phone_verified=verified, first_name=f"U{n}")
    user = User.objects.get(pk=user.pk)
    if with_profile:
        client_for(user).post("/api/v1/profiles/")
    return user


def client_for(user, acting=None):
    client = APIClient()
    client.force_authenticate(user)
    if acting is not None:
        client.credentials(HTTP_X_ACTING_PROFILE=str(acting))
    return client


@pytest.fixture
def owner():
    user = make_user(1, with_profile=True)
    ProfileBasicInfo.objects.create(
        profile=MatrimonialProfile.objects.get(owner=user),
        full_name="Owner Person",
        date_of_birth="1995-01-01",
    )
    return user


@pytest.fixture
def manager():
    return make_user(2)


def profile_of(user):
    return MatrimonialProfile.objects.get(owner=user)


def send_invitation(owner, phone, **body):
    """POST an invitation and run the on-commit resolution task (eager Celery)."""
    with TestCase.captureOnCommitCallbacks(execute=True):
        return client_for(owner).post(
            f"{FAM}authorizations/", {"phone_number": phone, **body}, format="json"
        )


def invite(owner, manager, group="standard", **extra):
    response = send_invitation(owner, manager.phone_number, permission_group=group, **extra)
    assert response.status_code == 202, response.json()
    invitation = ManagerInvitation.objects.get(pk=response.json()["invitation"]["id"])
    assert invitation.authorization_id is not None
    return invitation.authorization


def active(owner, manager, group="standard"):
    a = invite(owner, manager, group)
    assert client_for(manager).post(f"{FAM}authorizations/{a.pk}/accept/").status_code == 200
    a.refresh_from_db()
    return a


def granted(a):
    return set(
        AuthorizationPermission.objects.filter(authorization=a, is_granted=True).values_list(
            "permission__code", flat=True
        )
    )


def error(response):
    return response.json()["error"]["code"]


class TestInvitation:
    def test_owner_invites_and_template_grants_only_normal_permissions(self, owner, manager):
        a = invite(owner, manager, "communication")
        assert a.status == "PENDING" and a.expires_at is None  # no expiry by default
        codes = granted(a)
        assert {"view_profile", "send_requests"} <= codes
        assert not {"view_conversations", "send_messages"} & codes  # Sensitive: not automatic
        assert ManagerAuthorizationHistory.objects.filter(
            authorization=a, action="INVITED"
        ).exists()
        assert AuditLog.objects.filter(action="family.invited").exists()
        assert OutboxEvent.objects.filter(event_type="family.invitation_received").count() == 1

    def test_sensitive_or_owner_only_permissions_cannot_be_set_at_invitation(self, owner, manager):
        for code in (
            "send_messages",
            "request_data_export",
            "manage_family_authorizations",
            "nope",
        ):
            response = client_for(owner).post(
                f"{FAM}authorizations/",
                {"phone_number": manager.phone_number, "permissions": [code]},
                format="json",
            )
            assert response.status_code == 400, code

    def test_only_profile_owners_invite_and_invitations_are_rate_limited(
        self, owner, manager, settings
    ):
        no_profile = make_user(4)
        response = client_for(no_profile).post(
            f"{FAM}authorizations/", {"phone_number": manager.phone_number}, format="json"
        )
        assert response.status_code == 404
        settings.AUTH_RATE_LIMITS = {
            **settings.AUTH_RATE_LIMITS,
            "family_invite_account": "1/86400",
        }
        invite(owner, manager)
        response = send_invitation(owner, make_user(5).phone_number)
        assert response.status_code == 429
        # The limit applies to unregistered numbers too (no free probing).
        assert send_invitation(owner, "+923009999999").status_code == 429

    def test_manager_must_accept_and_only_the_invitee_can(self, owner, manager):
        a = invite(owner, manager)
        stranger = make_user(6)
        assert client_for(stranger).post(f"{FAM}authorizations/{a.pk}/accept/").status_code == 404
        assert client_for(owner).post(f"{FAM}authorizations/{a.pk}/accept/").status_code == 404
        # Pending grants nothing.
        assert client_for(manager, profile_of(owner).pk).get(ME).status_code == 404
        assert client_for(manager).post(f"{FAM}authorizations/{a.pk}/accept/").status_code == 200
        assert client_for(manager).post(f"{FAM}authorizations/{a.pk}/accept/").status_code == 409
        assert OutboxEvent.objects.filter(event_type="family.invitation_accepted").count() == 1

    def test_rejected_invitation_is_final(self, owner, manager):
        a = invite(owner, manager)
        assert (
            client_for(manager).post(f"{FAM}authorizations/{a.pk}/reject/").json()["status"]
            == "REJECTED"
        )
        # Never accepted: the owner has no authorization to act on, only a declined invitation.
        assert client_for(owner).post(f"{FAM}authorizations/{a.pk}/resume/").status_code == 404
        assert ManagerInvitation.objects.get(authorization=a).status == "DECLINED"
        invite(owner, manager)  # a new invitation is possible


class TestInvitationPrivacy:
    """KI-34: an invitation never reveals whether a number belongs to an (eligible) account."""

    CASES = ["eligible", "unregistered", "unverified", "inactive", "deactivated", "pending_other"]

    def number_for(self, case, owner, manager):
        if case == "eligible":
            return manager.phone_number
        if case == "unregistered":
            return "+923009999999"
        if case == "unverified":
            return make_user(3, verified=False).phone_number
        if case == "inactive":
            User.objects.filter(pk=manager.pk).update(is_active=False)
            return manager.phone_number
        if case == "deactivated":
            User.objects.filter(pk=manager.pk).update(is_active=False, deactivated=True)
            return manager.phone_number
        # An account with a live authorization for another owner's profile: still eligible here.
        other_owner = make_user(40, with_profile=True)
        invite(other_owner, manager)
        return manager.phone_number

    @staticmethod
    def shape(body):
        invitation = dict(body["invitation"])
        for volatile in ("id", "invited_at", "expires_at", "phone_hint"):
            invitation.pop(volatile)
        return {**body, "invitation": invitation}

    @pytest.mark.parametrize("case", CASES)
    def test_every_case_gets_the_same_answer_and_list_entry(self, owner, manager, case):
        phone = self.number_for(case, owner, manager)
        response = send_invitation(owner, phone, permission_group="standard")
        assert response.status_code == 202
        reference = send_invitation(owner, "+923008888888", permission_group="standard")
        assert self.shape(response.json()) == self.shape(reference.json())
        body = response.json()
        assert body["invitation"]["status"] == "PENDING"
        assert body["invitation"]["authorization_id"] is None
        assert (
            body["invitation"]["phone_hint"] == f"{phone[:4]}{'•' * (len(phone) - 6)}{phone[-2:]}"
        )
        listing = client_for(owner).get(f"{FAM}authorizations/").json()
        assert listing["as_owner"] == []  # nothing accepted yet, in every case
        entries = {i["id"]: i for i in listing["invitations"]}
        mine, ref = entries[body["invitation"]["id"]], entries[reference.json()["invitation"]["id"]]
        for key in ("id", "invited_at", "expires_at", "phone_hint"):
            mine.pop(key), ref.pop(key)
        assert mine == ref
        text = str(body) + str(listing)
        assert "U2" not in text and "U3" not in text  # no invitee names
        assert manager.phone_number not in text

    def test_request_does_the_same_database_work_either_way(self, owner, manager):
        from django.db import connection as conn
        from django.test.utils import CaptureQueriesContext

        counts = []
        for phone in (manager.phone_number, "+923007777777"):
            with CaptureQueriesContext(conn) as queries, TestCase.captureOnCommitCallbacks():
                assert (
                    client_for(owner)
                    .post(f"{FAM}authorizations/", {"phone_number": phone}, format="json")
                    .status_code
                    == 202
                )
            counts.append(len(queries))
        assert counts[0] == counts[1]

    def test_only_eligible_numbers_reach_an_account(self, owner, manager):
        unverified = make_user(3, verified=False)
        for phone in (manager.phone_number, unverified.phone_number, "+923009999999"):
            send_invitation(owner, phone)
        assert set(ProfileManagerAuthorization.objects.values_list("manager", flat=True)) == {
            manager.pk
        }
        received = OutboxEvent.objects.filter(event_type="family.invitation_received")
        assert received.count() == 1
        assert ManagerInvitation.objects.filter(status="PENDING").count() == 3
        unresolved = AuditLog.objects.filter(action="family.invitation_unresolved")
        assert unresolved.count() == 2

    def test_refusals_depend_only_on_the_owners_own_data(self, owner, manager):
        assert send_invitation(owner, owner.phone_number).status_code == 400  # own number
        assert send_invitation(owner, "not a phone").status_code == 400
        for phone in (manager.phone_number, "+923009999999"):
            assert send_invitation(owner, phone).status_code == 202
            again = send_invitation(owner, phone)
            assert again.status_code == 409 and error(again) == "already_invited"
        a = ProfileManagerAuthorization.objects.get(manager=manager)
        client_for(manager).post(f"{FAM}authorizations/{a.pk}/accept/")
        known = send_invitation(owner, manager.phone_number)
        assert known.status_code == 409 and error(known) == "already_managing"

    def test_pending_authorizations_are_invisible_to_the_owner(self, owner, manager):
        a = invite(owner, manager)
        client = client_for(owner)
        for action in ("pause", "resume", "revoke", "renew"):
            response = client.post(
                f"{FAM}authorizations/{a.pk}/{action}/", {"expires_at": None}, format="json"
            )
            assert response.status_code == 404, action
        assert client.get(f"{FAM}authorizations/{a.pk}/history/").status_code == 404
        assert (
            client.put(
                f"{FAM}authorizations/{a.pk}/permissions/", {"permissions": []}, format="json"
            ).status_code
            == 404
        )
        # The invitee still sees and answers it.
        assert client_for(manager).get(f"{FAM}authorizations/{a.pk}/history/").status_code == 200

    def test_acceptance_reveals_the_authorization_to_the_owner(self, owner, manager):
        a = active(owner, manager)
        listing = client_for(owner).get(f"{FAM}authorizations/").json()
        assert [x["id"] for x in listing["as_owner"]] == [str(a.pk)]
        assert listing["invitations"][0]["status"] == "ACCEPTED"
        assert listing["invitations"][0]["authorization_id"] == str(a.pk)

    def test_nothing_sensitive_in_audit_or_logs(self, owner, manager, caplog):
        import logging

        caplog.set_level(logging.DEBUG)
        for phone in (manager.phone_number, "+923009999999"):
            send_invitation(owner, phone)
        rows = AuditLog.objects.filter(action__startswith="family.invitation")
        assert rows.exists()
        for row in rows:
            assert "+92300" not in str(row.safe_metadata)
        assert "+92300" not in caplog.text
        assert all(len(i.phone_digest) == 64 for i in ManagerInvitation.objects.all())
        assert not ManagerInvitation.objects.filter(phone_digest__contains="9230").exists()

    def test_owner_cancels_resolved_and_unresolved_invitations(self, owner, manager):
        a = invite(owner, manager)
        ghost = send_invitation(owner, "+923009999999").json()["invitation"]["id"]
        linked = ManagerInvitation.objects.get(authorization=a).pk
        client, stranger = client_for(owner), make_user(8)
        for invitation_id in (linked, ghost):
            for user in (manager, stranger):
                assert (
                    client_for(user).post(f"{FAM}invitations/{invitation_id}/cancel/").status_code
                    == 404
                )
            body = client.post(f"{FAM}invitations/{invitation_id}/cancel/").json()
            assert body["status"] == "CANCELLED"
            assert client.post(f"{FAM}invitations/{invitation_id}/cancel/").status_code == 409
        a.refresh_from_db()
        assert a.status == "REVOKED"
        assert client_for(manager).post(f"{FAM}authorizations/{a.pk}/accept/").status_code == 409
        # The number can be invited again.
        assert send_invitation(owner, "+923009999999").status_code == 202

    def test_cancel_before_resolution_stops_the_task(self, owner, manager):
        with TestCase.captureOnCommitCallbacks(execute=False) as callbacks:
            response = client_for(owner).post(
                f"{FAM}authorizations/", {"phone_number": manager.phone_number}, format="json"
            )
        invitation_id = response.json()["invitation"]["id"]
        client_for(owner).post(f"{FAM}invitations/{invitation_id}/cancel/")
        for callback in callbacks:
            callback()
        assert not ProfileManagerAuthorization.objects.exists()
        assert not OutboxEvent.objects.filter(event_type="family.invitation_received").exists()

    def test_resolution_is_idempotent(self, owner, manager):
        a = invite(owner, manager)
        invitation = ManagerInvitation.objects.get(authorization=a)
        assert svc.resolve_invitation(invitation.pk) is None
        assert ProfileManagerAuthorization.objects.count() == 1


class TestManagerAccess:
    def test_manager_acts_within_permissions_and_actor_is_recorded(self, owner, manager):
        active(owner, manager)
        profile = profile_of(owner)
        client = client_for(manager, profile.pk)
        body = client.get(ME).json()
        assert body["id"] == str(profile.pk)
        assert body["basic_info"]["date_of_birth"] == "1995-01-01"  # holds edit_basic_info
        response = client.patch(
            ME, {"basic_info": {"full_name": "Edited By Manager"}}, format="json"
        )
        assert response.status_code == 200
        profile.refresh_from_db()
        assert profile.updated_by_id == manager.pk and profile.owner_id == owner.pk
        log = ManagerActionLog.objects.get(action_type="profile.updated")
        assert log.manager_id == manager.pk and log.profile_id == profile.pk
        assert ProfileAccessHistory.objects.filter(manager=manager, profile=profile).count() == 2

    def test_dob_hidden_from_managers_without_edit_basic_info(self, owner, manager):
        a = active(owner, manager, "communication")
        assert "edit_basic_info" not in granted(a)
        body = client_for(manager, profile_of(owner).pk).get(ME).json()
        assert "date_of_birth" not in body["basic_info"] and body["age"] is not None

    @pytest.mark.parametrize(
        ("method", "url", "payload"),
        [
            ("patch", ME, {"location": {"city": "Lahore"}}),  # owner-only part
            ("patch", ME, {"visibility_status": "HIDDEN"}),  # Sensitive, not granted
            ("patch", ME, {"basic_info": {"full_name": "X"}}),  # not in this template
            ("put", "/api/v1/profiles/me/partner-preferences/", {"job": True}),
        ],
    )
    def test_missing_permissions_are_denied(self, owner, manager, method, url, payload):
        active(owner, manager, "communication")
        client = client_for(manager, profile_of(owner).pk)
        response = getattr(client, method)(url, payload, format="json")
        assert response.status_code == 403 and error(response) == "permission_not_granted"

    def test_photos_need_manage_photos(self, owner, manager):
        active(owner, manager)
        profile = profile_of(owner)
        response = client_for(manager, profile.pk).post(f"/api/v1/profiles/{profile.pk}/photos/")
        assert response.status_code == 403

    @pytest.mark.parametrize("state", ["PAUSED", "REVOKED", "EXPIRED_BY_TIME", "STRANGER"])
    def test_no_access_is_an_identical_404(self, owner, manager, state):
        profile = profile_of(owner)
        a = active(owner, manager)
        user = manager
        if state == "PAUSED":
            client_for(owner).post(f"{FAM}authorizations/{a.pk}/pause/")
        elif state == "REVOKED":
            client_for(owner).post(f"{FAM}authorizations/{a.pk}/revoke/")
        elif state == "EXPIRED_BY_TIME":  # the runtime check doesn't wait for the job
            ProfileManagerAuthorization.objects.filter(pk=a.pk).update(
                invited_at=timezone.now() - timedelta(days=3),
                expires_at=timezone.now() - timedelta(seconds=1),
            )
        else:
            user = make_user(7)
        response = client_for(user, profile.pk).get(ME)
        missing = client_for(user, uuid.uuid4()).get(ME)
        assert response.status_code == missing.status_code == 404
        assert response.json() == missing.json()

    def test_permission_removal_applies_to_the_next_request(self, owner, manager):
        a = active(owner, manager)
        client = client_for(manager, profile_of(owner).pk)
        assert (
            client.patch(ME, {"basic_info": {"full_name": "A"}}, format="json").status_code == 200
        )
        svc.set_permissions(
            owner,
            a.pk,
            permission_group=None,
            permissions=["view_profile"],
            confirm_sensitive=False,
            auth_session=None,
        )
        assert (
            client.patch(ME, {"basic_info": {"full_name": "B"}}, format="json").status_code == 403
        )

    def test_pause_between_resolve_and_write_is_caught_in_the_transaction(self, owner, manager, rf):
        from apps.profiles.services.profiles import update_profile

        a = active(owner, manager)
        request = rf.get("/", HTTP_X_ACTING_PROFILE=str(profile_of(owner).pk))
        request.user = manager
        ctx = resolve(request, permission="view_profile")
        svc.pause(owner, a.pk)
        with pytest.raises(ActingProfileNotAvailable):
            update_profile(ctx, {"basic_info": {"full_name": "Late"}})

    def test_billing_identity_is_the_owner(self, owner, manager, rf):
        active(owner, manager)
        request = rf.get("/", HTTP_X_ACTING_PROFILE=str(profile_of(owner).pk))
        request.user = manager
        ctx = resolve(request, permission="view_profile")
        assert ctx.billing_account_id == owner.pk and not ctx.is_owner

    def test_submit_for_review_by_manager_is_audited_as_manager(self, owner, manager, settings):
        settings.PROFILE_REQUIRED_FIELDS = ["basic_info.full_name"]
        active(owner, manager)
        profile = profile_of(owner)
        response = client_for(manager, profile.pk).post(
            f"/api/v1/profiles/{profile.pk}/submit-review/"
        )
        assert response.status_code == 200
        assert AuditLog.objects.get(action="profile.submitted_for_review").actor_type == "MANAGER"


class TestOwnerControls:
    def test_pause_resume_revoke_and_renew(self, owner, manager):
        a = active(owner, manager)
        client = client_for(owner)
        assert (
            client.post(f"{FAM}authorizations/{a.pk}/pause/", {"reason": "TRAVEL"}).json()["status"]
            == "PAUSED"
        )
        assert client.post(f"{FAM}authorizations/{a.pk}/resume/").json()["status"] == "ACTIVE"
        later = (timezone.now() + timedelta(days=30)).isoformat()
        assert client.post(
            f"{FAM}authorizations/{a.pk}/renew/", {"expires_at": later}, format="json"
        ).json()["expires_at"]
        assert (
            client.post(
                f"{FAM}authorizations/{a.pk}/renew/", {"expires_at": None}, format="json"
            ).json()["expires_at"]
            is None
        )
        past = (timezone.now() - timedelta(days=1)).isoformat()
        assert (
            client.post(
                f"{FAM}authorizations/{a.pk}/renew/", {"expires_at": past}, format="json"
            ).status_code
            == 400
        )
        assert client.post(f"{FAM}authorizations/{a.pk}/revoke/").json()["status"] == "REVOKED"
        for action in ("resume", "pause", "renew"):
            assert (
                client.post(
                    f"{FAM}authorizations/{a.pk}/{action}/", {"expires_at": None}, format="json"
                ).status_code
                == 409
            )
        actions = list(
            ManagerAuthorizationHistory.objects.filter(authorization=a).values_list(
                "action", flat=True
            )
        )
        assert actions == [
            "INVITED",
            "ACCEPTED",
            "PAUSED",
            "RESUMED",
            "RENEWED",
            "RENEWED",
            "REVOKED",
        ]

    def test_managers_and_strangers_cannot_control(self, owner, manager):
        a = active(owner, manager)
        for user in (manager, make_user(8)):
            for action in ("pause", "revoke", "renew"):
                response = client_for(user).post(
                    f"{FAM}authorizations/{a.pk}/{action}/", {"expires_at": None}, format="json"
                )
                assert response.status_code == 404
            response = client_for(user).put(
                f"{FAM}authorizations/{a.pk}/permissions/", {"permissions": []}, format="json"
            )
            assert response.status_code == 404

    def test_sensitive_permissions_need_confirmation_and_owner_step_up(self, owner, manager):
        a = active(owner, manager)
        body = {"permissions": ["view_profile", "send_messages"]}
        with pytest.raises(Exception, match="Confirm"):
            svc.set_permissions(
                owner,
                a.pk,
                permission_group=None,
                permissions=body["permissions"],
                confirm_sensitive=False,
                auth_session=None,
            )
        with pytest.raises(svc.OwnerStepUpRequired):
            svc.set_permissions(
                owner,
                a.pk,
                permission_group=None,
                permissions=body["permissions"],
                confirm_sensitive=True,
                auth_session=None,
            )
        session = AuthSession.objects.create(
            user=owner,
            client_type="WEB",
            last_seen_at=timezone.now(),
            idle_expires_at=timezone.now() + timedelta(hours=1),
            absolute_expires_at=timezone.now() + timedelta(hours=2),
            reauthenticated_at=timezone.now() - timedelta(hours=1),
        )
        with pytest.raises(svc.OwnerStepUpRequired):  # stale step-up
            svc.set_permissions(
                owner,
                a.pk,
                permission_group=None,
                permissions=body["permissions"],
                confirm_sensitive=True,
                auth_session=session,
            )
        AuthSession.objects.filter(pk=session.pk).update(reauthenticated_at=timezone.now())
        change = svc.set_permissions(
            owner,
            a.pk,
            permission_group=None,
            permissions=body["permissions"],
            confirm_sensitive=True,
            auth_session=session,
        )
        assert "send_messages" in change["granted"]
        assert (
            OutboxEvent.objects.filter(event_type="family.sensitive_permissions_changed").count()
            == 1
        )
        # Re-saving the same sensitive grant doesn't need a new step-up.
        svc.set_permissions(
            owner,
            a.pk,
            permission_group=None,
            permissions=body["permissions"],
            confirm_sensitive=False,
            auth_session=None,
        )

    def test_owner_only_permissions_are_never_delegated(self, owner, manager):
        a = active(owner, manager)
        response = client_for(owner).put(
            f"{FAM}authorizations/{a.pk}/permissions/",
            {"permissions": ["request_account_deletion"]},
            format="json",
        )
        assert response.status_code == 400
        AuthorizationPermission.objects.create(  # even a forged row grants nothing
            authorization=a,
            permission_id=__import__("apps.family.models", fromlist=["x"])
            .ManagerPermission.objects.get(code="request_account_deletion")
            .pk,
            is_granted=True,
            granted_by=owner,
            granted_at=timezone.now(),
        )
        from apps.family.context import granted_codes

        assert "request_account_deletion" not in granted_codes(a.pk)

    def test_expiry_job(self, owner, manager):
        a = active(owner, manager)
        ProfileManagerAuthorization.objects.filter(pk=a.pk).update(
            invited_at=timezone.now() - timedelta(days=3),
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        assert svc.expire_due() == 1
        assert svc.expire_due() == 0
        a.refresh_from_db()
        assert a.status == "EXPIRED"
        assert OutboxEvent.objects.filter(event_type="family.authorization_expired").count() == 2


class TestRecordsAndBoundaries:
    def test_history_is_append_only_and_visible_to_the_parties_only(self, owner, manager):
        a = active(owner, manager)
        with pytest.raises(DatabaseError), transaction.atomic():
            ManagerAuthorizationHistory.objects.filter(authorization=a).update(action="X")
        with pytest.raises(DatabaseError), transaction.atomic():
            ManagerActionLog.objects.all().delete()
            ProfileAccessHistory.objects.create(
                profile=profile_of(owner), authorization=a, manager=manager, access_type="x"
            )
            ProfileAccessHistory.objects.all().delete()
        for user, code in ((owner, 200), (manager, 200), (make_user(9), 404)):
            assert client_for(user).get(f"{FAM}authorizations/{a.pk}/history/").status_code == code

    def test_owner_sees_access_history_without_ip_addresses(self, owner, manager):
        active(owner, manager)
        client_for(manager, profile_of(owner).pk).get(ME)
        body = client_for(owner).get(f"{FAM}profile-access-history/").json()
        assert body["accesses"][0]["access_type"] == "view_profile"
        assert "ip_address" not in str(body) and "127.0.0.1" not in str(body)

    def test_account_scoped_endpoints_refuse_the_header(self, owner):
        client = client_for(owner, profile_of(owner).pk)
        for url in ("/api/v1/auth/me/", f"{FAM}authorizations/", f"{FAM}permissions/"):
            response = client.get(url)
            assert response.status_code == 400 and error(response) == "header_not_allowed", url
        assert client.post("/api/v1/profiles/").status_code == 400
        bad = client_for(owner)
        bad.credentials(HTTP_X_ACTING_PROFILE="not-a-uuid")
        assert bad.get(ME).status_code == 400

    def test_catalogue_and_templates(self, owner):
        catalogue = client_for(owner).get(f"{FAM}permissions/").json()
        codes = {p["code"]: p["sensitivity"] for p in catalogue}
        assert (
            codes["send_messages"] == "SENSITIVE" and codes["request_data_export"] == "OWNER_ONLY"
        )
        assert "manage_family_authorizations" not in codes  # inactive pending OD-05c
        groups = {g["code"]: g for g in client_for(owner).get(f"{FAM}permission-groups/").json()}
        assert set(groups) == {"standard", "communication", "advanced"}
        assert "send_messages" in groups["communication"]["permissions"]
        assert "send_messages" not in groups["communication"]["granted_on_apply"]

    def test_lists_show_each_side_its_own_view(self, owner, manager):
        active(owner, manager)
        mine = client_for(owner).get(f"{FAM}authorizations/").json()
        theirs = client_for(manager).get(f"{FAM}authorizations/").json()
        assert len(mine["as_owner"]) == 1 and mine["as_manager"] == []
        assert theirs["as_owner"] == [] and len(theirs["as_manager"]) == 1
        assert owner.phone_number not in str(theirs) and manager.phone_number not in str(mine)


@pytest.mark.django_db(transaction=True)
def test_concurrent_invitations_create_one_live_authorization():
    owner = make_user(30, with_profile=True)
    manager = make_user(31)
    profile = MatrimonialProfile.objects.get(owner=owner)
    from apps.family.context import ActorContext

    ctx = ActorContext(owner, profile, True, None)
    barrier, outcomes = threading.Barrier(4), []

    def attempt():
        try:
            barrier.wait()
            svc.invite(
                ctx, phone_number=manager.phone_number, permission_group=None, permissions=[]
            )
            outcomes.append("ok")
        except svc.AlreadyInvited:
            outcomes.append("taken")
        finally:
            connection.close()

    threads = [threading.Thread(target=attempt) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes) == ["ok", "taken", "taken", "taken"]
    assert ManagerInvitation.objects.filter(profile=profile, status="PENDING").count() == 1
    # (transaction=True: on-commit callbacks ran, so the eager task resolved it)
    assert ProfileManagerAuthorization.objects.filter(profile=profile, manager=manager).count() == 1
