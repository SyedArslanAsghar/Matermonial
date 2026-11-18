"""Writing security events (TR-17, TR-23; doc 06 §22.3, doc 03 §22.2).

- Subject and actor are stored as pseudonyms. Personal context (IP address, user agent,
  approximate location) belongs to the actor's envelope; linkable identifiers about the subject
  (such as ``session_id``) go into the subject's envelope (linkable-ID rule).
- A failed login for an unknown phone has no resolvable subject: it stores only
  ``subject_hash = HMAC(SUBJECT_HASH key, normalised phone)``, never the phone.
- Flood control: while a subject or source is throttled, one RATE_LIMIT_TRIGGERED per window.
- The writers (auth, OTP, account-state services) arrive in G5 Phase 2.
"""

import uuid

from django.core.cache import cache
from django.utils import timezone

from common.crypto.aead import keyed_hash
from common.crypto.keys import ring

from ..models import AccountSecurityEvent
from ..models.security_events import EVENT_TYPES
from .pseudonyms import pseudonym_for, seal_envelopes

RATE_LIMIT_WINDOW_SECONDS = 15 * 60


def subject_hash(normalised_phone: str) -> str:
    return keyed_hash(ring("SUBJECT_HASH").active_key, normalised_phone)


def record_security_event(
    event_type: str,
    result: str,
    *,
    actor_type: str,
    subject_user_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    unknown_subject_phone: str | None = None,
    reason_code: str | None = None,
    request_id: str | None = None,
    actor_context: dict | None = None,
    subject_linkable: dict | None = None,
) -> AccountSecurityEvent:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown security event type: {event_type}")
    subject = pseudonym_for("ACCOUNT", subject_user_id) if subject_user_id else None
    if actor_type == AccountSecurityEvent.ActorType.SELF:
        actor = subject
    else:
        actor = pseudonym_for("ACCOUNT", actor_user_id) if actor_user_id else None

    event_id_value = AccountSecurityEvent._meta.pk.default()
    parts: dict[uuid.UUID, dict] = {}
    if actor and actor_context:
        parts.setdefault(actor, {}).update(actor_context)
    if subject and subject_linkable:
        parts.setdefault(subject, {}).update(subject_linkable)

    return AccountSecurityEvent.objects.create(
        id=event_id_value,
        event_type=event_type,
        result=result,
        reason_code=reason_code,
        actor_type=actor_type,
        request_id=request_id,
        occurred_at=timezone.now(),
        subject_pseudonym=subject,
        actor_pseudonym=actor,
        subject_hash=subject_hash(unknown_subject_phone)
        if subject is None and unknown_subject_phone
        else None,
        enc_parts=seal_envelopes(event_id_value, parts),
    )


def record_rate_limit_once(scope_key: str, **event_kwargs) -> AccountSecurityEvent | None:
    """Flood control: write RATE_LIMIT_TRIGGERED at most once per window per scope key.

    ``scope_key`` identifies the throttled subject or source (already hashed by the caller);
    cache.add is atomic, so concurrent rejections produce one row.
    """
    marker = "sec-ratelimit:" + keyed_hash(ring("SUBJECT_HASH").active_key, scope_key)
    if not cache.add(marker, 1, RATE_LIMIT_WINDOW_SECONDS):
        return None
    return record_security_event("RATE_LIMIT_TRIGGERED", "INFO", **event_kwargs)
