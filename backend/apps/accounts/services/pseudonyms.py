"""Pseudonyms, subject data keys and envelopes (TR-23; doc 03 §22.2, doc 06 §22.6).

- Eager creation: an account's pseudonym and data key are created in the same transaction as
  the account (``create_subject``; called by ``UserManager.create_user``).
- Envelopes: ``{pseudonym, key_id, kek_version, nonce, ciphertext}``, one per subject, sealed
  with AES-256-GCM under the subject's data key with the event ID and pseudonym as associated
  data, so an envelope can't be moved to another row or subject.
- After deletion PROCESSING (``unlink_subject`` + ``destroy_subject_key``) envelopes can no
  longer be opened: ``open_envelope`` returns None. The orchestration (Stream R SHRED,
  registry, holds) is the deletion workflow of G5 Phase 15.
"""

import base64
import os
import uuid
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from common.crypto.aead import open_json, open_sealed, seal, seal_json
from common.crypto.keys import ring

from ..models import SubjectDataKey, SubjectPseudonym

DATA_KEY_BYTES = 32


@dataclass(frozen=True)
class LiveKey:
    key_id: uuid.UUID
    kek_version: int
    key: bytes


def _key_aad(key_id: uuid.UUID) -> bytes:
    return b"matermonial:subject-data-key:" + key_id.bytes


def _envelope_aad(event_id: uuid.UUID, pseudonym: uuid.UUID) -> bytes:
    return b"matermonial:envelope:" + event_id.bytes + pseudonym.bytes


def _new_wrapped_key(key_id: uuid.UUID) -> tuple[int, bytes]:
    kek = ring("KEK")
    nonce, wrapped = seal(kek.active_key, os.urandom(DATA_KEY_BYTES), _key_aad(key_id))
    return kek.active_version, nonce + wrapped


@transaction.atomic
def create_subject(subject_type: str, subject_id: uuid.UUID) -> SubjectPseudonym:
    """Create the subject's pseudonym and live data key (idempotent per subject)."""
    existing = SubjectPseudonym.objects.filter(
        subject_type=subject_type, subject_id=subject_id
    ).first()
    if existing is not None:
        return existing
    pseudonym = SubjectPseudonym.objects.create(subject_type=subject_type, subject_id=subject_id)
    key_id = uuid.uuid4()
    kek_version, wrapped = _new_wrapped_key(key_id)
    SubjectDataKey.objects.create(
        key_id=key_id, pseudonym=pseudonym, kek_version=kek_version, wrapped_key=wrapped
    )
    return pseudonym


def pseudonym_for(subject_type: str, subject_id: uuid.UUID) -> uuid.UUID | None:
    """The linked pseudonym of a subject, or None (unknown or unlinked)."""
    return (
        SubjectPseudonym.objects.filter(subject_type=subject_type, subject_id=subject_id)
        .values_list("pseudonym", flat=True)
        .first()
    )


def live_key(pseudonym: uuid.UUID) -> LiveKey | None:
    row = SubjectDataKey.objects.filter(pseudonym_id=pseudonym, destroyed_at__isnull=True).first()
    if row is None:
        return None
    wrapped = bytes(row.wrapped_key)
    kek = ring("KEK")
    key = open_sealed(kek.key(row.kek_version), wrapped[:12], wrapped[12:], _key_aad(row.key_id))
    return LiveKey(row.key_id, row.kek_version, key)


def seal_envelopes(event_id: uuid.UUID, parts: dict[uuid.UUID, dict]) -> list[dict]:
    """One envelope per subject pseudonym. Subjects without a live key are skipped, because
    their personal context must not be stored (it could never be shredded)."""
    envelopes = []
    for pseudonym, content in parts.items():
        key = live_key(pseudonym)
        if key is None:
            continue
        nonce, ciphertext = seal_json(key.key, content, _envelope_aad(event_id, pseudonym))
        envelopes.append(
            {
                "pseudonym": str(pseudonym),
                "key_id": str(key.key_id),
                "kek_version": key.kek_version,
                "nonce": base64.b64encode(nonce).decode(),
                "ciphertext": base64.b64encode(ciphertext).decode(),
            }
        )
    return envelopes


def open_envelope(event_id: uuid.UUID, envelope: dict) -> dict | None:
    """Decrypt one envelope; None once the subject's key has been destroyed."""
    pseudonym = uuid.UUID(envelope["pseudonym"])
    key = live_key(pseudonym)
    if key is None or str(key.key_id) != envelope["key_id"]:
        return None
    return open_json(
        key.key,
        base64.b64decode(envelope["nonce"]),
        base64.b64decode(envelope["ciphertext"]),
        _envelope_aad(event_id, pseudonym),
    )


@transaction.atomic
def unlink_subject(pseudonym: uuid.UUID) -> None:
    """Break the pseudonym -> subject link (one-way; enforced by trigger)."""
    SubjectPseudonym.objects.filter(pseudonym=pseudonym, subject_id__isnull=False).update(
        subject_id=None, unlinked_at=timezone.now()
    )


@transaction.atomic
def destroy_subject_key(pseudonym: uuid.UUID) -> int:
    """Crypto-shred: drop the wrapped key, keep a non-sensitive tombstone. Returns rows changed.

    Old row versions persist until VACUUM and in WAL/backups; doc 06 §22.6 bounds that window
    by KEK destruction, which is production key management (deferred).
    """
    return SubjectDataKey.objects.filter(pseudonym_id=pseudonym, destroyed_at__isnull=True).update(
        wrapped_key=None, destroyed_at=timezone.now()
    )
