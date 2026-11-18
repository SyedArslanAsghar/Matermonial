"""Versioned key rings (doc 16 §10; TR-23, TR-11, TR-24).

Every key is 32 bytes, configured as ``"<version>:<base64>,<version>:<base64>"`` plus an
active version. Key material never enters the database, Git or logs.

Local and test settings use **dev-only** keys derived from a public label (``dev_keyring``).
They are deliberately not secret, so they must never protect real data: deployed settings
refuse them (common.config). Production key management (secret store, rotation, KEK
destruction schedule) is deployment work, deferred with AWS (DR-2026-11-18-CI).
"""

import base64
import binascii
import hashlib
from dataclasses import dataclass

KEY_BYTES = 32
DEV_LABEL = "matermonial-dev-only-not-secret"

# Purposes (doc 16 §10.1): KEK wraps subject data keys; QUEUE encrypts outbox payloads;
# DEDUPE keys the outbox dedupe HMAC; SUBJECT_HASH keys the unknown-phone HMAC;
# REGISTRY signs compliance-registry entries; OTP keys the one-time-code hash (doc 06 §3);
# ROT is K_rot, which derives child tokens in refresh rotation (TR-01, doc 06 §22.1).
PURPOSES = ("KEK", "QUEUE", "DEDUPE", "SUBJECT_HASH", "REGISTRY", "OTP", "ROT")


class KeyConfigurationError(Exception):
    """A key ring is missing, malformed or lacks its active version."""


def dev_key(purpose: str, version: int = 1) -> bytes:
    return hashlib.sha256(f"{DEV_LABEL}:{purpose}:v{version}".encode()).digest()


def dev_keyring(purpose: str) -> str:
    """Key-ring spec holding the dev-only key for ``purpose`` at version 1."""
    return f"1:{base64.b64encode(dev_key(purpose)).decode()}"


def parse_keyring(spec: str) -> dict[int, bytes]:
    """Parse ``"1:<b64>,2:<b64>"``. Errors never include key material."""
    ring: dict[int, bytes] = {}
    for item in filter(None, (part.strip() for part in (spec or "").split(","))):
        version_text, sep, encoded = item.partition(":")
        if not sep or not version_text.isdigit():
            raise KeyConfigurationError("Key ring entries must look like '<version>:<base64>'.")
        try:
            key = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            raise KeyConfigurationError(
                f"Key version {version_text} is not valid base64."
            ) from None
        if len(key) != KEY_BYTES:
            raise KeyConfigurationError(f"Key version {version_text} must be {KEY_BYTES} bytes.")
        ring[int(version_text)] = key
    if not ring:
        raise KeyConfigurationError("Key ring is empty.")
    return ring


@dataclass(frozen=True)
class KeyRing:
    purpose: str
    keys: dict[int, bytes]
    active_version: int

    def __post_init__(self):
        if self.active_version not in self.keys:
            raise KeyConfigurationError(f"{self.purpose}: active version is not in the key ring.")

    @property
    def active_key(self) -> bytes:
        return self.keys[self.active_version]

    def key(self, version: int) -> bytes:
        try:
            return self.keys[version]
        except KeyError:
            raise KeyConfigurationError(
                f"{self.purpose}: key version {version} unavailable."
            ) from None

    def uses_dev_keys(self) -> bool:
        return any(key == dev_key(self.purpose, v) for v, key in self.keys.items())

    def __repr__(self):  # never print key material
        return (
            f"KeyRing({self.purpose}, versions={sorted(self.keys)}, active={self.active_version})"
        )


def ring(purpose: str) -> KeyRing:
    """The configured key ring for ``purpose`` (settings ``<PURPOSE>_KEYS`` / ``..._ACTIVE_VERSION``)."""
    from django.conf import settings

    return KeyRing(
        purpose=purpose,
        keys=parse_keyring(getattr(settings, f"{purpose}_KEYS")),
        active_version=getattr(settings, f"{purpose}_ACTIVE_VERSION"),
    )
