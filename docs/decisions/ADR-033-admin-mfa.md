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

---

## Amendment 1 (APPROVED, 2026-11-19, DR-2026-11-19-O-8): two-person MFA recovery

**Status:** **APPROVED** by the owner with one security correction to A1-2, and A1-3 not approved (see "Owner decisions" at the end of this amendment). It **supersedes §Decision 7** (single-administrator recovery). Requested by DR-2026-11-19-R-3.

### Review of the current implementation (`services/mfa.py`, `admin_access` command)

| Aspect | Current behaviour | Gap |
|---|---|---|
| Who initiates | One administrator holding `admin_access.reset_admin_mfa` (never for themselves), or the CLI operator | A single person can remove another admin's second factor |
| Approval | None; the reset executes immediately | No separation of duties |
| Audit | `admin.mfa_reset` audit row; `ADMIN_MFA_REMOVED` security event; sessions revoked (`SESSION_REVOKED`, reason ADMIN) | Adequate |
| Notification | None to the affected account | The account holder isn't told that their factor was removed |
| Replacement | Password + single-use enrollment code (HMAC-stored, 24 h) + TOTP confirmation | The code is shown to the initiating admin, who could pass it to anyone (they still need the target's password) |
| Recovery codes | None | n/a |
| Server-access recovery | `manage.py admin_access reset-mfa` and `issue-mfa-enrollment`: audited with `channel=cli`, but no reason code and no notification | Not marked as an emergency procedure |

### Proposed changes

1. **Two-person recovery.**
   - An administrator with `admin_access.reset_admin_mfa` creates a recovery *request* (reason code required; expires after 24 h). It is stored as an `AdminActionApproval` (doc 03 §16.7, already in the approved schema list): `action_type = ADMIN_MFA_RECOVERY`.
   - A *different* administrator with a new sensitive permission `admin_access.approve_admin_mfa_recovery` approves or rejects it. The approver is never the requester or the target (service check plus a database CHECK).
   - Only approval executes the reset: device removed, open codes revoked, admin sessions ended.
   - States: PENDING, APPROVED (executed), REJECTED, EXPIRED. Every transition is audited.
2. **Security notifications.**
   - A `security.admin_mfa_recovery` notice is sent to the target account through the outbox on request, on approval or rejection, and on completed re-enrollment.
   - A copy goes to every active superuser.
   - New security-event types `ADMIN_MFA_RECOVERY_REQUESTED` and `ADMIN_MFA_RECOVERY_DECIDED`. This needs a migration that widens the `ase_event_type` CHECK.
3. **Replacement enrollment.**
   - Unchanged factors: password, single-use code and TOTP confirmation.
   - The enrollment code is delivered by **SMS to the target's verified phone number** instead of being displayed to an administrator. This adds possession of the phone, and nobody else sees the code.
   - If SMS is unavailable, the approver (not the requester) sees the code once.
4. **Recovery codes (optional; owner choice).**
   - If introduced: 10 codes of at least 100 bits each, shown once at enrollment and stored only as HMAC (ADMIN_MFA ring). Each is single use, and regeneration revokes the old set.
   - Using one records a security event, sends a notice, and forces a new authenticator enrollment in the same session.
   - *Recommendation:* don't introduce them for the MVP. Two-person recovery covers the need with fewer secrets to protect.
5. **Server access as audited break-glass only.**
   - The CLI `reset-mfa` / `issue-mfa-enrollment` need `--break-glass --reason CODE`, and record `admin.mfa_break_glass` (audit, `channel=cli`).
   - They notify the target and every superuser, and are refused without both flags.
   - They are documented as an emergency procedure (for example, the only administrator is locked out).

### Decisions requested from the owner

| # | Decision | Recommendation |
|---|---|---|
| A1-1 | Require two-person approval for admin MFA recovery | Yes |
| A1-2 | Deliver replacement enrollment codes by SMS to the verified phone | Yes, with approver display as fallback |
| A1-3 | Introduce hashed recovery codes | No, for the MVP |
| A1-4 | CLI recovery only as flagged, reason-coded, notifying break-glass | Yes |
| A1-5 | Add the two security-event types (migration widening `ase_event_type`) | Yes, if A1-1 is approved |

Implementation, when approved: the `AdminActionApproval` table (§16.7), the services and admin actions, the outbox notice (delivery handlers arrive with Phase 12; until then the notice waits in the outbox), and tests for separation of duties, expiry, races (one execution per request) and notifications.

### Owner decisions (DR-2026-11-19-O-8)

| # | Decision |
|---|---|
| A1-1 | **APPROVED.** Two-person recovery through `AdminActionApproval`; the requester can never approve |
| A1-2 | **APPROVED WITH CORRECTION.** The replacement enrollment secret goes **only** by SMS to the account holder's verified phone and is **never shown to the requesting or approving admin**. If SMS delivery fails, recovery fails safely: the secret is revoked, nothing is revealed, and the audited emergency procedure (A1-4) or a new request is the way forward. The secret is never logged, and persisted only as an HMAC |
| A1-3 | **NOT APPROVED** for the MVP: no recovery codes |
| A1-4 | **APPROVED.** CLI recovery only with `--emergency` and `--reason CODE`; fully audited; notifies the account holder and all superusers; delivers the secret by SMS only and never prints it |
| A1-5 | **APPROVED.** Security-event types `ADMIN_MFA_RECOVERY_REQUESTED`, `ADMIN_MFA_RECOVERY_DECIDED` and `ADMIN_MFA_EMERGENCY_RECOVERY` added, with the CHECK widened |

## Amendment 2 (2026-11-20, DR-2026-11-20-C-3): first-enrollment codes by SMS only (KI-39)

The first enrollment code was shown once to the issuing administrator (admin action page) or printed by the CLI. Following the approved A1-2 direction, it now goes **only by SMS** to the account holder's verified phone:

- `issue_enrollment` requires a verified phone, creates the code (HMAC only) and sends it directly after commit, never through the broker. It returns only whether the SMS provider accepted it.
- The admin action ("Send a first MFA enrollment code by SMS") and `manage.py admin_access issue-mfa-enrollment` show only the outcome. The template that displayed codes was removed.
- On SMS failure, the code is revoked and the audit row `admin.mfa_enrollment_delivery` records FAILURE. The account holder is notified (`security.admin_mfa_enrollment`), and issuing again (audited) is the recovery path. The flow stays separate from two-person recovery (Amendment 1) and is still limited to accounts that have never enrolled.
- **Local development:** `SMS_PROVIDER=console`, allowed only when `ENVIRONMENT=local` (deployed settings refuse it), writes SMS bodies to the process's standard output as a simulated handset. It never writes to the logging system. In tests, the mock provider keeps messages in memory.
