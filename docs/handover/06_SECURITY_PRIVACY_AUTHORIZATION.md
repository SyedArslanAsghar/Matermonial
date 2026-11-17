# Matermonial — Security, Privacy and Authorization Requirements

**Version:** 1.0 (G1 revision 2026-11-16)  
**Date:** 11 November 2026  
**Document status:** APPROVED_WITH_OPEN_ITEMS (project owner, 2026-11-17, DR-2026-11-17-A; record in doc 20 §5). **Open items:** OPEN ODs: OD-02, OD-03, OD-04, OD-06, OD-08; OPEN legacy ODs (doc 13 series): OD-005; PROPOSED TRs: TR-01, TR-03, TR-07, TR-16, TR-17, TR-19, TR-21, TR-23, TR-24. Listed items keep their own status (doc 19); this document status doesn't approve them.  
**Applied corrections:** DCR-10, 16, 29, 35, 39, 40, 41, 44, 52, 54, 59, 64, 67, 72, 74, 75, 76, 83, 86, 89, 92, 93, 94, 97 (doc 20). The reconciled security specification is in **§22**, which wins where it differs from §1–§21. G1 correction pass 2026-11-17 (DR-2026-11-17-C). Verbatim extracts start with a "*Verbatim from …*" (or "*Adapted from …*") line and end with "*— End of verbatim extract —*"; text outside those markers is editorial.

## 1. Security objectives

The platform processes highly personal matrimonial information. Security and privacy must be enforced in the backend, not merely through frontend controls.

The system must protect:

- Account credentials.
- Phone numbers and email addresses.
- Identity verification information.
- Date of birth.
- Profile and family information.
- Photographs.
- Income and employment information.
- Private preferences.
- Conversations.
- Shared documents.
- Payment and credit history.
- Family-manager authorization.
- Moderation evidence.
- Data exports.

## 2. Authentication security

- Use Django's supported password hashing.
- Never store plaintext passwords.
- Normalize phone numbers to E.164.
- Enforce rate limits for registration, login, OTP, and password reset.
- Store OTPs as hashes.
- Expire OTPs after the configured validity period.
- Enforce resend cooldown and attempt limits.
- Do not disclose whether an account exists through sensitive recovery responses.
- Revoke sessions/tokens after password reset or security-sensitive events as appropriate.
- Record login attempts and security events.
- Protect refresh tokens if JWT is used.
- Avoid storing tokens in browser local storage where a safer supported session design is available.
- Use platform secure storage for mobile credentials.

> **G1 (DCR-16):** the full authentication lifecycle (web sessions, mobile tokens and rotation, lifetimes, cookies, replay limits, key management, security events) is in §22.1–§22.3.

## 3. OTP security

Initial defaults:

- Validity: 5 minutes.
- Resend cooldown: 60 seconds.
- Maximum verification attempts: 5.
- Maximum send attempts: 5 per hour, configurable.

Additional requirements:

- Use cryptographically secure random OTP generation.
- Store only a keyed hash or secure hash suitable for verification.
- Compare securely.
- Invalidate OTP after successful verification.
- Prevent concurrent verification from consuming the same OTP multiple times.
- Rate-limit by account, phone, IP, and other appropriate signals.
- Do not log OTP plaintext.
- Do not include OTP values in analytics or audit metadata.

## 4. Identity verification security

- Store identity documents privately.
- Use separate access permissions from ordinary profile media.
- Limit access to authorized verification reviewers.
- Log document views, downloads, and review decisions.
- Use protected HMAC fingerprints for duplicate-document detection.
- Never store plain hashes of predictable identity numbers as the duplicate-detection mechanism.
- Avoid placing identity numbers in logs.
- Define retention and deletion policies.
- Allow resubmission after rejection according to the review workflow.
- Require elevated approval for manual duplicate-detection overrides.
- Do not expose internal reviewer notes to ordinary profile viewers.

## 5. Account and profile authorization

Authentication identifies an account. It does not automatically authorize access to every profile.

Every operation involving a matrimonial profile must resolve:

1. The authenticated account.
2. The requested profile.
3. Whether the account owns the profile or has an active authorization.
4. Whether the required permission is granted.
5. Whether the authorization is expired, paused, or revoked.
6. Whether the target profile is eligible for the action.
7. Whether blocking or privacy rules prevent the action.
8. Whether additional verification is required.

Do not rely on a frontend-supplied profile ID.

## 6. Family-manager authorization

- The owner creates authorization.
- The manager accepts it.
- Permission is scoped to a specific profile.
- Permission groups are templates only.
- Individual permissions are enforced by the backend.
- Sensitive permissions are owner-only by default.
- The owner can pause, resume, or revoke authorization.
- Paused/revoked/expired authorization immediately loses access.
- Every permission change is audited.
- Sensitive manager actions may require additional verification and owner notification.
- Manager actions record both actual account and represented profile.
- Do not grant access to the owner's account credentials, password, or authentication tokens.

## 7. Object-level authorization

Every private endpoint must check ownership, participation, authorization, and resource state.

Examples:

- A user cannot retrieve another user's private favorite notes.
- A conversation participant cannot access a conversation unrelated to their profile.
- A manager cannot access a profile after authorization revocation.
- A document recipient cannot download a revoked document.
- A blocked profile cannot initiate new communication.
- A hidden profile cannot discover the owner through search.
- An ordinary moderator cannot access unrelated identity documents.
- A support agent cannot read private messages without a specifically approved operational process.

## 8. API security

- Enforce HTTPS in production.
- Validate all request data.
- Apply authentication and permission checks.
- Apply throttling to sensitive endpoints.
- Prevent mass assignment of protected fields.
- Do not accept owner, creator, reviewer, or actor fields blindly from the client.
- Set actor fields from the authenticated request context.
- Use secure CORS configuration.
- Use appropriate CSRF protection for cookie-based authentication.
- Avoid overly permissive production CORS.
- Prevent insecure direct object reference vulnerabilities.
- Do not reveal private resource existence unnecessarily.
- Keep error messages useful but non-disclosing.

## 9. Privacy classification

Classify data into access levels:

### Public or discoverable

Only fields explicitly approved for profile discovery, such as selected display name, age, general location, profile description, and approved photographs.

### Authenticated limited

Information available to verified or eligible platform users under profile visibility rules.

### Connection-only

Information available only to connected profiles where the owner has permitted disclosure.

### Owner-only

