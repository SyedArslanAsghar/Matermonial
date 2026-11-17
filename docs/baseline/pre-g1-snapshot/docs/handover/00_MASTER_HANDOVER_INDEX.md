# Master Handover Index

# Matermonial — Master Project Handover Index

**Project:** Matermonial  
**Document:** 00 — Master Handover Index  
**Purpose:** Single entry point for understanding and implementing the project  
**Status:** Handover baseline — subject to the approval status recorded in individual documents

---

## 1. Project Purpose

Matermonial is a privacy-conscious matrimonial platform designed to help adults and their families discover suitable matrimonial matches, manage introductions, communicate after mutual acceptance, and manage the matrimonial process in a structured and secure environment.

The platform supports:

- Individual account ownership.
- Matrimonial profiles.
- Family-managed profiles with owner-controlled authorization.
- Profile search and rule-based matching.
- Interests and formal matrimonial requests.
- Connections and relationship progress tracking.
- Private messaging and shared documents.
- Profile privacy and media access controls.
- Subscriptions, credit allowances and top-up purchases.
- Notifications.
- Moderation and reporting.
- Data exports and account deletion.
- Administrative and operational management.

The MVP must be designed as a production-oriented foundation rather than a temporary prototype.

## 2. Product and Technical Direction

| Area | Approved direction |
|---|---|
| Backend | Django + Django REST Framework |
| Web frontend | React + Vite + TypeScript |
| Mobile applications | React Native + Expo |
| Database | PostgreSQL |
| Architecture | Modular monolith |
| Background processing | Celery + Redis |
| API | REST, versioned under `/api/v1/` |
| Local development | Native/local development; Docker is not mandatory |
| Production deployment | AWS EC2 with Docker and Docker Compose |
| CI/CD | GitHub Actions or an equivalent documented pipeline |
| API documentation | OpenAPI |
| Languages | English and Urdu, including RTL support |

Microservices are not part of the MVP architecture.

## 3. Source of Truth and Decision Priority

Claude Code must treat the following documents as the project specification.

When documents appear to conflict, use this priority:

1. Explicitly approved decisions recorded in Architecture Decision Records.
2. Approved business rules and workflows.
3. Complete SRS and MVP requirements.
4. Security, privacy and authorization specifications.
5. Database, API and architecture specifications.
6. Development and operational standards.
7. Recommendations and assumptions.

A recommendation must never silently override an approved requirement.

If a contradiction cannot be resolved from the documents, Claude Code must identify it, explain its impact, and request approval before implementing the conflicting behavior.

## 4. Handover Document Catalogue

| ID | Document | Purpose |
|---|---|---|
| 00 | Master Handover Index | Entry point and document authority |
| 01 | Complete SRS | Business requirements and MVP scope |
| 02 | System Architecture | Application structure and technical architecture |
| 03 | Database Design | Entities, fields, relationships, constraints and indexes |
| 04 | API and Integrations | REST endpoints, contracts and external integrations |
| 05 | Business Rules and Workflows | Core operations and domain behavior |
| 06 | Security, Privacy and Authorization | Access control, security and personal data protection |
| 07 | Repository and Development Standards | Project structure and engineering conventions |
| 08 | Testing and QA | Testing levels and quality gates |
| 09 | AWS Deployment and CI/CD | Production infrastructure and delivery |
| 10 | Implementation Roadmap | Phases, milestones and backlog |
| 11 | Architecture Decision Records | Approved technical decisions |
| 12 | Claude Code Instructions | Repository-level AI development instructions |
| 13 | Assumptions, Risks and Traceability | Unresolved decisions and risk tracking |
| 14 | Family Manager Permission Matrix | Delegated permissions |
| 15 | State Machines | Valid status transitions |
| 16 | Environment Configuration | Settings, providers and feature flags |
| 17 | Glossary | Consistent domain terminology |

## 5. Functional Domains and Database Modules

The SRS organizes functionality into 22 functional domains. The database design organizes persistent entities into 16 implementation modules.

These are different views of the same product and must not be treated as competing module counts.

The 16 database design modules are:

1. Accounts and Authentication
2. Profiles
3. Partner Preferences
4. Verification
5. Family Management
6. Matching and Search
7. Interests and Requests
8. Connections and Relationship Progress
9. Messaging and Shared Documents
10. Privacy and Media Access
11. Subscriptions and Credits
12. Notifications
13. Moderation and Reporting
14. Data Exports and Account Deletion
15. Audit Logs and Administrative Management
16. Admin Support and Platform Operations

Document 01 must contain the functional-domain catalogue and its mapping to these implementation modules. Document 03 is the authoritative database design.

## 6. Important Business Principles

Claude Code must preserve the following principles:

