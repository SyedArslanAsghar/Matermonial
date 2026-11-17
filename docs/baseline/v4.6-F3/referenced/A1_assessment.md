# Matermonial: Project Assessment Report

**Scope:** Assessment only. I didn't create, modify, delete, install or migrate anything.
**Evidence base:** I read the root `CLAUDE.md`, `README.md`, all 18 files in `docs/handover/` (00–17) in full, the 5 placeholder files in `docs/decisions/` and `docs/implementation/`, every file under `backend/`, and the repository and environment state.

**Labels used:** **[APPROVED]** is a documented approved decision. **[EXISTING]** is something already in the repository. **[REC]** is my recommendation. **[ASSUMPTION]** is something I inferred and haven't confirmed.

---

## A. Executive Summary

Matermonial is a privacy-first matrimonial platform. Its distinguishing feature is the separation of three things: the **account** (authentication and billing identity), the **matrimonial profile** (the person seeking a match), and **profile-scoped, owner-granted family-manager authorization**. On top of that sit a consent-driven funnel (interest → formal request → connection → conversation), a two-bucket credit economy (subscription allowances vs. purchased top-ups, with an append-only ledger), strict media and document permissions, and GDPR-style export and deletion.

**Readiness:**

| Area | State |
|---|---|
| Specification | **Strong but not implementation-complete.** The business rules (doc 05), security (06), permissions (14) and state machines (15) are good quality. Three structural defects matter: **(1)** the **Interest entity is missing from the database design** even though the SRS, rules, API and state machines all depend on it; **(2)** the SRS is two merged drafts and lacks the required 22-domain catalogue; **(3)** several financial and gating rules are ambiguous (see M). |
| Code | **Very early Phase 1.** There is one Django app (`accounts`) with a custom UUID `User`, settings split into base/local/test/production, DRF, drf-spectacular and a health endpoint. There are **no migrations**, the frontend, mobile, infrastructure and CI folders are empty, and the project is **not a Git repository**. |
| Runnable? | **Not verified.** The root `.venv` contains only pip (no Django), and it was created at a different path (`…/matermonial_backend_foundation/.venv`), so its activation scripts are stale. Installing dependencies was out of scope, so **I didn't run any tests**. |
| Key opportunity | No migration has ever been generated. The `User` model and app layout can therefore still be finalised **at zero data-migration cost**. That window closes at the first `makemigrations`. |

---

## B. Documentation Inventory

### `docs/handover/` (all 18 present)

| File | Purpose | Complete? | Decision status |
|---|---|---|---|
| `00_MASTER_HANDOVER_INDEX.md` | Entry point, authority order, catalogue | Yes | "Handover baseline". Defines the conflict-priority order. |
| `01_COMPLETE_SRS.md` | Requirements and MVP scope | **Structurally defective** (see C1–C3) | "Development Handover Baseline" |
| `02_SYSTEM_ARCHITECTURE.md` | Architecture, app layout, outbox, storage | Yes | "Architecture Baseline". Layout and error format are "recommended". |
| `03_DATABASE_DESIGN.md` | 16 modules, entities, constraints | Substantial. **Missing Interest.** Many enums, types and `on_delete` rules are unspecified. | No status line. Modules 15 and 16 are explicitly "recommended". |
| `04_API_AND_INTEGRATIONS.md` | Endpoint list, provider interfaces, JazzCash flow | **Endpoint inventory only.** No request/response schemas, error-code catalogue or admin API. | No status line. Auth endpoints are "recommended". |
| `05_BUSINESS_RULES_AND_WORKFLOWS.md` | Domain rules and workflows | Good | No status line. Treated as approved per doc 00 priority #2. |
| `06_SECURITY_PRIVACY_AUTHORIZATION.md` | Security, privacy, authorization | Good. **Token lifetimes missing** (SRS FR-007 defers them to this doc). | No status line |
| `07_REPOSITORY_AND_DEVELOPMENT_STANDARDS.md` | Monorepo layout, conventions, DoD | Yes. Its docs tree doesn't match reality. | No status line |
| `08_TESTING_AND_QA.md` | Test layers, critical scenarios, gates | Yes | No status line |
| `09_AWS_DEPLOYMENT_AND_CICD.md` | EC2/Docker/Nginx topology, CI/CD | Yes, as a recommendation | "Recommended initial topology" |
| `10_IMPLEMENTATION_ROADMAP.md` | Phases 0–18 | Yes. **Has dependency-ordering problems** (C8). | No status line |
| `11_ARCHITECTURE_DECISIONS.md` | ADR-001…024 | Yes | Mixed: ADR-014 and 022 are "Recommended", ADR-023 is "Proposed", the rest are approved |
| `12_CLAUDE_CODE_INSTRUCTIONS.md` | AI instructions | Yes, but an **older copy** of the root `CLAUDE.md` | n/a |
| `13_ASSUMPTIONS_RISKS_TRACEABILITY.md` | Assumptions A-001…020, open decisions OD-001…007, risks, traceability | Yes (the traceability matrix is coarse) | Clearly separates approved from recommended. Good. |
| `14_FAMILY_MANAGER_PERMISSION_MATRIX.md` | Permission catalogue and templates | Mostly. Missing permissions (C6). | Templates are "recommended" |
| `15_STATE_MACHINES.md` | Lifecycle transitions | **Interest is unfinalised.** Several transitions are missing (C7). | Payment and moderation states are "recommended" |
| `16_ENVIRONMENT_CONFIGURATION.md` | Settings, flags, validation | Yes | No status line |
| `17_GLOSSARY.md` | Terminology | Yes | n/a |