Private notes, account settings, hidden-profile list, detailed visitor controls, and other owner-controlled information.

### Manager-authorized

Information available only to managers with explicit permission for the represented profile.

### Restricted operational

Identity documents, internal moderation evidence, security investigations, sensitive audit details, and private provider responses.

Serializers must use explicit field allowlists. Do not serialize entire model objects.

> **G1 (DCR-29, DCR-40):** access levels L0–L3 and the full visibility and interaction matrix are in §22.4 [REC-BIZ, OD-03, OPEN].

## 10. Private media security

- Store private files outside public web roots.
- Use private object storage in production.
- Use opaque storage keys.
- Do not store public permanent URLs in database fields.
- Generate short-lived signed URLs or serve through an authorization-controlled endpoint.
- Check permission before generating a URL.
- Apply content-type, size, and extension validation.
- Inspect file content rather than trusting the extension.
- Scan uploaded files where supported.
- Use separate storage permissions for identity documents, profile photos, shared documents, attachments, evidence, and exports.
- Revoke database permissions immediately when access is withdrawn.
- Recognize that a previously issued signed URL may remain valid until its expiry unless proxy delivery or another revocation mechanism is used.
- Never claim that remote deletion can recall a file already downloaded by another person.

## 11. Blocking and hiding privacy

Blocking and Hide My Profile From are separate mechanisms.

### Blocking

- Unilateral.
- No notification to the blocked person.
- Prevents discovery, new requests, and communication.
- Disables applicable media/document access.
- Preserves history.

### Hide My Profile From

- Unilateral.
- No notification.
- Prevents search/recommendation discovery and new interests/requests.
- Does not terminate an existing accepted connection.
- Does not automatically terminate existing communication.
- Does not automatically revoke existing photo/document permissions.

The backend must apply these rules consistently across search, recommendations, requests, conversations, and media access.

## 12. Financial security

- Use Decimal for monetary values.
- Use integer quantities for credits.
- Store currency explicitly.
- Keep subscription and purchased balances separate.
- Keep an append-only credit ledger.
- Lock relevant rows during balance deductions.
- Prevent negative balances.
- Use unique idempotency keys.
- Validate payment callbacks.
- Verify merchant reference, amount, currency, gateway identity, and status.
- Never grant credits from frontend assertions.
- Record sanitized gateway responses.
- Do not store prohibited payment credentials.
- Reconcile uncertain payments.
- Use compensating transactions for corrections and refunds.
- Require additional approval for manual credit adjustments.

## 13. Notification security

- Use generic SMS and push content.
- Do not include OTPs in ordinary notification history.
- Do not include private profile details in lock-screen notifications.
- Do not include conversation contents or documents in push payloads.
- Mask phone/email destinations in delivery logs.
- Sanitize provider responses.
- Keep security notifications enabled.
- Protect notification action URLs with normal authentication and authorization.

## 14. Messaging security

- Enforce active connection status.
- Enforce block restrictions.
- Verify the sender profile belongs to the account or is manager-authorized.
- Record actual sender account.
- Validate attachment content and size.
- Scan files where supported.
- Restrict message and attachment retrieval to participants.
- Do not expose internal support or moderation notes as conversation messages.
- Preserve legitimate message history according to retention policy.

## 15. Administrative security

- Use least-privilege admin roles.
- Require MFA for production administrative accounts.
- Separate support, moderation, finance, verification, and system administration permissions.
- Restrict access to identity documents.
- Audit sensitive administrative reads and writes.
- Require dual approval for configured high-risk actions.
- Prevent moderators from reviewing cases with conflicts of interest.
- Avoid shared administrator accounts.
- Review inactive and expired admin roles.
- Store admin login and access history.

> **G1 (DCR-44):** administrative authorization comes from a single source, the `AdminRole` / `AdminUserRole` tables (doc 03 §22.15); Django Groups aren't used [TR-07].

## 16. Audit requirements

Audit:

- Authentication and security events.
- Profile access by family managers.
- Authorization creation, changes, pause, resume, and revocation.
- Sensitive privacy changes.
- Identity verification decisions.
- Request and connection state transitions.
- Credit and payment changes.
- Document sharing and access.
- Moderation actions and appeals.
- Data export and download.
- Account deletion.
- Administrative configuration changes.
- Feature-flag changes.
- Sensitive administrative access.

Audit logs must be append-only to normal application users. Corrections must be represented as new events.

Never put passwords, OTP plaintext, access tokens, private file contents, or full message bodies into general audit records.

## 17. Data export security

- Require identity confirmation.
- Export only the requester's authorized data.
- Exclude other users' private information.
- Exclude internal moderation evidence and identity verification documents by default.
- Store ZIP files privately.
- Use temporary signed links.
- Apply seven-day export availability.
- Use 24-hour link expiry.
- Log downloads.
- Delete expired export files according to retention policy.

## 18. Account deletion security

- Require identity confirmation.
- Use a 30-day recovery period.
- Disable public visibility and new activity during recovery.
- Revoke sessions and manager authorizations when processing begins. (G1, DCR-41: all sessions are already revoked when the deletion request is confirmed; during recovery, manager access is denied at runtime without changing the authorizations; authorizations are revoked by the processing fan-out. Recovery flow: doc 05 §25.9.)
- Use idempotent deletion steps.
- Apply documented legal and security retention holds.
- Preserve other users' legitimate conversation history as appropriate.
- Do not transfer profile ownership automatically.
- Record every deletion step and result.
- Delete or anonymize remaining data according to retention policy.

## 19. Logging and secret management

Never log:

- Passwords.
- OTP plaintext.
- Access or refresh tokens.
- Full identity numbers.
- Private document contents.
- Unmasked payment credentials.
- Private signed URLs.
- Full private message content.

Use secure deployment secret management or environment injection.

Never commit production `.env` files, credentials, certificates, or API keys.

> **G1 (DCR-67, DCR-74, DCR-75, DCR-76, DCR-86):** log pseudonymisation, encryption envelopes, key destruction and the external compliance registry are in §22.6–§22.7.

## 20. Security testing

Required tests include:

- Unauthorized access.
- Cross-account data access.
- IDOR attempts.
- Manager permission escalation.
- Expired/revoked manager authorization.
- Blocked profile access.
- Hidden-profile discovery.
- Private document access after revocation.
- Expired signed URL behavior.
- OTP brute-force/rate-limit behavior.
- Payment callback forgery.
- Duplicate callback processing.
- Concurrent credit deductions.
- Negative balance prevention.
- Moderator conflict restrictions.
- Unauthorized export access.
- Account deletion recovery and retention holds.

