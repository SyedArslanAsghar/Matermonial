# Matermonial — System Architecture and Technology Decisions

**Version:** 1.0  
**Date:** 11 November 2026  
**Status:** Architecture Baseline

## 1. Architecture objectives

The architecture must:

- Support web and mobile applications through one backend API.
- Keep business domains independently organized.
- Support future growth without premature microservices.
- Enforce privacy and authorization consistently.
- Support transactional financial and request workflows.
- Support asynchronous notifications, media processing, and scheduled tasks.
- Permit native local development.
- Support containerized AWS EC2 production deployment.

## 2. Selected architecture

**Modular monolith with a shared PostgreSQL database.**

The backend will be one Django deployment composed of independently organized Django applications.

Each application owns its domain models and exposes business operations through explicit services.

The system will not split into microservices for the MVP.

### 2.1 Logical architecture

```text
                 Web Application
                 React + Vite
                       |
                       |
                 Mobile Apps
              React Native + Expo
                       |
                       v
                HTTPS / REST API
                 /api/v1/
                       |
                       v
              Django REST Framework
                       |
        +--------------+--------------+
        |              |              |
        v              v              v
   Accounts         Profiles       Verification
        |              |              |
        +--------------+--------------+
                       |
                 Domain Services
                       |
        +--------------+--------------+
        |              |              |
        v              v              v
     Matching       Requests       Connections
        |              |              |
        +--------------+--------------+
                       |
                 PostgreSQL
                       |
        +--------------+--------------+
        |              |              |
        v              v              v
      Redis          Celery        File Storage
                       |
              Background Processing
                       |
        +--------------+--------------+
        |              |              |
        v              v              v
    Email/SMS       Push          Payment Gateway
```

## 3. Technology decisions

### 3.1 Backend

**Django + Django REST Framework**

Reasons:

- Mature authentication and security ecosystem.
- ORM and migration support.
- Strong administrative capabilities.
- Suitable for domain-oriented modular applications.
- DRF supports serializers, permissions, pagination, throttling, and API versioning.

### 3.2 Web frontend

**React + Vite + TypeScript**

Requirements:

- TypeScript strict mode.
- Reusable components.
- Centralized API client.
- Centralized authentication/session handling.
- Route-level authorization and navigation guards.
- Form validation.
- Responsive layouts.
- English and Urdu localization.
- RTL layout support.

The frontend must not be the final authority for permissions or business rules.

### 3.3 Mobile applications

**React Native + Expo**

Requirements:

- Shared API contracts with the web application.
- Secure token storage using platform-appropriate secure storage.
- Push notification registration.
- Deep-link support where required.
- Consistent permission and privacy behavior.
- Separate environment configuration for development, staging, and production.

### 3.4 Database

**PostgreSQL**

PostgreSQL is the authoritative database for business data.

Requirements:

- UUID identifiers for major domain entities.
- Foreign-key constraints.
- Unique constraints for business invariants.
- Database indexes for common filters.
- Transactions for multi-step operations.
- Row-level locking for credit and payment operations.
- JSON fields only for genuinely flexible metadata/configuration.
- Decimal for financial amounts.
- Integer for whole-unit earning preference bounds where specified.
- UTC timestamps stored consistently.

### 3.5 Background processing

**Celery + Redis**

Celery shall handle:

- Email and SMS delivery.
- Push notifications.
- Scheduled request expiration.
- Subscription and allowance lifecycle tasks.
- Payment reconciliation tasks.
- Media processing and scanning coordination.
- Data export generation.
- Account deletion processing.
- Retention jobs.
- Other non-request-critical asynchronous operations.

Redis shall be used as the configured broker/cache backend where appropriate.

Celery tasks must be idempotent where retries can repeat an operation.

### 3.6 API documentation

**drf-spectacular / OpenAPI**

The backend shall generate OpenAPI documentation.

Every implemented endpoint shall define:

- HTTP method.
- URL.
- Authentication requirement.
- Permission requirement.
- Request schema.
- Response schema.
- Validation errors.
- Pagination behavior.
- Relevant business rules.

### 3.7 Payment gateway

**JazzCash**

The integration shall be implemented behind a payment-provider interface.

The application shall not assume that the frontend payment result is authoritative.

Gateway callbacks must be signature/authenticity verified, persisted, and processed idempotently.

Final production behavior must follow the current merchant integration documentation and approved merchant configuration.

