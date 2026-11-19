"""ADR-033 Amendment 1 (approved, DR-2026-11-19-O-8): two-person admin MFA recovery, SMS-only
replacement codes, fail-safe delivery, emergency CLI recovery and notifications."""

import threading
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.db import IntegrityError, connection, transaction
from django.test import Client
from django.utils import timezone

from apps.accounts.models import AccountSecurityEvent, AuthSession, User
from apps.admin_access.models import AdminActionApproval, AdminMfaEnrollment, AdminTotpDevice
from apps.admin_access.services import mfa
from apps.admin_access.services.catalogue import sync_catalogue
from apps.admin_access.services.recovery import (
    RecoveryAlreadyPending,
    RecoveryNotPending,
    approve_recovery,
    emergency_recovery,
    expire_recovery_requests,
    reject_recovery,
    request_recovery,
)
from apps.admin_access.services.roles import CLI, Actor, NotAuthorized, assign_role
from apps.admin_access.services.superusers import grant_superuser
from apps.admin_access.tests.test_admin_mfa import admin_login, code_for, enroll
from apps.audit.models import AuditLog
from common.events.models import OutboxEvent
from common.providers import MockSMSProvider

pytestmark = pytest.mark.django_db
PASSWORD = "Correct-Horse-Battery-9"


def make_admin(n: int, *, verified=True) -> User:
    user = User.objects.create_user(phone_number=f"+92300800{n:04d}", password=PASSWORD)
    User.objects.filter(pk=user.pk).update(is_phone_verified=verified)
    assign_role(CLI, user, "system_admin")
    return User.objects.get(pk=user.pk)


def actor(user):
    return Actor(user=User.objects.get(pk=user.pk))


def events(event_type, reason=None):
    rows = AccountSecurityEvent.objects.filter(event_type=event_type)
    return rows.filter(reason_code=reason) if reason else rows


def sms_code_for(user) -> str:
    [message] = [m for m in MockSMSProvider.sent if m["to"] == user.phone_number]
    return message["message"].split("code: ")[1].split(".")[0]


@pytest.fixture
def team():
    sync_catalogue(CLI)
    target, requester, approver = make_admin(1), make_admin(2), make_admin(3)
    device = enroll(target)
    return target, requester, approver, device


def everything_text() -> str:
    """Everything an administrator could read: approvals, audit metadata, events, outbox."""
    parts = [str(list(AdminActionApproval.objects.values()))]
    parts += [str(a.safe_metadata) for a in AuditLog.objects.all()]
    parts += [str(list(AccountSecurityEvent.objects.values("event_type", "reason_code")))]
    parts += [str(list(OutboxEvent.objects.values()))]
    return "\n".join(parts)


