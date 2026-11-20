"""Owner decisions DR-2026-11-20-O-1..4: two-way authorization with permission selection,
owner-only permission management, strict manager restrictions, 30-day expiry with history,
TR-16 step-up with the manager's own authenticator, and owner-only identity verification."""

import time
import uuid
from datetime import timedelta

import pytest
from django.test import TestCase
from django.utils import timezone
from django_otp.oath import TOTP

from apps.accounts.models import AccountSecurityEvent, AccountTotpDevice, AuthSession
from apps.accounts.services import mfa
from apps.audit.models import AuditLog
from apps.family.context import ActorContext, granted_codes
from apps.family.models import (
    AuthorizationPermission,
    ManagerAuthorizationHistory,
    ManagerInvitation,
    ManagerPermission,
    ManagerRequest,
    ProfileManagerAuthorization,
    SensitiveActionVerification,
)
from apps.family.services import authorizations as svc
from apps.family.tests.test_family import (
    FAM,
    ME,
    active,
    client_for,
    error,
    granted,
    invite,
    make_user,
    profile_of,
    send_invitation,
)
from apps.profiles.models import MatrimonialProfile, ProfileBasicInfo
from common.events.models import OutboxEvent

pytestmark = pytest.mark.django_db
STEP_UP = "/api/v1/profiles/step-up/"
REQ = f"{FAM}requests/"


@pytest.fixture
def owner():
    user = make_user(1, with_profile=True)
    ProfileBasicInfo.objects.filter(profile=MatrimonialProfile.objects.get(owner=user)).update(
        full_name="Owner Person", date_of_birth="1995-01-01"
    )
    return user


@pytest.fixture
def manager():
    return make_user(2)


def fresh_session(user):
    now = timezone.now()
    return AuthSession.objects.create(
        user=user,
        client_type="WEB",
        last_seen_at=now,
        idle_expires_at=now + timedelta(hours=1),
        absolute_expires_at=now + timedelta(hours=2),
        reauthenticated_at=now,
    )


def owner_client_with_step_up(owner):
    """An owner client whose session has a recent password step-up (needed for Sensitive)."""
    session = fresh_session(owner)
    client = client_for(owner)
    original = client.post, client.put

    def with_session(method):
        def call(path, data=None, **kwargs):
            from unittest import mock

            with mock.patch(
                "apps.family.api.views._session",
                return_value=AuthSession.objects.get(pk=session.pk),
            ):
                return method(path, data, **kwargs)

        return call

    client.post, client.put = with_session(original[0]), with_session(original[1])
    return client


def send_request(requester, phone, **body):
    with TestCase.captureOnCommitCallbacks(execute=True):
        return client_for(requester).post(REQ, {"phone_number": phone, **body}, format="json")


def totp_code(user, steps_ahead=0):
    device = AccountTotpDevice.objects.get(user=user)
    totp = TOTP(mfa._seed(device), device.step, 0, device.digits, device.drift)
    totp.time = time.time() + steps_ahead * device.step
    return f"{totp.token():0{device.digits}d}"


def enroll_authenticator(user):
    mfa.begin_enrollment(user, fresh_session(user))
    mfa.confirm_enrollment(user, totp_code(user))
    return AccountTotpDevice.objects.get(user=user)


def grant_sensitive(owner, a, *codes):
    return svc.set_permissions(
        owner,
        a.pk,
        permission_group=None,
        permissions=["view_profile", *codes],
        confirm_sensitive=True,
        auth_session=fresh_session(owner),
    )


# --- Flow A: permission selection at invitation ------------------------------------------


