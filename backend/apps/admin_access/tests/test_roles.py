"""G5 Phase 2e-2: admin roles, deny-by-default permissions, audited assignment, staff
projection and the break-glass superuser limit (TR-07, ADR-027; doc 03 §16.2-16.5, §22.15)."""

import threading
from datetime import timedelta
from io import StringIO

import pytest
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.utils import timezone

from apps.accounts.models import AuthSession, User
from apps.accounts.services.auth import create_admin_session
from apps.admin_access.backends import AdminRoleBackend
from apps.admin_access.catalogue import MANAGE_ROLES
from apps.admin_access.models import AdminPermission, AdminRole, AdminRolePermission, AdminUserRole
from apps.admin_access.selectors import has_admin_access, permission_codes
from apps.admin_access.services.catalogue import sync_catalogue
from apps.admin_access.services.roles import (
    CLI,
    Actor,
    AlreadyAssigned,
    InvalidTarget,
    NotAssigned,
    NotAuthorized,
    assign_role,
    revoke_role,
    sync_expired_assignments,
)
from apps.admin_access.services.superusers import (
    SuperuserLimitReached,
    grant_superuser,
    revoke_superuser,
)
from apps.audit.models import AuditLog

PASSWORD = "Correct-Horse-Battery-9"
pytestmark = pytest.mark.django_db


def make_user(n: int) -> User:
    return User.objects.create_user(phone_number=f"+92300100{n:04d}", password=PASSWORD)


def fresh(user: User) -> User:
    return User.objects.get(pk=user.pk)


def audits(action: str, result: str | None = None):
    rows = AuditLog.objects.filter(action=action)
    return rows.filter(result=result) if result else rows


def expire(row: AdminUserRole) -> None:
    now = timezone.now()
    AdminUserRole.objects.filter(pk=row.pk).update(
        assigned_at=now - timedelta(hours=2), expires_at=now - timedelta(seconds=1)
    )


@pytest.fixture
def catalogue():
    sync_catalogue(CLI)


@pytest.fixture
def limited_role(catalogue):
    """A role with a single non-sensitive permission (for escalation tests)."""
    role = AdminRole.objects.create(code="viewer", name="Viewer")
    AdminRolePermission.objects.create(
        role=role, permission=AdminPermission.objects.get(code="admin_access.view_adminrole")
    )
    return role


@pytest.fixture
def admin(catalogue):
    user = make_user(1)
    assign_role(CLI, user, "system_admin")
    return fresh(user)


class TestDenyByDefault:
    def test_ordinary_user_has_no_permission_and_no_admin_access(self, catalogue):
        user = make_user(2)
        assert permission_codes(user) == frozenset()
        assert not user.has_perm(MANAGE_ROLES)
        assert not user.has_module_perms("admin_access")
        assert not user.has_perm("accounts.view_user")
        assert not has_admin_access(user)
        assert user.is_staff is False

    def test_is_staff_alone_grants_nothing(self, catalogue):
        user = make_user(3)
        User.objects.filter(pk=user.pk).update(is_staff=True)  # forged projection
        user = fresh(user)
        assert not has_admin_access(user)
        assert not user.has_perm("accounts.view_user")
        assert AdminRoleBackend().get_all_permissions(user) == set()

    def test_django_groups_and_user_permissions_cannot_be_used(self, catalogue):
        user = make_user(4)
        perm = Permission.objects.get(codename="view_user")
        with pytest.raises(DatabaseError), transaction.atomic():
            user.user_permissions.add(perm)
        group = Group.objects.create(name="sneaky")
        with pytest.raises(DatabaseError), transaction.atomic():
            user.groups.add(group)
        backend = AdminRoleBackend()
        assert backend.get_user_permissions(user) == set()
        assert backend.get_group_permissions(user) == set()

    def test_role_grants_exactly_its_active_permissions(self, admin):
        assert admin.has_perm(MANAGE_ROLES)
        assert admin.has_perm("accounts.view_user")
        assert not admin.has_perm("accounts.change_user")
        assert not admin.has_perm("accounts.delete_user")
        assert admin.has_module_perms("admin_access")

    def test_inactive_permission_or_role_grants_nothing(self, admin):
        AdminPermission.objects.filter(code=MANAGE_ROLES).update(is_active=False)
        assert MANAGE_ROLES not in permission_codes(admin)
        AdminRole.objects.filter(code="system_admin").update(is_active=False)
        assert permission_codes(admin) == frozenset()
        assert not has_admin_access(admin)

    def test_deactivated_account_loses_everything(self, admin):
        User.objects.filter(pk=admin.pk).update(is_active=False, deactivated=True)
        admin = fresh(admin)
        assert permission_codes(admin) == frozenset()
        assert not admin.has_perm(MANAGE_ROLES)

    def test_object_permissions_are_never_granted(self, admin):
        assert AdminRoleBackend().has_perm(admin, MANAGE_ROLES, obj=admin) is False