### `docs/decisions/`
| File | State |
|---|---|
| `new_architecture_decisions.md` | **Placeholder (`_TODO_`).** ADRs currently live only in handover doc 11. |

### `docs/implementation/`
| File | State |
|---|---|
| `progress.md`, `completed_features.md`, `pending_features.md`, `known_issues.md` | **All placeholders (`_TODO_`).** The mandatory tracking hasn't started. |

### Referenced but absent
- `CLAUDE.md` §2 and doc 07 §1 point to `docs/00_master_handover_index.md`, `docs/01_srs.md` and so on. **None of these paths exist.** The real files are `docs/handover/NN_UPPERCASE.md`. I used the handover files, as `CLAUDE.md` instructs when a document is missing.
- There's no traceability matrix file, no OpenAPI artifact and no `LICENSE` (doc 07 lists one).

---

## C. Documentation Gaps, Conflicts and Duplications

**C1. The SRS is two merged drafts.** It has two "Introduction"/"Purpose" blocks, duplicated §1.3 and §1.3.1 principles, an "End of Document 01 — Part 1" marker in the middle, and **two requirement-ID schemes**: `FR-001…FR-021` and `FR-ACC/PRO/VER/FAM/MAT/REQ/CON/MSG/PRI/SUB/DAT`. Doc 13's traceability uses only the second scheme, so the Part 1 IDs are orphaned. *[REC] Consolidate onto one ID scheme and add a cross-reference table.*

**C2. The 22-domain catalogue and its mapping to the 16 modules are missing.** Doc 00 §5 says doc 01 "must contain" them, and they're a handover-completion criterion (doc 00 §11). The SRS actually has about 15 requirement sections, so **the handover-completion criteria aren't yet met.**

**C3. Stack contradiction.** SRS §1.4 says *"Django-based administration, with the approved SQLAdmin patterns"*. SQLAdmin is a SQLAlchemy/FastAPI admin and doesn't work with Django. It looks like a leftover from an earlier stack. *[REC] Remove it.*

**C4. The Interest entity is missing from the database design (highest-impact gap).** The SRS (FR-REQ-001…003), doc 05 §3, the doc 04 `/interests/*` endpoints, doc 15 §5 and the glossary all treat Interest as a separate concept with its own 30-day directional decline cooldown. Doc 03 Module 07 has only `MatrimonialRequest`, `RequestHistory` and `RequestCooldown`, whose reason field is DECLINED or EXPIRED and is request-only. Doc 15 §5 openly says the interest model isn't final. Undefined points:
- What does "Show Interest Back" produce: just mutual visibility, or a free connection?
- When a recipient "sends a formal request" from an interest, they become the sender and pay the credit. Is that right?
- Are interests free, rate-limited or credit-charged?

