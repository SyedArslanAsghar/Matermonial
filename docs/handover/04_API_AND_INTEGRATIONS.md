# Matermonial — API and Third-Party Integration Specifications

**Version:** 1.0  
**Date:** 11 November 2026  
**API base path:** `/api/v1/`  
**Document status:** APPROVED_WITH_OPEN_ITEMS (project owner, 2026-11-17, DR-2026-11-17-A; record in doc 20 §5). **Open items:** OPEN ODs: OD-02, OD-03, OD-06, OD-08; PROPOSED TRs: TR-01, TR-02, TR-08, TR-19, TR-21. Listed items keep their own status (doc 19); this document status doesn't approve them.  
**Applied corrections:** DCR-04, 10, 17, 26, 39, 41, 64, 72 (doc 20); G1 correction pass 2026-11-17 (DR-2026-11-17-C). The acting-profile algorithm, view billing and error catalogue are in **§24**. Verbatim extracts start with a "*Verbatim from …*" line and end with "*— End of verbatim extract —*"; text outside those markers is editorial.

## 1. API principles

1. Use REST conventions and JSON responses.
2. Use UUIDs for major resource identifiers.
3. Require authentication for protected operations.
4. Enforce object-level permissions on every private resource.
5. Keep business logic in domain services.
6. Use pagination for collection endpoints.
7. Document endpoints with OpenAPI.
8. Use standardized errors.
9. Use idempotency keys for payment and retry-sensitive operations.
10. Never trust frontend authorization or payment-success claims.
11. Do not expose private database fields in serializers.
12. Keep API versioning independent from application release versions.

## 2. Authentication endpoints

Recommended endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/register/` | Create account |
| POST | `/auth/otp/send/` | Send phone OTP |
| POST | `/auth/otp/verify/` | Verify OTP |
| POST | `/auth/login/` | Authenticate |
| POST | `/auth/logout/` | Revoke current session/token |
| POST | `/auth/token/refresh/` | Refresh access token, if using refresh-token architecture |
| POST | `/auth/password/forgot/` | Start password reset |
| POST | `/auth/password/reset/` | Complete password reset |
| GET | `/auth/me/` | Current account |
| GET | `/auth/sessions/` | List permitted session history |
| DELETE | `/auth/sessions/{id}/` | Revoke a session (identical 404 for sessions that aren't the caller's) |
| POST | `/auth/sessions/revoke-others/` | Revoke all other sessions (G1, TR-01) |
| GET | `/auth/csrf/` | Obtain the CSRF token for web login (G1, TR-01) |
| POST | `/auth/reauthenticate/` | Step-up re-authentication; sets `reauthenticated_at` (G1, TR-01) |

Use a secure token/session architecture. If JWT is selected, use short-lived access tokens, protected refresh-token handling, rotation, and revocation strategy. Store tokens securely on mobile.

> **G1 (DCR-16):** the proposed architecture [TR-01] uses Django server-side sessions for web and opaque, hashed access and refresh tokens with deterministic rotation for mobile; see doc 06 §22.1–§22.2.

## 3. Profile endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/profiles/` | Create own profile |
| GET | `/profiles/me/` | Retrieve own profile |
| PATCH | `/profiles/me/` | Update own profile |
| GET | `/profiles/{id}/` | View eligible profile. Re-evaluates access on every request; **never charges** (G1, DCR-26, DCR-39; §24.2) |
| POST | `/profiles/{id}/views/` | Create or reuse a profile-view grant; the only endpoint that charges (G1, DCR-26; §24.2) |
| PATCH | `/profiles/{id}/` | Update represented profile if authorized |
| GET | `/profiles/{id}/completion/` | Profile completion |
| POST | `/profiles/{id}/submit-review/` | Submit profile for applicable review |
| POST | `/profiles/{id}/photos/` | Upload photo |
| GET | `/profiles/{id}/photos/` | List accessible photos |
| PATCH | `/profiles/{id}/photos/{photo_id}/` | Update permitted photo metadata |
| DELETE | `/profiles/{id}/photos/{photo_id}/` | Remove own/authorized photo |

