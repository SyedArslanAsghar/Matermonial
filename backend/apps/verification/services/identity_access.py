"""Who may submit identity verification (OD-05c, owner decision DR-2026-11-20-O-4, final).

- Only the profile owner personally submits identity verification, from their own account.
- A family manager can't submit it on the owner's behalf and is never required to.
- No manager permission overrides this: ``manage_verification_submission`` is Owner-only
  (``family.0004``), so it can't be granted and a stored grant is ignored.

Identity verification itself is G5 Phase 5 (not authorized yet). This guard is the enforcement
point its endpoints and services must call first; it keeps identity verification separate from
profile management and manager authorization.
"""

from rest_framework import status
from rest_framework.exceptions import APIException


class OwnerMustSubmitIdentityVerification(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "identity_verification_owner_only"
    default_detail = (
        "Only the profile owner can submit identity verification, from their own account."
    )


def ensure_owner_submits(ctx) -> None:
    """``ctx`` is the request's ``ActorContext``. Raises for anyone but the owner, whatever
    permissions an authorization holds."""
    if not ctx.is_owner or ctx.authorization_id is not None:
        raise OwnerMustSubmitIdentityVerification()
    if ctx.actual_account.pk != ctx.represented_profile.owner_id:
        raise OwnerMustSubmitIdentityVerification()
