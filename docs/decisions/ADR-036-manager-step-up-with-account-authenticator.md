# ADR-036: Manager step-up for Sensitive actions with the account authenticator (TR-16)

- **Status:** ACCEPTED for implementation (owner decision DR-2026-11-20-O-3, 2026-11-20); TR-16 approved. Owner review pending.
- **Context:** doc 04 §24.1 step 10; FR-FAM-005; doc 14; ADR-033 (admin authenticator design reused).

## Decision

- **Account authenticator:** optional TOTP enrollment for every account (`AccountTotpDevice`). The seed is sealed with AES-256-GCM under a new `ACCOUNT_MFA` key ring, bound to the account, and shown once. Enrolling or removing needs a recent password step-up. Each time step is accepted once, with django-otp exponential throttling. Events: `ACCOUNT_MFA_ENROLLED` / `_REMOVED` / `_FAILED`. Endpoints: `/api/v1/auth/mfa/` (status), `enroll/`, `confirm/`, `remove/`.
- **Step-up:** `POST /api/v1/profiles/step-up/` with `X-Acting-Profile` and `{action, code}`. The action must be a Sensitive permission currently granted on the manager's authorization; the code must match the manager's own authenticator. The result is a `SensitiveActionVerification` bound to manager, profile, authorization and action, valid for at most 300 s.
- **Use:** the Sensitive request sends `X-Step-Up-Verification`. In the business transaction, after the profile lock, the verification is locked and consumed once (domain level). If it is missing, expired, used, or for another manager, profile or action, the request is refused with `403 step_up_required`. One Sensitive action per request. The owner is notified (`family.sensitive_action`) and every step is audited (`family.step_up_verified/failed/consumed/rejected`) with security events `STEP_UP_SUCCEEDED/FAILED`.
- A manager without an authenticator gets `403 authenticator_required`. Owners need no manager step-up. Revoking the permission blocks the next request even with a fresh verification.

## Security assumptions

- The authenticator secret lives only on the manager's device and, sealed, in the database; key-ring rotation follows the other rings (re-encryption job not built, as for admin MFA, KI-26).
- TOTP is phishing-susceptible (a real-time relay could reuse a code within its window); the per-action binding and 5-minute single use limit the impact. WebAuthn could replace it later.
- Owner-granted permission, manager authentication and the owner's identity verification stay separate.
