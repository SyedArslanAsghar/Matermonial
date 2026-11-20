"""Helpers for services that act on a represented profile through an ``ActorContext``.

Lock order (doc 12 §5, doc 04 §24.1 step 13): the manager's authorization FOR SHARE (level 1;
re-checked: still ACTIVE, not expired, permissions still granted), the acting User FOR SHARE
(level 2), the represented profile FOR UPDATE (level 3, the state anchor), then, for a Sensitive
permission, the manager's step-up verification (domain level; consumed once, TR-16).
"""

from rest_framework.exceptions import NotFound

from apps.accounts.models import User
from apps.profiles.models import MatrimonialProfile
from common.db.locking import LockLevel, lock_rows_for_share, lock_rows_for_update

from ..context import (
    ActorContext,
    PermissionNotGranted,
    granted_codes,
    lock_authorization_for_write,
    sensitive_needed,
)
from ..models import ManagerActionLog

LEVELS = (LockLevel.AUTHORIZATION, LockLevel.ACCOUNT, LockLevel.PROFILE, LockLevel.DOMAIN)


def lock_represented_profile(
    ctx: ActorContext, *permissions: str, any_of: tuple[str, ...] = ()
) -> MatrimonialProfile:
    lock_authorization_for_write(ctx, *permissions)
    if any_of and not ctx.is_owner and not set(any_of) & granted_codes(ctx.authorization_id):
        raise PermissionNotGranted()
    lock_rows_for_share(User.objects.filter(pk=ctx.actual_account.pk), LockLevel.ACCOUNT)
    rows = lock_rows_for_update(
        MatrimonialProfile.objects.filter(pk=ctx.profile_id), LockLevel.PROFILE, anchor=True
    )
    if not rows:
        raise NotFound()
    needed = sensitive_needed(ctx, permissions) if permissions else []
    if any_of:
        needed += sensitive_needed(ctx, any_of, any_of=True)
    for action in sorted(set(needed)):
        from .step_up import consume

        consume(ctx, action)
    return rows[0]


def record_manager_action(
    ctx: ActorContext, action_type: str, target_model: str, target_id=None, description: str = ""
) -> None:
    """FR-FAM-009: what a manager did for the profile (owners' own actions aren't logged here)."""
    if ctx.is_owner:
        return
    ManagerActionLog.objects.create(
        authorization_id=ctx.authorization_id,
        profile_id=ctx.profile_id,
        manager=ctx.actual_account,
        action_type=action_type,
        target_model=target_model,
        target_id=target_id,
        description=description[:200],
        ip_address=ctx.ip,
        user_agent=ctx.user_agent,
    )