A profile ID in the URL does not establish ownership or manager authorization.

## 4. Partner preference endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/profiles/me/partner-preferences/` | Retrieve preferences |
| PUT | `/profiles/me/partner-preferences/` | Replace preferences |
| PATCH | `/profiles/me/partner-preferences/` | Partially update preferences |

Validate age and earning ranges. Preserve nullable Boolean semantics.

## 5. Verification endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/verification/identity/` | Start identity verification |
| GET | `/verification/identity/me/` | Current verification status |
| POST | `/verification/identity/{id}/documents/` | Upload document |
| POST | `/verification/identity/{id}/resubmit/` | Resubmit after rejection |
| GET | `/verification/identity/{id}/history/` | Authorized verification history |

Administrative review endpoints should be separately permission-protected.

Do not expose internal reviewer notes or duplicate-document fingerprints through user APIs.

## 6. Family management endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/family-management/authorizations/` | List relevant authorizations |
| POST | `/family-management/authorizations/` | Invite manager |
| POST | `/family-management/authorizations/{id}/accept/` | Accept invitation |
| POST | `/family-management/authorizations/{id}/reject/` | Reject invitation |
| POST | `/family-management/authorizations/{id}/pause/` | Pause |
| POST | `/family-management/authorizations/{id}/resume/` | Resume |
| POST | `/family-management/authorizations/{id}/revoke/` | Revoke |
| GET | `/family-management/permissions/` | List permission catalog |
| GET | `/family-management/permission-groups/` | List templates |
| PUT | `/family-management/authorizations/{id}/permissions/` | Update permissions |
| GET | `/family-management/authorizations/{id}/history/` | Authorization history |
| GET | `/family-management/profile-access-history/` | Owner's profile-access history |

The owner must be the only actor allowed to manage authorization by default.

## 7. Search and matching endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/search/profiles/` | Search eligible profiles |
| GET | `/matching/recommendations/` | Rule-based recommendations |
| POST | `/search/saved/` | Save named search |
| GET | `/search/saved/` | List saved searches |
| PATCH | `/search/saved/{id}/` | Update saved search |
| DELETE | `/search/saved/{id}/` | Delete saved search |
| GET | `/favorites/` | List favorites |
| POST | `/favorites/` | Add favorite |
| PATCH | `/favorites/{id}/` | Update private note |
| DELETE | `/favorites/{id}/` | Remove favorite |

Search must exclude ineligible, blocked, and hidden profiles before returning results.

## 8. Interest and request endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/interests/` | Express interest |
| GET | `/interests/received/` | Received interests |
| GET | `/interests/sent/` | Sent interests |
| POST | `/interests/{id}/show-interest-back/` | Show interest back |
| POST | `/interests/{id}/formal-request/` | Convert/advance to formal request according to business rules |
| POST | `/interests/{id}/decline/` | Decline interest |
| POST | `/interests/{id}/withdraw/` | Withdraw a pending interest (sender), or a reciprocated interest (either party) [REC-BIZ, OD-06d/OD-06m, OPEN] |
| POST | `/requests/` | Create formal request |
| GET | `/requests/` | List relevant requests |
| GET | `/requests/{id}/` | Retrieve authorized request |
| POST | `/requests/{id}/accept/` | Accept |
| POST | `/requests/{id}/decline/` | Decline |
| POST | `/requests/{id}/withdraw/` | Withdraw |
| GET | `/requests/{id}/history/` | Request history |

The exact relationship between a lightweight interest record and a formal request must be implemented consistently with the approved interest workflow. Do not create duplicate records or charge a formal-request credit for an action that is only an interest unless the configured business rule explicitly requires it.

