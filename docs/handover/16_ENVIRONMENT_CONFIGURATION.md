# Matermonial — Configuration and Environment Specification

**Version:** 1.0 (G1 revision 2026-11-16)  
**Date:** 11 November 2026  
**Document status:** APPROVED_WITH_OPEN_ITEMS (project owner, 2026-11-17, DR-2026-11-17-A; record in doc 20 §5). **Open items:** OPEN legacy ODs (doc 13 series): OD-005; PROPOSED TRs: TR-11, TR-23, TR-24. Listed items keep their own status (doc 19); this document status doesn't approve them.  
**Applied corrections:** DCR-10, and DCR-74, DCR-75, DCR-84, DCR-86 within the scope of DR-2026-11-16-P2 (doc 20). New configuration: **§10**.

## 1. Objective

Provide one consistent configuration approach for local, test, staging, and production environments.

## 2. Django settings structure

```text
backend/config/settings/
├── base.py
├── local.py
├── test.py
├── staging.py
└── production.py
```

## 3. Configuration categories

### Application

- Environment name.
- Django secret key.
- Debug mode.
- Allowed hosts.
- Trusted origins.
- Logging level.

### Database

- PostgreSQL host.
- Port.
- Database name.
- Username.
- Password.
- Connection options.

### Redis and Celery

- Redis URL.
- Celery broker URL.
- Result backend configuration.
- Task retry policy.
- Task timeouts.
- Queue configuration.

### Storage

- Storage backend.
- Local media path.
- AWS region.
- S3 bucket.
- Object prefix.
- Temporary URL expiry.
- Private storage policy.

### Email

- Provider.
- Sender address.
- API credentials.
- Timeout.
- Retry settings.

### SMS and OTP

- Provider.
- API credentials.
- Sender ID.
- OTP validity.
- Resend cooldown.
- Maximum attempts.
- Rate limits.

### Payment

- Provider.
- JazzCash merchant ID.
- Merchant password.
- Integrity/signature secret as specified by the gateway.
- Sandbox/production mode.
- Callback URL.
- Timeout.
- Reconciliation settings.

### Push

- Provider configuration.
- Platform credentials.
- Token lifecycle settings.

### Localization

- Default language.
- Supported languages.
- Fallback language.
- Timezone policy.

## 4. Environment behavior

| Setting | Local | Test | Staging | Production |
|---|---|---|---|---|
| Debug | Enabled | Disabled or controlled | Disabled | Disabled |
| Database | Local PostgreSQL | Isolated test PostgreSQL | Staging DB | Production DB |
| Media | Local private filesystem | Temporary test storage | Private storage | Private object storage recommended |
| Email | Console/mock | Mock | Sandbox/test provider | Real provider |
| SMS | Mock | Mock | Sandbox | Real provider |
| Payment | Mock | Mock | Sandbox | Live JazzCash |
| Redis | Optional local | Test service | Protected service | Protected service |
| Celery | Optional | Test worker/eager mode as suitable | Worker | Worker |
| Secrets | Local environment | CI secrets | Secure deployment secrets | Secure deployment secrets |

## 5. Feature flags

Centralized flags should cover:

- Object storage.
- External email.
- External SMS.
- JazzCash.
- Push notifications.
- Redis.
- Celery/background jobs.

Flags must be environment-aware.

A feature flag must never bypass authentication, privacy, payment verification, or authorization.

## 6. Safe local defaults

- Debug email backend or mock.
- Mock SMS/OTP.
- Mock payment provider.
- Local private media.
- Optional Redis/Celery.
- Test accounts only.
- No real user identity documents.
- No production secrets.

## 7. Configuration validation

At startup, validate required configuration.

If production payment is enabled but credentials are missing, fail clearly.

If private storage is enabled but bucket configuration is incomplete, fail clearly.

Never silently fall back from private production storage to public storage.

## 8. Secret management

- Never commit real credentials.
- Provide `.env.example`.
- Keep production secrets outside Git.
- Restrict secret access.
- Rotate credentials when compromised.
- Redact secrets from logs and error reports.
- Do not expose configuration secrets through admin APIs.

## 9. Configuration acceptance

- Local startup works without production credentials.
- Test environment uses mock providers.
- Production requires explicit credentials.
- Feature flags are centrally documented.
- Sensitive configuration is protected.
- Startup validation identifies missing required settings.

## 10. Compliance registry, key and outbox configuration (G1)

**Scope:** limited to the configuration required by DCR-74, DCR-75, DCR-84 and DCR-86 (DR-2026-11-16-P2). **Status:** [TR] PROPOSED (TR-11, TR-23, TR-24). The item names below are proposed and may be adjusted at G3 without changing their purpose.

