"""Mobile token values (TR-01; doc 06 §22.1 §8.3).

- 256-bit random values, prefixed ``mat_at_`` (access) / ``mat_rt_`` (refresh); only the
  SHA-256 hex digest is stored, and plaintext is never logged.
- Rotation derives the children deterministically:
  ``HMAC-SHA256(K_rot[v], parent ‖ label ‖ generation)``, so a retried refresh within the grace
  window recomputes the identical pair without any plaintext being stored.
"""

import base64
import hashlib
import hmac
import secrets

from common.crypto.keys import ring

ACCESS_PREFIX, REFRESH_PREFIX = "mat_at_", "mat_rt_"


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def random_pair() -> tuple[str, str]:
    return ACCESS_PREFIX + _encode(secrets.token_bytes(32)), REFRESH_PREFIX + _encode(
        secrets.token_bytes(32)
    )


def derived_pair(parent_refresh: str, generation: int, key_version: int) -> tuple[str, str]:
    key = ring("ROT").key(key_version)

    def derive(label: str) -> bytes:
        message = f"{parent_refresh}\x00{label}\x00{generation}".encode()
        return hmac.new(key, message, hashlib.sha256).digest()

    return ACCESS_PREFIX + _encode(derive("access")), REFRESH_PREFIX + _encode(derive("refresh"))


def looks_like(value: str, prefix: str) -> bool:
    return isinstance(value, str) and value.startswith(prefix) and 40 <= len(value) <= 60