## 21. Security release gate

Do not release to production until:

- Authentication and authorization tests pass.
- Sensitive data is not exposed by serializers.
- Private storage is verified.
- Payment callback verification is implemented.
- Financial concurrency tests pass.
- Admin MFA and least privilege are configured.
- Secrets are removed from source control.
- Backup restoration is tested.
- Logging redaction is verified.
- High-risk security findings are resolved or formally accepted.

## 22. Reconciled security specification (G1)

**Status:** the mechanisms in this section are **[TR] PROPOSED** (doc 19: TR-01, TR-03, TR-07, TR-17, TR-19, TR-21, TR-23, TR-24). Items tagged [REC-BIZ] belong to an OPEN owner decision. [DECIDED] rules are approved requirements.

### 22.1 Authentication lifecycle (DCR-16) [TR-01]

> *Verbatim from `docs/baseline/v4.6-F3/referenced/A4_v3.md` §8.2–8.5 (incorporated by reference, DR-2026-11-16-P1). Section references inside this block refer to that package.*

##### 8.2 Linking a web session to AuthSession, without storing raw session keys
1. Use Django's server-side session store (database, or cache_db backed by Redis). The browser cookie holds only Django's random session key.
2. At login, Django `login()` rotates the key (preventing fixation). The server then writes `request.session["auth_session_id"] = <AuthSession UUID>` **inside the server-side session data**.
3. **`AuthSession` stores no Django session key and no hash of one.** The link runs one way: session data → `AuthSession`. Clients can't tamper with server-side session data.
4. On every request: load `auth_session_id` from the session, fetch the `AuthSession`, and require `status == ACTIVE`, `user_id == request.user.id`, and that the idle and absolute limits haven't passed. If any check fails, flush the session and return `401 session_revoked`.
5. Revocation only flips `AuthSession.status`. The orphaned Django session row is rejected on its next use and purged by the scheduled `clearsessions` job.
6. Defence in depth: Django's session auth hash also invalidates web sessions automatically when the password changes.

##### 8.3 Mobile tokens and rotation
- **Token values:** 256-bit random, prefixed `mat_at_` / `mat_rt_`. Only the SHA-256 hash is stored, and plaintext is never logged.
- **Access tokens are independent of rotation.** An access token is valid when it's unexpired (15 min), unrevoked, and its **session is ACTIVE**. Rotating the refresh token **doesn't revoke the current access token**, so in-flight API calls keep working until the token expires naturally. Logout, revocation and reuse detection still take effect immediately, because every request checks the session status.
- **Deterministic, idempotent rotation:**
  - The child refresh token is derived as `HMAC-SHA256(K_rot[key_version], parent_plaintext ‖ "refresh" ‖ generation+1)`.
  - The new access token is derived the same way with the label `"access"`.
  - The server stores only the children's hashes. It can **recompute the same pair** from the parent token the client presents again, **without ever storing plaintext tokens**.
- **`POST /auth/token/refresh/`**, all in one transaction with `SELECT … FOR UPDATE` on the parent row:

| Parent state | Result |
|---|---|
| Valid and unused | Mark `used_at`. Insert the child hashes. Extend the rolling expiry, capped at the 90-day absolute limit. Return the pair. |
| Used ≤ 15 s ago and **child refresh not yet used** | **Recompute and return the identical pair** (idempotent replay). Nothing new is created. |
| Used > 15 s ago, **or** its child has already been used | **Reuse detected:** revoke the session (REFRESH_REUSE), record a security event, send a security notification. `401 session_revoked`. |
| Expired or session not ACTIVE | `401 session_expired` |
| Unknown | `401 invalid_token` |

**How the 15-second grace works, and how the client recovers:**
1. The mobile client runs refresh as **single-flight**: one refresh at a time, and every request that got a 401 waits for it.
2. The client keeps the old refresh token until the new pair is safely stored.
3. If the refresh response is lost (timeout or dropped connection), the client retries **with the same old token** for up to 10 seconds. Inside the grace window, the server recomputes and returns the identical pair.
4. Two concurrent refreshes also receive the same pair. The row lock serialises them, and no extra generation is created.
5. If the client stays offline past the grace window, its next attempt counts as reuse. The session is revoked and the user logs in again. That's the deliberate security trade-off.
6. A thief replaying a stolen token inside the grace window gets the same pair as the real user. Whichever side uses the child refresh token second triggers reuse detection, and the session is revoked.
7. **The key `K_rot` is versioned and stored in the deployment secret store**, and rotating it doesn't invalidate existing tokens (the `key_version` column records which key derived each token).

##### 8.4 Other lifecycle events