**This section lists names and purposes only. It never contains secret values.** Real values are supplied at deploy time from the deployment secret store or environment and are never committed to Git. The owner-managed root `.env` is not part of this specification.

### 10.1 Configuration items

| Item (proposed name) | Purpose | Security requirement | Source |
|---|---|---|---|
| `COMPLIANCE_REGISTRY_BACKEND` | Registry implementation: write-once object storage (recommended) or a separate PostgreSQL instance | Non-secret. Production and staging must not use a local or mock backend. | DCR-74 |
| `COMPLIANCE_REGISTRY_LOCATION` | Reference to the registry bucket or database | Non-secret reference; access is granted by role, not by embedded credentials | DCR-74 |
| `COMPLIANCE_REGISTRY_SIGNING_KEYS` / `COMPLIANCE_REGISTRY_SIGNING_KEY_ACTIVE_VERSION` | Versioned HMAC keys that sign registry entries, and the active version | **Secret.** Secret store only. Never logged. | DCR-74 |
| Application registry role | Credentials allowing the application to **add** registry objects only | **Secret.** No delete, overwrite or read rights. | DCR-74 |
| Restore registry role | Credentials allowing the restore process to **read** the registry | **Secret.** Not available to the running application. | DCR-74 |
| `REGISTRY_STREAM_R_RETENTION` | Object-lock retention for stream R | Longest backup retention + 30 days | DCR-86 |
| `REGISTRY_STREAM_M_RETENTION` | Object-lock retention for stream M | Placeholder 7 years, subject to legal review (doc 13 OD-005) | DCR-86 |
| `REGISTRY_CHECKPOINT_INTERVAL` | How often a signed stream R checkpoint is written to stream M | Daily | DCR-86 |
| `KEK_KEY_REFS` / `KEK_ACTIVE_VERSION` | Secret-store references to each KEK version that wraps subject data keys, and the active version | **Secret references.** Key material never leaves the secret store. Rotated monthly; a version is destroyed only after the longest backup and WAL retention that could hold keys it wrapped has passed. | DCR-75 |
| `QUEUE_KEY_REFS` / `QUEUE_KEY_ACTIVE_VERSION` | Versioned keys that encrypt outbox payloads, and the active version | **Secret.** Wrapped by the KEK. Rotated monthly. Destroyed only when the destruction preconditions hold (doc 09 §19.9). | DCR-84 |
| `OUTBOX_DEDUPE_KEY` | HMAC key for outbox `dedupe_key` values | **Secret.** Secret store only. | DCR-84 |
| `OUTBOX_REDACT_AFTER_DAYS` / `OUTBOX_PURGE_AFTER_DAYS` | Outbox redaction and purge timing | Defaults 7 and 30 days; financial events follow the stricter rules in doc 03 §22.12 | DCR-84 |
| `OUTBOX_LEASE_SECONDS` | Lease length for claimed outbox events | Non-secret | DCR-84 (with DCR-73) |

### 10.2 Handling rules

- **Fail closed:** in staging and production, startup validation refuses to start if any registry, KEK, queue-key or dedupe-key item above is missing, or if a local/mock registry backend is configured.
- **Restore startup gate:** in staging and production the application refuses to start until restore reconciliation has recorded `restore_reconciled_seq` at least equal to both registry heads (doc 09 §19.11). This can't be disabled by a feature flag (§5).
- **Local and test environments:** use a local or mock registry and locally generated development keys. Development keys are never reused in any other environment, and real user data is never used locally (§6).
- **`.env.example`** lists the item names with empty placeholders only.
- **Logging:** values of every secret item are redacted from logs and error reports (§8).

## 11. Configuration implemented in G3 (2026-11-17)

Implementation record (`CLAUDE.md` CC-R63). The names are in `backend/.env.example` with safe placeholders only, and the code is in `backend/config/settings/`. This section adds no requirement; §1–§10 still govern.