## 9. Connection endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/connections/` | List connections |
| GET | `/connections/{id}/` | Connection detail |
| POST | `/connections/{id}/pause/` | Pause |
| POST | `/connections/{id}/resume/` | Resume |
| POST | `/connections/{id}/close/` | Close |
| POST | `/connections/{id}/complete/` | Mark completed/engaged |
| POST | `/connections/{id}/reopen/` | Request mutual reopening; if the other party already has a pending request, this confirms it (doc 15 §19) |
| GET | `/connections/{id}/history/` | Connection history |
| GET | `/connections/{id}/progress/` | Relationship progress |
| PATCH | `/connections/{id}/progress/` | Update progress |
| GET | `/connections/{id}/progress/history/` | Progress history |

Enforce connection state and block restrictions on every action.

## 10. Messaging endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/conversations/` | List conversations |
| GET | `/conversations/{id}/` | Conversation detail |
| GET | `/conversations/{id}/messages/` | Paginated message history |
| POST | `/conversations/{id}/messages/` | Send message |
| POST | `/conversations/{id}/attachments/` | Upload attachment |
| POST | `/messages/{id}/read/` | Mark read |
| GET | `/documents/` | List own/accessible documents |
| POST | `/documents/` | Upload shared document |
| POST | `/documents/{id}/share/` | Grant access |
| POST | `/documents/{id}/revoke-access/` | Revoke access |
| GET | `/documents/{id}/access-history/` | Authorized access history |

Message sending requires an active connection and valid participant authorization.

## 11. Privacy endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/privacy/settings/` | Retrieve privacy settings |
| PATCH | `/privacy/settings/` | Update privacy settings |
| GET | `/privacy/blocked-profiles/` | List blocked profiles |
| POST | `/privacy/blocked-profiles/` | Block profile |
| DELETE | `/privacy/blocked-profiles/{id}/` | Unblock |
| GET | `/privacy/hidden-profiles/` | List hidden profiles |
| POST | `/privacy/hidden-profiles/` | Hide profile |
| DELETE | `/privacy/hidden-profiles/{id}/` | Unhide |
| POST | `/privacy/photo-access-requests/` | Request photo access |
| POST | `/privacy/photo-access-requests/{id}/approve/` | Approve |
| POST | `/privacy/photo-access-requests/{id}/decline/` | Decline |
| GET | `/privacy/visitor-history/` | Retrieve eligible visitor history |
| DELETE | `/privacy/visitor-history/{id}/` | Remove visible visitor record |

Do not reveal the existence of a hidden or blocked relationship through error messages.

## 12. Subscription, credit, and payment endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/subscriptions/plans/` | List active plans |
| GET | `/subscriptions/me/` | Current subscription |
| POST | `/subscriptions/purchase/` | Initiate subscription purchase |
| POST | `/subscriptions/cancel/` | Cancel future renewal |
| GET | `/credits/wallet/` | Current credit balances |
| GET | `/credits/transactions/` | Transaction history |
| GET | `/credits/packages/` | Active top-up packages |
| POST | `/credits/purchase/` | Initiate top-up purchase |
| GET | `/payments/{id}/` | Retrieve own payment |
| POST | `/payments/jazzcash/callback/` | Gateway callback endpoint |

The callback endpoint must be verified according to the gateway contract. It must not accept a frontend assertion of payment success.

Payment endpoints should use idempotency and merchant-reference validation.

## 13. Notification endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/notifications/` | List notifications |
| POST | `/notifications/{id}/read/` | Mark read |
| POST | `/notifications/read-all/` | Mark all read |
| GET | `/notifications/preferences/` | Retrieve preferences |
| PATCH | `/notifications/preferences/` | Update preferences |
| GET | `/notifications/devices/` | List push devices |
| POST | `/notifications/devices/` | Register push device |
| DELETE | `/notifications/devices/{id}/` | Revoke push device |

## 14. Moderation endpoints

User-facing:

- `POST /reports/`
- `GET /reports/my/`
- `GET /reports/{id}/`
- `POST /moderation/appeals/`
- `GET /moderation/appeals/my/`

Administrative moderation endpoints must be placed under an admin namespace or otherwise clearly separated and permission-protected.

Do not expose other users' reports or internal evidence to ordinary users.