class TestInvitationPermissionSelection:
    def test_invitee_gets_exactly_the_selected_permissions(self, owner, manager):
        a = invite(owner, manager, group=None, permissions=["view_profile", "edit_education"])
        assert granted(a) == {"view_profile", "edit_education"}
        client_for(manager).post(f"{FAM}authorizations/{a.pk}/accept/")
        assert granted(a) == {"view_profile", "edit_education"}
        assert granted_codes(a.pk) == {"view_profile", "edit_education"}

    def test_sensitive_selection_needs_confirmation_and_owner_step_up(self, owner, manager):
        body = {"permissions": ["view_profile", "send_messages"]}
        no_confirm = send_invitation(owner, manager.phone_number, **body)
        assert no_confirm.status_code == 400
        no_step_up = send_invitation(owner, manager.phone_number, confirm_sensitive=True, **body)
        assert no_step_up.status_code == 403 and error(no_step_up) == "step_up_required"
        client = owner_client_with_step_up(owner)
        with TestCase.captureOnCommitCallbacks(execute=True):
            ok = client.post(
                f"{FAM}authorizations/",
                {"phone_number": manager.phone_number, "confirm_sensitive": True, **body},
                format="json",
            )
        assert ok.status_code == 202
        a = ProfileManagerAuthorization.objects.get(manager=manager)
        assert granted(a) == {"view_profile", "send_messages"}

    def test_owner_only_can_never_be_selected(self, owner, manager):
        for code in ("manage_family_authorizations", "manage_verification_submission"):
            response = send_invitation(owner, manager.phone_number, permissions=[code])
            assert response.status_code == 400, code

    def test_invitation_history_is_recorded_without_revealing_resolution(self, owner, manager):
        a = invite(owner, manager, group=None, permissions=["view_profile"])
        invitation = ManagerInvitation.objects.get(authorization=a)
        rows = client_for(owner).get(f"{FAM}invitations/{invitation.pk}/history/").json()
        assert [r["action"] for r in rows] == ["INVITATION_CREATED"]
        assert rows[0]["new"]["permissions"] == ["view_profile"]
        client_for(manager).post(f"{FAM}authorizations/{a.pk}/accept/")
        rows = client_for(owner).get(f"{FAM}invitations/{invitation.pk}/history/").json()
        assert [r["action"] for r in rows] == ["INVITATION_CREATED", "ACCEPTED"]


# --- Flow B: requests to manage a profile ------------------------------------------------


