"""G4 stage 5: pseudonyms, subject data keys and envelopes (TR-23; T-SEC subset)."""

import base64
import uuid
from io import StringIO
from unittest import mock

import pytest
from django.core.management import call_command
from django.db import DatabaseError, transaction

from apps.accounts.models import SubjectDataKey, SubjectPseudonym, User
from apps.accounts.services import pseudonyms as svc
from common.crypto.aead import DecryptionError
from common.crypto.keys import dev_key, ring

pytestmark = pytest.mark.django_db


def make_user(phone="+923001234567"):
    return User.objects.create_user(phone_number=phone, password="Strong-pass-123!")


def account_pseudonym(user):
    return svc.pseudonym_for("ACCOUNT", user.id)


def test_account_creation_eagerly_creates_pseudonym_and_live_key():
    user = make_user()
    pseudonym = account_pseudonym(user)
    assert pseudonym is not None
    key = SubjectDataKey.objects.get(pseudonym_id=pseudonym)
    assert key.destroyed_at is None and key.kek_version == ring("KEK").active_version


def test_account_and_pseudonym_commit_or_fail_together():
    with mock.patch.object(svc, "create_subject", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            make_user()
    assert not User.objects.filter(phone_number="+923001234567").exists()


def test_create_subject_is_idempotent_per_subject():
    user = make_user()
    again = svc.create_subject("ACCOUNT", user.id)
    assert again.pseudonym == account_pseudonym(user)
    assert SubjectPseudonym.objects.filter(subject_id=user.id).count() == 1


def test_wrapped_key_is_not_the_plain_data_key():
    user = make_user()
    row = SubjectDataKey.objects.get(pseudonym_id=account_pseudonym(user))
    live = svc.live_key(account_pseudonym(user))
    assert live.key not in bytes(row.wrapped_key)


def test_envelope_round_trip_and_binding_to_event_and_subject():
    user = make_user()
    pseudonym, event_id = account_pseudonym(user), uuid.uuid4()
    [envelope] = svc.seal_envelopes(event_id, {pseudonym: {"ip": "203.0.113.7"}})
    assert set(envelope) == {"pseudonym", "key_id", "kek_version", "nonce", "ciphertext"}
    assert "203.0.113.7" not in str(envelope)
    assert svc.open_envelope(event_id, envelope) == {"ip": "203.0.113.7"}
    with pytest.raises(DecryptionError):  # moved to another event
        svc.open_envelope(uuid.uuid4(), envelope)


def test_tampered_envelope_is_rejected():
    user = make_user()
    pseudonym, event_id = account_pseudonym(user), uuid.uuid4()
    [envelope] = svc.seal_envelopes(event_id, {pseudonym: {"ua": "x"}})
    raw = bytearray(base64.b64decode(envelope["ciphertext"]))
    raw[0] ^= 1
    envelope["ciphertext"] = base64.b64encode(bytes(raw)).decode()
    with pytest.raises(DecryptionError):
        svc.open_envelope(event_id, envelope)


def test_crypto_shredding_makes_envelopes_unreadable_and_keeps_a_tombstone():
    user = make_user()
    pseudonym, event_id = account_pseudonym(user), uuid.uuid4()
    [envelope] = svc.seal_envelopes(event_id, {pseudonym: {"ip": "198.51.100.1"}})
    svc.unlink_subject(pseudonym)
    assert svc.destroy_subject_key(pseudonym) == 1
    assert svc.open_envelope(event_id, envelope) is None
    tombstone = SubjectDataKey.objects.get(pseudonym_id=pseudonym)
    assert tombstone.wrapped_key is None and tombstone.destroyed_at is not None
    assert SubjectPseudonym.objects.get(pk=pseudonym).subject_id is None
    assert svc.seal_envelopes(uuid.uuid4(), {pseudonym: {"x": 1}}) == []


def test_database_guards_on_pseudonyms():
    user = make_user()
    pseudonym = account_pseudonym(user)
    with pytest.raises(DatabaseError), transaction.atomic():
        SubjectPseudonym.objects.filter(pk=pseudonym).delete()
    svc.unlink_subject(pseudonym)
    with pytest.raises(DatabaseError), transaction.atomic():  # never relinked
        SubjectPseudonym.objects.filter(pk=pseudonym).update(subject_id=user.id, unlinked_at=None)


def test_database_guards_on_keys():
    user = make_user()
    pseudonym = account_pseudonym(user)
    with pytest.raises(DatabaseError), transaction.atomic():
        SubjectDataKey.objects.filter(pseudonym_id=pseudonym).delete()
    svc.destroy_subject_key(pseudonym)
    with pytest.raises(DatabaseError), transaction.atomic():  # tombstone is frozen
        SubjectDataKey.objects.filter(pseudonym_id=pseudonym).update(wrapped_key=b"x" * 60)
    with pytest.raises(DatabaseError), transaction.atomic():  # CHECK: live needs a key
        SubjectDataKey.objects.create(pseudonym_id=pseudonym, kek_version=1, wrapped_key=None)


def test_old_kek_versions_still_unwrap_after_rotation(settings):
    user = make_user()
    v1_key = svc.live_key(account_pseudonym(user)).key
    v2 = base64.b64encode(dev_key("KEK", 2)).decode()
    settings.KEK_KEYS = f"{settings.KEK_KEYS},2:{v2}"
    settings.KEK_ACTIVE_VERSION = 2
    assert svc.live_key(account_pseudonym(user)).key == v1_key
    other = make_user("+923001234568")
    assert SubjectDataKey.objects.get(pseudonym_id=account_pseudonym(other)).kek_version == 2


def test_backfill_command_is_idempotent():
    User.objects.bulk_create([User(phone_number="+923009999999")])  # bypasses the manager
    out = StringIO()
    call_command("backfill_subject_pseudonyms", stdout=out)
    call_command("backfill_subject_pseudonyms", stdout=out)
    assert "Backfilled 1" in out.getvalue() and "Backfilled 0" in out.getvalue()
    user = User.objects.get(phone_number="+923009999999")
    assert account_pseudonym(user) is not None


def test_key_ring_repr_never_shows_key_material():
    text = repr(ring("KEK"))
    assert base64.b64encode(dev_key("KEK")).decode() not in text and "versions=[1]" in text