## 15. Data export and account deletion endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/data-exports/` | Request export |
| GET | `/data-exports/` | List own export requests |
| GET | `/data-exports/{id}/` | Export status |
| POST | `/data-exports/{id}/verify/` | Complete required identity confirmation |
| GET | `/data-exports/{id}/download/` | Obtain temporary download access |
| POST | `/account-deletion/` | Request account deletion |
| GET | `/account-deletion/` | Retrieve own deletion request |
| POST | `/account-deletion/{id}/cancel/` | Cancel during recovery period |

The export must include only data the requester is authorized to access.

> **G1 (DCR-41):** while a deletion request is in PENDING_RECOVERY, the only login is a recovery-scoped session (password + OTP, 15-minute limit, no refresh). It may call only `GET /account-deletion/`, `POST /account-deletion/{id}/cancel/` and `POST /auth/logout/`; everything else returns `403 account_pending_deletion` (doc 05 §25.9) [REC-BIZ, OD-02d, OPEN]. **Canonical paths (DR-2026-11-17-C4):** this §15 catalogue (`/account-deletion/…`) is the canonical endpoint reference. The baseline v4 §10.6 text (reproduced in doc 05 §25.9) names these endpoints `/account/deletion/` and `/account/deletion/cancel/`; that wording sits in an OPEN/proposed area (TR-21, OD-02d) and doesn't override this catalogue. No endpoint behaviour is changed.

## 16. API pagination

Use a consistent pagination response.

Recommended format:

```json
{
  "count": 100,
  "next": "https://example.com/api/v1/profiles/?page=2",
  "previous": null,
  "results": []
}
```

Set sensible default and maximum page sizes through backend settings.

## 17. Third-party integration architecture

Define provider interfaces instead of placing provider-specific code throughout business modules.

Recommended interfaces:

```text
PaymentProvider
├── initiate_payment()
├── verify_callback()
├── query_transaction()
└── process_refund()

SMSProvider
├── send_message()
└── get_delivery_status()

EmailProvider
├── send_email()
└── get_delivery_status()

PushProvider
├── send_notification()
└── invalidate_token()

StorageProvider
├── upload()
├── delete()
├── generate_temporary_url()
└── inspect_metadata()

OTPProvider
├── generate()
├── dispatch()
└── verify()
```

Implement local/mock providers for development and test environments.

## 18. JazzCash integration

The payment module must:

1. Create a local pending payment transaction.
2. Generate a unique merchant reference.
3. Initiate payment through the configured provider.
4. Redirect or otherwise guide the user through the provider's approved payment flow.
5. Receive the callback.
6. Verify callback authenticity and transaction details.
7. Match the callback to the local payment.
8. Confirm amount, currency, merchant reference, and status.
9. Process the payment exactly once.
10. Activate the subscription or grant the purchased credits.
11. Record the payment event and credit transaction.
12. Reconcile uncertain or missing callbacks.

Never grant credits based solely on a browser redirect.

The current JazzCash merchant contract, signatures, endpoint URLs, field names, and sandbox behavior must be verified before production integration.

## 19. Email and SMS

Email use cases:

- Account verification.
- Password reset.
- Security alerts.
- Request and connection notifications.
- Payment receipts.
- Export ready notifications.
- Deletion confirmation.

SMS use cases:

- OTP.
- Essential security notifications.
- Critical account notifications where configured.

Do not send private profile details or message contents in generic SMS notifications.

## 20. Push notifications

Support:

- Device registration.
- Multiple devices per account.
- Token replacement.
- Invalid token revocation.
- Notification preferences.
- Generic notification payloads.
- Deep links that still require server-side authorization.

## 21. Object storage

Use a storage abstraction with local filesystem support and production private object storage.

Recommended storage groups:

- Profile photos.
- Identity verification documents.
- Message attachments.
- Shared documents.
- Moderation evidence.
- Data exports.

Apply separate permissions and retention policies. Never store sensitive files in a public bucket by default.

## 22. Integration configuration

Use centralized environment/configuration settings for:

- S3/object storage.
- Email.
- SMS/OTP.
- JazzCash.
- Push notifications.
- Redis.
- Celery/background jobs.

