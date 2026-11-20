"""Provider abstractions: SMS, email, push and malware scanning (CLAUDE.md CC-R55, CC-R56;
doc 04 §17–§22; doc 16 §5; owner decisions DR-2026-11-20-O-7, -8). See ``base`` for the shared
rules and each module for its supported providers and configuration. The payment provider is
defined with the payments phase (Phase 13)."""

from .base import DisabledProvider, DispatchResult, ProviderDisabledError, ProviderError
from .email import DisabledEmailBackend, send_email
from .push import (
    ConsolePushProvider,
    ExpoPushProvider,
    MockPushProvider,
    PushProvider,
    get_push_provider,
)
from .scanning import (
    CLEAN,
    EICAR_MARKER,
    INFECTED,
    MOCK_UNAVAILABLE_MARKER,
    ClamAVScanner,
    DisabledScanner,
    MockScanner,
    ScannerUnavailable,
    ScanResult,
    get_malware_scanner,
)
from .sms import (
    ConsoleSMSProvider,
    MockSMSProvider,
    SMSProvider,
    TwilioSMSProvider,
    get_sms_provider,
)

__all__ = [
    "CLEAN",
    "EICAR_MARKER",
    "INFECTED",
    "MOCK_UNAVAILABLE_MARKER",
    "ClamAVScanner",
    "ConsolePushProvider",
    "ConsoleSMSProvider",
    "DisabledEmailBackend",
    "DisabledProvider",
    "DisabledScanner",
    "DispatchResult",
    "ExpoPushProvider",
    "MockPushProvider",
    "MockSMSProvider",
    "MockScanner",
    "ProviderDisabledError",
    "ProviderError",
    "PushProvider",
    "SMSProvider",
    "ScanResult",
    "ScannerUnavailable",
    "TwilioSMSProvider",
    "get_malware_scanner",
    "get_push_provider",
    "get_sms_provider",
    "send_email",
]
