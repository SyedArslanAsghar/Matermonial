# Matermonial — Architecture Decision Records (ADRs)

**Version:** 1.0  
**Date:** 11 November 2026

An Architecture Decision Record captures a significant technical or structural decision, its context, consequences, and current status.

## ADR-001: Use a modular monolith

**Status:** Approved baseline

**Context:** The MVP needs multiple business domains, but independent microservices would add deployment, monitoring, and integration complexity.

**Decision:** Use one Django backend organized into domain-specific Django applications.

**Consequences:**

- Simpler deployment.
- Shared database transactions.
- Clear internal boundaries.
- Future extraction remains possible if justified.
- Developers must prevent uncontrolled cross-module dependencies.

## ADR-002: Use Django and Django REST Framework

**Status:** Approved baseline

**Context:** The project requires a secure API backend, relational data, authentication, administrative workflows, and modular business logic.

**Decision:** Use Django and DRF.

**Consequences:**

- Mature ORM and migrations.
- Standardized API development.
- Django admin support.
- Domain boundaries must be maintained through application structure and services.

## ADR-003: Use React, Vite, and TypeScript for web

**Status:** Approved baseline

**Context:** The project requires a modern web application consuming the backend API.

**Decision:** Use React, Vite, and TypeScript.

**Consequences:**

- Shared typed frontend contracts.
- Independent frontend deployment.
- Backend remains authoritative for business rules.

## ADR-004: Use React Native and Expo for mobile

**Status:** Approved baseline

**Context:** The platform requires mobile applications without creating separate backend business logic.

**Decision:** Use React Native with Expo.

**Consequences:**

- Shared REST API.
- Cross-platform mobile development.
- Platform-specific secure storage and push handling are required.

## ADR-005: Use PostgreSQL

**Status:** Approved baseline

**Context:** The platform has relational entities, complex constraints, financial records, and transactional workflows.

**Decision:** Use PostgreSQL.

**Consequences:**

- Strong relational integrity.
- Transaction and locking support.
- JSON fields available for limited flexible metadata.
- Production backups and recovery are critical.

## ADR-006: Use Celery and Redis

**Status:** Approved baseline

**Context:** Notifications, exports, deletion, scheduled expiry, and other operations must run asynchronously.

**Decision:** Use Celery with Redis.

**Consequences:**

- Background operations are separated from request-response processing.
- Retry and idempotency are mandatory.
- Worker and scheduler operations require monitoring.

## ADR-007: Local development does not require Docker

**Status:** Approved baseline

**Context:** Developers should be able to work using native local tools.

**Decision:** Docker is not mandatory for local development.

**Consequences:**

- Native setup instructions are required.
- Local/mock services must be supported.
- Local Docker remains optional.

## ADR-008: Use Docker and Docker Compose for AWS EC2 production

**Status:** Approved baseline

**Context:** Production deployment requires repeatable service configuration.

**Decision:** Use Docker and Docker Compose for the EC2 deployment.

**Consequences:**

- Production images must be reproducible.
- Secrets must be injected securely.
- Volumes, health checks, logging, and rollback must be designed.

## ADR-009: Use a monorepo

**Status:** Approved baseline

**Context:** Backend, web, mobile, documentation, and deployment code must evolve together.

**Decision:** Use one repository with `backend/`, `frontend/`, `mobile/`, `docs/`, `scripts/`, and infrastructure/CI directories.

**Consequences:**

- Shared documentation and version coordination.
- CI must support multiple application stacks.
- Repository access and ownership can be managed centrally.

## ADR-010: Use `/api/v1/` REST API versioning

**Status:** Approved baseline

**Context:** Web and mobile clients require stable API contracts.

**Decision:** All application APIs use `/api/v1/`.

**Consequences:**

- OpenAPI documentation is required.
- Breaking API changes need a versioning strategy.
- Consistent errors and pagination are mandatory.

## ADR-011: Use rule-based matching for MVP

**Status:** Approved baseline

**Context:** Initial matching must be transparent, testable, and feasible without AI infrastructure.

**Decision:** Use deterministic rule-based matching for MVP. AI-based matching is post-MVP.

**Consequences:**

- Criteria and ranking rules must be documented.
- Optional preferences must not unintentionally disqualify profiles.
- Future AI recommendations must not bypass eligibility/privacy rules.

## ADR-012: Separate account ownership from matrimonial profile ownership/management

**Status:** Approved baseline

**Context:** One account can own its personal profile and manage other family members' profiles.

**Decision:** Use separate account, profile, and manager authorization entities.

**Consequences:**