class TestManagerRequests:
    def test_owner_accepts_and_selects_permissions(self, owner, manager):
        response = send_request(manager, owner.phone_number)
        assert response.status_code == 202
        request = ManagerRequest.objects.get()
        assert request.profile_id == profile_of(owner).pk  # resolved in the background
        received = client_for(owner).get(REQ).json()["received"]
        assert received[0]["requester"]["display"] == "U2"
        assert OutboxEvent.objects.filter(event_type="family.manager_request_received").count() == 1
        accepted = client_for(owner).post(
            f"{REQ}{request.pk}/accept/",
            {"permissions": ["view_profile", "edit_family_details"]},
            format="json",
        )
        assert accepted.status_code == 200 and accepted.json()["status"] == "ACTIVE"
        a = ProfileManagerAuthorization.objects.get(manager=manager)
        assert granted(a) == {"view_profile", "edit_family_details"}
        assert client_for(manager, profile_of(owner).pk).get(ME).status_code == 200
        sent = client_for(manager).get(REQ).json()["sent"][0]
        assert (
            sent["status"] == "ACCEPTED" and sent["profile_code"] == profile_of(owner).profile_code
        )
        actions = list(
            ManagerAuthorizationHistory.objects.filter(authorization=a).values_list(
                "action", flat=True
            )
        )
        assert actions == ["REQUESTED", "REQUEST_ACCEPTED"]
        history = client_for(manager).get(f"{REQ}{request.pk}/history/").json()
        assert [h["action"] for h in history] == [
            "REQUEST_CREATED",
            "REQUESTED",
            "REQUEST_ACCEPTED",
        ]

    @pytest.mark.parametrize("case", ["eligible", "unregistered", "no_profile", "unverified"])
    def test_every_number_gets_the_same_answer(self, owner, manager, case):
        phone = {
            "eligible": owner.phone_number,
            "unregistered": "+923009999999",
            "no_profile": make_user(5).phone_number,
            "unverified": make_user(6, verified=False).phone_number,
        }[case]
        body = send_request(manager, phone).json()
        reference = send_request(manager, "+923008888888").json()
        for b in (body, reference):
            for key in ("id", "requested_at", "expires_at", "phone_hint"):
                b["request"].pop(key)
        assert body == reference
        assert body["request"]["status"] == "PENDING" and body["request"]["profile_code"] is None
        delivered = ManagerRequest.objects.filter(profile__isnull=False).count()
        assert delivered == (1 if case == "eligible" else 0)

    def test_requester_refusals_depend_only_on_their_own_data(self, owner, manager):
        assert send_request(manager, manager.phone_number).status_code == 400
        assert send_request(make_user(7, verified=False), owner.phone_number).status_code == 403
        assert send_request(manager, owner.phone_number).status_code == 202
        again = send_request(manager, owner.phone_number)
        assert again.status_code == 409 and error(again) == "already_requested"

    def test_only_the_owner_answers_and_only_the_requester_cancels(self, owner, manager):
        other_manager = make_user(8)
        active(owner, other_manager)
        send_request(manager, owner.phone_number)
        request = ManagerRequest.objects.get()
        for user in (manager, other_manager, make_user(9)):
            for action in ("accept", "decline"):
                response = client_for(user).post(
                    f"{REQ}{request.pk}/{action}/", {"permissions": []}, format="json"
                )
                assert response.status_code == 404, (user, action)
        # A manager can't answer for the owner through the acting-profile header either.
        acting = client_for(other_manager, profile_of(owner).pk)
        assert acting.post(f"{REQ}{request.pk}/accept/", {}, format="json").status_code == 400
        assert client_for(owner).post(f"{REQ}{request.pk}/cancel/").status_code == 404
        declined = client_for(owner).post(f"{REQ}{request.pk}/decline/")
        assert declined.json()["status"] == "DECLINED"
        assert client_for(manager).post(f"{REQ}{request.pk}/cancel/").status_code == 409

    def test_requests_are_always_for_the_requester_themselves(self, owner, manager):
        third = make_user(10)
        with TestCase.captureOnCommitCallbacks(execute=True):
            client_for(manager).post(
                REQ,
                {
                    "phone_number": owner.phone_number,
                    "requester": str(third.pk),
                    "requester_id": str(third.pk),
                    "manager_id": str(third.pk),
                },
                format="json",
            )
        assert ManagerRequest.objects.get().requester_id == manager.pk

    def test_requester_cancels_their_pending_request(self, owner, manager):
        send_request(manager, owner.phone_number)
        request = ManagerRequest.objects.get()
        body = client_for(manager).post(f"{REQ}{request.pk}/cancel/").json()
        assert body["status"] == "CANCELLED"
        assert client_for(owner).post(f"{REQ}{request.pk}/accept/", {}).status_code == 409


# --- Owner-only permission management ------------------------------------------------------


class TestOwnerManagesPermissions:
    def test_grant_and_revoke_individually_with_history_and_notice(self, owner, manager):
        a = active(owner, manager, group=None)
        client = client_for(owner)
        client.put(
            f"{FAM}authorizations/{a.pk}/permissions/",
            {"permissions": ["view_profile", "edit_education"]},
            format="json",
        )
        client.put(
            f"{FAM}authorizations/{a.pk}/permissions/",
            {"permissions": ["view_profile"]},
            format="json",
        )
        assert granted(a) == {"view_profile"}
        rows = list(
            ManagerAuthorizationHistory.objects.filter(
                authorization=a, action__startswith="PERMISSIONS_"
            ).values_list("action", "new_values")
        )
        assert ("PERMISSIONS_GRANTED", {"permissions": ["edit_education", "view_profile"]}) in rows
        assert ("PERMISSIONS_REVOKED", {"permissions": ["edit_education"]}) in rows
        assert OutboxEvent.objects.filter(event_type="family.permissions_changed").count() == 2
        assert ProfileManagerAuthorization.objects.filter(manager=manager).count() == 1


