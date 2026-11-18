"""Local cache of registry SHRED entries (TR-23; doc 03 §22.2).

Re-applying is insert-or-nothing; an existing row with a different ``op_id`` or
``keys_digest`` is an integrity alarm (doc 09). Rows never expire and are never updated
(append-only trigger). Written by the Stream R SHRED workflow (G5 Phase 15) and by restore.
"""

from django.db import IntegrityError, transaction

from ..models import ShreddedPseudonym
from ..registry import IntegrityAlarm


def record_shred(
    *, pseudonym, subject_type, keys_digest, op_id, intent_seq, intent_entry_hash, shredded_at
) -> bool:
    """Returns True when inserted, False when the identical row already existed."""
    try:
        with transaction.atomic():
            ShreddedPseudonym.objects.create(
                pseudonym=pseudonym,
                subject_type=subject_type,
                keys_digest=keys_digest,
                op_id=op_id,
                intent_seq=intent_seq,
                intent_entry_hash=intent_entry_hash,
                shredded_at=shredded_at,
            )
            return True
    except IntegrityError:
        existing = ShreddedPseudonym.objects.get(pseudonym=pseudonym)
        if existing.op_id != op_id or existing.keys_digest != keys_digest:
            raise IntegrityAlarm(
                "shredded pseudonym re-applied with different op or keys"
            ) from None
        return False