**C5. Duplicate sources of truth in doc 03:**
- `MatrimonialProfile.visibility_status` duplicates `ProfilePrivacySettings.profile_visibility`.
- `MatrimonialProfile.verification_status` duplicates `IdentityVerification.status`.
- `MatrimonialProfile.is_active` duplicates `profile_status`.
- `show_location` exists on both `ProfileLocation` and `ProfilePrivacySettings`.
- The visibility enums disagree: doc 03 has `HIDDEN / VISIBLE_IN_MATCH_SEARCH / LIMITED_VISIBILITY`, while FR-PRO-006 has "Visible in match search / Visible after acceptance / Hidden".
- `CreditWallet` subscription balances duplicate the sum of `CreditAllowance.remaining_amount`.
- §18 lists "one wallet per account" twice (#2 and #17).

*[REC] Pick one authoritative field for each and derive or display the others. For credits, make allowance rows authoritative for the subscription bucket and the wallet authoritative for the purchased bucket, with both locked during deductions.*

**C6. Gaps in the permission matrix (doc 14):**
- **The Communication Manager template includes `view_conversations` and `send_messages`, which the same document classifies as Sensitive.** That contradicts §4's rule that sensitive permissions are never granted by template.
- Missing permission codes:
  - `view_requests`: the Standard template says "view interests and requests", but only `view_interests` exists.
  - Photo-access request approval: BR §13.5 requires explicit permission, but there's no code for it.
  - Favorites and private notes.
  - Editing location, lifestyle and languages.
- **There's no permission for billable profile views.** `search_profiles` would let a manager spend the owner's profile-view credits.
- `manage_verification_submission` is delegable, but verification uses the owner's live pictures.

**C7. State-machine gaps (doc 15):**
- **Profile:** no PENDING_REVIEW→DRAFT (rejection), no SUSPENDED→ACTIVE (lifted or appealed), no behaviour defined for deletion recovery. It's also unclear whether PENDING_REVIEW means profile moderation or identity review.
- **Identity:** CANCELLED transitions are undefined. Is verification of the account (`user`) or the profile (nullable `profile`)?
- **Authorization:** missing PENDING→REVOKED (owner withdraws an invite), PAUSED→EXPIRED, and invitation expiry.
- **Request:** doc 15 says "only recipient can accept", while docs 03 and 05 say "or authorized manager". These are consistent if read as acting through the profile, but should be worded the same way.
- **Request vs. connection:** after a connection is CLOSED, can the pair send a new formal request, or is reopening the only path? This is undefined.

**C8. The roadmap order conflicts with its own dependencies (doc 10):**
- Profile-view billing (Phase 7) and atomic request credits (Phase 8) depend on the credit ledger (Phase 11).
- The outbox (Phase 12) is needed from Phase 5, because manager and owner notifications are required.
- The central audit (Phase 15) is needed from Phase 2 (security events).
- Moderation restrictions (Phase 13) feed every eligibility check from Phase 6.
- Feature flags appear in both Phase 1 and Phase 15.

**C9. Two versions of the instructions.** The root `CLAUDE.md` is a superset of doc 12: it adds the §19 status list and the §20 approval rules. But it ends §20 mid-sentence ("Wait for approval if the decision materially") and duplicates its closing paragraphs. Separately, the status vocabularies differ: doc 00 and `CLAUDE.md` use `PLANNED/APPROVED`, while doc 13 uses `REVIEWED/POST_MVP`. *[REC] Make the root `CLAUDE.md` authoritative, fix the truncation, and either sync doc 12 or mark it as superseded.*

**C10. Recommendations being treated as rules.** ADR-014 (outbox) is "Recommended", yet `CLAUDE.md` lists "Notifications use a transactional outbox" as a critical rule. ADR-022 (audit) and ADR-023 (platform operations) are also not formally approved. Per doc 00 §3 this needs formal approval rather than silent promotion.

**C11. Missing acceptance and specification details:**
- The FR-012 locked-field list is "must identify exactly" but not given.
- FR-001 underage handling is undefined.
- FR-ACC-009's "limited browsing" field set is undefined.
- The matching ranking rules are required by ADR-011 but not documented.
- There's no per-criterion "strict" flag in `PartnerPreference`, even though FR-021 distinguishes strict criteria from optional ones.
- Photo-visibility enum values, `PhotoAccessRequest`/`ModerationReport`/`CreditPurchase` status enums, and the shape of `SensitiveActionVerification` ("additional security verification") are all undefined.

**C12. Every document from 03 to 17 lacks a status line**, but doc 00 §11 requires "each document has a clear status".

---

## D. Business Requirements Understanding

These are all **[APPROVED]** unless marked otherwise.

- **Identity model:** an account owns at most **one** personal profile and may manage others only through **owner-initiated, manager-accepted, profile-scoped** authorization. Statuses are PENDING, ACTIVE, PAUSED, EXPIRED, REVOKED and REJECTED. Expiry is optional and defaults to none. Paused, revoked or expired authorizations lose access immediately. Every manager action records the **actual account and the represented profile**. Billing goes to the **owner's account** (ADR-020). Deleting a manager revokes their authorizations and never deletes the profiles they managed. *[ASSUMPTION, per SRS 2.2]* The represented person must hold their own account, because only owners can invite. So a parent cannot create a profile for someone who has no account.
- **Eligibility:** 18 or older, calculated from DOB, and the DOB is never exposed. Phone OTP verification and identity verification are separate. OTP defaults: 5 minutes validity, 60-second resend cooldown, 5 attempts, 5 sends per hour, hashed storage. Identity approval makes the profile Visible in Match Search by default, but it never overrides suspension, deactivation, restrictions or privacy settings. Education and profession stay editable after verification. Duplicate documents are detected with a keyed HMAC fingerprint.
- **Discovery:** deterministic rule-based matching. Optional preferences never disqualify. A null boolean means "no preference". Search is worldwide and nationality is not a global filter. Results exclude blocked, hidden, suspended, non-visible and ineligible profiles. Search impressions are free. A detail view is billed at most once per account-target pair per 24 hours.
- **Funnel:**
  - **Interest:** lightweight. A decline triggers a 30-day directional cooldown.
  - **Formal request:** costs a credit, atomically with request creation and its history. Duplicates are blocked in either direction. Pending requests expire after three calendar months. Decline or expiry triggers a 30-day directional cooldown. Withdrawal and admin cancellation trigger no cooldown. Expiry gives no refund.
  - **Acceptance:** creates exactly one connection for the unordered pair, plus its conversation, in the same transaction.
- **Connections:** ACTIVE, PAUSED, COMPLETED or CLOSED. A CLOSED connection reopens only by mutual confirmation. A COMPLETED one doesn't reopen by default. Relationship progress has 8 stages with append-only history and shared notes.
- **Messaging:** one conversation per connection with exactly two profile participants. Messages are text only and allowed only while the connection is active and unblocked. Read receipts are on. Attachments are private. Shared documents need a separate, expiring or revocable permission. Manager document sharing needs explicit permission, extra verification and owner notification, with owner approval recommended.
- **Privacy:**
  - A **block** is unilateral and silent. It stops discovery, requests and communication and disables media access.
  - **Hide My Profile From** stops discovery and new interests and requests only. Existing connections and permissions survive.
  - Photo access can be granted for 7 days, 30 days or until manually revoked.
  - Visitor history is a premium feature with 90-day retention. Private browsing keeps the visitor anonymous.
- **Money:**
  - Separate request and profile-view credit types, each split into subscription and purchased buckets.
  - Allowances expire at the end of the billing period. Purchased credits never expire.
  - Allowances are consumed first. Balances can never go negative. The ledger is append-only, with row locking and idempotency keys.
  - Failed renewal gets a 3-day grace period. Cancellation stops renewal. Refunds use compensating transactions.
  - JazzCash callbacks must be verified (reference, amount, currency, status) and processed exactly once. A frontend "success" is never trusted.
  - **No prices or quantities are defined. They are admin-configurable** (OD-001 and OD-002).
- **Platform:** notifications go through a transactional outbox to in-app, email, SMS and push. SMS and push content stays generic. Security notices can't be disabled. Templates come in English and Urdu.
- **Moderation:** reports, evidence, cases, restrictions and appeals. A report never auto-suspends. Reporters stay confidential. Moderators can't review cases where they have a conflict of interest. Permanent actions need elevated approval.
- **Data rights:** exports are ZIP+JSON, require identity confirmation, are available for 7 days with links valid for 24 hours, and exclude ID documents and moderation evidence. Deletion requires identity confirmation, has a 30-day recovery period, runs asynchronously in idempotent steps, and respects retention and legal holds.

---

## E. Architecture Understanding

**[APPROVED]** (ADR-001 to 013, 015 to 021, 024): a Django + DRF modular monolith with one PostgreSQL database. Celery + Redis handle background work. The API is `/api/v1/` with drf-spectacular. The web client is React + Vite + TypeScript (strict). Mobile is React Native + Expo. It's a monorepo. Local development is native, with Docker optional. Production runs on AWS EC2 with Docker Compose behind Nginx, and CI/CD uses GitHub Actions. Payments go through JazzCash behind a `PaymentProvider` interface. There are provider abstractions for storage, email, SMS/OTP, push, Redis and Celery, with mock implementations locally. English and Urdu are supported, with RTL.

**Internal pattern:**
- Domain apps live under `backend/apps/` (doc 02 lists 16 of them), with shared code in `common/`.
- Services handle writes and transactions. Selectors handle reads.
- Views stay thin. Signals are not used for business workflows.
- Cross-module writes go only through the owning module's public service.
- Every profile-scoped operation resolves: account, represented profile, ownership or active authorization, permission, eligibility, block/hide status, and any extra verification.

**Not yet decided:**
- The authentication mechanism: session, JWT, or both.
- Real-time messaging delivery: polling + push, or WebSockets. Channels would be a new technology.
- The malware scanner.
- The push provider: Expo Push or FCM/APNs directly.
- The SMS provider.
- The admin MFA library.
- The CORS and cookie domain topology.

---

## F. Repository Assessment

### Structure, compared with the doc 07 target

| Path | State |
|---|---|
| Git | **Not initialised** (`fatal: not a git repository`). Roadmap Phase 0 task is undone. |
| `.gitignore` | **[EXISTING]** Covers Python only. Missing `node_modules/`, Expo/Metro, `dist/`, `.env.*` (with `!.env.example`). |
| `.venv/` (repo root) | Contains pip only. Created at another path, so its scripts are stale. `README` says to use `backend/.venv` instead. |
| `backend/` | **[EXISTING]** `config/` and `accounts/`. **No `apps/`, `common/` or `tests/`.** `accounts` sits at the top level rather than under `apps/accounts` as docs 02 and 07 specify. |
| `frontend/`, `mobile/`, `infrastructure/`, `scripts/`, `.github/workflows/` | `.gitkeep` only |
| `README.md` | Backend-only setup. Titled "Matrimonial Platform" with `matrimonial_*` database names, while the project name is "Matermonial". |

### Backend detail
- **Dependencies:**
  - `base.txt`: Django 5.2, DRF 3.16, django-environ, psycopg 3, drf-spectacular 0.28.
  - `local.txt`: django-extensions, pytest, pytest-django, ruff.
  - `production.txt`: gunicorn, whitenoise.
  - Absent: Celery, redis, django-cors-headers, a factory library, any lock file or hashes, and any S3 library.
- **Settings:** `base`, `local`, `test` and `production` exist. **`staging.py` is missing.**
  - `production.py` fails fast if the secret key is the default or `ALLOWED_HOSTS` is empty, and turns on HSTS, SSL redirect and secure cookies.
  - `TIME_ZONE=Asia/Karachi` with `USE_TZ=True`, so timestamps are stored in UTC.
- **`User` model:** UUID primary key and `AbstractBaseUser + PermissionsMixin`.
  - Phone number is unique, with E.164 validation on every `save()`. Email is nullable and unique.
  - Has `is_phone_verified`, `is_email_verified`, `deactivated`/`deactivated_reason`, and `created_by`/`updated_by` self-FKs with `SET_NULL`. Setting `deactivated` forces `is_active=False`.
  - **It largely matches doc 03 §2.1.** The only naming difference is `is_phone_verified` vs. the doc's `phone_verified`, and the code follows the doc 07 boolean-prefix convention, which is better.
- **Admin:** a custom `UserAdmin` with creation and change forms.
- **API:** `GET /api/v1/health/` (unauthenticated liveness check, no database check), `/api/schema/`, `/api/docs/` and `/admin/`.
- **Migrations:** `accounts/migrations/` contains only `__init__.py`, so the model has never been migrated. `README` tells developers to run `makemigrations` themselves, so migrations aren't committed.
- **Tests:** 3 model tests (phone normalisation and password hashing, unusable password, invalid phone). **I didn't run them**, because Django isn't installed and installing was out of scope.
- **Not present:**
  - Authentication endpoints, OTP, login history and security events.
  - Everything in Modules 02–16.
  - Celery, storage abstraction, provider interfaces, feature flags.
  - A standard error handler, logging configuration, request IDs, CORS.
  - Docker, Nginx and CI.

### Issues found in existing code (all fixable now, before the first migration)
1. `config/settings/test.py` uses **SQLite in-memory**. Doc 08 §7 and `CLAUDE.md` §14 require PostgreSQL for locking and constraint tests, and the partial and functional unique indexes needed in Modules 07 and 08 are PostgreSQL-specific.
2. **Throttling is inert.** `DEFAULT_THROTTLE_RATES` is set but `DEFAULT_THROTTLE_CLASSES` isn't. Production throttles will also need a shared cache (Redis); per-process memory is ineffective across workers.
3. **The OpenAPI schema and Swagger UI are public in every environment** (drf-spectacular's default `SERVE_PERMISSIONS` is AllowAny).
4. There's no standard error envelope. Doc 02 §8 specifies `{success, error:{code,message,details}}`, and the code uses DRF defaults.
5. `PageNumberPagination` has no maximum page size or client page-size limit.
6. `wsgi.py`, `asgi.py` and `manage.py` all default to `config.settings.local`. A production container that forgets the environment variable would boot with local settings (`DEBUG=True`). *[REC] Require the variable explicitly in production entry points.*
7. `CSRF_COOKIE_HTTPONLY=True` stops a React SPA from reading the CSRF token if cookie sessions are chosen. Fixing this depends on the auth decision.
8. Email uniqueness is case-sensitive (`A@x.com` and `a@x.com` both allowed). *[REC] Add a unique index on `Lower(email)`.*
9. The phone number is unique across **all** accounts, while FR-002 says "multiple *active* accounts". Phone reuse after deletion or anonymisation needs a rule.
10. Normalisation only strips whitespace and validates. Local formats like `03001234567` are rejected rather than normalised. That's acceptable, but it's a UX decision.
11. `whitenoise` is a production dependency but isn't in `MIDDLEWARE`. There's also no CORS or logging configuration, and `.env.example` lacks Redis, storage and provider variables.
12. The semantics of `deactivated` vs. `is_active` aren't defined against moderation restrictions and deletion recovery. FR-006 requires an explicit capability matrix.

---

## G. Database Readiness

**Ready to implement once small gaps are closed:** Modules 01, 02, 03, 05, 09, 10 and 12. The core of 11 and 14 is also close.

**Missing or unresolved:**
- **Interest model (Module 07).** This blocks Phase 8 (C4).
- **Authoritative fields** for visibility, verification status and the subscription credit bucket (C5).
- **The `on_delete` rule for every FK.** Doc 03 §19 gives principles only. Financial, audit and moderation FKs to `User` and `Profile` must be `PROTECT` or `SET_NULL` with anonymisation, never `CASCADE`.
- **Field types, lengths and enum values** are largely unspecified: photo visibility, `PhotoAccessRequest.status`, report and appeal statuses, `CreditPurchase.status`, `profile_code` format, and the reference-data approach for religion, community and caste (free text vs. lookup tables).
- **Missing columns:**
  - `ProfilePhoto` has no `uploaded_by` (manager attribution), MIME type, size or checksum.
  - `PartnerPreference` has no per-criterion "strict" flag.
  - `IdentityDocumentFingerprint` has no HMAC key-version field, so rotating the key would break duplicate detection.
  - Authorizations have no invitation token or expiry.
- **Constraints that need PostgreSQL-specific features:**
  - Duplicate active requests in either direction need a partial unique index on `(LEAST(a,b), GREATEST(a,b)) WHERE status='PENDING'`.
  - The unordered connection pair needs a normalised-pair check plus a unique constraint.
  - "No duplicate pending/active authorization" needs a partial unique index.
  - "No overlapping active billing periods" needs an exclusion constraint or service-level locking.
  - "Exactly two participants" can't be a database constraint. It has to be enforced in the service and tested.
- **The meaning of "active request":** whether ACCEPTED counts once a connection exists, and the rule after a CLOSED connection (C7).
- **Calendar-month expiry:** which timezone defines the month, and month-end clamping (e.g. 30 Nov + 3 months = 28 Feb). *[REC] Use `relativedelta` in UTC and document it.*
- **Modules 15 and 16 are explicitly "recommended".** Before building custom `AdminRole`/`AdminPermission`, decide whether to reuse Django's Groups and Permissions instead, to avoid two RBAC systems.

I generated no migrations.

---

## H. API and Integration Readiness

**Specified (endpoint inventory, method and path only):** auth, profiles, preferences, verification, family management, search, favorites, interests, requests, connections, messaging, documents, privacy, subscriptions, credits, payments, notifications, user-facing moderation, exports and deletion.

**Unspecified:**
- Request and response schemas.
- The error-code catalogue.
- Filtering and sorting parameters for search.
- **The represented-profile mechanism.** How does a manager tell the API which profile they're acting for? Examples: an `X-Acting-Profile` header, a path prefix, or a body field validated server-side. This must be one consistent, documented mechanism.
- Idempotency-key transport (an `Idempotency-Key` header is recommended).
- All admin, moderation, verification-review and finance endpoints. Doc 04 only says "separate namespace".
- Photo and document **delivery** endpoints: signed URL vs. authorised proxy.
- Endpoints for photo-access permission revocation, the connection-reopen confirmation, and the identity-confirmation step for export and deletion.

**Integrations:**

| Provider | State |
|---|---|
| JazzCash | Interface defined. **The contract, signature, fields, status mapping and refunds are all unknown (OD-003).** Build against a mock, keep it disabled, and don't invent fields. |
| SMS/OTP | Interface defined. No provider chosen. Mock only. |
| Email | Interface defined. Console backend locally. |
| Push | Interface defined. Expo Push vs. FCM/APNs is undecided. |
| Storage | Interface defined. Local private filesystem locally. A private S3 bucket is recommended for production. Region, bucket and KMS are undecided. |
| Malware scanning | "Where supported". No tool chosen. |
| Image processing | **Not mentioned anywhere.** Thumbnails and **EXIF/GPS stripping** are needed (see I). |

---

## I. Security Assessment

**Strong points in the specification:** backend-only authorization, an explicit represented-profile check on every action, field allowlists, private storage, hashed OTPs, HMAC fingerprints, non-disclosure of block and hide, an append-only ledger, idempotent callbacks, log redaction, and a security release gate. These are sound and I'd keep all of them.

**Design gaps to close:**
1. **The authentication design is undecided**, and the token lifetimes and rotation that the SRS says are in doc 06 aren't there. This gates Phase 2.
2. **Account enumeration via manager invitation.** Inviting "a registered account" by phone number can reveal whether that number is registered. The invitation response must be identical either way.
3. **Photo EXIF/GPS metadata** isn't addressed. Uploaded photos can leak a home location. Strip metadata server-side and re-encode the image.
4. **Signed-URL revocation window.** Doc 06 acknowledges it. *[REC]* Use an authorised proxy, or very short TTLs (≤ 60 seconds), for identity documents and shared documents.
5. **HMAC key management:** where the key is stored, how it rotates, and a version column.
6. **Encryption at rest** for identity documents isn't specified. *[REC]* S3 SSE-KMS with separate prefixes and IAM per storage group.
7. **"Additional security verification"** for sensitive manager actions is undefined. *[REC]* OTP to the owner's phone plus immediate owner notification, with owner approval for document sharing.
8. **Credit spending by managers.** There's no permission gating billable profile views, so a manager with `search_profiles` could drain the owner's view credits (C6).
9. **Rate limiting** depends on Redis in production. Redis is "optional" locally but **mandatory** for OTP, login and throttle counters in production.
10. **Admin MFA** is required (doc 06 §15) but no package has been chosen. Also, the admin is served at the default `/admin/` path.
11. **Realtime messaging.** If WebSockets are added later, every socket message needs the same participant, connection and block checks. That's a new technology and needs approval.
12. **Deletion and phone reuse.** Whether to retain a keyed hash of the phone number to enforce bans on re-registration is a legal and privacy decision (OD-005).

**Existing code:** no secrets are committed and passwords use Django hashers, which is good. The concrete issues are listed in F (inert throttles, public schema, local-settings default in WSGI, SQLite test database, case-sensitive email).

---

## J. Implementation Readiness

| Classification | Items |
|---|---|
| **Ready for implementation** | Phase 0 (Git, CI skeleton, tracking docs). Phase 1 foundation (settings, error envelope, logging, storage abstraction, feature-flag settings, Celery wiring, PostgreSQL tests). Profiles and preferences schema (Module 02/03) once C5 is settled. Family-management models and permission engine (after fixing C6). Privacy models (block, hide). Notification outbox and delivery models. Audit log. Provider interfaces with mocks. |
| **Requires specification completion** | Interest model and workflow (C4). Matching ranking and strict-criteria rules. Full API schemas and the represented-profile mechanism. Photo-visibility levels. Admin, moderation and finance API. Missing state transitions (C7). Delete behaviour per FK. Locked identity fields. Moderation conflict-of-interest definition. |
| **Requires owner decision** | Authentication mechanism. Participation gating (what needs phone vs. identity verification, and what anonymous users see). Manager profile-view billing semantics and behaviour at zero credits. Subscription auto-renewal vs. manual renewal. Request credit refund on decline or withdrawal. Underage handling. Admin console approach and MFA. Formal approval of ADR-014, 022 and 023 and the roadmap reorder. Gender compatibility as a hard rule vs. a preference. |
| **Blocked by external dependency** | Live JazzCash (OD-003). SMS, email and push providers. Identity document policy (OD-004). Legal and retention policy (OD-005). AWS infrastructure (OD-006). Commercial plans and packages (OD-001/002). None of these block development against mocks. |

---

## K. Recommended Development Roadmap

**[REC]** This keeps doc 10's phases but reorders them so each phase's dependencies already exist. It needs your approval under doc 00 §8 and `CLAUDE.md` §20.

| # | Phase | Key dependency fixed | Mandatory tests |
|---|---|---|---|
| 0 | Repository foundation | — | CI runs green |
| 1 | Backend foundation and **platform kernel**: settings, errors, logging, storage, flags, Celery, **AuditLog + Outbox models and services** (pulled forward from 12 and 15) | Audit and outbox available to all later phases | Error envelope, redaction, storage privacy, migration check |
| 2 | Accounts and authentication: OTP, login, sessions, security events, deactivation | Auth decision (Q1) | OTP expiry, limits and races. Enumeration. Deactivated sessions. |
| 3 | Profiles and preferences | — | One profile per account. DOB privacy. Decimal income. Null-boolean semantics. |
| 4 | Verification | Private storage | State transitions. Document access. HMAC duplicates. |
| 5 | Family management and the **actor-context resolver** (account + represented profile + permission) | Used by every later phase | Revoked, paused or expired authorization. Escalation. IDOR. |
| 6 | Privacy, plus a **shared eligibility service** with a hook for moderation restrictions | — | Block vs. hide. Non-disclosure. |
| 7 | **Credit ledger core**: wallet, allowance, transaction, deduction service (pulled forward from 11, no payments yet) | Needed by 8 and 9 | Concurrent deductions on PostgreSQL. Never negative. Idempotency. Rollback. |
| 8 | Matching, search and profile-view billing | Ledger | Exclusions. Free impressions. The 24-hour rule under concurrency. |
| 9 | Interests and requests | Interest specification (Q2), ledger | Atomic credit. Duplicates in both directions. Cooldowns. Expiry job. |
| 10 | Connections and progress | — | Exactly one connection under concurrent acceptance. |
| 11 | Messaging and documents | — | Participants only. Block. Revoked or expired document access. |
| 12 | Subscriptions, payments and JazzCash adapter (mock first) | OD-003 for live | Forged or duplicate callbacks. Amount mismatch. Refund compensation. |
| 13 | Notification delivery (channels, templates, retries) | Outbox from Phase 1 | Retry and dedupe. SMS/push content sanitised. |
| 14 | Moderation and full restriction enforcement | Eligibility hook from Phase 6 | Conflict of interest. No auto-suspend. |
| 15 | Export and deletion | — | Scope allowlist. Idempotent steps. Holds. Manager deletion. |
| 16 | Admin RBAC, configuration, support, maintenance | ADR-023 | Least privilege. Internal notes private. |
| 17–19 | Web, mobile, release preparation | Stable API contracts | E2E, RTL, security gate |

Frontend scaffolding (Vite, TypeScript strict, ESLint, Vitest) can start in parallel after Phase 2, against the auth contract.

---

## L. Initial Backend Foundation Plan (not executed)

**Phase 0: repository**
1. `git init` on `main`, then a baseline commit of the current tree *(needs approval)*.
2. Expand `.gitignore` for Node, Expo, `dist/` and `.env.*` (keeping `!.env.example`).
3. Rebuild the virtual environment in one documented location (`backend/.venv`, matching `README`) and remove the stale root `.venv` *(deletion, so needs approval)*.
4. Add a GitHub Actions backend workflow: `ruff check`, `ruff format --check`, `pytest` against a PostgreSQL 16 service container, `makemigrations --check --dry-run`, and `spectacular --validate`.
5. Fill in `docs/implementation/*`, start ADR-025+ in `docs/decisions/`, and add a traceability-matrix file.
6. Documentation fixes, as recommendations for you to approve: correct the doc paths in `CLAUDE.md` and doc 07, fix the truncated `CLAUDE.md` §20, and mark doc 12 as superseded.

**Phase 1: backend foundation (one reviewable change per step)**
1. **Layout:** move `accounts` to `apps/accounts`, keeping app label `accounts` so `AUTH_USER_MODEL` stays the same, and add `common/`. This is free now because no migrations exist.
2. **Finalise `User` and commit migration `0001`:** add a case-insensitive email constraint, apply the auth decision (Q1), and settle the phone-reuse semantics. After this, the model can only change through migrations.
3. **Test infrastructure:** move the test settings to PostgreSQL, add a factory library (new dev dependency, e.g. factory-boy), and add a `transactional`/concurrency marker.
4. **Settings:**
   - Add `staging.py` and startup configuration validation (fail clearly; never fall back to public storage).
   - Production entry points require `DJANGO_SETTINGS_MODULE` explicitly.
   - CORS and CSRF trusted origins (django-cors-headers, a new dependency).
   - Restrict OpenAPI outside local; activate throttle classes; configure the Redis cache, optional locally.
5. **`common/` API layer:** an exception handler emitting the doc 02 §8 envelope, pagination with a maximum page size, request-ID middleware, structured JSON logging with a redaction filter, and liveness plus readiness (database) health checks.
6. **Providers:** a `StorageProvider` interface with a local private filesystem implementation and a disabled S3 implementation. Add Email/SMS/Push/Payment interfaces with mock implementations and environment-based feature flags (`USE_S3_STORAGE`, etc.). The database-backed `FeatureFlag` model waits for Phase 16.
7. **Celery:** app wiring, eager mode in tests, a bounded-retry base task, and optional local use.
8. **Platform kernel (pulled forward):** a `common/audit` append-only `AuditLog` with an audit service, plus a `NotificationOutbox` model with a dispatcher skeleton.
9. **Documentation:** a root README (monorepo) and `backend/README`, and update the progress, tracking and traceability documents.

**Each step's tests:** settings validation, error envelope shape, redaction (no password, OTP or token in logs), local storage never served publicly, outbox written in the same transaction as the business change, AuditLog immutable through the ORM service, and the migration check.

---

## M. Questions Requiring Owner Approval

**Blocking Phase 0 and Phase 1:**
1. **Structural approvals.** May I: (a) `git init` and commit the baseline; (b) move `accounts` to `apps/accounts` before the first migration; (c) delete the stale root `.venv` and recreate it in `backend/`; (d) switch the test database to PostgreSQL; (e) add the new dependencies django-cors-headers, celery[redis] and factory-boy?
2. **Authentication.** *[REC]* httpOnly-cookie sessions with CSRF for the web, and short-lived access tokens plus rotating, revocable refresh tokens for mobile (e.g. djangorestframework-simplejwt with a blacklist), with sessions tracked in `LoginHistory`. Or do you prefer one mechanism for both clients?
3. **Governance.** Formally approve ADR-014 (outbox), ADR-022 (audit) and ADR-023 (platform operations), and the roadmap reorder in K (audit and outbox in Phase 1, ledger before matching and requests)?

**Needed before their phases** (I'll build safe, configurable defaults until then):

4. **Interest workflow (Phase 9).** Are interests free (rate-limited only)? Does "Show Interest Back" only signal mutual interest, with a formal request still needed to connect? When a recipient converts an interest into a formal request, are they the paying sender?
5. **Participation gating (Phases 2, 3 and 8).** Which actions need phone verification only, and which need approved identity verification? For example: search, profile detail view, sending interests or requests. Can logged-out visitors see anything? (FR-ACC-009 "limited browsing" is undefined.)
6. **Profile-view billing (Phase 8).** When a manager views the same target on behalf of two different owners within 24 hours, is each owner charged once, or does the manager's account deduplicate? And when an account has zero view credits, what does a detail view show?
7. **Subscriptions (Phase 12).** The SRS excludes "unapproved automatic renewal" yet specifies failed-renewal grace periods. For the MVP, is renewal manual (the user pays each period) or automatic? For plans longer than a month, are allowances issued monthly?
8. **Refunds (Phase 9).** Is a request credit refunded when a request is declined or withdrawn? The docs only say "no refund on expiry".
9. **Identity and eligibility (Phases 3 and 4).** Which fields lock after identity approval? *[REC]* full name, DOB and gender. And how should an under-18 DOB be handled? *[REC]* reject with a generic message and record a security event.
10. **Admin console (Phase 16).** For the MVP, is the admin and moderation interface a customised Django admin with MFA (e.g. django-otp) and RBAC built on Django Groups? Or a separate React admin?

---

**What I verified and didn't verify:** I read every listed file in full. I didn't run any command that changes state, and I executed no tests: Django isn't installed in the existing `.venv`, and installing was out of scope. Every conclusion about runtime behaviour comes from reading the code, not from running it.

I can also publish this report as a private web page if you want to share it with your team.