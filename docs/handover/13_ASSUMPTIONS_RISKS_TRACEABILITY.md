# Matermonial — Assumptions, Open Decisions, Risks and Requirements Traceability

**Version:** 1.0 (G1 revision 2026-11-16)  
**Date:** 11 November 2026  
**Document status:** APPROVED_WITH_OPEN_ITEMS (project owner, 2026-11-17, DR-2026-11-17-A; record in doc 20 §5). **Open items:** OPEN ODs: OD-02, OD-03, OD-04, OD-05, OD-06, OD-07, OD-08, OD-09, OD-10; OPEN legacy ODs (doc 13 series): OD-001, OD-002, OD-003, OD-004, OD-005, OD-006, OD-007. Listed items keep their own status (doc 19); this document status doesn't approve them. TR-13 approved 2026-11-17 (DR-2026-11-17-G2D-2).  
**Applied corrections:** DCR-10, DCR-12, DCR-33, DCR-67, DCR-71, DCR-74 (doc 20)

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

### 4.0 Owner decisions OD-01…OD-10 and the implementation rule (DCR-33)

Two separate decision series exist:
- **OD-01…OD-10** (owner decision bundles from specification reconciliation) are held in **doc 19**. OD-01 is RESOLVED (DR-2026-11-16-5). OD-02…OD-10 are OPEN.
- **OD-001…OD-007** below are the original handover decisions. They stay here and keep their own status.

**Rule: no implementation from an unanswered OD.** Behaviour that depends on an OPEN owner decision (from either series) is not implemented. In doc 18 a requirement is marked BLOCKED only when the whole requirement depends on the open decision; otherwise the dependency is recorded in its OD-dependency column until the decision is recorded (`CLAUDE.md` CC-R25). A PROPOSED technical recommendation (doc 19 §4) is likewise not treated as an approved requirement.

The legal review under OD-005 also covers the retention and disposition items listed in doc 19 §5: retention periods for logs, sessions, ProfileView and financial records, messages, VisitorHistory, the maintenance log, the outbox and backups; the KEK and queue-key destruction schedule; pseudonymous event grouping after unlinking; identifiability of financial records; and the published credit-and-refund policy that OD-07g depends on (DCR-67, DCR-71, DCR-74).

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

### 5.1 Specification assumptions (AS-1…AS-21)

Recorded during specification reconciliation (baseline v4–v4.6-F3). Each must be confirmed or replaced before the dependent work.

| ID | Assumption | Source |
|---|---|---|
| AS-1 | The represented person holds their own account [DECIDED, SRS §2.2, FR-FAM-001] | v3 (A4 §15) |
| AS-2 | Same-origin hosting of the web app and API is acceptable for the AWS topology | v3 |
| AS-3 | PostgreSQL 15 or later is supported; CI runs on PostgreSQL 16 and 18 | v3; v4.6 §4 |
| AS-4 | Django 5.2 and DRF 3.16 stay as already pinned | v3 |
| AS-5 | The Expo Push service is acceptable when EP-05 is decided | v3 |
| AS-6 | The ten-question limit applies to bundled owner decisions with approvable sub-items | v3 |
| AS-7 | "Calendar months" are counted on the UTC date | v4 §13 |
| AS-8 | Expo SecureStore is acceptable for mobile tokens | v4 |
| AS-9 | Retention values in the specification are placeholders until legal review | v4 |
| AS-10 | A request can expire during the recipient's deletion recovery period without a refund | v4.1 |
| AS-11 | The added share locks have acceptable overhead at MVP scale (to be load-tested) | v4.1; v4.2 |
| AS-12 | Reopen requests have a 14-day TTL (configurable) | v4.1 |
| AS-13 | The `User` row isn't written on hot paths | v4.2 |
| AS-14 | Message retention stays as documented; no deletion is introduced | v4.2 |
| AS-15 | Refunds complete asynchronously within seconds; the obligation is atomic and durable | v4.3 |
| AS-16 | Request refunds are full per debit row | v4.3 |
| AS-17 | Residual key copies in backups and WAL are bounded by KEK destruction after the backup and WAL retention period | v4.4; v4.5 |
| AS-18 | `transaction_timeout` is used only as an optional backstop (PostgreSQL 17+) | v4.4 |
| AS-19 | Monthly partitioning of AuditLog and AccountSecurityEvent is acceptable | v4.4 |
| AS-20 | Monthly KEK rotation with re-wrapping is operationally acceptable | v4.5 |
| AS-21 | Log IDs are UUIDv7 values generated by the database | v4.5 |
| AS-22 | *(Revised by DR-2026-11-19-R-1.)* Proposed value-list options (gender, marital status and the neutral lists in `apps/profiles/reference.py` `PROPOSED`) are seeded **inactive** as admin-managed vocabularies; none is offered until approved and activated. No religion, community or caste value is proposed | G5 Phase 3 (DR-2026-11-19-R-1) |
| AS-23 | Required fields for completion and DRAFT → PENDING_REVIEW: name, DOB, gender, marital status, religion, nationality, country, city, at least one language, employment status (configurable). **APPROVED by the owner** (DR-2026-11-19-O-7); no longer an assumption. Submission is unavailable while a required vocabulary has no active option | G5 Phase 3 (DR-2026-11-19-R-2) |
| AS-24 | Photo limits: 10 MB upload, 40 MP decoded, 200–2048 px stored edge, 6 live photos per profile, output JPEG quality 85 (configurable) | G5 Phase 3 (TR-10) |
| AS-25 | Enumeration-safe invitations (KI-34, ADR-034): an invitation whose number has no eligible account stays PENDING until the owner cancels it (no TTL until OD-05e). An account that registers or verifies its phone after the invitation isn't linked to it; the owner invites again. A decline is shown to the owner because the invitee chose to respond | DR-2026-11-20-C-2 |
| AS-26 | Employment-status options were approved with English labels only; `label_ur` is left for administrators to fill in | DR-2026-11-20-C-1 |