Production credentials must be injected securely. Never commit `.env` files containing real secrets.

## 23. API acceptance criteria

- Every endpoint has an OpenAPI schema.
- All protected endpoints require appropriate authentication.
- Object-level authorization is tested.
- Pagination and error formats are consistent.
- Financial operations are idempotent.
- Payment callbacks are verified.
- Private files are not exposed publicly.
- Provider integrations have mock/test implementations.
- Integration failures are logged without exposing secrets.
- Web and mobile clients use the same API contracts.

## 24. Reconciled API specification (G1)

**Status:** [TR] PROPOSED (TR-02, TR-08, TR-19) unless marked [DECIDED]. Items tagged [REC-BIZ] depend on an OPEN owner decision.

### 24.1 Acting-profile authorization algorithm (DCR-17) [TR-02]

> *Verbatim from `docs/baseline/v4.6-F3/referenced/A4_v3.md` §9 (incorporated by reference, DR-2026-11-16-P1). Section references inside this block refer to that package.*

#### 9. Acting-Profile Authorization Algorithm [TR-02]

**Principle:** `X-Acting-Profile` *selects* a context. It never proves authorization.

**Ordered steps** (every profile-scoped request):
1. **Authenticate the account** per §8, including the account-state gate. The result is `actual_account`.
2. **Classify the endpoint.** Account-scoped endpoints reject the header with `400 header_not_allowed`. Profile-scoped endpoints continue to step 3.
3. **Select the profile.** Use the header (must be a valid UUID, otherwise `400`). If there's no header, use the caller's own personal profile. If there's neither, return `400 acting_profile_required`.
4. **Load the selected profile.** It must exist, not be CLOSED, and not have its owner's deletion in PROCESSING. Otherwise return `404 acting_profile_not_available`. The same response covers every failure in steps 4–7.
5. **Ownership:** if `profile.owner_id == actual_account.id`, mark the caller as owner and go to step 8.
6. **Manager authorization:** a `ProfileManagerAuthorization(profile, manager=actual_account)` row must exist with `status == ACTIVE`. PAUSED, PENDING, REVOKED, EXPIRED and REJECTED all deny, so **a paused manager has no access at all** [DECIDED]. Otherwise 404.
7. **Authorization expiry:** `expires_at IS NULL OR expires_at > now()`, evaluated at runtime regardless of the job-maintained status. Otherwise 404.
8. **Owner account status:** the owner account must be active, not deactivated, without a `FULL_ACCOUNT` restriction, and not in the deletion recovery period or processing (new activity is disabled then). For managers this returns `403 acting_profile_unavailable`; for owners, step 1 already covers it.
9. **Required permission:** each endpoint declares a permission code and tier.
   - Owners hold all owner capabilities.
   - For managers, an O-tier action returns `403 permission_not_granted`. Otherwise the `AuthorizationPermission` row must have `is_granted=True` and the catalogue entry must be active; if not, `403 permission_not_granted`.
10. **Step-up verification:**
    - S (communication): `AuthSession.reauthenticated_at` within 12 h.
    - Other S: within 10 min.
    - H: a valid, unconsumed `SensitiveActionVerification` for this exact action, consumed atomically in the business transaction, plus owner approval where required.
    - Owner O-tier actions (export, deletion, security changes): owner step-up within 10 min.
    
    If any check fails: `403 step_up_required`.