class TestManagerRestrictions:
    """§1.4: a manager never manages managers or acts for other people, whatever they hold."""

    @pytest.fixture
    def team(self, owner):
        a = make_user(11)
        b = make_user(12)
        auth_a = active(owner, a, group="advanced")
        auth_b = active(owner, b)
        # Even a forged grant of the Owner-only permission gives nothing.
        AuthorizationPermission.objects.create(
            authorization=auth_a,
            permission=ManagerPermission.objects.get(code="manage_family_authorizations"),
            is_granted=True,
            granted_by=owner,
            granted_at=timezone.now(),
        )
        return a, auth_a, b, auth_b

    def test_cannot_change_another_managers_authorization(self, owner, team):
        a, auth_a, b, auth_b = team
        before = granted(auth_b)
        assert "manage_family_authorizations" not in granted_codes(auth_a.pk)
        for client in (client_for(a), client_for(a, profile_of(owner).pk)):
            for action in ("pause", "resume", "revoke", "renew"):
                response = client.post(
                    f"{FAM}authorizations/{auth_b.pk}/{action}/",
                    {"expires_at": None},
                    format="json",
                )
                assert response.status_code in (400, 404), action
            response = client.put(
                f"{FAM}authorizations/{auth_b.pk}/permissions/",
                {"permissions": ["view_profile", "edit_basic_info"]},
                format="json",
            )
            assert response.status_code in (400, 404)
        # Nor their own.
        response = client_for(a).put(
            f"{FAM}authorizations/{auth_a.pk}/permissions/",
            {"permissions": ["view_profile", "manage_photos"]},
            format="json",
        )
        assert response.status_code == 404
        auth_b.refresh_from_db()
        assert auth_b.status == "ACTIVE" and granted(auth_b) == before

    def test_cannot_invite_or_cancel_on_behalf_of_the_owner(self, owner, team):
        a, *_ = team
        outsider = make_user(13)
        acting = client_for(a, profile_of(owner).pk)
        response = acting.post(
            f"{FAM}authorizations/", {"phone_number": outsider.phone_number}, format="json"
        )
        assert response.status_code == 400 and error(response) == "header_not_allowed"
        # Without the header the manager acts as themselves: they have no profile to invite for.
        response = client_for(a).post(
            f"{FAM}authorizations/", {"phone_number": outsider.phone_number}, format="json"
        )
        assert response.status_code == 404
        invitation = send_invitation(owner, outsider.phone_number).json()["invitation"]["id"]
        assert client_for(a).post(f"{FAM}invitations/{invitation}/cancel/").status_code == 404
        assert client_for(a).get(f"{FAM}invitations/{invitation}/history/").status_code == 404
        assert not ManagerInvitation.objects.filter(invited_by=a).exists()

    def test_cannot_accept_for_another_person(self, owner, team):
        a, *_ = team
        outsider = make_user(14)
        target = invite(owner, outsider)
        assert client_for(a).post(f"{FAM}authorizations/{target.pk}/accept/").status_code == 404
        target.refresh_from_db()
        assert target.status == "PENDING"

    def test_managers_get_no_admin_control_from_their_authorization(self, owner, team):
        a, auth_a, b, auth_b = team
        listing = client_for(a).get(f"{FAM}authorizations/").json()
        assert listing["as_owner"] == [] and listing["invitations"] == []
        assert [x["id"] for x in listing["as_manager"]] == [str(auth_a.pk)]
        assert client_for(a).get(f"{FAM}authorizations/{auth_b.pk}/history/").status_code == 404
        acting = client_for(a, profile_of(owner).pk)
        assert acting.get(f"{FAM}profile-access-history/").status_code == 400


# --- 30-day expiry ---------------------------------------------------------------------------


def past_deadline(model, **filters):
    old = timezone.now() - timedelta(days=31)
    field = "invited_at" if model is ManagerInvitation else "requested_at"
    model.objects.filter(**filters).update(**{field: old, "expires_at": old + timedelta(days=30)})


