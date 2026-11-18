"""AES-256-GCM sealing and keyed hashes (TR-23 envelopes, TR-11 payloads, HMAC keys).

- Every seal uses a fresh 96-bit random nonce; associated data binds a ciphertext to its
  context (event ID, pseudonym, key ID) so it can't be replayed into another row.
- HMACs use the standard library (dedupe keys, unknown-phone subject hash, registry signing).
"""

import hashlib
import hmac
import json
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_BYTES = 12


class DecryptionError(Exception):
    """Ciphertext failed authentication (wrong key, wrong context or tampering)."""


def seal(key: bytes, plaintext: bytes, associated_data: bytes) -> tuple[bytes, bytes]:
    nonce = os.urandom(NONCE_BYTES)
    return nonce, AESGCM(key).encrypt(nonce, plaintext, associated_data)


def open_sealed(key: bytes, nonce: bytes, ciphertext: bytes, associated_data: bytes) -> bytes:
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, associated_data)
    except InvalidTag:
        raise DecryptionError("authentication failed") from None


def seal_json(key: bytes, value: dict, associated_data: bytes) -> tuple[bytes, bytes]:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return seal(key, payload, associated_data)


def open_json(key: bytes, nonce: bytes, ciphertext: bytes, associated_data: bytes) -> dict:
    return json.loads(open_sealed(key, nonce, ciphertext, associated_data))


def keyed_hash(key: bytes, message: str) -> str:
    """HMAC-SHA256 as lowercase hex."""
    return hmac.new(key, message.encode(), hashlib.sha256).hexdigest()