### 5.2 Specification risks (R-1…R-19)

| ID | Risk | Status / mitigation |
|---|---|---|
| R-1 | The existing backend code has never been executed in this environment | Open. Addressed at G2/G3. |
| R-2 | No Git history | Open. Pre-G1 snapshot in `docs/baseline/pre-g1-snapshot/` until G2. |
| R-3 | Current test settings use SQLite | Mitigated in G2: test settings use PostgreSQL and CI tests on PostgreSQL 16 and 18 (TR-13 approved, DR-2026-11-17-G2D-2). The scaffold tests can't run until the G4 migration exists (KI-14). |
| R-4 | JazzCash contract and recurring-payment support unknown | Open (EP decisions) |
| R-5 | No SMS, email or push provider chosen | Open (EP decisions) |
| R-6 | Legal review pending (retention, consent, minors, international users) | Open (OD-005) |
| R-7 | Production rate limits depend on Redis | Open |
| R-8 | Photo signed URLs leave a revocation window of up to 300 seconds | Accepted residual |
| R-9 | Compromise of K_rot or the HMAC fingerprint key weakens protection | Mitigated by secret storage and rotation procedures (doc 06) |
| R-10 | Single EC2 host; RPO/RTO undefined; business data after the last backup is lost on restore; hold cases created after the backup must be re-entered | Open (operational decision) |
| R-11 | Urdu legal and security text needs reviewed translation | Open |
| R-12 | Performance targets not measured | Open |
| R-13 | The 15-second refresh grace adds a small replay window | Accepted trade-off with mitigations (doc 06) |
| R-14 | Functional-domain list was a reconstruction | **Resolved** (OD-01, DR-2026-11-16-5) |
| R-15 | K_rot and a token compromised together force mass revocation of a key version | Accepted; procedure in doc 06 |
| R-16 | Traceability depended on the reconstructed catalogue | **Resolved** (OD-01) |
| R-17 | High-volume security-event writes during an attack | Mitigated by flood control (doc 06) |
| R-18 | Lazy expiry depends on every create path using the shared function | Mitigated by a single service entry point and tests |
| R-19 | Pseudonymous event grouping remains after unlinking | Open (legal review) |

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

Status values follow the three-dimension status model in doc 00 §9 (DCR-12): each requirement carries a **requirement approval status** (for example APPROVED, PROPOSED, POST_MVP) and a separate **implementation status** (NOT_STARTED, PLANNED, BLOCKED, IN_PROGRESS, IMPLEMENTED, TESTED, REVIEWED, ACCEPTED, DEFERRED). The full per-requirement matrix is doc 18.

## 7. Initial requirements traceability matrix

This summary is kept for orientation. The authoritative, per-requirement matrix is doc 18.

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