class TestAssignment:
    def test_assign_sets_projection_and_audits(self, catalogue):
        target = make_user(5)
        row = assign_role(CLI, target, "system_admin")
        assert row.assigned_by is None and row.revoked_at is None
        assert fresh(target).is_staff is True
        entry = audits("admin.role_assign", "SUCCESS").get()
        assert entry.category == "ADMINISTRATIVE" and entry.actor_type == "SYSTEM"
        assert entry.safe_metadata["role"] == "system_admin"
        assert entry.safe_metadata["channel"] == "cli"
        assert entry.subject_pseudonym is not None

    def test_admin_with_manage_roles_can_assign(self, admin, limited_role):
        target = make_user(6)
        assign_role(Actor(user=admin), target, "viewer")
        assert permission_codes(fresh(target)) == {"admin_access.view_adminrole"}
        entry = audits("admin.role_assign", "SUCCESS").filter(actor_type="ADMIN").get()
        assert entry.actor_pseudonym is not None

    def test_ordinary_user_cannot_assign(self, catalogue):
        attacker, target = make_user(7), make_user(8)
        with pytest.raises(NotAuthorized):
            assign_role(Actor(user=attacker), target, "system_admin")
        assert not AdminUserRole.objects.filter(user=target).exists()
        assert audits("admin.role_assign", "DENIED").count() == 1

    def test_nobody_assigns_themselves(self, admin, limited_role):
        with pytest.raises(NotAuthorized):
            assign_role(Actor(user=admin), admin, "viewer")
        with pytest.raises(IntegrityError), transaction.atomic():
            AdminUserRole.objects.create(
                user=admin, role=limited_role, assigned_by=admin, assigned_at=timezone.now()
            )

    def test_no_escalation_beyond_the_assigners_permissions(self, admin, limited_role):
        # A role manager whose role lacks accounts.view_user can't grant a role that has it.
        manager = make_user(9)
        role = AdminRole.objects.create(code="role_manager", name="Role manager")
        AdminRolePermission.objects.create(
            role=role, permission=AdminPermission.objects.get(code=MANAGE_ROLES)
        )
        assign_role(CLI, manager, "role_manager")
        target = make_user(10)
        with pytest.raises(NotAuthorized):
            assign_role(Actor(user=fresh(manager)), target, "system_admin")
        # ... and it can't hand out its own manage_roles either via a broader role.
        assert not AdminUserRole.objects.filter(user=target).exists()

    def test_inactive_target_and_retired_role_are_refused(self, catalogue):
        target = make_user(11)
        User.objects.filter(pk=target.pk).update(is_active=False, deactivated=True)
        with pytest.raises(InvalidTarget):
            assign_role(CLI, fresh(target), "system_admin")
        AdminRole.objects.filter(code="system_admin").update(is_active=False)
        with pytest.raises(InvalidTarget):
            assign_role(CLI, make_user(12), "system_admin")
        with pytest.raises(InvalidTarget):
            assign_role(CLI, make_user(13), "no_such_role")

    def test_duplicate_live_assignment_is_refused(self, admin):
        with pytest.raises(AlreadyAssigned):
            assign_role(CLI, admin, "system_admin")
        assert AdminUserRole.objects.filter(user=admin).count() == 1

    def test_expired_assignment_grants_nothing_and_can_be_renewed(self, catalogue):
        target = make_user(14)
        row = assign_role(
            CLI, target, "system_admin", expires_at=timezone.now() + timedelta(hours=1)
        )
        expire(row)
        assert not has_admin_access(fresh(target))
        renewed = assign_role(CLI, target, "system_admin")
        assert AdminUserRole.objects.get(pk=row.pk).revoked_at is not None
        assert renewed.revoked_at is None

    def test_expiry_in_the_past_is_refused(self, catalogue):
        with pytest.raises(InvalidTarget):
            assign_role(CLI, make_user(15), "system_admin", expires_at=timezone.now())