## 4. Backend application boundaries

Recommended Django applications:

```text
backend/
├── config/
├── apps/
│   ├── accounts/
│   ├── profiles/
│   ├── preferences/
│   ├── verification/
│   ├── family_management/
│   ├── matching/
│   ├── requests/
│   ├── connections/
│   ├── messaging/
│   ├── privacy/
│   ├── subscriptions/
│   ├── notifications/
│   ├── moderation/
│   ├── data_management/
│   ├── audit/
│   └── platform_operations/
├── common/
└── manage.py
```

The application names are implementation names. They may differ slightly from the business module labels as long as domain ownership remains clear.

## 5. Internal application structure

A typical Django app should use:

```text
apps/profiles/
├── __init__.py
├── apps.py
├── models/
│   ├── __init__.py
│   ├── profile.py
│   ├── education.py
│   ├── profession.py
│   └── media.py
├── api/
│   ├── serializers/
│   ├── views/
│   ├── urls.py
│   └── permissions.py
├── services/
├── selectors/
├── tasks.py
├── signals.py
├── admin.py
├── constants.py
├── exceptions.py
├── tests/
└── migrations/
```

Use a single `models.py` for small apps. Split models into a package only when complexity justifies it.

### 5.1 Services

Services contain business operations that create or modify data.

Examples:

- `create_matrimonial_request()`
- `accept_matrimonial_request()`
- `deduct_request_credit()`
- `create_connection_from_accepted_request()`
- `authorize_family_manager()`
- `revoke_document_access()`

Services should enforce business rules and transactions.

### 5.2 Selectors

Selectors contain read/query logic.

Examples:

- `get_visible_profiles()`
- `get_pending_requests()`
- `get_active_connections()`
- `get_authorized_managers()`

Selectors should optimize query counts and avoid leaking unauthorized data.

### 5.3 API layer

Views should remain thin.

A view should generally:

1. Authenticate the caller.
2. Validate request data.
3. invoke a service or selector.
4. Return a standardized response.

Do not place complex business logic directly inside views, serializers, model signals, or frontend components.

## 6. Cross-module operations

Modules must not create uncontrolled circular imports or modify another module's records without using a defined service interface.

For cross-domain operations:

- Define a public service function in the owning module.
- Validate the actor and represented profile.
- Use a database transaction for multi-module writes.
- Emit an outbox event where asynchronous work is required.
- Record the business history and central audit event as appropriate.

Example: accepting a formal request.

```text
Request API
    |
    v
Request service
    |
    +--> Validate recipient authorization
    |
    +--> Lock request record
    |
    +--> Change request status
    |
    +--> Create connection through connection service
    |
    +--> Create request history
    |
    +--> Create notification outbox event
    |
    v
Commit transaction
```

The request status and connection creation must succeed or fail together.

## 7. API architecture

Base path:

```text
/api/v1/
```

Use RESTful resource-oriented endpoints.

Use JSON request and response bodies unless a file upload requires multipart form data.

API conventions:

- Consistent plural resource names.
- UUID identifiers.
- Pagination for collection endpoints.
- Filtering and sorting through documented parameters.
- Standardized validation errors.
- Explicit permission checks.
- Idempotency keys for applicable financial or retry-sensitive operations.
- No direct exposure of internal database implementation details.

## 8. Standard API error response

Recommended format:

```json
{
  "success": false,
  "error": {
    "code": "permission_denied",
    "message": "You are not authorized to perform this action.",
    "details": {}
  }
}
```

Validation errors should identify fields without exposing sensitive information.

## 9. Configuration architecture

Use environment-specific Django settings:

```text
config/settings/
├── __init__.py
├── base.py
├── local.py
├── test.py
├── staging.py
└── production.py
```

Use environment variables for deployment-specific settings and secrets.

Maintain centralized provider configuration for:

- Object storage.
- Email.
- SMS/OTP.
- JazzCash.
- Push notifications.
- Redis.
- Background jobs.
- External identity verification, if introduced.

### 9.1 Feature flags

Feature flags shall support controlled activation of optional infrastructure and functionality.

Examples:

```text
USE_S3_STORAGE
USE_EXTERNAL_EMAIL_PROVIDER
USE_EXTERNAL_SMS_PROVIDER
USE_JAZZCASH
USE_PUSH_NOTIFICATIONS
USE_REDIS
USE_CELERY
```

