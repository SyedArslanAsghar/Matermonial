"""Writing the central audit log (ADR-022, TR-23; doc 06 §22.3, doc 03 §22.2 envelopes rule).

- References are pseudonyms; request context (IP, user agent, location) goes into the actor's
  envelope; linkable IDs about a target go into the target's envelope.
- ``safe_metadata`` holds only allowlisted structured values: keys are snake_case and values are
  numbers, booleans, null, or code-like strings. Free-text personal content is rejected.
- Holds: ``place_hold`` links events to a hold case; partitions holding linked events are
  archived into ``audit_log_hold`` by the maintenance role when dropped (doc 09).
"""

import re
import uuid

from django.utils import timezone

from apps.accounts.services.pseudonyms import pseudonym_for, seal_envelopes

from .models import AuditLog, AuditLogHoldLink

CODE = re.compile(r"^[a-z][a-z0-9_.]{1,99}$")
META_KEY = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
META_STRING = re.compile(r"^[A-Za-z0-9_.:-]{0,64}$")


class UnsafeAuditData(ValueError):
    """Audit input would store free text or a non-code value in plaintext."""


def _check_metadata(metadata: dict) -> dict:
    for key, value in metadata.items():
        if not META_KEY.fullmatch(key):
            raise UnsafeAuditData(f"metadata key {key!r} is not snake_case")
        if isinstance(value, str):
            if not META_STRING.fullmatch(value):
                raise UnsafeAuditData(f"metadata {key!r} must be a code, not free text")
        elif value is not None and not isinstance(value, bool | int | float):
            raise UnsafeAuditData(f"metadata {key!r} must be a scalar")
    return metadata


def _account(user_id):
    return pseudonym_for("ACCOUNT", user_id) if user_id else None


def record_audit(
    *,
    action: str,
    resource_type: str,
    actor_type: str,
    result: str,
    category: str,
    actor_user_id: uuid.UUID | None = None,
    subject_user_id: uuid.UUID | None = None,
    represented_profile_pseudonym: uuid.UUID | None = None,
    request_id: str | None = None,
    metadata: dict | None = None,
    actor_context: dict | None = None,
    subject_linkable: dict | None = None,
) -> AuditLog:
    if not CODE.fullmatch(action) or not CODE.fullmatch(resource_type):
        raise UnsafeAuditData("action and resource_type must be dotted lowercase codes")
    actor, subject = _account(actor_user_id), _account(subject_user_id)
    event_id = AuditLog._meta.pk.default()
    parts: dict[uuid.UUID, dict] = {}
    if actor and actor_context:
        parts.setdefault(actor, {}).update(actor_context)
    if subject and subject_linkable:
        parts.setdefault(subject, {}).update(subject_linkable)
    return AuditLog.objects.create(
        id=event_id,
        occurred_at=timezone.now(),
        actor_type=actor_type,
        actor_pseudonym=actor,
        subject_pseudonym=subject,
        represented_profile_pseudonym=represented_profile_pseudonym,
        action=action,
        resource_type=resource_type,
        result=result,
        category=category,
        request_id=request_id,
        safe_metadata=_check_metadata(metadata or {}),
        enc_parts=seal_envelopes(event_id, parts),
    )


def place_hold(event_ids: list[uuid.UUID], hold_case_id: uuid.UUID) -> int:
    """Link events to a legal or security hold case (idempotent)."""
    now = timezone.now()
    links = [
        AuditLogHoldLink(event_id=e, hold_case_id=hold_case_id, created_at=now) for e in event_ids
    ]
    return len(AuditLogHoldLink.objects.bulk_create(links, ignore_conflicts=True))
