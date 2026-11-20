"""Malware scanning (TR-10; owner decision DR-2026-11-20-O-8).

Outcomes: ``CLEAN`` and ``INFECTED`` come back as a ``ScanResult``. A scanner that can't give an
answer (unreachable, timeout, protocol error, scanner error) raises ``ScannerUnavailable``,
which callers record as ``FAILED`` and **never** treat as clean. Files stay quarantined until a
CLEAN result. Supported ``MALWARE_SCANNER`` values:

- ``mock`` (tests and local only; deployed settings refuse it): flags the EICAR test signature;
  bytes containing ``MOCK-SCANNER-UNAVAILABLE`` simulate an unavailable scanner.
- ``clamav``: the open-source ClamAV daemon (clamd) over TCP using its INSTREAM command. Set
  ``CLAMAV_HOST``, ``CLAMAV_PORT`` (3310) and ``CLAMAV_TIMEOUT_SECONDS``. No file leaves the
  infrastructure; nothing is sent to third-party services.
- ``disabled``: every scan is unavailable, so uploads are refused up front.
"""

import socket
import struct
from dataclasses import dataclass

from django.conf import settings

from .base import ProviderDisabledError, ProviderError, unknown

EICAR_MARKER = b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"
MOCK_UNAVAILABLE_MARKER = b"MOCK-SCANNER-UNAVAILABLE"
SUPPORTED = {"mock", "clamav", "disabled"}
CLEAN, INFECTED = "CLEAN", "INFECTED"


class ScannerUnavailable(ProviderError):
    def __init__(self, code: str = "scanner_unavailable"):
        super().__init__(code, retryable=True)


@dataclass(frozen=True)
class ScanResult:
    outcome: str  # CLEAN or INFECTED
    provider: str
    signature: str = ""  # the detected signature name (never file content)

    @property
    def clean(self) -> bool:
        return self.outcome == CLEAN


class MockScanner:
    name = "mock"

    def scan(self, data: bytes) -> ScanResult:
        if MOCK_UNAVAILABLE_MARKER in data:
            raise ScannerUnavailable("mock_unavailable")
        if EICAR_MARKER in data:
            return ScanResult(INFECTED, self.name, "Eicar-Test-Signature")
        return ScanResult(CLEAN, self.name)


class DisabledScanner:
    name = "disabled"

    def scan(self, data: bytes) -> ScanResult:
        raise ProviderDisabledError("Malware scanning is disabled in this environment.")


class ClamAVScanner:
    """clamd INSTREAM: ``zINSTREAM\\0``, then chunks prefixed with a 4-byte big-endian length,
    ending with a zero-length chunk. Replies: ``stream: OK``, ``stream: <name> FOUND`` or
    ``... ERROR``."""

    name = "clamav"
    CHUNK = 64 * 1024

    def __init__(self, host: str, port: int, timeout: float):
        self.host, self.port, self.timeout = host, port, timeout

    def scan(self, data: bytes) -> ScanResult:
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as conn:
                conn.settimeout(self.timeout)
                conn.sendall(b"zINSTREAM\0")
                for start in range(0, len(data), self.CHUNK):
                    chunk = data[start : start + self.CHUNK]
                    conn.sendall(struct.pack("!L", len(chunk)) + chunk)
                conn.sendall(struct.pack("!L", 0))
                reply = b""
                while not reply.endswith(b"\0") and len(reply) < 4096:
                    part = conn.recv(4096)
                    if not part:
                        break
                    reply += part
        except (OSError, TimeoutError):
            raise ScannerUnavailable("clamav_unreachable") from None
        return self.parse(reply)

    def parse(self, reply: bytes) -> ScanResult:
        text = reply.rstrip(b"\0").decode("utf-8", "replace").strip()
        if text.endswith("OK") and "FOUND" not in text:
            return ScanResult(CLEAN, self.name)
        if text.endswith("FOUND"):
            signature = text.split(":", 1)[-1].removesuffix("FOUND").strip()
            return ScanResult(INFECTED, self.name, signature[:120])
        raise ScannerUnavailable("clamav_error")  # "... ERROR", size limit, empty reply


def get_malware_scanner():
    choice = getattr(settings, "MALWARE_SCANNER", "disabled")
    if choice == "mock":
        return MockScanner()
    if choice == "clamav":
        return ClamAVScanner(
            settings.CLAMAV_HOST, settings.CLAMAV_PORT, settings.CLAMAV_TIMEOUT_SECONDS
        )
    if choice == "disabled":
        return DisabledScanner()
    raise unknown("MALWARE_SCANNER", choice, SUPPORTED)