| Variable | Purpose | Default (local) | Deployed environments |
|---|---|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.{local,test,staging,production}` | local (`manage.py`) | Set explicitly. WSGI, ASGI and Celery default to production. |
| `DJANGO_ENVIRONMENT` | Environment name | `local` | `staging` / `production` |
| `DJANGO_SECRET_KEY` | Django secret | Insecure local default | **Required**, ≥ 50 characters; the default is refused |
| `DJANGO_DEBUG` | Debug mode | on (local) | Always off |
| `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS` | Host and origin allowlists (same origin, TR-12) | localhost | **Hosts required** |
| `DATABASE_URL`, `DATABASE_CONN_MAX_AGE` | PostgreSQL connection | Local default URL | **Explicit URL required** |
| `DB_LOCK_TIMEOUT_MS` | `lock_timeout` set by `@retry_on_contention` (doc 12 §5.3) | 5000 | 5000 |
| `LOCK_TRACKER_ENABLED` | LOCK_PLAN tracker (doc 12 §5.6) | on (local, test) | off |
| `API_PAGE_SIZE`, `API_MAX_PAGE_SIZE` | Pagination defaults (doc 04 §16) | 20 / 100 | 20 / 100 |
| `API_DOCS_ENABLED` | Serve the OpenAPI schema and Swagger UI | on (local) | off unless explicitly enabled |
| `EMAIL_BACKEND` | Django email backend | console | Console, locmem, file and dummy backends are refused |
| `SMS_PROVIDER`, `PUSH_PROVIDER` | `mock` or `disabled` | mock (local, test) | `disabled` until real providers exist; `mock` is refused |
| `STORAGE_BACKEND`, `MEDIA_ROOT` | Private file storage; not served by Django (CC-R46) | `local`, `backend/media` | Only `local` exists. Object storage needs an approved dependency; there is never a fallback to public storage. |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Celery broker and results | Redis on localhost; no results | **`CELERY_BROKER_URL` or `REDIS_URL` must be set explicitly**; no silent fallback to localhost Redis. The startup error names the variables, never their values or credentials. Local development is unchanged (DR-2026-11-17-G3C-1; retained by DR-2026-11-18-G3A-3) |
| `CELERY_TASK_ALWAYS_EAGER`, `CELERY_TASK_TIME_LIMIT`, `CELERY_TASK_SOFT_TIME_LIMIT` | Inline tasks locally; time limits | eager; 300 / 270 s | Not eager |
| `DJANGO_LOG_LEVEL`, `DJANGO_LOG_FORMAT` | Log level; `json` or `text` | INFO, text | INFO, json |
| `KEK_KEYS`, `QUEUE_KEYS`, `DEDUPE_KEYS`, `SUBJECT_HASH_KEYS`, `REGISTRY_KEYS` and each `*_ACTIVE_VERSION` | Versioned 32-byte keys (`"<version>:<base64>,..."`): KEK wraps subject data keys (TR-23); QUEUE encrypts outbox payloads (TR-11); DEDUPE keys the outbox dedupe HMAC; SUBJECT_HASH keys the unknown-phone HMAC (TR-17); REGISTRY signs registry entries (TR-24) | **Dev-only keys** derived from a public label (`common/crypto/keys.py`): not secret, never for real data | **Required**; refused when missing, malformed, lacking the active version, or containing a dev key. Values come from the secret store (production key management is deferred with AWS). Errors name the setting, never the key |
| `COMPLIANCE_REGISTRY_BACKEND`, `COMPLIANCE_REGISTRY_LOCATION` | Compliance registry (TR-24). `local` writes hash-chained, signed, write-once JSON files | `local`, `backend/var/compliance_registry` | `local`/`mock` refused; the external store needs owner approval before production (doc 19 §5) |
| `OUTBOX_LEASE_SECONDS`, `OUTBOX_REDACT_AFTER_DAYS`, `OUTBOX_PURGE_AFTER_DAYS` | Outbox claim lease and retention (TR-11; doc 03 §22.12) | 300 / 7 / 30 | Same defaults |
| `MATERMONIAL_TEST_POSTGRES_URL` | Disposable PostgreSQL database for the PostgreSQL foundation tests (tests only; see §11.1) | unset: those tests skip | Never set. Tests and CI only |

Startup validation (`backend/common/config.py`) applies to staging and production. The compliance-registry, KEK, queue-key and dedupe-key items in §10 belong to TR-11, TR-23 and TR-24 (PROPOSED) and aren't implemented yet.

### 11.1 `MATERMONIAL_TEST_POSTGRES_URL` (test-only)

Added by the G3 correction (DR-2026-11-17-G3C-3). Test code reads it (`backend/tests/test_postgres_foundation.py`, marker `postgres`). Django settings never read it, so it has no effect on any running environment.

- **Purpose:** points the 9 PostgreSQL foundation tests at a real PostgreSQL server: readiness, advisory-lock acquisition and release, `lock_timeout`, and the `@retry_on_contention` behaviour (doc 12 §5.3).
- **Format:** a PostgreSQL URL, `postgresql://<user>:<password>@<host>:<port>/<database>`. Use throwaway values only. Never put real credentials in this variable, in `.env.example` or in documentation.
- **When unset:** the tests skip with a reason, and the rest of the suite runs normally.
- **Expected usage:**
  - **CI:** set in `.github/workflows/ci.yml` to the job's throwaway PostgreSQL service container (PostgreSQL 16 and 18), published on host port 55432.
  - **Locally (optional):** start a throwaway container on a port other than 5432, e.g. `docker run --rm -d -p 127.0.0.1:55432:5432 -e POSTGRES_USER=<user> -e POSTGRES_PASSWORD=<password> -e POSTGRES_DB=<db> postgres:16`. Set the variable for that test run only, then remove the container. Docker here is a test convenience; it is not required for local development (CC-R21).