11. **Resource participation:** any resource in the path is loaded **through a query filtered by the represented profile** (for example, a request where sender or receiver is that profile, a conversation where it's a participant, a document it owns or holds an active permission for).
    - If not found: `404`, identical to a non-existent resource.
    - A participant acting in the wrong role (for example, the sender trying to accept): `403 action_not_allowed`.
12. **Eligibility and state:** block, hide, restriction and connection-state checks through the eligibility service. Failures return generic errors that reveal no hidden relationship.
13. **Transactional re-verification (writes):** inside the service transaction, `SELECT … FOR SHARE` on the authorization row and re-check steps 6–7. Pause and revoke take `FOR UPDATE`.
14. **Billing account:** `billing_account = represented_profile.owner`. **It's never `actual_account` unless the caller is the owner.**
15. **Build the immutable `ActorContext`:** `actual_account`, `represented_profile`, `is_owner`, `authorization_id`, `permission_code`, `step_up_reference`, `billing_account`, `request_id`, `ip`, `user_agent`. It's per-request only and never cached.
16. **Execute the service.** Services accept an `ActorContext`, never raw actor or profile IDs from the client.
17. **Record:**
    - domain history (`performed_by` = actual account, `performed_for_profile` = represented profile)
    - audit (`actor_type` OWNER|MANAGER, `authorization_id`, `request_id`)
    - `ManagerActionLog` and `ProfileAccessHistory` on the manager path
    - owner notification via the outbox for S and H actions
    
    The response uses context-aware field allowlists.

**Tests (T-ACT):**

| ID | Case | Expected |
|---|---|---|
| 001 | Header pointing at a stranger's profile | 404, same body as a non-existent profile |
| 002 | Paused / revoked / pending authorization | 404 |
| 003 | Expired by timestamp, job not yet run | 404 |
| 004 | Owner deactivated or in deletion recovery | 403 for the manager |
| 005 | Permission not granted / O-tier action | 403 |
| 006 | S without step-up, H without verification, H verification reused | 403 |
| 007 | **Request** belonging to another pair, accessed by owner or manager | 404 |
| 008 | Sender tries to accept their own request | 403 |
| 009 | **Conversation** messages read by a non-participant profile | 404 |
| 010 | Manager without `view_conversations` | 403 |
| 011 | **Document** download by a non-recipient / after permission revoked or expired | 404 / denied |
| 012 | Photo of another profile without photo permission | Denied |
| 013 | Another account's favorite or private note | 404 |
| 014 | Header = profile A, path resource belongs to profile B | 404 |
| 015 | Header sent to an account-scoped endpoint | 400 |
| 016 | Revocation racing a delegated write | Either commits before revoke, or is denied |
| 017 | Billing and audit fields | Owner account billed. Manager recorded as actor. |
| 018 | Notification for a hidden or blocked relationship | No disclosure |

*— End of verbatim extract —*

---

### 24.2 Profile-view billing and profile-detail access (DCR-26, DCR-39, DCR-64, DCR-72) [DECIDED rules; TR-08, TR-19 mechanics]

> *Verbatim from `docs/baseline/v4.6-F3/referenced/A4_v3.md` §10 (incorporated by reference). Section references inside this block refer to that package.*

**Billing account** = the owner account of the represented profile performing the view. **A manager's personal account is never charged, read or locked for a delegated view.** The window is a rolling 24 hours per (billing account, target) [DECIDED]. Allowance is consumed before purchased credits [DECIDED].

**Billing is separate from visibility:** the access level (L0–L3, OD-03) decides *whether* full detail can be seen at all. Billing decides only whether a view grant must be paid for. Billing never widens access.

**`POST /profiles/{id}/views/`**, in one transaction:
1. Run §9 with `view_profile_details`. Eligibility must allow L2.
2. Apply the exemptions if OD-08a is approved. Until then, no exemptions are implemented.
3. `SELECT … FOR UPDATE` on the billing account's `CreditWallet`. This is the per-account serialisation point for the owner and all their managers.
4. Look for a billable view by this billing account for this target within the last 24 hours. If one exists, record a non-billable view and return the existing grant.
5. Otherwise lock the active PROFILE_VIEW allowances (earliest expiry first) and debit 1, falling back to the purchased view bucket. If both are empty, raise `insufficient_profile_view_credits` and roll everything back (response per OD-08b).
6. Insert the ledger row with `bucket_balance_after`, update the projection, write `ProfileView` (with `billing_account`, `viewer_user`, `viewer_profile`), write `VisitorHistory` (respecting private browsing), write the audit entry.
7. Commit.

**`GET /profiles/{id}/`** returns full detail only when a grant exists in the window, or an approved exemption applies. Otherwise `402 profile_view_required`. The `GET` itself never charges.

**Guarantees:**
- **Idempotency:** the optional `Idempotency-Key` header replays the original response. Even without it, the window rule under the wallet lock prevents double charging.
- **Rollback:** any failure leaves no ledger row, projection change or view record. If the response fails after commit, the grant already exists, so a retry costs nothing.
- **Ledger consistency:** governed by §6 rows 8–9.

**Tests:** T-MAT-010…016 (from v2), plus T-MAT-017: GET never charges, and T-MAT-018: billing never grants access above the visibility level.

*— End of verbatim extract —*

**Amendments (baseline v4 §8, v4.3 §4, v4.4 §5):**
- `GET /profiles/{id}/` re-evaluates every access rule on **every** request (visibility, blocks in both directions, Hide My Profile From, restrictions, connection status, eligibility, access level). A billing grant is necessary for billable L2 access but never sufficient, and never raises access above the computed level (doc 06 §22.5).
- `POST /profiles/{id}/views/` **refuses to charge** when the maximum access level is below L2, returning `403 profile_detail_not_available`.
- The GET runs in one `READ ONLY, REPEATABLE READ` snapshot with a request deadline (default 3 s). If the deadline is exceeded it returns `503 request_deadline_exceeded` with `Retry-After`, an error envelope and no profile data (baseline v4.4 §5.2; doc 06 §22.5, doc 12 §7).
- Billing exemptions are OD-08a and the zero-credit response is OD-08b [REC-BIZ, OPEN]; until approved, no exemptions are implemented.

### 24.3 Idempotency

Financial and retry-sensitive endpoints accept an optional `Idempotency-Key` header. A repeated key replays the original response (stored in `IdempotencyRecord`, doc 03 §22.2). Internal operations also use deterministic keys (for example `refund:request:<request_id>`).

### 24.4 Error catalogue (codes introduced by the baseline)

| HTTP | Code | Meaning |
|---|---|---|
| 400 | `header_not_allowed` | `X-Acting-Profile` sent to an account-scoped endpoint |
| 400 | `acting_profile_required` | No acting profile could be selected |
| — | `invalid_credentials` | Generic login failure |
| 401 | `session_revoked` / `session_expired` / `invalid_token` | Session or token not usable |
| 402 | `profile_view_required` | Full detail needs a view grant |
| 402 (recommended; **OD-08b OPEN**) | `insufficient_profile_view_credits` | No view credits left. The `402` status and the response body are the OD-08b recommended default [REC-BIZ]; neither is final until OD-08b is decided. |
| 403 | `acting_profile_unavailable` | The represented profile's owner account is unavailable (manager path) |
| 403 | `permission_not_granted` | The manager lacks the permission, or the action is Owner-only |
| 403 | `step_up_required` | Re-authentication or single-use verification needed |
| 403 | `action_not_allowed` | The caller participates but in the wrong role (for example the sender accepting) |
| 403 | `profile_detail_not_available` | View charge refused because full detail isn't permitted |
| 403 | `account_pending_deletion` | Endpoint not available in a recovery-scoped session |
| — | `reopen_not_available` | A reopen check failed (generic) |
| 404 | `acting_profile_not_available` | Selected profile doesn't exist, isn't the caller's, or isn't authorized (same body as a missing profile) |
| — | `interest_not_pending` | The interest is no longer pending |
| — | `interest_pending` | A pending interest must be resolved before a direct request |
| 409 | `connection_already_paused` | The other party has already paused the connection |
| — | `reopen_request_expired` | The reopen request's time-to-live has passed |
| 429 | (rate limit) | With `Retry-After` |
| 503 | `request_deadline_exceeded` | Profile-detail deadline exceeded; no data returned; with `Retry-After` |
| 503 | `temporarily_unavailable` | Lock contention retries exhausted; with `Retry-After` |

"—" means the baseline doesn't fix the HTTP status; it is set in the OpenAPI contract for the phase. Errors never reveal a hidden or blocked relationship [DECIDED].
