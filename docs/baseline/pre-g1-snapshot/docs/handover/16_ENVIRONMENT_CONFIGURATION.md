# Matermonial — Configuration and Environment Specification

**Version:** 1.0  
**Date:** 11 November 2026

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