- **Safety restrictions, enforced by the tests:**
  - Only a PostgreSQL URL is accepted.
  - Port 5432, an empty host and local Unix sockets are refused, so a developer's own PostgreSQL server can't be reached by accident. Point it only at a database you can throw away.
  - The tests use temporary connection aliases. They don't create pytest-django's test database, run no migration, create no table and touch no application data. They only run `SELECT` and advisory-lock functions.
  - Teardown fails the test if a table was created or an advisory lock is left behind, and closes every connection it opened.
- **Not covered:** tests that need application tables, including the 3 User-model database tests, need the first migration and belong to G4 (KI-14).

## 12. Configuration added in G5 Phase 2 (2026-11-19)

Implementation record (CC-R63). The names are in `backend/.env.example`; the code is in `backend/config/settings/base.py`.

| Variable | Purpose | Default (local) | Deployed environments |
|---|---|---|---|
| `OTP_KEYS`, `ROT_KEYS`, `ADMIN_MFA_KEYS` and each `*_ACTIVE_VERSION` | OTP code HMAC (doc 06 §3); K_rot refresh-token derivation (TR-01); admin TOTP seed encryption and enrollment-code HMAC (TR-07, ADR-033) | Dev-only keys | **Required**; dev keys refused (same rules as §11) |
| `OTP_VALIDITY_SECONDS`, `OTP_RESEND_COOLDOWN_SECONDS`, `OTP_MAX_ATTEMPTS`, `OTP_MAX_SENDS_PER_HOUR` | One-time codes | 300 / 60 / 5 / 5 | Same |
| `AUTH_WEB_*`, `AUTH_MOBILE_*`, `AUTH_REFRESH_GRACE_SECONDS`, `AUTH_STEP_UP_WINDOW_SECONDS` | Session and token lifetimes (doc 06 §22.2) | 2 h / 7 d web; 15 min access, 30 d / 90 d mobile; 15 s; 300 s | Same |
| `RATE_*` (`RATE_LOGIN_PHONE_IP` … `RATE_ADMIN_ENROLL_IP`) | Authentication rate limits, `"<count>/<seconds>"` | doc 06 §22.1 §8.4 values; admin login 5/900 per phone+IP and 20/900 per IP; enrollment 5/3600 and 10/3600 | Same; a shared Redis `CACHE_URL` is required |
| `CACHE_URL` | Rate-limit and flood-control counters | in-process | **Redis required** |
| `ADMIN_URL_PATH` | Django Admin URL prefix | `admin/` | Recommended: a non-default path |
| `ADMIN_SESSION_COOKIE_NAME` | Separate admin session cookie | `mat_admin_session` | `__Host-mat_admin_session` (set in production settings) |
| `ADMIN_SESSION_IDLE_SECONDS`, `ADMIN_SESSION_ABSOLUTE_SECONDS` | Admin session limits (doc 06 §22.2) | 1800 / 43200 | Same |
| `ADMIN_MFA_ENROLLMENT_TTL_SECONDS`, `ADMIN_MFA_THROTTLE_FACTOR`, `OTP_TOTP_ISSUER` | Enrollment-code lifetime; TOTP failure back-off (1, 2, 4 … s × factor); issuer shown in authenticator apps | 86400 / 1 / `Matermonial` | Same |

## 13. Configuration added in G5 Phase 3 (2026-11-19)

| Variable | Purpose | Default (local) | Deployed environments |
|---|---|---|---|
| `MALWARE_SCANNER` | Upload scanner (TR-10): `mock` flags only the EICAR test string; `disabled` refuses uploads | `mock` (local, test) | `mock` refused; `disabled` until a real scanner is approved |
| `PHOTO_MAX_UPLOAD_BYTES`, `PHOTO_MAX_PIXELS`, `PHOTO_MAX_EDGE`, `PHOTO_MIN_EDGE`, `PHOTO_MAX_PER_PROFILE` | Photo pipeline limits (AS-24) | 10 MB, 40 MP, 2048, 200, 6 | Same |
| `PROFILE_REQUIRED_FIELDS`, `PROFILE_OPTIONAL_FIELDS` (settings, not environment) | Completion and the review gate (AS-23) | see `config/settings/base.py` | Same |