| Event | Specification |
|---|---|
| Login | Generic `invalid_credentials`, with a dummy hash computed for unknown phones. Account-state gate. Creates an AuthSession (+ key rotation on web, or token pair on mobile). Security event. Outbox event for the "new sign-in" security notice. Login on web requires CSRF (token from `GET /auth/csrf/`). |
| Account-state gate (every request) | Denies when `is_active` is false, a `LOGIN`/`FULL_ACCOUNT` restriction is active, or deletion is PROCESSING. During the deletion recovery period, login is allowed with limited capabilities. |
| Logout | Revokes the current session (web flush, or all of the session's tokens). Idempotent. |
| Session list and revocation | `GET /auth/sessions/` shows metadata with a masked IP and no tokens. `DELETE /auth/sessions/{id}/` returns an identical 404 for sessions that aren't the caller's. `POST /auth/sessions/revoke-others/`. Takes effect on the next request. |
| Password reset | Generic response. OTP with purpose PASSWORD_RESET. Success **revokes all sessions** and sends a security notification. No automatic login. |
| Password change | Current password + step-up. Revokes all *other* sessions. |
| Step-up | `POST /auth/reauthenticate/` sets `reauthenticated_at` (password, plus OTP if OD-04c is approved). |
| Deactivation | Account-state service revokes all sessions in the same transaction. Delegated access to that owner's profiles is denied by §9 step 8. Authorizations aren't mutated. |
| Manager authorization pause or revoke | Takes effect on the next request (§9). Delegated writes take `FOR SHARE` on the authorization row and revoke takes `FOR UPDATE`, so the two can't interleave. Photo signed URLs (≤ 300 s) are a documented residual window; documents are proxied and revoked immediately. |
| Device history | Revoked and expired sessions are retained under a `DataRetentionPolicy` category (period subject to legal review, OD-005 in doc 13). |
| Cookies | Production cookies `__Host-mat_session` (HttpOnly, Secure, SameSite=Lax) and `__Host-mat_csrf` (readable by JavaScript, Secure, SameSite=Lax). Same-origin deployment. A request carrying both a cookie and a bearer token is rejected. |
| Rate limits (Redis in production) | Login: 5 per 15 min per phone+IP and 20 per IP. Register: 10 per hour per IP. OTP: as documented + a per-IP limit. Refresh: 30 per hour per session. No hard account lockout. 429 with `Retry-After`. |

##### 8.5 Authentication tests (T-AUTH)

| Group | Tests |
|---|---|
| Login | 001 generic failure. 002 timing parity for unknown phones. 003 session key rotated at login (fixation). 004 login CSRF enforced. 005 restricted or deactivated account denied. |
| Web linkage | 010 `auth_session_id` mismatch → 401 + flush. 011 revoked AuthSession → next request 401. 012 no raw or hashed session key persisted anywhere outside Django's session store. |
| Rotation | 020 happy path. 021 **lost response: retry within 15 s returns the identical pair**. 022 **10 concurrent refreshes produce one generation and identical pairs**. 023 retry after 15 s revokes the session. 024 using a grandparent token revokes. 025 **old access token still works after rotation until it expires**. 026 database failure injected mid-rotation rolls back and the parent stays usable. 027 rotating `K_rot` keeps existing tokens valid. |
| Revocation | 030 logout invalidates access and refresh immediately. 031 revoke one session leaves others working. 032 password reset revokes all. 033 deactivation revokes all. 034 absolute expiry enforced. |
| Abuse | 040 rate limits. 041 cookie + bearer together rejected. 042 tokens never appear in logs (log capture test). |

*— End of verbatim extract —*

**Amendments to the block above (later baseline packages win):**
- **Records:** `AuthSession` gains `scope` (FULL | DELETION_RECOVERY) and `key_version_current`; field definitions are in doc 03 §22.2. `AuthSession` replaces `LoginHistory` as the session record; security history is kept separately in `AccountSecurityEvent` (§22.3).
- **Deletion recovery:** a FULL session can't be created while the account is in deletion recovery. The only login is the recovery-scoped login in doc 05 §25.9 (this replaces "login is allowed with limited capabilities").
- **Lock order (DCR-52, DCR-54):** login, refresh, logout and session revocation take the account's `User FOR SHARE` first. Refresh then locks `AuthSession FOR UPDATE` and then the parent `AuthToken FOR UPDATE` (replaces "FOR UPDATE on the parent row" as the first lock). See doc 12 §5.

### 22.2 Session lifetimes, cookies, replay limits and K_rot (DCR-16) [TR-01]

> *Verbatim from `docs/baseline/v4.6-F3/approved/01_v4.md` §10.2–10.4. Section references inside this block refer to that package.*

##### 10.2 Session and token lifetimes (all configurable; TR-01)

| Client | Idle expiry | Absolute expiry | Mechanics |
|---|---|---|---|
| Web (user) | **2 h** without activity | **7 days** from login | Django session cookie `Max-Age` = absolute limit. `AuthSession.idle_expires_at` is extended on activity, with writes throttled to once per 60 s. Both are checked on every request (v3 §8.2 step 4). |
| Web (Django Admin) | **30 min** | **12 h** | Same mechanics plus django-otp MFA at login. A separate admin session. |
| Mobile access token | — | **15 min** | Independent of rotation (v3 §8.3) |
| Mobile refresh | **30 days rolling** (each successful refresh extends it) | **90 days** from login | Never extended past the absolute limit. After that, a full login is needed. |
| Deletion-recovery session | — | **15 min**, no refresh | §10.6 |

Step-up windows (TR-16) are separate from session lifetime.

##### 10.3 Cookie rules (production and staging)

- `__Host-mat_session`: `Secure`, `HttpOnly`, `SameSite=Lax`, **`Path=/`, no `Domain` attribute**.
- `__Host-mat_csrf`: `Secure`, readable by JavaScript, `SameSite=Lax`, **`Path=/`, no `Domain`**.
- Django settings: `SESSION_COOKIE_DOMAIN=None`, `CSRF_COOKIE_DOMAIN=None`, both paths `/`, both `SECURE=True`, `CSRF_COOKIE_HTTPONLY=False` (the current `True` is a correction for G3).
- Startup validation fails if any `__Host-` precondition is broken.
- **Local development over HTTP can't use the `__Host-` prefix.** Local settings use unprefixed names with `Secure=False`. That's the only environment allowed to.

##### 10.4 Refresh rotation: limits of replay detection and compromise response (C9)

The design is kept: deterministic HMAC derivation and a 15-second idempotent grace. Its limits:

**What it does not prevent:**
1. **A replay inside the grace window gets the same pair.** An attacker who presents a stolen parent within 15 s of its legitimate use receives the identical access and refresh tokens. Nothing is detected **until one side uses the child refresh token after the other**. Until then, the attacker's access token works for up to 15 minutes.
2. **A stolen, still-unused refresh token** can be used by the attacker first. Detection happens only when the legitimate client later presents it (reuse), so the attacker has a session until then.
3. **If the legitimate client never refreshes again** (uninstalled, device lost), the attacker's chain is never detected. It ends only at the 30-day idle or 90-day absolute limit, or when the user revokes sessions or resets their password.
4. Detection relies on reuse, so it's **after the fact**. It limits how long a compromise lasts. It doesn't stop theft.

The grace window is therefore **a deliberate trade-off that adds a small replay surface in exchange for recovering lost responses.** It doesn't eliminate replay risk.

**Mitigations:**
- Tokens only ever live in the platform's secure keystore (Expo SecureStore).
- TLS only.
- Tokens are never logged.
- Every session appears in the session list, so the user can revoke it.
- A new-sign-in security notice is sent.
- Optionally (behind a feature flag, off by default), a device-binding check that compares the platform and app identifier recorded at login.

**Response to suspected compromise:**

| Trigger | Action, in the same transaction |
|---|---|
| Refresh reuse detected | Session → REVOKED (`REFRESH_REUSE`). Every token in the session revoked. `AccountSecurityEvent REFRESH_REUSE_DETECTED`. Outbox security notification ("a sign-in was ended for your protection"). The response is `401 session_revoked`. |
| User reports compromise, or "sign out everywhere" | Revoke all sessions (`USER_REVOKED_ALL`). Recommend a password change. |
| Password reset | Revoke all sessions [v3]. Event. Notification. |
| Repeated reuse events on one account (≥ 2 in 24 h) | `SUSPICIOUS_ACTIVITY` event and an alert to the security admin role. No automatic lockout. |

**K_rot key management:**
- **Where it's used:** K_rot only derives child tokens. Verifying a token never needs it (the server hashes the presented token). The only time an old key is needed again is to recompute a pair during the 15-second grace replay.
- **Storage:** the deployment secret store, as versioned entries `K_rot[v]`. Never in Git, the database or logs. The active version is in configuration.
- **Planned rotation** (recommended every 90 days): add `v+1` and make it active, so new rotations use it. Keep `v` for at least 15 s plus a margin (1 hour), then retire it. **No sessions are revoked.** Tokens already issued stay valid because verification is hash-based.
- **Compromise of K_rot alone:** an attacker can't produce valid tokens without a parent token's plaintext, so the direct impact is limited. But it combines dangerously with any token theft, so the procedure is:
  1. Mark `K_rot[v]` as COMPROMISED in configuration. Rotation and grace replays refuse to use it, and a grace replay under v returns `401 session_expired`.
  2. Activate a new version.
  3. Run the management command `revoke_sessions_by_key_version v`. It revokes every ACTIVE mobile session whose `key_version_current = v` (reason `KEY_COMPROMISE`), writes the events, and queues notifications in batches.
  4. Open a security incident and record it in AuditLog.
  5. Review the HMAC fingerprint key and other secrets in the same store.
- **Web sessions aren't affected by K_rot.** If Django's `SECRET_KEY` is compromised, a separate procedure revokes all web sessions (rotate the key, flush the session store, bulk-revoke WEB AuthSessions).

*— End of verbatim extract —*

### 22.3 Security and history records (DCR-35) [TR-17]

> *Verbatim from `docs/baseline/v4.6-F3/approved/01_v4.md` §10.5. Section references inside this block refer to that package.*

##### 10.5 Security and history records (C8)

**`AccountSecurityEvent`** is append-only (UPDATE and DELETE blocked by a trigger).

Fields:
- `id`, `user` (nullable)
- `subject_hash` (a keyed HMAC of the normalised phone, used when there's no user or the phone is unknown; never the raw phone)
- `event_type`, `result` (SUCCESS | FAILURE | INFO), `reason_code`
- `session` (nullable)
- `actor_type` (SELF | ADMIN | SYSTEM | ANONYMOUS), `actor_user` (nullable, for admin-initiated events)
- `ip_address`, `user_agent`, `request_id`
- `metadata` (an allowlisted JSON schema per event type, never secrets)
- `occurred_at`

| Event types | Recorded for |
|---|---|
| `LOGIN_SUCCEEDED`, `LOGIN_FAILED`, `LOGIN_DENIED_ACCOUNT_STATE` | Successful login, failed login, gated login |
| `SESSION_CREATED`, `SESSION_REVOKED` (with the reason: LOGOUT, USER_REVOKED, USER_REVOKED_ALL, PASSWORD_RESET, PASSWORD_CHANGED, DEACTIVATED, DELETION_REQUESTED, ADMIN, REFRESH_REUSE, KEY_COMPROMISE) | Session creation and revocation. Natural expiry is recorded only on AuthSession. |
| `REFRESH_REUSE_DETECTED` | Token replay detection |
| `PASSWORD_RESET_REQUESTED`, `PASSWORD_RESET_COMPLETED`, `PASSWORD_RESET_FAILED`, `PASSWORD_CHANGED`, `PASSWORD_CHANGE_FAILED` | Password reset and change attempts |
| `OTP_VERIFICATION_FAILED`, `OTP_ATTEMPTS_EXHAUSTED`, `OTP_RATE_LIMITED` | OTP failures. The OTP itself lives in `PhoneVerification`. |
| `STEP_UP_SUCCEEDED`, `STEP_UP_FAILED` | Re-authentication |
| `PHONE_CHANGED`, `EMAIL_CHANGED`, `ADMIN_MFA_ENROLLED`, `ADMIN_MFA_REMOVED`, `DEACTIVATED`, `REACTIVATED`, `DELETION_REQUESTED`, `DELETION_CANCELLED` | Account security changes |
| `SUSPICIOUS_ACTIVITY`, `RATE_LIMIT_TRIGGERED` | Suspicious authentication activity |

**Flood control:** while an IP or subject is being throttled, only one `RATE_LIMIT_TRIGGERED` is written per window, not one row per rejected request.

**The four record families:**

| Record | What it records | Actual actor | Written by | Who can read it | Retention (placeholder, subject to doc 13 OD-005) |
|---|---|---|---|---|---|
| **Account login and security history** (`AccountSecurityEvent` + `AuthSession`) | Authentication and account-security facts about one account | The account itself, an admin, the system, or anonymous | Auth, OTP and account-state services | The account owner sees their own logins, sessions and security changes (IP masked; no failed attempts against unknown subjects). The security admin role sees everything. Support sees a limited subset. **Managers never see it** (there's no delegable permission; `manage_account_security` is O-tier). | 12 months. Anonymous failed events 90 days. AuthSession 12 months after it ends. Kept beyond deletion only under FR-DAT-009 holds. |
| **ProfileAccessHistory** | A manager accessing a represented profile (sessions or views on the manager path) | The manager account | Acting-profile layer (v3 §9 step 17) | The profile owner. Security admins. | While the authorization exists + 12 months |
| **ManagerActionLog** | Each delegated action (what was done, for which profile, under which authorization) | The manager account | Acting-profile layer | The profile owner (activity view, FR-FAM-009). Security and moderation admins. | While the authorization exists + 12 months |
| **AuditLog** | Significant system, financial, administrative and state-change actions across domains | Actual account (owner, manager or admin) or SYSTEM, with `authorization_id` where relevant | Domain services and admin actions | The auditor role, read-only. Never end users. | Per category. Financial at least the statutory period (legal review). |

**Rules for which record gets written:**
- An admin revoking a user's session writes both **AuditLog** (the admin action) and **AccountSecurityEvent** (`SESSION_REVOKED`, actor ADMIN).
- A manager sending a message writes **ManagerActionLog** and the domain history. It writes **AuditLog** only for S or H tier actions.
- Nothing is copied between families beyond these rules.

**Tests (T-SEC):**
- 001: every listed event type is emitted by its flow.
- 002: UPDATE and DELETE on events are rejected.
- 003: no secret, OTP, token or raw phone appears in event rows (asserted against the schema).
- 004: a manager can't read the owner's security history.
- 005: flood control caps rows during an attack.
- 006: after the deletion's PROCESSING step, events are retained but pseudonymised.

*— End of verbatim extract —*

**Amendment (DCR-60, DCR-67, DCR-76):** the field list above is superseded by doc 03 §22.2. `AccountSecurityEvent` and `AuditLog` store pseudonyms instead of `user_id`, and keep personal context (IP address, user agent, location) and linkable identifiers such as `session_id` inside per-subject encrypted envelopes. The event types, record families, access rules and flood control above still apply.

### 22.4 Access levels and the visibility and interaction matrix (DCR-29, DCR-40) [REC-BIZ, OD-03, OPEN]

**Authoritative source for OD-03:** doc 19 §3.1 (OD-03a…OD-03j, all OPEN) and baseline v4 §9 and §15 (the matrix below). Nothing in this section is an approved requirement unless tagged [DECIDED].

**Recommended access-level definitions (OD-03a) [REC-BIZ, OPEN]**, from baseline A4 §13 OD-03 item (a), which v4 §15 OD-03(a) carries forward unchanged:
- **L0:** search listing.
- **L1:** limited card (display name, age, city/country if shown, religion/community, education level, profession title, primary photo subject to photo visibility).
- **L2:** full detail (allowlist minus connection-only fields).
- **L3:** connection-only (contact details if enabled, shared progress, conversation, documents by permission).

*Historical note (G1 correction pass, DR-2026-11-17-C):* an earlier G1 revision reproduced the whole A4 §13 OD-03 row here, including its items (b)–(f). Those items are superseded by the v4 §15 OD-03 sub-items and the v4 §9 matrix, and they are no longer shown. The original row remains in `docs/baseline/v4.6-F3/referenced/A4_v3.md` §13 for traceability. The current recommendations for VISIBLE_AFTER_ACCEPTANCE, HIDDEN, block and hide, PENDING_REVIEW and display names are OD-03b, c, d, e and f in doc 19.

> *Adapted from `docs/baseline/v4.6-F3/approved/01_v4.md` §9. Section references inside this block refer to that package. Editorial change: the §9.3 heading, originally phrased as a reply to the reviewer, was renamed "Answers to specific visibility questions"; the text is otherwise verbatim.*

Every row here is **REC-BIZ** under OD-03 unless tagged [DECIDED].

**Visibility modes** [DECIDED as options, FR-PRO-006]:
- **VIS** = Visible in match search
- **VAA** = Visible after acceptance
- **HID** = Hidden

**Access levels:**
- **L0:** appears in search
- **L1:** limited card
- **L2:** full detail (billable unless exempt)
- **L3:** connection-only data

"–" = no access (generic 404).

##### 9.1 What viewer V can see of target T, by T's visibility mode and the relationship's state

Read each row as "V's relationship to T".

| V's relationship to T | T = VIS | T = VAA | T = HID |
|---|---|---|---|
| Unrelated searcher | L0, L1, L2 | – | – |
| V sent T an interest (pending) | L0, L1, L2 (unchanged by sending) | – (V couldn't have discovered T. If an interest exists, it was created before T switched to VAA: V sees L1 in that item only.) | L1 inside that pending item only |
| **T sent V an interest** (V is the recipient) | L1, L2 (billing exemption per OD-08a) | **L1** (to evaluate the approach; never L2) | L1 inside the item (T can't send new approaches while HID; see 9.3) |
| Interest reciprocated (either side) | Unchanged: L2 billable or exempt | **Unchanged: L1.** Reciprocation ≠ acceptance. | L1 in the item |
| V sent T a formal request (pending) | Unchanged | L1 in the item | L1 in the item |
| **T sent V a formal request** (V is the recipient) | L1, L2 (exempt per OD-08a) | **L1 only.** A request alone doesn't change visibility. | L1 in the item |
| **Request accepted → connection ACTIVE** | **L3** (includes L2, no charge) | **L3** | **L3.** Hiding doesn't end connections [DECIDED]. |
| Connection PAUSED | L2 + read-only conversation history. No contact details. No new messages or shares. | Same | Same |
| Connection COMPLETED | L2 + read-only history | Same | Same |
| Connection CLOSED | Back to the unrelated row (L2 billable, no connection exemption). Read-only history kept per retention. | **L1 only** (history card). Acceptance is no longer in force. | L1 history card only |
| **V is on T's Hide-From list** | – for L0/L1/L2 (404). Exceptions: an existing connection keeps its connection row's access [DECIDED: FR-PRI-003]. An existing pending item shows L1 in the item. V can't send new approaches [DECIDED]. | Same | Same |
| **Block in either direction** | – everywhere, including inside existing items and connections. Records are kept [DECIDED, FR-PRI-001]. Pending interests and requests close (OD-06f). The connection isn't auto-closed, but L3, messaging and media are suspended while the block exists. Unblocking restores access only where nothing else forbids it [DECIDED, FR-PRI-002]. | Same | Same |
| **T's owner** (or a manager acting for T) | Owner view: all own fields, including private fields and DOB. Managers: the fields their permissions cover. Identity-locked and O-tier data stays owner-only. | Same | Same |

##### 9.2 Lifecycle overlay (applied before 9.1)

| T's state | Non-connected viewers | Connected viewers |
|---|---|---|
| DRAFT, PENDING_REVIEW | – | n/a |
| ACTIVE | Per 9.1 | Per 9.1 |
| PAUSED | – | L1 + read-only history |
| SUSPENDED | – | L1 + read-only history. No messaging. |
| CLOSED | – | History card only |
| Owner in deletion recovery or processing | – | History card only, labelled "No longer available". The deletion isn't disclosed. |

##### 9.3 Answers to specific visibility questions

| Question | Answer (REC-BIZ, OD-03h) |
|---|---|
| Do incoming interests and requests stay visible to a recipient whose own profile is HIDDEN? | **Yes.** The HIDDEN owner can still see and respond to pending items that arrived before hiding. Accepting creates a connection as normal. |
| Does HIDDEN block incoming approaches or only remove search visibility? | **Both.** No L0. **New incoming approaches are rejected generically**, even from someone who has the profile ID, because otherwise "hidden" would leak. **New outgoing approaches are also disabled.** A user who wants to approach privately uses VAA. |
| Does reciprocal interest change profile-detail visibility? | **No** |
| Does a formal request alone change it? | **No.** Receiving ≠ accepting. |
| Does an accepted formal request grant L3? | **Yes.** It creates the ACTIVE connection, which gives L3 to both participants. |

**Consistency rule:** this matrix replaces every visibility statement in v3 §5 and §13 and in OD-08a. OD-08a exemptions only affect billing for rows where L2 is already allowed.

*— End of verbatim extract —*

### 22.5 Profile-detail access: revalidation, snapshot and deadline (DCR-39, DCR-64, DCR-72) [TR-19]

> *Verbatim from `docs/baseline/v4.6-F3/approved/01_v4.md` §8. Section references inside this block refer to that package.*

#### 8. Profile-Detail Access: Revalidation vs Billing (C5; TR-19)

**Principle:** authorization decides *whether* someone can see something. Billing only decides *whether a view must have been paid for*. A paid grant is never permanent access.

`GET /profiles/{id}/` runs these steps on **every** request and writes **no** billing, ledger, ProfileView or VisitorHistory rows:
1. The acting-profile algorithm (v3 §9) with `view_profile_details` (or `view_profile` for the owner's own profile).
2. Load the target. If it's absent, CLOSED, or its owner's deletion is in progress or recovery: generic 404 (§9 lifecycle overlay).
3. **Blocks in both directions:** a block either way → 404.
4. **Hide My Profile From:** if the target hid the viewer → 404, unless an L3 connection or an existing pending item exists (§9).
5. **Restrictions:** a viewer account or profile restriction, or a target restriction or suspension → 404 or 403 per the restriction type, generic.
6. **Connection status:** ACTIVE → L3. PAUSED or COMPLETED → L2 + read-only history. CLOSED → treated as unrelated, per §9.
7. **Visibility mode and eligibility:** compute the maximum access level from §9.
8. **Billing check, only if the maximum level is L2 and L2 is billable** (not a connection, not an OD-08a exemption): a ProfileView grant for (billing account, target) must exist in the last 24 hours. If it doesn't: `402 profile_view_required` with the L1 card (OD-08b). **A grant never raises the level above step 7.**
9. Serialize with the allowlist for the computed level. `Cache-Control: private, no-store`.

**Consequences:**
- Pay, then get blocked → 404 at once.
- Pay, then the target switches to HIDDEN → 404 at once (no L3 between them).
- Pay, then the target restricts → denied.

In every case the used credit isn't refunded (REC-BIZ, OD-08c). The grant row stays as a billing record.

`POST /profiles/{id}/views/` runs steps 1–7 first. It **refuses to charge** when the maximum level is below L2, returning a generic `403 profile_detail_not_available`, which reveals nothing beyond the L1 card the viewer already has.

**Tests:**
- T-MAT-017: GET never charges.
- T-MAT-018: a grant never exceeds the computed level.
- T-MAT-019: block or hide after a grant → denied.
- T-MAT-020: visibility changed to HIDDEN after a grant → denied.
- T-MAT-021: POST refuses to charge when L2 isn't permitted.
- T-MAT-022: responses are never cached.

*— End of verbatim extract —*

---

**Snapshot consistency (DCR-64):** each profile-detail GET runs in one `READ ONLY, REPEATABLE READ` transaction. The session and account gate, every access rule and the data returned all come from the same snapshot, so a response never mixes two database states. Changes that commit before the snapshot is taken are always honoured. Nothing caches the result (`Cache-Control: private, no-store`). Document content is never in the GET response: each download goes through the document-access service at request time. Each photo signed-URL issuance re-checks permission and eligibility (URLs live at most 300 seconds, risk R-8).

> *Verbatim from `docs/baseline/v4.6-F3/approved/05_v4.4.md` §5.1–5.3. Section references inside this block refer to that package.*

##### 5.1 Request deadline [TR; refines TR-19]

- **Deadline D = request start + 3 s** (configurable, `PROFILE_DETAIL_DEADLINE_MS`), set when the view starts.
- The GET opens one `READ ONLY, REPEATABLE READ` transaction.
- A Django `execute_wrapper` around that transaction does this **before every statement**:
  - computes the remaining time `r = D − now`
  - if `r ≤ 0`, raises `DeadlineExceeded`
  - otherwise runs `SET LOCAL statement_timeout = min(r, 5000 ms)`

  So no statement can run past D. **The 5-second `statement_timeout` stays as the per-query safeguard.**
- The response body is **built entirely in memory inside the transaction**. After the last read, the deadline is checked once more. Only then does the read-only transaction commit and the response go out.
- **Backstops** for stalls in application code between statements: `idle_in_transaction_session_timeout = 5 s` on this connection, and the web server worker timeout. If PostgreSQL ≥ 17 is used, `SET LOCAL transaction_timeout = D` is added as a further backstop (optional; AS-18, since AS-3 only assumes ≥ 15).

##### 5.2 When the deadline is exceeded

- Any `DeadlineExceeded`, `statement_timeout` cancellation (57014), idle-transaction termination or connection loss → **roll back**.
- Return **`503 request_deadline_exceeded`** with `Retry-After`, an error envelope, and **no profile data at all**. Any partly built body is thrown away.
- Nothing is written (it was read-only). Nothing is charged.
- The event is logged with the `request_id` and counted in a metric.

##### 5.3 Guarantee (replaces v4.3)

Each successful response comes from one consistent snapshot. **The snapshot is never more than D old when the response is released** (plus network transfer time). Changes that commit before the snapshot is taken are always honoured. A request that can't finish within D returns nothing.

**Tests:**
- T-MAT-023: a delay injected between statements past D → 503, no data.
- T-MAT-024: a slow single statement → cancelled by the per-statement limit derived from D → 503.
- T-MAT-025: deadline passed after the body is built but before release → 503.
- T-MAT-026: normal requests still meet D.

*— End of verbatim extract —*

### 22.6 Log privacy, anonymisation and key destruction (DCR-67, DCR-75, DCR-76) [TR-23]

- **Structures:** pseudonyms, subject data keys, envelopes and the linkable-ID rule are defined in doc 03 §22.2. OutboxEvent privacy is in doc 03 §22.12.
- **Anonymisation without modifying logs:** at deletion PROCESSING, each subject's pseudonym is unlinked and its data key is destroyed through a Stream R SHRED operation (doc 09). Existing AuditLog and AccountSecurityEvent rows stay byte-for-byte unchanged, but can no longer be linked to the person and their encrypted personal context can't be decrypted. The append-only rule isn't weakened.
- **Holds:** if an active legal or security hold covers the subject, unlinking and key destruction are deferred until the hold is released (FR-DAT-009).
- **Retention:** log partitions are dropped whole at the end of retention by a maintenance role (doc 09); the application role has no UPDATE or DELETE rights on these logs.
- **Retained financial records** (ledger, ProfileView) keep their `account_id`, which points at the retained, anonymised User row (doc 03 §19) under financial retention [FR-DAT-009].

> *Verbatim from `docs/baseline/v4.6-F3/approved/06_v4.5.md` §2.2. Section references inside this block refer to that package.*

##### 2.2 Key destruction and tombstones

`SubjectDataKey` columns: `key_id`, `pseudonym`, `kek_version`, `wrapped_key` (nullable), `created_at`, `destroyed_at`.

```sql
CHECK ((destroyed_at IS NULL) = (wrapped_key IS NOT NULL))
```

**Destruction** sets `wrapped_key = NULL` and `destroyed_at = now()` in one update. The remaining row is a **non-sensitive tombstone**: IDs and timestamps only, no key material. This table is a mutable mapping, not an append-only log.

**Making it irreversible, stated honestly.** Copies of the wrapped key can persist in old row versions until VACUUM runs, in archived WAL, and in backups. To make destruction truly irreversible:
- (a) The master key (KEK) is **versioned** and rotated monthly. New data keys are wrapped with the current version, and existing data keys are re-wrapped on rotation.
- (b) **Each KEK version is destroyed in the secret store once the longest backup or WAL retention that could hold keys it wrapped has passed.** After that, every old copy of a wrapped key is permanently undecryptable.
- (c) VACUUM runs on the key table after every destruction batch.

So the residual window is **at most the backup retention period** (AS-17, now explicitly bounded by KEK destruction). The retention period itself is part of the legal review (doc 13 OD-005).

*— End of verbatim extract —*

**Residual risks (from the linkable-ID rule, baseline v4.5 §2.4):**
- (a) Identity can still be recovered only through records legally kept in identifiable form (financial or hold records). Those are accessible only to authorised roles, with every read audited. The logs add no extra path to them.
- (b) After unlinking, a pseudonym still groups that subject's past events together, which is pseudonymous behavioural data. Whether that is acceptable is part of the legal review (risk R-19, doc 13).

### 22.7 External compliance registry (DCR-74, DCR-86) [TR-24]

The registry is an append-only, hash-chained record kept **outside the primary database** in a write-once storage location (recommended: a separate S3 bucket with Object Lock in compliance mode, versioning and cross-region replication). The application role can only add objects; only the restore role can read them. **This is a new AWS resource that may carry cost and needs owner approval before production** (`CLAUDE.md` CC-R73, doc 19 §5). The write order, operation protocol, restore procedure and startup gate are in doc 09.

> *Verbatim from `docs/baseline/v4.6-F3/approved/07_v4.6.md` §2.1–2.3. Section references inside this block refer to that package.*

##### 2.1 Content: pseudonyms only (C-54)

| Entry | Fields |
|---|---|
| `SHRED` | `op_id`, `pseudonym`, `key_id`, `kek_version` |
| `DELETION_COMPLETED` | `op_id`, **`account_pseudonym`, `profile_pseudonym`** (the random UUIDs from `SubjectPseudonym`), `completed_at` (day precision) |
| `MAINTENANCE` | §3 / §6 (contains no personal data) |

The registry stores **no** account ID, profile ID, deletion-request ID, phone, email or name. An internal reference such as a deletion request is represented only by `op_id` (a random UUIDv7) and the pseudonyms.

##### 2.2 How a restore finds the right deletions without the registry identifying anyone

- A pseudonym means something **only** together with a `SubjectPseudonym` row that still has `subject_id` set.
- In the **live** database, deleted subjects have been unlinked, so the registry resolves to nobody.
- A **restored backup** taken before the deletion still holds that link. The restore process matches `account_pseudonym` against the restored `SubjectPseudonym` and re-runs the idempotent deletion steps for that subject (v4.5 §2.1 step 3), which unlinks it again. A pseudonym that isn't in the restored database is skipped, because that subject didn't exist when the backup was taken.

So the registry on its own is just a list of random UUIDs. It becomes identifying only next to a backup that already contains the identities, and backups expire.

##### 2.3 Two streams with different retention, plus checkpoints (C-55)

| Stream | Entries | Object-lock retention |
|---|---|---|
| **R (restore)** | `SHRED`, `DELETION_COMPLETED` | **Longest backup retention + 30 days.** Once no restorable backup predates an entry, it can't be needed. |
| **M (maintenance)** | All maintenance operations (§6) | The maintenance-audit retention placeholder (7 years, subject to legal review) |

Each stream has its own `seq` and hash chain. One chain with mixed retention would break verification once the shorter-lived entries expired.

**Checkpoints:** every day, a signed `CHECKPOINT {stream R, seq, head_hash}` entry is written to stream **M**, so it's retained long-term. Verifying stream R starts from the newest checkpoint older than the oldest restorable backup. Expired R entries before that checkpoint don't break verification.

**Test:** T-REG-010 (§3.6) checks registry content and finds no account, profile or deletion-request IDs and no direct identifiers.

*— End of verbatim extract —*

### 22.8 Account standing (DCR-89, DCR-93) [TR-03]

`get_account_standing(account)` is the single predicate used by the account-state gate, delegated access, the recovery-scoped login and notification eligibility. Its definition and the notification category matrix [REC-BIZ, OD-02e] are in doc 05 §25.5. A subject in `restore_quarantine` has standing `RESTORE_QUARANTINED`, treated exactly like `DELETION_PROCESSING`.

### 22.9 Closed-connection history (DCR-59, DCR-83)

Entering CLOSED ends connection-derived access and new communication, but keeps conversation history readable read-only for both participants under the existing access and retention rules (doc 15 §7, doc 05 §25.10). A block in either direction makes history unreadable.
