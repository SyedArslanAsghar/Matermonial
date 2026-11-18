"""Compliance registry: entry format and the local backend (TR-24; doc 03 §22.15 A.1, doc 09 §19).

Entry = ``{header, params, entry_hash, signature}``:
- ``H_in = "MATREG" 0x00 "v1" 0x00 JCS(header)``; ``entry_hash = SHA-256(H_in)``;
  ``signature = HMAC-SHA256(K_reg[registry_key_version], entry_hash)``.
- ``params_digest = SHA-256(JCS(params))`` binds params to the header. Params are stored only in
  the registry, never locally (keeps Stream R pseudonyms out of the long-lived local log).

JCS (RFC 8785) here: UTF-8, keys sorted, no insignificant whitespace. Our values are strings,
integers below 2^53, booleans, null, lists and objects with ASCII keys, for which sorted-key
compact JSON is exactly the JCS form. UUIDs are lowercase; timestamps RFC 3339 UTC with
milliseconds and ``Z``.

``LocalRegistry`` (COMPLIANCE_REGISTRY_BACKEND = "local"; development and tests only) stores one
write-once file per ``<stream>/<seq>``: exclusive create is the local equivalent of the
external store's conditional create (``If-None-Match: *``). Deployed environments refuse it.
"""

import hashlib
import hmac
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings

from common.crypto.keys import ring

SCHEMA_VERSION = 1
GENESIS_HASH = "0" * 64


class RegistryError(Exception):
    pass


class EntryExists(RegistryError):
    """The stream already has an entry at this sequence number."""


class IntegrityAlarm(RegistryError):
    """An entry failed signature, hash, chain or params verification."""


def jcs(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def rfc3339(moment: datetime) -> str:
    """RFC 3339 UTC with milliseconds and ``Z`` (registry encoding rule)."""
    utc = moment.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def entry_hash(header: dict) -> str:
    return sha256_hex(b"MATREG\x00v1\x00" + jcs(header))


def sign(entry_hash_hex: str, key_version: int) -> str:
    key = ring("REGISTRY").key(key_version)
    return hmac.new(key, entry_hash_hex.encode(), hashlib.sha256).hexdigest()


def build_entry(header: dict, params: dict) -> dict:
    header = {**header, "params_digest": sha256_hex(jcs(params))}
    digest = entry_hash(header)
    return {
        "header": header,
        "params": params,
        "entry_hash": digest,
        "signature": sign(digest, header["registry_key_version"]),
    }


def verify_entry(entry: dict, previous: dict | None) -> None:
    """Reconstruction checks 2-5 of doc 03 §22.15 A.1; raises IntegrityAlarm."""
    header = entry["header"]
    expected_sig = sign(entry["entry_hash"], header["registry_key_version"])
    if not hmac.compare_digest(expected_sig, entry["signature"]):
        raise IntegrityAlarm(f"bad signature at {header['stream']}/{header['seq']}")
    if entry_hash(header) != entry["entry_hash"]:
        raise IntegrityAlarm(f"hash mismatch at {header['stream']}/{header['seq']}")
    if sha256_hex(jcs(entry["params"])) != header["params_digest"]:
        raise IntegrityAlarm(f"params digest mismatch at {header['stream']}/{header['seq']}")
    prev_hash = previous["entry_hash"] if previous else GENESIS_HASH
    prev_seq = previous["header"]["seq"] if previous else 0
    if header["prev_hash"] != prev_hash or header["seq"] != prev_seq + 1:
        raise IntegrityAlarm(f"broken chain at {header['stream']}/{header['seq']}")


class LocalRegistry:
    def __init__(self, location: str | os.PathLike | None = None):
        self.root = Path(location or settings.COMPLIANCE_REGISTRY_LOCATION)

    def _path(self, stream: str, seq: int) -> Path:
        return self.root / stream / f"{seq:012d}.json"

    def put(self, entry: dict) -> None:
        header = entry["header"]
        path = self._path(header["stream"], header["seq"])
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "x", encoding="utf-8") as handle:  # write-once
                handle.write(jcs(entry).decode())
        except FileExistsError:
            raise EntryExists(f"{header['stream']}/{header['seq']}") from None

    def get(self, stream: str, seq: int) -> dict | None:
        path = self._path(stream, seq)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def entries(self, stream: str):
        seq = 1
        while (entry := self.get(stream, seq)) is not None:
            yield entry
            seq += 1

    def verify_stream(self, stream: str) -> int:
        """Verify every entry of a stream from genesis; returns the number verified."""
        previous, count = None, 0
        for entry in self.entries(stream):
            verify_entry(entry, previous)
            previous, count = entry, count + 1
        return count


def get_registry():
    backend = settings.COMPLIANCE_REGISTRY_BACKEND
    if backend in ("local", "mock"):
        return LocalRegistry()
    raise RegistryError(f"Registry backend {backend!r} is not available in this build.")
