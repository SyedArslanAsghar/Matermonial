"""Implicit foreign-key lock inventory (doc 12 §5.5; TR-22, approved).

Rule: every foreign key in a project app must be assigned an implicit-lock class at design
review. An unclassified foreign key fails the test suite (tests/test_architecture_rules.py).

Classes (doc 12 §5.5, inventory from baseline v4.5 §6.1):
- P  prior-locked: the transaction already holds FOR SHARE or stronger on the referenced row
- S  soft reference: no database FK, no implicit lock
- B1 counterparty profile in a protective action (bounded wait)
- B2 staff actor User (bounded wait)
- N  the transaction holds no other locks when the FK check runs
"""

from django.apps import apps

LOCK_CLASSES = frozenset({"P", "S", "B1", "B2", "N"})

# "<app_label>.<Model>.<field>": class
FK_LOCK_CLASSES: dict[str, str] = {
    # doc 12 §5.5 class B2: created_by/updated_by where the actor is staff, including the
    # User.updated_by self-FK.
    "accounts.User.created_by": "B2",
    "accounts.User.updated_by": "B2",
    # TR-01 lock order (doc 06 §22.1 amendment): login, refresh, logout and revocation take
    # the account's User FOR SHARE first, and refresh locks AuthSession before AuthToken.
    "accounts.AuthSession.user": "P",
    "accounts.AuthToken.session": "P",
    # TR-23: a data key is created in the same transaction as its pseudonym, and key
    # destruction runs inside the deletion step that already locks the subject.
    "accounts.SubjectDataKey.pseudonym": "P",
    # The idempotent operation runs inside a service that has already locked the account
    # (doc 12 §5: account level 2 precedes inserts).
    "idempotency.IdempotencyRecord.account": "P",
    # Maintenance lock domain (doc 09 §19.2): the operation row is locked first; the approver
    # is a staff actor (class B2, bounded wait).
    "platform_ops.MaintenanceApproval.operation": "P",
    "platform_ops.MaintenanceApproval.approver": "B2",
    # TR-07 admin access: every write locks the target User FOR UPDATE first (level 2), so the
    # account FK is prior-locked; the acting administrator is a staff actor (B2). Role and
    # permission rows are reference data changed only by the catalogue sync, outside business
    # transactions (N).
    "admin_access.AdminUserRole.user": "P",
    "admin_access.AdminUserRole.assigned_by": "B2",
    "admin_access.AdminUserRole.role": "N",
    "admin_access.AdminRolePermission.role": "N",
    "admin_access.AdminRolePermission.permission": "N",
    "admin_access.AdminTotpDevice.user": "P",
    "admin_access.AdminMfaEnrollment.user": "P",
    "admin_access.AdminMfaEnrollment.issued_by": "B2",
    # Recovery approvals: the target User is locked first; the people are staff actors (B2).
    "admin_access.AdminActionApproval.requested_by": "B2",
    "admin_access.AdminActionApproval.approved_by": "B2",
    "admin_access.AdminActionApproval.rejected_by": "B2",
    # Profiles (Phase 3): the owner/actor User is locked FOR SHARE first and the profile FOR
    # UPDATE before any section write, so every FK below is prior-locked.
    "profiles.MatrimonialProfile.owner": "P",
    "profiles.MatrimonialProfile.created_by": "P",
    "profiles.MatrimonialProfile.updated_by": "P",
    "profiles.ProfileBasicInfo.profile": "P",
    "profiles.ProfileLocation.profile": "P",
    "profiles.ProfileFamilyDetails.profile": "P",
    "profiles.ProfileEducation.profile": "P",
    "profiles.ProfileProfession.profile": "P",
    "profiles.ProfileLifestyle.profile": "P",
    "profiles.ProfileLanguage.profile": "P",
    "profiles.PartnerPreference.profile": "P",
    "profiles.ProfilePhoto.profile": "P",
    # Reference data edited in the admin, outside business transactions.
    "profiles.VocabularyOption.parent": "N",
    "profiles.ProfilePhoto.uploaded_by": "P",
    "profiles.PartnerPreferenceLocation.preference": "P",
    "profiles.PartnerPreferenceEducation.preference": "P",
    "profiles.PartnerPreferenceLanguage.preference": "P",
    "profiles.PartnerPreferenceReligion.preference": "P",
    # Family management (Phase 4): writes lock the authorization (level 1), then the acting
    # account(s) FOR SHARE (level 2), then the profile; access history is a lone autocommit
    # insert (N); catalogue and templates are reference data (N).
    "family.ProfileManagerAuthorization.profile": "P",
    "family.ProfileManagerAuthorization.manager": "P",
    "family.ProfileManagerAuthorization.invited_by": "P",
    "family.ProfileManagerAuthorization.permission_group": "N",
    "family.AuthorizationPermission.authorization": "P",
    "family.AuthorizationPermission.permission": "N",
    "family.AuthorizationPermission.granted_by": "P",
    "family.ManagerAuthorizationHistory.authorization": "P",
    "family.ManagerAuthorizationHistory.performed_by": "P",
    "family.ManagerActionLog.authorization": "P",
    "family.ManagerActionLog.profile": "P",
    "family.ManagerActionLog.manager": "P",
    "family.ProfileAccessHistory.profile": "N",
    "family.ProfileAccessHistory.authorization": "N",
    "family.ProfileAccessHistory.manager": "N",
    # Invitations (KI-34): the invite request locks the owner and any matched invitee account
    # FOR SHARE (level 2) and the profile FOR UPDATE (level 3) before the insert; the
    # resolution task does the same and links an authorization it created in that transaction;
    # the template is reference data (N).
    "family.ManagerInvitation.profile": "P",
    "family.ManagerInvitation.invited_by": "P",
    "family.ManagerInvitation.invitee": "P",
    "family.ManagerInvitation.authorization": "P",
    "family.ManagerInvitation.permission_group": "N",
    # Owner decisions DR-2026-11-20-O-1..3: history rows are written after their invitation,
    # request or authorization is locked or inserted in the same transaction; requests lock the
    # requester and owner accounts (2) and the profile (3) first; step-up locks the
    # authorization (1), the manager account (2) and the profile (3) before inserting.
    "family.ManagerAuthorizationHistory.invitation": "P",
    "family.ManagerAuthorizationHistory.request": "P",
    "family.ManagerRequest.requester": "P",
    "family.ManagerRequest.owner": "P",
    "family.ManagerRequest.profile": "P",
    "family.ManagerRequest.authorization": "P",
    "family.SensitiveActionVerification.manager": "P",
    "family.SensitiveActionVerification.profile": "P",
    "family.SensitiveActionVerification.authorization": "P",
    "family.ManagerPermissionGroupPermission.group": "N",
    "family.ManagerPermissionGroupPermission.permission": "N",
    # OTP verify locks the account (level 2) before the verification row; send runs with no
    # other business locks.
    "verification.PhoneVerification.user": "P",
    # Notifications (DR-2026-11-20-O-7): the handler locks the recipient account (2) and their
    # active devices (domain) FOR SHARE before inserting; the delivery's notification is
    # inserted in the same transaction; device registration locks the account first.
    "notifications.InAppNotification.recipient": "P",
    "notifications.PushDevice.user": "P",
    "notifications.NotificationDelivery.notification": "P",
    "notifications.NotificationDelivery.device": "P",
    # Account authenticator (TR-16): every write locks the account FOR SHARE first.
    "accounts.AccountTotpDevice.user": "P",
}


def project_foreign_keys() -> list[str]:
    """Every concrete FK/OneToOne declared by models in project apps (``apps.*``, ``common.*``)."""
    found = []
    for model in apps.get_models():
        if not model._meta.app_config.name.startswith(("apps.", "common.")):
            continue
        for field in model._meta.get_fields():
            if field.concrete and (field.many_to_one or field.one_to_one):
                found.append(f"{model._meta.app_label}.{model.__name__}.{field.name}")
    return sorted(found)


def unclassified_foreign_keys() -> list[str]:
    return [fk for fk in project_foreign_keys() if fk not in FK_LOCK_CLASSES]