- Every profile action must resolve the represented profile.
- Permissions are profile-scoped.
- Actual actor identity is recorded.
- Billing remains account-level.

## ADR-013: Use a credit ledger

**Status:** Approved baseline

**Context:** Subscription allowances and purchased credits require accurate financial history.

**Decision:** Maintain separate balances and an append-only credit transaction ledger.

**Consequences:**

- Credit changes are traceable.
- Row locking and idempotency are required.
- Corrections use compensating transactions.
- Negative balances are prohibited.

## ADR-014: Use transactional outbox for notifications

**Status:** Recommended implementation decision

**Context:** Notifications must not be lost when a business transaction commits but a provider call fails.

**Decision:** Write outbox events in the same transaction as the business operation and process them asynchronously.

**Consequences:**

- Reliable event handoff.
- Celery workers can retry.
- Duplicate processing must be idempotent.

## ADR-015: Use private media storage

**Status:** Approved security direction

**Context:** Profile photos, identity documents, shared documents, moderation evidence, and exports have different access requirements.

**Decision:** Use private storage and short-lived authorized access URLs.

**Consequences:**

- Access must be checked before URL issuance.
- Storage permissions must be separated.
- Previously downloaded files cannot be remotely recalled.

## ADR-016: Use centralized feature flags and provider configuration

**Status:** Approved baseline

**Context:** External services may be unavailable or not configured in local development.

**Decision:** Centralize configuration for object storage, email, SMS/OTP, JazzCash, push, Redis, and background jobs.

**Consequences:**

- Local/mock providers are possible.
- Provider implementations are replaceable.
- Feature flags must not bypass security requirements.

## ADR-017: Support English and Urdu with RTL

**Status:** Approved baseline

**Context:** The target platform requires English and Urdu support.

**Decision:** Support localized content and RTL layouts.

**Consequences:**

- Templates require language variants.
- Frontend components must handle direction.
- API data must remain language-neutral where possible.

## ADR-018: Separate blocking from Hide My Profile From

**Status:** Approved product decision

**Context:** Users need a way to avoid discovery without applying the stronger communication restrictions of blocking.

**Decision:** Implement separate `ProfileBlock` and `HiddenProfile` mechanisms.

**Consequences:**

- Search and request eligibility must evaluate both.
- Hiding does not terminate existing connections.
- Blocking prevents new communication and applicable access.

## ADR-019: Keep monthly allowances separate from purchased credits

**Status:** Approved product decision

**Context:** Subscription benefits and purchased top-ups have different expiry rules.

**Decision:** Store separate allowance and purchased-credit buckets.

**Consequences:**

- Monthly allowances expire at billing-period end.
- Purchased unused credits do not expire.
- Subscription allowances are consumed first.

## ADR-020: Use account-level billing for family-manager actions

**Status:** Approved product decision

**Context:** A manager must not use their own wallet for actions performed on behalf of a profile owner.

**Decision:** Charge the owning account's wallet and record the actual manager and represented profile.

**Consequences:**

- Billing identity is consistent.
- Manager actions remain attributable.
- Profile switching cannot bypass account-level view billing.

## ADR-021: Use identity confirmation for export and deletion

**Status:** Approved product decision

**Context:** Exports and deletion are sensitive operations.

**Decision:** Require identity confirmation and use secure asynchronous workflows.

**Consequences:**

- Exports include only authorized data.
- Deletion has a 30-day recovery period.
- Retention holds are respected.

## ADR-022: Preserve domain history and central audit separately

**Status:** Recommended implementation decision

**Context:** Request, connection, manager, moderation, and subscription histories serve business-specific purposes, while administrators need a central audit view.

**Decision:** Keep domain histories in their owning modules and create a central AuditLog for significant events.

**Consequences:**

- Business history remains easy to query.
- Central audit provides cross-module traceability.
- Avoid duplicating sensitive payloads.

## ADR-023: Keep admin support and platform operations in a separate domain

**Status:** Proposed implementation baseline

**Context:** Support cases and maintenance windows have different permissions and lifecycles from ordinary user-facing features.

**Decision:** Group support cases, support messages, and maintenance windows in the platform operations module.

**Consequences:**

- Internal support notes can be restricted.
- Maintenance communication is centrally managed.
- Exact operational fields should be confirmed during implementation.

## ADR-024: Use staged implementation rather than full-project generation

**Status:** Approved delivery approach

**Context:** Generating a complete application in one operation increases errors and makes review difficult.

**Decision:** Implement the project in roadmap stages with tests and review gates.

**Consequences:**

- Each stage is verifiable.
- Dependencies are discovered earlier.
- Claude Code must report changes and test results after each stage.