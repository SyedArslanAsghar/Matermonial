# Matermonial — Assumptions, Open Decisions, Risks and Requirements Traceability

**Version:** 1.0  
**Date:** 11 November 2026

## 1. Purpose

This document records known assumptions, implementation recommendations, unresolved decisions, risks, and traceability requirements.

It prevents Claude Code from treating an unspecified detail as an approved business decision.

## 2. Approved baseline decisions

The following decisions form the implementation baseline:

| Area | Decision |
|---|---|
| Architecture | Modular monolith |
| Backend | Django + Django REST Framework |
| Web | React + Vite + TypeScript |
| Mobile | React Native + Expo |
| Database | PostgreSQL |
| Background jobs | Celery + Redis |
| API | REST, `/api/v1/`, OpenAPI |
| Matching | Rule-based for MVP |
| Local development | Native development; Docker not mandatory |
| Production | AWS EC2 with Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Payment gateway | JazzCash integration |
| Languages | English and Urdu, including RTL |
| Account/profile model | Separate account, personal profile, and manager authorization |
| Family management | Explicit owner authorization and granular permissions |
| Request expiry | Three calendar months |
| Decline/expiry cooldown | 30 days, directional |
| Visitor history | Advance/Premium feature; 90-day retention recommended |
| Export | ZIP containing JSON and eligible media |
| Export availability | Seven days |
| Export link expiry | 24 hours |
| Deletion recovery | 30 days |
| Photo access | Seven days, thirty days, or manual expiry |
| Subscription allowance | Expires at billing-period end |
| Purchased unused credits | Do not expire |
| Request acceptance | Creates a connection transactionally |
| Messaging | Text messaging in MVP |
| Voice/video | Post-MVP |
| AI matching | Post-MVP |
| Microservices | Not part of MVP |

## 3. Assumptions and recommendations

The following items are recommended implementation assumptions. They should not be represented as finalized commercial, legal, or operational decisions.

| ID | Topic | Recommended approach | Confirmation needed |
|---|---|---|---|
| A-001 | Subscription prices | Admin-configurable; no hardcoded prices | Before commercial launch |
| A-002 | Credit quantities | Admin-configurable | Before commercial launch |
| A-003 | Currency | Store explicit ISO currency code per amount | Confirm supported sales currencies |
| A-004 | Payment mode | JazzCash sandbox during development | Before live payment |
| A-005 | Database hosting | Start with a protected PostgreSQL deployment; evaluate managed hosting | Before production |
| A-006 | Redis hosting | Protected Redis service; evaluate managed option | Before production |
| A-007 | Private media | S3 private storage recommended in production | Before real sensitive uploads |
| A-008 | Email provider | Provider adapter with local console/mock implementation | Before production |
| A-009 | SMS provider | Provider adapter with mock implementation | Before production |
| A-010 | Identity review | Authorized human review workflow | Before real verification operations |
| A-011 | Photo moderation | Human review plus configurable status workflow | Before public launch |
| A-012 | Support permissions | Least-privilege support roles | Before support team access |
| A-013 | Admin approvals | Dual approval for high-risk operations | Confirm thresholds |
| A-014 | Retention | Configurable retention policy by data category | Legal review |
| A-015 | Performance | Measure under an agreed realistic load profile | Before production launch |
| A-016 | Availability | Define service targets based on budget and operations | Before production launch |
| A-017 | Urdu translations | Use reviewed translations for critical legal/security text | Before public launch |
| A-018 | Profile discovery fields | Explicit allowlist of fields | During privacy review |
| A-019 | Support case fields | Use the recommended Module 16 fields | During admin implementation |
| A-020 | Audit field details | Use the recommended Module 15 design | During audit implementation |

## 4. Open decisions

These decisions should be recorded and resolved before the related feature is enabled in production.

### OD-001: Commercial subscription structure

Confirm:

- Plan names.
- Plan durations.
- Prices.
- Supported currencies.
- Monthly request allowances.
- Monthly profile-view allowances.
- Paid benefits.
- Feature availability by plan.
- Refund and cancellation policy.

The database and admin interfaces should support configuration without hardcoding these values.

### OD-002: Credit package catalog

Confirm:

- Request-credit package quantities.
- Profile-view package quantities.
- Package prices.
- Currencies.
- Package availability.
- Refund eligibility.

### OD-003: JazzCash production configuration

Confirm:

- Merchant account.
- Production credentials.
- Current callback contract.
- Signature verification.
- Payment status mapping.
- Refund process.
- Reconciliation process.

Do not invent gateway fields or signatures.

### OD-004: Identity verification policy

Confirm:

- Accepted identity-document types.
- Required live photographs.
- Review checklist.
- Rejection reasons.
- Resubmission policy.
- Manual duplicate-detection override process.
- Retention period.

### OD-005: Legal and privacy policy