class TestThirtyDayExpiry:
    def test_deadline_is_thirty_days(self, owner, manager):
        a = invite(owner, manager)
        invitation = ManagerInvitation.objects.get(authorization=a)
        assert invitation.expires_at - invitation.invited_at == timedelta(days=30)
        assert a.invitation_expires_at == invitation.expires_at

    def test_resolved_and_unresolved_invitations_expire_the_same_way(self, owner, manager):
        a = invite(owner, manager)
        ghost = send_invitation(owner, "+923009999999").json()["invitation"]["id"]
        past_deadline(ManagerInvitation)
        ProfileManagerAuthorization.objects.filter(pk=a.pk).update(
            invitation_expires_at=timezone.now() - timedelta(days=1)
        )
        # Not accepted in time: refused even before the job runs.
        late = client_for(manager).post(f"{FAM}authorizations/{a.pk}/accept/")
        assert late.status_code == 409 and error(late) == "invitation_expired"
        assert svc.expire_due() == 2
        assert svc.expire_due() == 0
        for invitation in ManagerInvitation.objects.all():
            assert (
                invitation.status == "EXPIRED"
                and invitation.reason == "NOT_ACCEPTED_WITHIN_30_DAYS"
            )
            rows = client_for(owner).get(f"{FAM}invitations/{invitation.pk}/history/").json()
            assert rows[-1]["action"] == "INVITATION_EXPIRED"
            assert rows[-1]["reason"] == "NOT_ACCEPTED_WITHIN_30_DAYS"
        a.refresh_from_db()
        assert a.status == "EXPIRED" and a.reason == "NOT_ACCEPTED_WITHIN_30_DAYS"
        assert ManagerAuthorizationHistory.objects.filter(
            authorization=a, action="EXPIRED", reason="NOT_ACCEPTED_WITHIN_30_DAYS"
        ).exists()
        events = OutboxEvent.objects.filter(event_type="family.invitation_expired")
        assert events.count() == 3  # owner twice (same for both), invitee once
        assert (
            str(ghost)
            and client_for(manager).post(f"{FAM}authorizations/{a.pk}/accept/").status_code == 409
        )
        assert send_invitation(owner, manager.phone_number).status_code == 202  # may invite again

    def test_requests_expire_with_history_and_notices(self, owner, manager):
        send_request(manager, owner.phone_number)
        request = ManagerRequest.objects.get()
        past_deadline(ManagerRequest)
        late = client_for(owner).post(f"{REQ}{request.pk}/accept/", {}, format="json")
        assert late.status_code == 409 and error(late) == "invitation_expired"
        assert svc.expire_due() == 1
        request.refresh_from_db()
        assert request.status == "EXPIRED"
        history = client_for(manager).get(f"{REQ}{request.pk}/history/").json()
        assert history[-1]["action"] == "REQUEST_EXPIRED"
        assert history[-1]["reason"] == "NOT_ACCEPTED_WITHIN_30_DAYS"
        assert OutboxEvent.objects.filter(event_type="family.manager_request_expired").count() == 2
        assert send_request(manager, owner.phone_number).status_code == 202

    def test_owner_can_still_revoke_an_active_authorization_at_any_time(self, owner, manager):
        a = active(owner, manager)
        assert client_for(owner).post(f"{FAM}authorizations/{a.pk}/revoke/").status_code == 200


# --- TR-16 step-up ---------------------------------------------------------------------------


