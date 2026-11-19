"""Code-defined catalogue of administrative permissions and roles (TR-07; doc 06 §15).

Role definitions are reviewed like code and applied with ``manage.py sync_admin_catalogue``
(idempotent and audited). The admin interface shows roles read-only, so nobody can widen a role
by editing it in the browser.

Only permissions for features that exist are listed. doc 06 §15 asks for separate support,
moderation, finance, verification and system-administration permissions: each later phase adds
its permissions and role here (support/admin operations Phase 16, moderation Phase 14,
verification Phase 5, finance Phase 13). Until then only ``system_admin`` exists.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionSpec:
    code: str
    name: str
    is_sensitive: bool = False
    description: str = ""


@dataclass(frozen=True)
class RoleSpec:
    code: str
    name: str
    permissions: tuple[str, ...]
    description: str = ""


MANAGE_ROLES = "admin_access.manage_roles"
RESET_ADMIN_MFA = "admin_access.reset_admin_mfa"
APPROVE_ADMIN_MFA_RECOVERY = "admin_access.approve_admin_mfa_recovery"

PERMISSIONS: tuple[PermissionSpec, ...] = (
    PermissionSpec(
        MANAGE_ROLES,
        "Assign and revoke administrative roles",
        is_sensitive=True,
        description="Grant only roles whose permissions the assigner already holds.",
    ),
    PermissionSpec(
        RESET_ADMIN_MFA,
        "Request MFA recovery for another administrator; issue first-enrollment codes",
        is_sensitive=True,
    ),
    PermissionSpec(
        APPROVE_ADMIN_MFA_RECOVERY,
        "Approve or reject another administrator's MFA recovery request (never one's own)",
        is_sensitive=True,
    ),
    PermissionSpec("admin_access.view_adminactionapproval", "View approval requests"),
    PermissionSpec("admin_access.view_adminrole", "View administrative roles"),
    PermissionSpec("admin_access.view_adminpermission", "View administrative permissions"),
    PermissionSpec("admin_access.view_adminuserrole", "View role assignments"),
    PermissionSpec(
        "admin_access.add_adminuserrole", "Assign roles in the admin", is_sensitive=True
    ),
    PermissionSpec("profiles.view_vocabularyoption", "View profile value lists"),
    PermissionSpec(
        "profiles.add_vocabularyoption",
        "Add profile value-list options",
        is_sensitive=True,
        description="New options start inactive unless activated; activation needs owner approval.",
    ),
    PermissionSpec(
        "profiles.change_vocabularyoption",
        "Relabel, reorder, activate or deactivate profile value-list options",
        is_sensitive=True,
    ),
    PermissionSpec(
        "accounts.view_user",
        "View accounts in the admin",
        is_sensitive=True,
        description="Shows phone numbers and email addresses.",
    ),
)

ROLES: tuple[RoleSpec, ...] = (
    RoleSpec(
        "system_admin",
        "System administrator",
        permissions=tuple(p.code for p in PERMISSIONS),
        description="Administers administrative access. Not a superuser.",
    ),
)