Feature flags must not be used to bypass security or authorization requirements.

A disabled production integration must fail safely and visibly rather than silently pretending an operation succeeded.

## 10. Local versus production configuration

| Area | Local development | Production |
|---|---|---|
| Database | Local PostgreSQL | Production PostgreSQL |
| Media | Local protected filesystem | Private object storage recommended |
| Email | Console/mock provider | Configured email provider |
| SMS/OTP | Mock or development provider | Configured SMS provider |
| Payments | Mock/sandbox | JazzCash merchant integration |
| Push | Mock or development | Push provider |
| Redis | Optional local service | Production Redis |
| Celery | Optional local worker | Managed worker process/container |
| Containers | Not mandatory | Docker + Docker Compose |
| Secrets | Local environment file | Secure deployment secrets |

## 11. Storage architecture

The application shall use a storage abstraction.

Local development may use a protected local media directory.

Production should use private object storage, such as an appropriately configured AWS S3 bucket.

Requirements:

- Private bucket by default.
- No public object ACLs for private documents.
- Storage keys stored in PostgreSQL.
- Short-lived signed URLs or controlled proxy downloads.
- File-type and size validation.
- Malware scanning where supported.
- Separate access policies for profile photos, identity documents, shared documents, and export files.
- Retention and deletion lifecycle policies.

## 12. Authentication and authorization architecture

Authentication identifies the account.

Authorization determines whether the account may perform an action for a particular profile or resource.

For family management, every relevant operation must establish:

- Actual authenticated account.
- Target/represented matrimonial profile.
- Ownership or active manager authorization.
- Required permission.
- Profile eligibility.
- Relevant connection/request state.
- Blocking and privacy restrictions.
- Additional verification requirements for sensitive actions.

Do not trust a profile ID supplied by the frontend without checking this relationship.

## 13. Audit and event architecture

Business histories remain owned by their domain modules.

Examples:

- RequestHistory.
- ConnectionHistory.
- ManagerAuthorizationHistory.
- ModerationCaseHistory.
- SubscriptionChangeHistory.

A shared audit service shall create central audit events for significant security, administrative, financial, and privacy-sensitive actions.

Avoid copying sensitive document contents, OTPs, passwords, payment credentials, or full message bodies into general audit logs.

## 14. Transactional outbox

Critical business events that trigger asynchronous notifications shall use an outbox pattern.

Within one database transaction:

1. Perform the business operation.
2. Record required domain history.
3. Insert an outbox event.
4. Commit.

A Celery worker processes the outbox after commit.

The worker must safely handle retries and duplicate delivery attempts.

## 15. Caching

Caching may be used for:

- Static configuration.
- Non-sensitive reference data.
- Public catalog data.
- Short-lived computed data where invalidation is understood.

Do not cache private profile data or authorization results in a way that allows access after permission revocation.

Do not treat Redis as the authoritative financial ledger.

## 16. Observability

Production shall provide:

- Structured application logs.
- Error tracking.
- Health endpoints.
- Celery task failure visibility.
- Payment reconciliation visibility.
- Database backup monitoring.
- Deployment logs.
- Operational alerts.

Logs must redact passwords, OTPs, tokens, identity numbers, private document URLs, and sensitive personal information.

## 17. Scalability strategy

The modular monolith shall scale through:

- Multiple Django application workers.
- Separate Celery workers by task category where useful.
- Database indexing and query optimization.
- Controlled caching.
- Private object storage.
- Pagination.
- Background processing for expensive operations.

Microservices are not required to achieve MVP scale.

## 18. Architecture constraints

- One backend codebase.
- One authoritative PostgreSQL database.
- Explicit Django module boundaries.
- REST API versioning.
- No business-rule dependence on frontend behavior.
- No hardcoded payment or subscription prices.
- No direct public access to private media.
- No unreviewed migration of business logic into asynchronous tasks.
- No microservices during MVP without a new architecture decision.

## 19. Production readiness conditions

Before production launch:

- Secrets and environment configuration must be reviewed.
- Database backups and restoration must be tested.
- HTTPS must be enforced.
- Admin MFA must be enabled.
- Private storage permissions must be reviewed.
- Payment callback verification must be tested.
- Celery retry and failure handling must be tested.
- Monitoring and alerting must be active.
- Security and privacy tests must pass.
- Deployment rollback procedure must be documented.
