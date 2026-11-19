"""Read side of administrative authorization (TR-07). Deny by default.

An account has an administrative permission only when **all** hold:
- the account is active and not deactivated;
- it has an assignment that is not revoked and not expired;
- the assigned role is active, and the permission is active and linked to that role.

``is_staff`` is never consulted here: it is only a projection of this data.
"""

from django.db.models import Q, QuerySet
from django.utils import timezone

from .models import AdminPermission, AdminUserRole


def live_assignments(user, now=None) -> QuerySet[AdminUserRole]:
    now = now or timezone.now()
    return AdminUserRole.objects.filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now),
        user_id=user.pk,
        revoked_at__isnull=True,
        role__is_active=True,
    )


def account_eligible(user) -> bool:
    return bool(
        user is not None
        and getattr(user, "is_authenticated", False)
        and user.is_active
        and not user.deactivated
    )


def has_live_role(user, now=None) -> bool:
    return account_eligible(user) and live_assignments(user, now).exists()


def permission_codes(user, now=None) -> frozenset[str]:
    """Active permission codes granted to ``user`` through live role assignments."""
    if not account_eligible(user):
        return frozenset()
    now = now or timezone.now()
    codes = AdminPermission.objects.filter(
        Q(roles__assignments__expires_at__isnull=True) | Q(roles__assignments__expires_at__gt=now),
        is_active=True,
        roles__is_active=True,
        roles__assignments__user_id=user.pk,
        roles__assignments__revoked_at__isnull=True,
    ).values_list("code", flat=True)
    return frozenset(codes)


def has_admin_access(user) -> bool:
    """May this account use the admin site at all (before MFA)? Superusers are break-glass."""
    if not account_eligible(user):
        return False
    return bool(user.is_superuser) or has_live_role(user)