class TestRevocation:
    def test_revoke_clears_projection_ends_admin_sessions_and_audits(self, admin):
        session = create_admin_session(admin, {})
        web = AuthSession.objects.create(
            user=admin,
            client_type="WEB",
            last_seen_at=timezone.now(),
            idle_expires_at=timezone.now() + timedelta(hours=1),
            absolute_expires_at=timezone.now() + timedelta(hours=2),
        )
        revoke_role(CLI, admin, "system_admin")
        assert fresh(admin).is_staff is False
        session.refresh_from_db()
        web.refresh_from_db()
        assert (session.status, session.revoked_reason) == ("REVOKED", "ADMIN")
        assert web.status == "ACTIVE"  # the user web session is not an admin session
        assert AdminUserRole.objects.get(user=admin).revoked_at is not None  # history kept
        assert audits("admin.role_revoke", "SUCCESS").count() == 1

    def test_revoking_twice_reports_not_assigned(self, admin):
        revoke_role(CLI, admin, "system_admin")
        with pytest.raises(NotAssigned):
            revoke_role(CLI, admin, "system_admin")

    def test_unauthorized_revocation_is_denied_and_audited(self, admin):
        with pytest.raises(NotAuthorized):
            revoke_role(Actor(user=make_user(16)), admin, "system_admin")
        assert fresh(admin).is_staff is True
        assert audits("admin.role_revoke", "DENIED").count() == 1

    def test_expiry_job_updates_projection_and_sessions(self, catalogue):
        target = make_user(17)
        row = assign_role(
            CLI, target, "system_admin", expires_at=timezone.now() + timedelta(hours=1)
        )
        session = create_admin_session(fresh(target), {})
        expire(row)
        assert sync_expired_assignments() == 1
        assert fresh(target).is_staff is False
        session.refresh_from_db()
        assert session.status == "REVOKED"
        assert sync_expired_assignments() == 0  # idempotent


