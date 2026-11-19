# ADR-033: Admin MFA, enrollment, recovery and the admin session

**Status:** PROPOSED (implementation record, 2026-11-19, G5 Phase 2e). The decisions below are engineering choices made inside the approved TR-07 / ADR-027 and doc 06 §22.2 under the clarification policy of DR-2026-11-18-G4. They are implemented and tested. **Owner review is requested** for the two items marked ⚑, because they concern security recovery.
**Date:** 2026-11-19
**Approved requirements implemented:** Django Admin with django-otp MFA (TR-07, ADR-027; doc 02 §12; doc 03 §22.15). A separate admin session: 30 min idle, 12 h absolute, MFA at login (doc 06 §22.2). Break-glass superusers: at most two, audited, MFA (doc 03 §22.15). Least privilege, no shared accounts, sensitive actions audited, admin login history (doc 06 §15). `ADMIN_MFA_ENROLLED` / `ADMIN_MFA_REMOVED` security events (doc 06 §22.3).

## Context

The approved documents name the library (django-otp) and require MFA, but they don't specify the factor, the enrollment path or recovery. The library's ready-made pieces don't all meet the project's rules:
- `otp_totp.TOTPDevice` stores its seed as plaintext hex.
- `otp_static` (backup codes) stores its codes in plaintext.
- The stock `OTPAdminSite` login doesn't create the project's `AuthSession`, so idle and absolute limits and revocation wouldn't apply.

## Decision

1. **Library use.** django-otp 1.7.5, core framework only: `Device`, `ThrottlingMixin`, `TimestampMixin`, `oath.TOTP`, `OTPMiddleware`, `django_otp.login()` and `OTPAdminSite` (as the base of the project's site). The bundled plugins aren't installed. Compatibility was verified on 2026-11-19: it requires Django ≥ 4.2 and has no other dependency. Its own suite passes on Django 5.2.19 with Python 3.12.16 and 3.13.18 (174 tests: 170 passed, 4 skipped). PyPI lists no known vulnerabilities, and it is actively maintained (releases 1.7.0–1.7.5 in 2026).
2. **Factor: TOTP** (RFC 6238; 6 digits, 30 s, ±1 step), in the project's own device model `AdminTotpDevice`:
   - the seed is encrypted with AES-256-GCM under the new `ADMIN_MFA` key ring; the associated data binds it to the account;
   - one device per account; `PROTECT` on the user FK (TR-09 F4);
   - a time step is accepted at most once (replay protection);
   - django-otp's exponential throttling applies;
   - the device row is locked during verification.
3. **Integer primary key for the device.** django-otp resolves a session's device from `"<app>.<model>/<int id>"`, so a UUID key would leave every session unverifiable. This internal table is never exposed through the API. It is the only exception to the UUID-key rule, and it is listed in the architecture test.
4. **Mandatory for everyone, superusers included.** The admin site requires all of the following, and `is_staff` alone grants nothing:
   - an active account;
   - a live role or break-glass superuser status;
   - the `is_staff` projection;
   - an MFA-verified session;
   - a valid ADMIN `AuthSession`.
5. **Sign-in in one step:** phone, password and TOTP code. Every failure shows the same message. Failures are security events (`LOGIN_FAILED` with reasons `BAD_PASSWORD`, `ADMIN_NOT_AUTHORIZED`, `ADMIN_MFA_NOT_ENROLLED`, `ADMIN_MFA_INVALID`). Limits are 5 per 15 min per phone+IP and 20 per 15 min per IP.
6. **⚑ Enrollment needs the password plus a single-use enrollment code** (24 h, 120 bits, stored only as an HMAC). The code is issued out of band by an administrator holding `admin_access.reset_admin_mfa`, never for themselves, or by the CLI operator. This means a stolen password alone can't register an attacker's authenticator. The seed is shown once to the enrolling account and confirmed with a TOTP code. Only IDs are kept in the session, never the seed or the code.
7. **⚑ Recovery is administrator-assisted; there are no backup codes.** `reset_mfa`:
   - removes the device;
   - revokes open enrollment codes;
   - ends every admin session of the account;
   - records `ADMIN_MFA_REMOVED` and an audit entry;
   - issues a new enrollment code.

   Nobody resets their own MFA. Backup codes aren't in the approved documents, and django-otp's implementation stores them in plaintext. If the owner wants them, they can be added as hashed, single-use codes.
8. **Separate admin session.** The admin URL area uses its own session cookie (`mat_admin_session`; `__Host-mat_admin_session` when deployed), backed by an `AuthSession` of client type `ADMIN` (30 min idle, 12 h absolute, both configurable). Each admin request is checked: the session's status, owner, limits and type, the account's admin access, and MFA verification. A failed check ends the session. The API never accepts an ADMIN session, and the admin never accepts a user session.
9. **The admin password-change pages are disabled.** Passwords change only through the account service (step-up, session revocation, events). Staff can't set another account's password.

## Consequences

- An administrator who loses the authenticator needs another administrator, or the CLI operator, to recover. With a single administrator, the CLI is the recovery path.
- Rotating the `ADMIN_MFA` key ring needs a re-encryption step for seeds (not built yet; the key version is stored per device). Enrollment codes are short-lived, so their HMAC isn't versioned.
- Signing in to the admin rotates the CSRF cookie, which the user web client shares (same origin). The web client fetches a new token from `/api/v1/auth/csrf/`.
- Admin login history is the security-event log (`LOGIN_SUCCEEDED` with reason `ADMIN`, plus `SESSION_*`); there is no separate `AdminAccessHistory` table (doc 03 §16.6). Dual approval (`AdminActionApproval`, §16.7) belongs to Phase 16.

## Where implemented

`backend/apps/admin_access/` (`services/mfa.py`, `middleware.py`, `site.py`, `views.py`); `backend/apps/accounts/services/auth.py` (`create_admin_session`); doc 03 §22.18; doc 06 §22.10; doc 16 §12.