class TestSensitiveStepUp:
    @pytest.fixture
    def setup(self, owner, manager):
        a = active(owner, manager)
        grant_sensitive(owner, a, "manage_privacy_settings")
        return a, client_for(manager, profile_of(owner).pk)

    def step_up(self, client, user, action="manage_privacy_settings", steps_ahead=1):
        return client.post(
            STEP_UP, {"action": action, "code": totp_code(user, steps_ahead)}, format="json"
        )

    def target(self, owner):
        current = profile_of(owner).visibility_status
        return "VISIBLE_IN_MATCH_SEARCH" if current == "HIDDEN" else "HIDDEN"

    def test_manager_without_authenticator_is_denied(self, owner, manager, setup):
        a, client = setup
        response = client.post(
            STEP_UP, {"action": "manage_privacy_settings", "code": "123456"}, format="json"
        )
        assert response.status_code == 403 and error(response) == "authenticator_required"
        no_header = client.patch(ME, {"visibility_status": self.target(owner)}, format="json")
        assert no_header.status_code == 403 and error(no_header) == "step_up_required"

    def test_fresh_verification_allows_exactly_one_action(self, owner, manager, setup, settings):
        settings.ACCOUNT_MFA_THROTTLE_FACTOR = 0  # the throttle is tested separately
        a, client = setup
        enroll_authenticator(manager)
        wrong = client.post(
            STEP_UP, {"action": "manage_privacy_settings", "code": "000000"}, format="json"
        )
        assert wrong.status_code == 403 and error(wrong) == "step_up_failed"
        assert AccountSecurityEvent.objects.filter(event_type="STEP_UP_FAILED").exists()
        ok = self.step_up(client, manager)
        assert ok.status_code == 201
        verification = ok.json()["verification_id"]
        expires = SensitiveActionVerification.objects.get(pk=verification)
        assert (expires.expires_at - expires.verified_at) <= timedelta(minutes=5)
        target = self.target(owner)
        client.credentials(
            HTTP_X_ACTING_PROFILE=str(profile_of(owner).pk),
            HTTP_X_STEP_UP_VERIFICATION=verification,
        )
        done = client.patch(ME, {"visibility_status": target}, format="json")
        assert done.status_code == 200
        assert profile_of(owner).visibility_status == target
        assert OutboxEvent.objects.filter(event_type="family.sensitive_action").count() == 1
        assert AuditLog.objects.filter(action="family.step_up_consumed").count() == 1
        # Single use.
        again = client.patch(ME, {"visibility_status": self.target(owner)}, format="json")
        assert again.status_code == 403 and error(again) == "step_up_required"

    def test_verification_is_bound_to_manager_profile_action_and_time(self, owner, manager, setup):
        a, client = setup
        enroll_authenticator(manager)
        verification = self.step_up(client, manager).json()["verification_id"]
        pid = str(profile_of(owner).pk)
        # Another manager of the same profile can't use it.
        other = make_user(20)
        other_auth = active(owner, other)
        grant_sensitive(owner, other_auth, "manage_privacy_settings")
        other_client = client_for(other)
        other_client.credentials(
            HTTP_X_ACTING_PROFILE=pid, HTTP_X_STEP_UP_VERIFICATION=verification
        )
        response = other_client.patch(ME, {"visibility_status": self.target(owner)}, format="json")
        assert response.status_code == 403
        # Wrong action: a verification for one action isn't valid for another.
        SensitiveActionVerification.objects.filter(pk=verification).update(
            action="manage_subscription"
        )
        client.credentials(HTTP_X_ACTING_PROFILE=pid, HTTP_X_STEP_UP_VERIFICATION=verification)
        assert (
            client.patch(ME, {"visibility_status": self.target(owner)}, format="json").status_code
            == 403
        )
        # Expired.
        SensitiveActionVerification.objects.filter(pk=verification).update(
            action="manage_privacy_settings",
            verified_at=timezone.now() - timedelta(minutes=10),
            expires_at=timezone.now() - timedelta(minutes=5),
        )
        assert (
            client.patch(ME, {"visibility_status": self.target(owner)}, format="json").status_code
            == 403
        )
        # Unknown id.
        client.credentials(HTTP_X_ACTING_PROFILE=pid, HTTP_X_STEP_UP_VERIFICATION=str(uuid.uuid4()))
        assert (
            client.patch(ME, {"visibility_status": self.target(owner)}, format="json").status_code
            == 403
        )

    def test_permission_must_be_granted_and_revocation_wins(self, owner, manager, setup):
        a, client = setup
        enroll_authenticator(manager)
        not_granted = self.step_up(client, manager, action="manage_subscription")
        assert not_granted.status_code == 403 and error(not_granted) == "permission_not_granted"
        verification = self.step_up(client, manager).json()["verification_id"]
        svc.set_permissions(
            owner,
            a.pk,
            permission_group=None,
            permissions=["view_profile"],
            confirm_sensitive=False,
            auth_session=None,
        )
        client.credentials(
            HTTP_X_ACTING_PROFILE=str(profile_of(owner).pk),
            HTTP_X_STEP_UP_VERIFICATION=verification,
        )
        response = client.patch(ME, {"visibility_status": self.target(owner)}, format="json")
        assert response.status_code == 403 and error(response) == "permission_not_granted"

    def test_owner_needs_no_manager_step_up(self, owner, setup):
        response = client_for(owner).patch(
            ME, {"visibility_status": self.target(owner)}, format="json"
        )
        assert response.status_code == 200
        owner_step = client_for(owner).post(
            STEP_UP, {"action": "manage_privacy_settings", "code": "1"}
        )
        assert owner_step.status_code == 400