### Account ownership
- An account owns its personal matrimonial profile.
- An account may manage other profiles only through explicit authorization.
- Account identity, profile identity and manager authorization are separate concepts.
- Manager actions must record both the actual acting account and the represented profile.

### Privacy and safety
- The platform is for adults aged 18 or older.
- Phone verification and identity verification are separate.
- Private profile media must not be publicly accessible.
- Blocking and Hide My Profile From are separate features.
- Sensitive family-manager actions require explicit permission and additional security controls.
- Personal data must not be disclosed through notifications, logs, APIs or exports without authorization.

### Matrimonial requests
- Active duplicate requests are prohibited in both directions.
- A declined or expired request creates a directional 30-day cooldown.
- Formal requests expire after three calendar months.
- Credit deduction and request creation must be atomic.
- Acceptance creates one connection in the same database transaction.

### Credits and payments
- Subscription allowances and purchased credits are separate.
- Subscription allowances expire at the billing-period boundary.
- Unused purchased credits do not expire.
- Subscription allowances are consumed before purchased credits.
- Credit balances must never become negative.
- Payment callbacks must be verified and idempotent.

### Communication
- One conversation exists per connection.
- Messaging requires an active connection.
- Paused or closed connections cannot send new messages.
- Conversation history is retained according to the applicable retention rules.
- Family managers act through an authorized profile, not as separate matrimonial participants.

### Data rights
- Users can request an authorized personal data export.
- Account deletion includes a 30-day recovery period.
- Export and deletion operations must be secure, auditable and idempotent.
- Another profile owner's data must not be deleted merely because a manager account is deleted.

## 7. Development Rules

Claude Code must:

1. Inspect the existing repository before proposing changes.
2. Read this index and all relevant specifications before implementation.
3. Identify existing code and reuse it where appropriate.
4. Avoid unnecessary rewrites and architectural changes.
5. Work in small, reviewable implementation phases.
6. Write and run tests for implemented functionality.
7. Use database transactions for operations requiring atomicity.
8. Enforce authorization on the backend, not only in the frontend.
9. Avoid hardcoded secrets, prices, limits and provider credentials.
10. Update documentation when implementation decisions or behavior change.
11. Never claim a feature is complete without verification.
12. Never silently remove, weaken or reinterpret an approved requirement.

## 8. Approval Requirements

Claude Code may inspect files, analyze architecture, identify missing components, propose implementation plans and prepare code changes within an approved task.

Explicit owner approval is required before:

- Changing the approved architecture.
- Removing or materially changing an approved feature.
- Changing business rules or financial calculations.
- Changing privacy or authorization behavior.
- Introducing a new external paid service.
- Applying destructive database operations or deleting production data.
- Making irreversible production changes.
- Changing the scope of the MVP.

Routine implementation details may follow the documented standards without asking for unnecessary approval.

## 9. Project Progress Tracking

Maintain these files:

- `docs/implementation/progress.md`
- `docs/implementation/completed_features.md`
- `docs/implementation/pending_features.md`
- `docs/implementation/known_issues.md`

For every implementation task, record:

- Feature or task name.
- Relevant requirement/document references.
- Implementation status.
- Files or modules affected.
- Tests written and their results.
- Known limitations.
- Outstanding decisions.
- Whether owner approval is required.

Use the following statuses:

- NOT_STARTED
- PLANNED
- IN_PROGRESS
- BLOCKED
- IMPLEMENTED
- TESTED
- APPROVED
- DEFERRED

IMPLEMENTED does not mean TESTED, and TESTED does not automatically mean APPROVED.

## 10. Initial Claude Code Assignment

Before writing application code, Claude Code must:

1. Inspect the repository and its current state.
2. Read all available handover documents.
3. Identify missing, incomplete or contradictory specifications.
4. Compare the repository against the approved target architecture.
5. Report existing code, configuration, dependencies and infrastructure.
6. Identify security-sensitive areas and potential data-loss risks.
7. Prepare a phased implementation plan.
8. Identify tasks that can safely proceed and tasks requiring owner approval.
9. Wait for owner approval before broad structural changes or feature implementation.

The first assignment is a repository and specification assessment, not an instruction to build the entire MVP immediately.

## 11. Handover Completion Criteria

The project handover is complete when:

- All documents 00–17 exist in the repository.
- Each document has a clear status.
- Approved requirements and recommendations are distinguishable.
- The 22 functional domains map to the 16 database modules.
- Business rules and state transitions are consistent.
- Security and permission rules are explicit.
- Claude Code has read and assessed the complete handover.
- Claude Code has produced a repository assessment and implementation plan.
- The project owner has reviewed and approved the first implementation phase.

---

**End of Document 00**