# Matermonial — Architecture Decision Records (ADRs)

**Version:** 1.0 (G1 revision 2026-11-16)  
**Date:** 11 November 2026  
**Document status:** APPROVED_WITH_OPEN_ITEMS (project owner, 2026-11-17, DR-2026-11-17-A; record in doc 20 §5). **Open items:** PROPOSED TRs: TR-01, TR-02, TR-07, TR-11, TR-15, TR-17, TR-23; ADR decisions pending: ADR-022, ADR-023 (RECOMMENDED / PROPOSED), ADR-025…ADR-032 (PROPOSED). Listed items keep their own status (doc 19); this document status doesn't approve them. TR-09, TR-22 approved 2026-11-17 (DR-2026-11-17-G3).  
**Applied corrections:** DCR-10, DCR-28 (doc 20); G1 correction pass 2026-11-17 (DR-2026-11-17-C). New ADRs from ADR-025 onwards are kept as files in `docs/decisions/` and indexed in §25.

An Architecture Decision Record captures a significant technical or structural decision, its context, consequences, and current status.

**ADR status vocabulary.** An ADR's status is a requirement-approval status (doc 00 §9.1), not a document status. ADR-001…024 keep their original labels, which map as follows: "Approved baseline", "Approved security direction", "Approved product decision" and "Approved delivery approach" = APPROVED; "Recommended implementation decision" = RECOMMENDED (awaiting a decision); "Proposed implementation baseline" = PROPOSED. ADR-025 onwards use the status values directly.

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

**Status:** APPROVED — core decision (DR-2026-11-17-C2) **and refinements** (DR-2026-11-18-G4, 2026-11-18, via ADR-028 / TR-11). Previously "Recommended implementation decision".

> **Scope of the approval.** The core decision below restates an already-approved requirement: SRS §15 / FR-NOT-005 (Notifications module, M12), `CLAUDE.md` CC-R30 ("Notifications use a transactional outbox"), and doc 02 §14. It is approved as such and doesn't await a further owner decision.
>
> **Not covered by this approval:** the refinements in ADR-028 / TR-11 (PROPOSED): `OutboxEvent` in `common/events`, two-phase claim and lease processing, level 9 completion, event classes and financial obligations, the queue key and encrypted payload, pseudonymous recipients, the dedupe key, and redaction and retention. They stay PROPOSED until doc 19 records TR-11's approval (before G4).

**Context:** Notifications must not be lost when a business transaction commits but a provider call fails.

**Decision (approved core):** Write outbox events in the same transaction as the business operation and process them asynchronously, with retryable background delivery.

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

**Status:** APPROVED (DR-2026-11-18-G4, 2026-11-18). Previously "Recommended implementation decision".

> **G1 (DCR-28):** a formal decision is still pending; it is due before G4 (baseline v4.6, approval-by-gate table: "Decisions on ADR-014 / 022 / 023 and ADR-025…032"). Its refined form for security events and log pseudonymisation is ADR-032 (PROPOSED).

**Context:** Request, connection, manager, moderation, and subscription histories serve business-specific purposes, while administrators need a central audit view.

**Decision:** Keep domain histories in their owning modules and create a central AuditLog for significant events.

**Consequences:**

- Business history remains easy to query.
- Central audit provides cross-module traceability.
- Avoid duplicating sensitive payloads.

## ADR-023: Keep admin support and platform operations in a separate domain

**Status:** APPROVED (DR-2026-11-18-G4, 2026-11-18). Previously "Proposed implementation baseline".

> **G1 (DCR-28):** a formal decision is still pending; it is due before G4 (baseline v4.6, approval-by-gate table). The approved domain catalogue (OD-01) places this under D22.

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

## 25. Index of ADRs recorded after G1 (DCR-28)

All ADR decisions below are due **before G4** (baseline v4.6, approval-by-gate table). The TR each ADR records may have its own, later approval point in doc 19.

| ADR | Title | Status | File |
|---|---|---|---|
| ADR-025 | Authentication sessions and tokens | PROPOSED (TR-01) | `docs/decisions/ADR-025-authentication.md` |
| ADR-026 | Acting-profile authorization (ActorContext) | PROPOSED (TR-02) | `docs/decisions/ADR-026-acting-profile.md` |
| ADR-027 | Administrative authorization from a single source | PROPOSED (TR-07) | `docs/decisions/ADR-027-admin-authorization.md` |
| ADR-028 | Transactional outbox as a pseudonymous work queue | PROPOSED (TR-11). Refines the approved ADR-014 core. | `docs/decisions/ADR-028-outbox.md` |
| ADR-029 | Three independent status dimensions | PROPOSED (the ADR document; DR-2026-11-17-C6). The status-model decision it records, TR-14, is APPROVED (DR-2026-11-16-2). | `docs/decisions/ADR-029-status-model.md` |
| ADR-030 | Ledger as the permanent record; balances as projections | PROPOSED (TR-15) | `docs/decisions/ADR-030-ledger-projections.md` |
| ADR-031 | Global lock-order and anchor policy | PROPOSED (the ADR document). The TRs it records, TR-09 and TR-22, are APPROVED (DR-2026-11-17-G3-2). | `docs/decisions/ADR-031-lock-order.md` |
| ADR-032 | Security-event model and log pseudonymisation | PROPOSED (TR-17, TR-23) | `docs/decisions/ADR-032-security-events.md` |
| ADR-033 | Admin MFA, enrollment, recovery and the admin session | PROPOSED (implementation record within approved TR-07; owner review requested, 2026-11-19). Amendment 1 (two-person recovery) **APPROVED** (DR-2026-11-19-O-8; A1-3 not approved). Amendment 2: first-enrollment codes by SMS only (DR-2026-11-20-C-3, KI-39) | `docs/decisions/ADR-033-admin-mfa.md` |
| ADR-034 | Enumeration-safe family-manager invitations (KI-34) | ACCEPTED for implementation (DR-2026-11-20-C-2, 2026-11-20); owner review of Phases 2–4 pending | `docs/decisions/ADR-034-enumeration-safe-invitations.md` |

Pending decisions on existing ADRs: ADR-022 and ADR-023 (see the notes under each). ADR-014 is APPROVED for its core decision only (DR-2026-11-17-C2).
