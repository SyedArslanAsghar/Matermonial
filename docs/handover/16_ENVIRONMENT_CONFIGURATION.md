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
