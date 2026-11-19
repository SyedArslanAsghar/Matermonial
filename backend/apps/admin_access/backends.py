"""The only Django authentication backend (TR-07, ADR-027; doc 03 §22.15).

Password authentication is Django's ``ModelBackend`` (phone number + password, inactive
accounts refused). Permissions come only from the AdminRole tables (``selectors``); Django
groups and ``user_permissions`` always yield nothing. Every answer is deny-by-default and is
computed per request (cached on the user object for that request only).

``is_superuser`` keeps Django's meaning (all permissions) because it is the break-glass account
type: at most two, granted only by ``services.superusers``, audited, and the admin site still
requires MFA and a valid admin session before any permission is used.
"""

from django.contrib.auth.backends import ModelBackend

from .selectors import account_eligible, permission_codes

_CACHE = "_admin_role_perm_cache"


class AdminRoleBackend(ModelBackend):
    def get_user_permissions(self, user_obj, obj=None):
        return set()

    def get_group_permissions(self, user_obj, obj=None):
        return set()

    def get_all_permissions(self, user_obj, obj=None):
        if obj is not None or not account_eligible(user_obj):
            return set()
        if not hasattr(user_obj, _CACHE):
            setattr(user_obj, _CACHE, permission_codes(user_obj))
        return set(getattr(user_obj, _CACHE))

    def has_perm(self, user_obj, perm, obj=None):
        return perm in self.get_all_permissions(user_obj, obj)

    def has_module_perms(self, user_obj, app_label):
        prefix = f"{app_label}."
        return any(code.startswith(prefix) for code in self.get_all_permissions(user_obj))

    def with_perm(self, perm, is_active=True, include_superusers=True, obj=None):
        raise NotImplementedError("Query AdminUserRole through apps.admin_access.selectors.")