Obtain appropriate legal review for:

- Terms of service.
- Privacy policy.
- Consent.
- Adult eligibility.
- Identity verification.
- Data retention.
- Account deletion.
- Financial records.
- International users.
- Data export.
- Moderation and appeals.

### OD-006: Production infrastructure

Confirm:

- AWS region.
- EC2 instance sizing.
- Database hosting choice.
- Redis hosting choice.
- Domain.
- TLS certificate approach.
- Backup frequency.
- Backup retention.
- RPO.
- RTO.
- Monitoring and alerting budget.

### OD-007: Operational administration

Confirm:

- Admin roles.
- Support roles.
- Verification reviewers.
- Moderators.
- Finance administrators.
- Approval thresholds for sensitive actions.
- Escalation process.

## 5. Project risks

| Risk | Impact | Mitigation |
|---|---|---|
| Manager authorization bypass | Unauthorized access to private profiles | Central permission service and object-level tests |
| Sensitive data exposure | Privacy and trust damage | Field allowlists, private storage, security tests |
| Incorrect credit deductions | Financial loss and user disputes | Ledger, locking, idempotency, reconciliation |
| Duplicate payment callbacks | Duplicate credits or subscriptions | Verified callbacks and idempotent processing |
| Duplicate requests | Conflicting matrimonial workflows | Database constraints and transactional services |
| Request expiry errors | Incorrect cooldown or history | Timezone-aware expiry service and tests |
| Hidden/blocking inconsistency | Privacy violation | Shared eligibility service |
| Media URL leakage | Unauthorized document/photo access | Private storage and short-lived access |
| Celery duplicate execution | Duplicate notifications or operations | Idempotent tasks and outbox |
| Export data leakage | Disclosure of other people's private data | Explicit export allowlist and tests |
| Deletion data loss | Legal or user-data problems | Recovery period, retention holds, idempotent steps |
| Overcomplicated architecture | Delayed MVP | Modular monolith; avoid microservices |
| Unverified provider assumptions | Failed payment/OTP delivery | Provider adapters and sandbox validation |
| Incomplete test coverage | Production defects | Mandatory business/security test gates |
| Documentation drift | Incorrect implementation | Update specifications with code changes |

## 6. Requirements traceability approach

Each requirement must have a unique identifier and map to:

- SRS requirement.
- Business rule.
- Database module.
- Model/entity.
- API endpoint or administrative operation.
- Authorization policy.
- Test case.
- Implementation status.

Recommended tracking statuses:

- NOT_STARTED.
- IN_PROGRESS.
- IMPLEMENTED.
- TESTED.
- REVIEWED.
- BLOCKED.
- DEFERRED.
- POST_MVP.

## 7. Initial requirements traceability matrix

| Requirement area | SRS references | Module | Key test |
|---|---|---|---|
| Registration/authentication | FR-ACC | M01, M04 | OTP and authentication tests |
| Profile management | FR-PRO | M02 | Ownership and privacy tests |
| Partner preferences | Preference requirements | M03 | Nullable Boolean/range tests |
| Identity verification | FR-VER | M04 | State transition/document access tests |
| Family management | FR-FAM | M05 | Permission and revocation tests |
| Search/matching | FR-MAT | M06, M10 | Eligibility and hidden-profile tests |
| Interests/requests | FR-REQ | M07, M11 | Duplicate/cooldown/credit tests |
| Connections | FR-CON | M08 | Acceptance and uniqueness tests |
| Messaging | FR-MSG | M09, M10 | Participant and block tests |
| Privacy/media | FR-PRI | M10 | Permission and expiry tests |
| Subscription/credits | FR-SUB | M11 | Ledger/concurrency/payment tests |
| Notifications | Notification requirements | M12 | Outbox/retry/idempotency tests |
| Moderation | Moderation requirements | M13, M15 | Conflict/restriction/appeal tests |
| Data export | FR-DAT | M14 | Scope and secure-download tests |
| Account deletion | FR-DAT | M14 | Recovery/retention/idempotency tests |
| Audit/admin | Admin requirements | M15 | Role and audit tests |
| Support/operations | Admin requirements | M16 | Internal-note access tests |

## 8. Change management

A change to a requirement must include:

1. Change description.
2. Business reason.
3. Affected modules.
4. Database impact.
5. API impact.
6. Security/privacy impact.
7. Migration impact.
8. Test impact.
9. Documentation updates.
10. Approval status.

Do not silently modify approved business rules.

## 9. Final handover note

The implementation baseline is intended to be sufficiently complete to begin repository foundation and staged backend development.

Commercial prices, external provider credentials, legal wording, exact production infrastructure sizing, and selected operational policies remain configurable or subject to confirmation.

These items should not prevent implementation of the underlying architecture, models, provider interfaces, admin configuration, and automated tests.