class TestAccountAuthenticator:
    def test_failed_codes_are_throttled(self, manager):
        enroll_authenticator(manager)
        from django.db import transaction

        from common.db.locking import LockLevel, lock_plan

        def attempt(code):
            with transaction.atomic(), lock_plan("t", [LockLevel.ACCOUNT, LockLevel.DOMAIN]):
                return mfa.verify_code(manager, code)

        assert attempt("000000") is False
        assert attempt(totp_code(manager, 1)) is False  # throttled right after a failure
        AccountTotpDevice.objects.filter(user=manager).update(throttling_failure_count=0)
        assert attempt(totp_code(manager, 1)) is True

    def test_enrollment_needs_step_up_and_a_valid_code(self, manager, settings):
        settings.ACCOUNT_MFA_THROTTLE_FACTOR = 0
        from common.api.auth_errors import StepUpRequired

        with pytest.raises(StepUpRequired):
            mfa.begin_enrollment(manager, None)
        enrollment = mfa.begin_enrollment(manager, fresh_session(manager))
        assert enrollment.otpauth_uri.startswith("otpauth://totp/")
        assert manager.phone_number not in enrollment.otpauth_uri
        with pytest.raises(mfa.MfaCodeInvalid):
            mfa.confirm_enrollment(manager, "000000")
        assert not mfa.is_enrolled(manager)
        mfa.confirm_enrollment(manager, totp_code(manager))
        assert mfa.is_enrolled(manager)
        device = AccountTotpDevice.objects.get(user=manager)
        assert bytes(device.key_ciphertext) and enrollment.secret_base32.encode() not in bytes(
            device.key_ciphertext
        )
        assert AccountSecurityEvent.objects.filter(event_type="ACCOUNT_MFA_ENROLLED").count() == 1

    def test_api_flow_and_removal(self, manager):
        from unittest import mock

        client = client_for(manager)
        assert client.get("/api/v1/auth/mfa/").json() == {"enrolled": False}
        session = fresh_session(manager)
        with mock.patch("apps.accounts.api.mfa._session", return_value=session):
            enroll = client.post("/api/v1/auth/mfa/enroll/")
            assert enroll.status_code == 200 and enroll["Cache-Control"] == "no-store"
            confirmed = client.post(
                "/api/v1/auth/mfa/confirm/", {"code": totp_code(manager)}, format="json"
            )
            assert confirmed.json() == {"enrolled": True}
            removed = client.post(
                "/api/v1/auth/mfa/remove/", {"code": totp_code(manager, 1)}, format="json"
            )
            assert removed.json() == {"enrolled": False}
        assert not AccountTotpDevice.objects.filter(user=manager).exists()


# --- OD-05c identity verification ------------------------------------------------------------


class TestIdentityVerificationIsOwnerOnly:
    def test_permission_is_owner_only_and_never_effective(self, owner, manager):
        assert ManagerPermission.objects.get(code="manage_verification_submission").sensitivity == (
            "OWNER_ONLY"
        )
        a = active(owner, manager)
        response = client_for(owner).put(
            f"{FAM}authorizations/{a.pk}/permissions/",
            {"permissions": ["manage_verification_submission"], "confirm_sensitive": True},
            format="json",
        )
        assert response.status_code == 400
        AuthorizationPermission.objects.create(
            authorization=a,
            permission=ManagerPermission.objects.get(code="manage_verification_submission"),
            is_granted=True,
            granted_by=owner,
            granted_at=timezone.now(),
        )
        assert "manage_verification_submission" not in granted_codes(a.pk)

    def test_only_the_owner_passes_the_identity_verification_guard(self, owner, manager):
        from apps.verification.services.identity_access import (
            OwnerMustSubmitIdentityVerification,
            ensure_owner_submits,
        )

        profile = profile_of(owner)
        a = active(owner, manager, group="advanced")
        ensure_owner_submits(ActorContext(owner, profile, True, None))
        manager_ctx = ActorContext(
            manager, profile, False, a.pk, frozenset({"manage_verification_submission"})
        )
        with pytest.raises(OwnerMustSubmitIdentityVerification):
            ensure_owner_submits(manager_ctx)
        forged = ActorContext(manager, profile, True, None)  # a context claiming ownership
        with pytest.raises(OwnerMustSubmitIdentityVerification):
            ensure_owner_submits(forged)