class TestSuperusers:
    def test_createsuperuser_goes_through_the_audited_service(self, catalogue):
        user = User.objects.create_superuser(phone_number="+923001009001", password=PASSWORD)
        assert user.is_superuser and user.is_staff
        assert audits("admin.superuser_grant", "SUCCESS").count() == 1

    def test_at_most_two_superusers(self, catalogue):
        first, second, third = make_user(20), make_user(21), make_user(22)
        grant_superuser(CLI, first, reason_code="BOOTSTRAP")
        grant_superuser(CLI, second, reason_code="BOOTSTRAP")
        with pytest.raises(SuperuserLimitReached):
            grant_superuser(CLI, third, reason_code="BOOTSTRAP")
        assert not fresh(third).is_superuser
        assert audits("admin.superuser_grant", "DENIED").count() == 1
        # The database enforces it even for a direct write.
        with pytest.raises(IntegrityError), transaction.atomic():
            User.objects.filter(pk=third.pk).update(is_superuser=True)
        # Revoking one frees a slot.
        revoke_superuser(CLI, first, reason_code="ROTATION")
        grant_superuser(CLI, third, reason_code="ROTATION")
        assert User.objects.filter(is_superuser=True).count() == 2

    def test_only_a_superuser_or_the_operator_can_grant(self, admin):
        target = make_user(23)
        with pytest.raises(NotAuthorized):  # a system_admin is not a superuser
            grant_superuser(Actor(user=admin), target, reason_code="ESCALATE")
        assert not fresh(target).is_superuser
        assert audits("admin.superuser_grant", "DENIED").count() == 1

    def test_superuser_cannot_change_their_own_status(self, catalogue):
        boss = make_user(24)
        grant_superuser(CLI, boss, reason_code="BOOTSTRAP")
        with pytest.raises(NotAuthorized):
            revoke_superuser(Actor(user=fresh(boss)), boss, reason_code="SELF")

    def test_revoking_the_last_access_ends_admin_sessions(self, catalogue):
        boss = make_user(25)
        grant_superuser(CLI, boss, reason_code="BOOTSTRAP")
        session = create_admin_session(fresh(boss), {})
        revoke_superuser(CLI, boss, reason_code="DONE")
        boss = fresh(boss)
        assert not boss.is_superuser and not boss.is_staff
        session.refresh_from_db()
        assert session.status == "REVOKED"


@pytest.mark.django_db(transaction=True)
def test_concurrent_superuser_grants_never_exceed_two():
    users = [User.objects.create_user(phone_number=f"+92300200{i:04d}") for i in range(5)]
    barrier, outcomes = threading.Barrier(5), []

    def grant(user):
        try:
            barrier.wait()
            grant_superuser(CLI, user, reason_code="RACE")
            outcomes.append("ok")
        except SuperuserLimitReached:
            outcomes.append("limit")
        finally:
            connection.close()

    threads = [threading.Thread(target=grant, args=(u,)) for u in users]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes) == ["limit", "limit", "limit", "ok", "ok"]
    assert User.objects.filter(is_superuser=True).count() == 2


@pytest.mark.django_db(transaction=True)
def test_concurrent_assignments_create_one_live_row():
    sync_catalogue(CLI)
    target = User.objects.create_user(phone_number="+923003000001")
    barrier, outcomes = threading.Barrier(4), []

    def assign():
        try:
            barrier.wait()
            assign_role(CLI, target, "system_admin")
            outcomes.append("ok")
        except AlreadyAssigned:
            outcomes.append("dup")
        finally:
            connection.close()

    threads = [threading.Thread(target=assign) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes) == ["dup", "dup", "dup", "ok"]
    assert AdminUserRole.objects.filter(user=target, revoked_at__isnull=True).count() == 1
    assert User.objects.get(pk=target.pk).is_staff is True


class TestCatalogueAndCommand:
    def test_sync_is_idempotent_and_retires_unknown_entries(self, catalogue):
        assert sync_catalogue(CLI) == 0
        extra = AdminRole.objects.create(code="legacy", name="Legacy")
        holder = make_user(30)
        assign_role(CLI, holder, "legacy")
        assert fresh(holder).is_staff
        assert sync_catalogue(CLI) == 1
        assert not AdminRole.objects.get(pk=extra.pk).is_active
        assert not fresh(holder).is_staff
        assert audits("admin.catalogue_sync").count() == 2

    def test_cli_assign_and_revoke(self, catalogue):
        target = make_user(31)
        out = StringIO()
        call_command(
            "admin_access",
            "assign-role",
            "--phone",
            target.phone_number,
            "--role",
            "system_admin",
            stdout=out,
        )
        assert fresh(target).is_staff
        call_command(
            "admin_access",
            "revoke-role",
            "--phone",
            target.phone_number,
            "--role",
            "system_admin",
            stdout=out,
        )
        assert not fresh(target).is_staff