class TestTwoPersonRecovery:
    def test_full_flow_code_reaches_only_the_account_holder(
        self, team, django_capture_on_commit_callbacks
    ):
        target, requester, approver, _ = team
        client = Client()
        admin_login(client, target, AdminTotpDevice.objects.get(user=target))
        request = request_recovery(actor(requester), target, "LOST_PHONE")
        assert request.status == "PENDING"
        assert AdminTotpDevice.objects.filter(user=target).exists()  # nothing reset yet
        with django_capture_on_commit_callbacks(execute=True):
            result = approve_recovery(actor(approver), request.pk)
        result.refresh_from_db()  # in tests, after-commit delivery runs when the block exits
        assert (result.status, result.outcome) == ("APPROVED", "DELIVERED")
        assert not AdminTotpDevice.objects.filter(user=target).exists()
        assert AuthSession.objects.get(user=target, client_type="ADMIN").status == "REVOKED"
        assert client.get("/admin/").status_code == 302
        code = sms_code_for(target)
        assert code.replace("-", "") not in everything_text().replace("-", "")
        # The holder re-enrolls with the SMS code and a TOTP code, then signs in.
        pending = mfa.begin_enrollment(target, code)
        assert mfa.confirm_enrollment(
            target, pending.device.pk, pending.enrollment_id, code_for(pending.device)
        )
        assert (
            admin_login(Client(), target, AdminTotpDevice.objects.get(user=target)).status_code
            == 302
        )

    def test_requester_cannot_approve_or_reject(self, team):
        target, requester, _, _ = team
        request = request_recovery(actor(requester), target, "LOST_PHONE")
        for decide in (approve_recovery, reject_recovery):
            with pytest.raises(NotAuthorized):
                decide(actor(requester), request.pk)
        assert AdminActionApproval.objects.get(pk=request.pk).status == "PENDING"
        assert AuditLog.objects.filter(
            action="admin.mfa_recovery_approve", result="DENIED"
        ).exists()
        with pytest.raises(IntegrityError), transaction.atomic():
            AdminActionApproval.objects.filter(pk=request.pk).update(
                status="APPROVED", approved_by=requester, approved_at=timezone.now()
            )

    def test_target_cannot_decide_and_requests_need_permission(self, team):
        target, requester, _, _ = team
        with pytest.raises(NotAuthorized):
            request_recovery(actor(target), target, "SELF")
        outsider = User.objects.create_user(phone_number="+923008009999", password=PASSWORD)
        with pytest.raises(NotAuthorized):
            request_recovery(actor(outsider), target, "LOST_PHONE")
        request = request_recovery(actor(requester), target, "LOST_PHONE")
        with pytest.raises(NotAuthorized):
            approve_recovery(actor(target), request.pk)
        with pytest.raises(NotAuthorized):
            approve_recovery(actor(outsider), request.pk)

    def test_one_pending_request_per_account_and_reason_codes(self, team):
        target, requester, approver, _ = team
        with pytest.raises(Exception):  # noqa: B017 - InvalidTarget for a free-text reason
            request_recovery(actor(requester), target, "lost my phone")
        request_recovery(actor(requester), target, "LOST_PHONE")
        with pytest.raises(RecoveryAlreadyPending):
            request_recovery(actor(approver), target, "LOST_PHONE")

    def test_no_verified_phone_means_no_normal_recovery(self, team):
        target, requester, _, _ = team
        User.objects.filter(pk=target.pk).update(is_phone_verified=False)
        with pytest.raises(Exception, match="verified phone"):
            request_recovery(actor(requester), target, "LOST_PHONE")

    def test_reject_and_expiry(self, team):
        target, requester, approver, _ = team
        request = request_recovery(actor(requester), target, "LOST_PHONE")
        assert reject_recovery(actor(approver), request.pk).status == "REJECTED"
        assert AdminTotpDevice.objects.filter(user=target).exists()
        with pytest.raises(RecoveryNotPending):
            approve_recovery(actor(approver), request.pk)
        again = request_recovery(actor(requester), target, "LOST_PHONE")
        AdminActionApproval.objects.filter(pk=again.pk).update(
            requested_at=timezone.now() - timezone.timedelta(days=2),
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        with pytest.raises(RecoveryNotPending):
            approve_recovery(actor(approver), again.pk)
        assert AdminActionApproval.objects.get(pk=again.pk).status == "EXPIRED"
        assert AdminTotpDevice.objects.filter(user=target).exists()
        third = request_recovery(actor(requester), target, "LOST_PHONE")
        AdminActionApproval.objects.filter(pk=third.pk).update(
            requested_at=timezone.now() - timezone.timedelta(days=2),
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        assert expire_recovery_requests() == 1
        assert expire_recovery_requests() == 0
        assert events("ADMIN_MFA_RECOVERY_DECIDED", "EXPIRED").count() == 2

    def test_events_audit_and_notifications(self, team, django_capture_on_commit_callbacks):
        target, requester, approver, _ = team
        boss = User.objects.create_user(phone_number="+923008007777", password=PASSWORD)
        grant_superuser(CLI, boss, reason_code="BOOTSTRAP")
        request = request_recovery(actor(requester), target, "LOST_PHONE")
        with django_capture_on_commit_callbacks(execute=True):
            approve_recovery(actor(approver), request.pk)
        assert events("ADMIN_MFA_RECOVERY_REQUESTED", "LOST_PHONE").count() == 1
        assert events("ADMIN_MFA_RECOVERY_DECIDED", "APPROVED").count() == 1
        assert events("ADMIN_MFA_REMOVED", "RECOVERY").count() == 1
        assert AuditLog.objects.filter(action="admin.mfa_recovery_request").count() == 1
        assert (
            AuditLog.objects.filter(action="admin.mfa_recovery_approve", result="SUCCESS").count()
            == 1
        )
        notices = OutboxEvent.objects.filter(event_type="security.admin_mfa_recovery")
        # REQUESTED and APPROVED, each to the account holder and the superuser.
        assert notices.count() == 4


class TestFailSafeDelivery:
    def test_sms_failure_revokes_the_code_and_reveals_nothing(
        self, team, settings, django_capture_on_commit_callbacks
    ):
        target, requester, approver, _ = team
        settings.SMS_PROVIDER = "disabled"
        request = request_recovery(actor(requester), target, "LOST_PHONE")
        with django_capture_on_commit_callbacks(execute=True):
            result = approve_recovery(actor(approver), request.pk)
        result.refresh_from_db()
        assert result.outcome == "DELIVERY_FAILED"
        assert not AdminMfaEnrollment.objects.filter(
            user=target, used_at__isnull=True, revoked_at__isnull=True
        ).exists()
        assert events("ADMIN_MFA_RECOVERY_DECIDED", "DELIVERY_FAILED").count() == 1
        assert MockSMSProvider.sent == []

    def test_admins_cannot_mint_codes_after_a_reset(self, team, django_capture_on_commit_callbacks):
        target, requester, approver, _ = team
        request = request_recovery(actor(requester), target, "LOST_PHONE")
        with django_capture_on_commit_callbacks(execute=True):
            approve_recovery(actor(approver), request.pk)
        with pytest.raises(mfa.AlreadyEnrolled):
            mfa.issue_enrollment(actor(requester), target)  # first enrollment only
        with pytest.raises(mfa.AlreadyEnrolled):
            mfa.issue_enrollment(CLI, target)

    def test_admin_action_shows_no_code(self, team, django_capture_on_commit_callbacks):
        target, requester, approver, _ = team
        approver_device = enroll(approver)
        client = Client()
        assert admin_login(client, approver, approver_device).status_code == 302
        request = request_recovery(actor(requester), target, "LOST_PHONE")
        with django_capture_on_commit_callbacks(execute=True):
            response = client.post(
                "/admin/admin_access/adminactionapproval/",
                {"action": "approve_selected", "_selected_action": [str(request.pk)]},
                follow=True,
            )
        code = sms_code_for(target)
        assert code not in response.content.decode()
        assert AdminActionApproval.objects.get(pk=request.pk).status == "APPROVED"


@pytest.mark.django_db(transaction=True)
def test_concurrent_approvals_execute_once():
    sync_catalogue(CLI)
    target, requester = make_admin(41), make_admin(42)
    approvers = [make_admin(43 + i) for i in range(3)]
    enroll(target)
    request = request_recovery(actor(requester), target, "LOST_PHONE")
    barrier, outcomes = threading.Barrier(3), []

    def decide(user):
        try:
            barrier.wait()
            approve_recovery(actor(user), request.pk)
            outcomes.append("ok")
        except RecoveryNotPending:
            outcomes.append("not_pending")
        finally:
            connection.close()

    threads = [threading.Thread(target=decide, args=(u,)) for u in approvers]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes) == ["not_pending", "not_pending", "ok"]
    assert len(MockSMSProvider.sent) == 1


class TestEmergencyRecovery:
    def test_requires_flag_and_reason_and_never_prints_the_code(
        self, team, django_capture_on_commit_callbacks
    ):
        target, *_ = team
        boss = User.objects.create_user(phone_number="+923008006666", password=PASSWORD)
        grant_superuser(CLI, boss, reason_code="BOOTSTRAP")
        with pytest.raises(CommandError, match="--emergency"):
            call_command(
                "admin_access",
                "emergency-mfa-recovery",
                "--phone",
                target.phone_number,
                "--reason",
                "INCIDENT_1",
            )
        with pytest.raises(CommandError, match="upper-case"):
            call_command(
                "admin_access",
                "emergency-mfa-recovery",
                "--phone",
                target.phone_number,
                "--emergency",
                "--reason",
                "oops",
            )
        out = StringIO()
        with django_capture_on_commit_callbacks(execute=True):
            call_command(
                "admin_access",
                "emergency-mfa-recovery",
                "--phone",
                target.phone_number,
                "--emergency",
                "--reason",
                "INCIDENT_1",
                stdout=out,
            )
        code = sms_code_for(target)
        assert code not in out.getvalue()
        assert not AdminTotpDevice.objects.filter(user=target).exists()
        assert events("ADMIN_MFA_EMERGENCY_RECOVERY", "INCIDENT_1").count() == 1
        entry = AuditLog.objects.get(action="admin.mfa_emergency_recovery")
        assert entry.safe_metadata["emergency"] is True and entry.safe_metadata["channel"] == "cli"
        assert code.replace("-", "") not in everything_text().replace("-", "")
        notices = OutboxEvent.objects.filter(event_type="security.admin_mfa_recovery")
        assert notices.count() == 2  # account holder and the superuser

    def test_emergency_with_failed_sms_fails_safe(
        self, team, settings, django_capture_on_commit_callbacks
    ):
        target, *_ = team
        settings.SMS_PROVIDER = "disabled"
        with django_capture_on_commit_callbacks(execute=True):
            emergency_recovery(target, "INCIDENT_2")
        assert MockSMSProvider.sent == []
        assert not AdminMfaEnrollment.objects.filter(
            user=target, used_at__isnull=True, revoked_at__isnull=True
        ).exists()
