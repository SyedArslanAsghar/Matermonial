# Matermonial — Implementation Roadmap and Development Backlog

**Version:** 1.0 (G1 revision 2026-11-16)  
**Date:** 11 November 2026  
**Document status:** APPROVED_WITH_OPEN_ITEMS (project owner, 2026-11-17, DR-2026-11-17-A; record in doc 20 §5). **Open items:** OPEN ODs: OD-02, OD-03, OD-04, OD-05, OD-06, OD-07, OD-08, OD-09, OD-10; PROPOSED TRs: TR-17, TR-21, TR-23, TR-24. Listed items keep their own status (doc 19); this document status doesn't approve them.  
**Applied corrections:** DCR-08, DCR-10, DCR-33 (doc 20)

## 0. Gated roadmap (authoritative sequence) — DCR-08, DCR-33

The project proceeds through five gates. **Each gate needs the project owner's explicit authorization; approving one gate never implies the next** (`CLAUDE.md` CC-R24). This section governs sequence. The phase sections further down (§2–§20) keep their original numbering and remain the task and acceptance backlog; table 0.3 maps them to the gated order.

### 0.1 Gates

| Gate | Activities | Entry | Exit criteria | Prohibited before this gate |
|---|---|---|---|---|
| **G1 Documentation reconciliation** | Apply DCR-01…DCR-99. Create docs 18–20 and ADR-025…032. Populate `docs/implementation/*`. | Baseline approval (DR-2026-11-16-1) and G1 authorization | The G1 exit checklist (§0.5) | Any code, dependency, database, migration or Git change |
| **G2 Repository governance** | `git init`, baseline commit, branch policy, `.gitignore`, virtual environment recreated in `backend/` (stale root `.venv` removed), CI skeleton with PostgreSQL (16 and 18) | G1 exit + owner authorization | CI runs on the baseline | App moves, migrations |
| **G3 Backend foundation** | Layout (`apps/`), settings (including staging and fail-closed validation), error envelope, logging, health checks, provider mocks, storage abstraction, Celery wiring. **No migrations.** | G2 exit + owner authorization | Lint and tests green on PostgreSQL. No migration files. | Domain models |
| **G4 First migration** | `User` (final), `AuthSession` (including `scope` and `key_version_current`), `AuthToken`, `AuditLog`, `AccountSecurityEvent` (extended, append-only), `OutboxEvent`, `IdempotencyRecord`, plus the G4 schema parts of TR-17, TR-21, TR-23 and TR-24 → migration `0001`, tested from an empty database | G3 exit + owner authorization + approval of the G4 TRs (doc 19) | Migration reviewed. Kernel tests pass. | Feature models |
| **G5 Features** | Phases 2–19 (§0.2) | G4 exit + per-phase scope approval | Per-phase definition of done | Behaviour that depends on an unanswered OD sub-item. Frontend work without an approved API contract. |

**G2 status (2026-11-17):** owner-accepted with carried-forward items (DR-2026-11-17-G2A); baseline commit `38f491dea79fb9bb10fd2010b1c2cb8a68d545f9`. The G2 exit criterion "CI runs on the baseline" is **OPEN**. G3 was entered under a narrow owner exception (DR-2026-11-17-G2X). This criterion **must be satisfied before G4 entry**. The criterion itself is unchanged.

**G2 criterion update (2026-11-18):** the owner accepted the successful GitHub Actions run `44294474904` on commit `c5fc346` (the G2 baseline plus the approved G3 implementation; 6/6 jobs) as satisfying "CI runs on the baseline" (DR-2026-11-18-G2C). The exact baseline commit `38f491d` did not run through CI on its own. This meets the G4-entry precondition of DR-2026-11-17-G2X; it does not authorize G4.

**G3 status (2026-11-18):** owner-accepted with an accepted exception and a carried-forward item (DR-2026-11-18-G3A). The G3 exit criterion "tests green on PostgreSQL" is not fully met. The PostgreSQL foundation tests pass; the 3 KI-14 User-model database tests are OPEN and must pass as part of G4. **G4 is NOT AUTHORIZED.**

**G4 status (2026-11-18):** authorized together with G5 (DR-2026-11-18-G4). **IMPLEMENTED; exit criteria met** (2026-11-18): migrations reviewed and validated from empty on PostgreSQL 16 and 18; kernel tests pass (220/220 on Python 3.12 and 3.13 × PostgreSQL 16 and 18; KI-14 resolved). **Owner acceptance pending** (only the owner sets ACCEPTED, CC-R70). G5 already authorized (DR-2026-11-18-G4). Record: `docs/implementation/progress.md`; schema notes: doc 03 §22.17. **ACCEPTED by the owner (DR-2026-11-18-G4A, 2026-11-18).**

### 0.2 G5 phase order

| Phase | Scope |
|---|---|
| 2 | Auth flows + Django Admin MFA |
| 3 | Profiles, preferences, uploads |
| 4 | Family management and ActorContext |
| 5 | Identity verification |
| 6 | Privacy, central eligibility, `UserRestriction` |
| 7 | **Credit ledger and projections** |
| 8 | Search, matching, view billing |
| 9 | Interests and requests |
| 10 | Connections |
| 11 | Messaging and documents |
| 12 | Notification delivery |
| 13 | Subscriptions and payments |
| 14 | Moderation |
| 15 | Export and deletion |
| 16 | Admin operations |
| 17 | Web (each module only after its API contract is approved) |
| 18 | Mobile (each module only after its API contract is approved) |
| 19 | Release |

**G5 Phase 2 status (2026-11-19):** **IMPLEMENTED and TESTED** on `feature/g5-phase2-auth`: auth flows (2a–2d), rate limits (2e-1), admin roles and permissions (2e-2), Django Admin MFA and admin session (2e-3). 347/347 tests pass on Python 3.12 and 3.13 × PostgreSQL 16 and 18. Not pushed. Owner review and acceptance pending (CC-R70). Record: `docs/implementation/progress.md`.

**G5 Phase 3 status (2026-11-19):** **IMPLEMENTED and TESTED** on `feature/g5-phase2-auth` (owner-only endpoints): profile and sections, completion, submit-for-review, partner preferences, and photos through the TR-10 pipeline. 404/404 tests pass on Python 3.12 and 3.13 × PostgreSQL 16 and 18. Open: the sensitive value lists (owner), confirmation of the required set (AS-23), and the items in `known_issues.md` KI-29…KI-32. Owner review and acceptance pending.

**Dependency check:**
- Auth and User are final before 0001 (G4).
- Audit and outbox exist at G4.
- The ledger (7) comes before billing (8) and requests (9).
- Authorization (4) comes before delegated actions.
- Eligibility and restrictions are central from 6.
- Contracts come before frontend work.
- PostgreSQL is used from G2.

### 0.3 Mapping of the backlog sections to the gated order

| Backlog section (original numbering) | Gated position |
|---|---|
| §2 Phase 0 — Repository and project foundation | G2 (repository parts) and G3 |
| §3 Phase 1 — Backend foundation | G3, with the kernel models at G4 |
| §4 Phase 2 — Accounts and authentication | G5 Phase 2 |
| §5 Phase 3 — Profiles and preferences | G5 Phase 3 |
| §6 Phase 4 — Verification | G5 Phase 5 |
| §7 Phase 5 — Family management | G5 Phase 4 |
| §8 Phase 6 — Privacy and media access | G5 Phase 6 |
| §9 Phase 7 — Matching and search | G5 Phase 8 |
| §10 Phase 8 — Interests and requests | G5 Phase 9 |
| §11 Phase 9 — Connections and relationship progress | G5 Phase 10 |
| §12 Phase 10 — Messaging and shared documents | G5 Phase 11 |
| §13 Phase 11 — Subscriptions, credits, and payments | G5 Phase 7 (ledger and projections) and Phase 13 (subscriptions and payments) |
| §14 Phase 12 — Notifications | G5 Phase 12 (outbox kernel at G4) |
| §15 Phase 13 — Moderation and reporting | G5 Phase 14 |
| §16 Phase 14 — Data export and account deletion | G5 Phase 15 |
| §17 Phase 15 — Audit and platform operations | G5 Phase 16 (audit kernel at G4) |
| §18 Phase 16 — Web frontend | G5 Phase 17 |
| §19 Phase 17 — Mobile applications | G5 Phase 18 |
| §20 Phase 18 — Release preparation | G5 Phase 19 |

### 0.4 No implementation from an unanswered OD (DCR-33)

When a phase reaches an OPEN owner decision (doc 19), the parts that don't depend on it proceed. **The dependent behaviour isn't implemented** until the decision is recorded. In doc 18 the requirement's implementation status is BLOCKED only when the whole requirement depends on the open decision; a partially dependent requirement keeps its status and the dependency is recorded in its OD-dependency column (`CLAUDE.md` CC-R25). A PROPOSED technical recommendation isn't treated as an approved requirement until its approval is recorded in doc 19.

### 0.5 G1 exit checklist

| # | Exit criterion | Evidence |
|---|---|---|
| 1 | DCR-01…DCR-99 applied, each recorded in doc 20 as APPLIED (or BLOCKED with a reason) | Doc 20 |
| 2 | OD-01 answered. The approved catalogue is in doc 01, and every FR maps to a domain and module in doc 18. | Doc 19, doc 18 |
| 3 | OD-02…OD-10 recorded in doc 19 as OPEN with their sub-items | Doc 19 |
| 4 | Every TR and REC-BIZ item labelled PROPOSED or RECOMMENDED. No unapproved item shown as APPROVED. | Doc 19, doc 18 |
| 5 | Every requirement in doc 18 has a requirement approval status and an implementation status | Doc 18 |
| 6 | "No implementation from an unanswered OD" rule recorded in docs 10 and 13 and in `CLAUDE.md` | Documents |
| 7 | Every document carries a document-status header (DCR-10) | Headers |
| 8 | `CLAUDE.md` and doc 12 are consistent: doc 12 refers to rule IDs, and nothing contradicts | Cross-check table in doc 20 |
| 9 | Contradictions C-1…C-78 each marked aligned or linked to an OPEN OD | Doc 20 |
| 10 | ADR-025…032 drafted with status PROPOSED and indexed in doc 11 | `docs/decisions/` |
| 11 | `docs/implementation/*` populated. Every implementation status is NOT_STARTED, PLANNED or BLOCKED. | Files |
| 12 | The owner approves the G1 result (document statuses set by the owner) | Doc 20 approval record |

**G1 exit record (2026-11-17):** all 12 criteria are met. Items 1–11 were verified in the G1 audit and correction pass (doc 20 §8). Item 12 is met by the project owner's acceptance, DR-2026-11-17-A, which also assigned the final document statuses (doc 20 §5). **G1 is COMPLETED. G2–G5 are NOT AUTHORIZED** and each needs separate, explicit owner authorization.

## 1. Roadmap principles

The project should be implemented incrementally.

Each phase must produce working, tested functionality. Do not build the complete database and all endpoints first and postpone business logic and testing until the end.

The roadmap is dependency-based rather than date-based. Actual sprint duration should be determined after repository inspection and team capacity assessment.

## 2. Phase 0 — Repository and project foundation

Tasks:

- Create monorepo.
- Create backend, frontend, mobile, docs, scripts, and infrastructure directories.
- Initialize Git.
- Add `.gitignore`.
- Add root README.
- Add `CLAUDE.md`.
- Configure development standards.
- Add CI workflow skeleton.
- Document local setup.

Acceptance:

- Repository structure is established.
- Developers can follow documented setup instructions.
- CI can install and validate initial projects.

## 3. Phase 1 — Backend foundation

Tasks:

- Initialize Django.
- Configure DRF.
- Configure environment-based settings.
- Configure PostgreSQL.
- Configure custom User model before the first production migration.
- Configure logging.
- Configure API versioning.
- Configure OpenAPI.
- Configure common error responses.
- Configure test framework.
- Configure storage abstraction.
- Configure feature flags.

Acceptance:

- Django starts locally without Docker.
- PostgreSQL migrations work.
- OpenAPI schema generates.
- Test and local settings work.
- No secrets are committed.

## 4. Phase 2 — Accounts and authentication

Tasks:

- Custom user model.
- User manager.
- Registration.
- Phone normalization.
- OTP service.
- OTP provider abstraction.
- Login/logout.
- Password reset.
- Session/token lifecycle.
- Login history.
- Security events.
- Account deactivation.

Acceptance:

- Account registration and verification work.
- OTP expiry and rate limits work.
- Authentication tests pass.
- Security history is recorded.

## 5. Phase 3 — Profiles and preferences

Tasks:

- MatrimonialProfile.
- Basic information.
- Location.
- Family details.
- Education.
- Profession.
- Lifestyle.
- Languages.
- Photos.
- Profile completion.
- Profile visibility.
- PartnerPreference.
- Multi-value preferences.
- Validation.

Acceptance:

- User can create and edit their own profile.
- Account cannot own duplicate personal profiles.
- DOB remains private.
- Income uses Decimal.
- Preference nullable Boolean semantics work.
- Education and profession remain editable.

## 6. Phase 4 — Verification

Tasks:

- Phone verification integration.
- Identity verification submission.
- Private document storage.
- Review workflow.
- Rejection/resubmission.
- HMAC duplicate detection.
- Reviewer permissions.
- Verification history.
- Profile activation integration.

Acceptance:

- Verification state transitions work.
- Documents are private.
- Decisions are audited.
- Rejected users can resubmit according to policy.
- Identity approval activates visibility only when other requirements are satisfied.

## 7. Phase 5 — Family management

Tasks:

- Authorization model.
- Invitation and acceptance.
- Permission catalog.
- Permission groups.
- Individual permission assignment.
- Pause/resume/revoke.
- Expiry processing.
- Manager action logs.
- Profile access history.
- Sensitive-action verification.

Acceptance:

- Owner controls authorization.
- Manager cannot self-authorize.
- Permission checks are enforced by services and APIs.
- Revoked/paused managers lose access.
- Actual actor is recorded.

## 8. Phase 6 — Privacy and media access

Tasks:

- Profile privacy settings.
- Blocking.
- Hide My Profile From.
- Hidden-profile management.
- Photo access requests.
- Photo permissions.
- Visitor history.
- Private browsing.
- Secure media URLs.
- Access history.

Acceptance:

- Blocking and hiding are distinct.
- Search and requests respect privacy rules.
- Existing connections survive hiding as specified.
- Revoked media permissions are denied.
- Private visitor identity is not disclosed.

## 9. Phase 7 — Matching and search

Tasks:

- Search selectors.
- Eligibility filtering.
- Location filters.
- Religion/community filters.
- Education/profession filters.
- Partner-preference matching.
- Recommendation ranking.
- Favorites.
- Private notes.
- Profile view tracking.
- Profile-view billing.

Acceptance:

- Search excludes restricted profiles.
- Optional preferences are handled correctly.
- Search impressions do not consume credits.
- Detail-view billing follows account-target 24-hour rules.

## 10. Phase 8 — Interests and requests

Tasks:

- Interest model and workflow.
- Show Interest Back.
- Formal request creation.
- Request-credit service.
- Request status transitions.
- Directional cooldown.
- Request expiry task.
- Request history.
- Concurrency protection.

Acceptance:

- Interest actions follow the approved workflow.
- Formal request credits are deducted atomically.
- Duplicate active requests are blocked in both directions.
- Decline/expiry cooldown is directional and 30 days.
- Withdrawal does not create cooldown by default.
- Request expiry is three calendar months.

## 11. Phase 9 — Connections and relationship progress

Tasks:

- Connection model.
- Unique unordered pair.
- Acceptance integration.
- Connection state transitions.
- Mutual reopening.
- Relationship progress.
- Progress history.
- Shared notes.

Acceptance:

- Request acceptance creates exactly one connection.
- Connection history is preserved.
- Paused/closed states are enforced.
- Progress updates are authorized and audited.

## 12. Phase 10 — Messaging and shared documents

Tasks:

- Conversation.
- Participants.
- Message creation.
- Message history.
- Read receipts.
- Attachment upload.
- Shared documents.
- Document permissions.
- Document access history.
- Manager communication.

Acceptance:

- Only active connection participants can communicate.
- Manager communication is permission-controlled.
- Attachments and documents are private.
- Revoked/expired document access is denied.
- Actual manager identity is preserved in history.

## 13. Phase 11 — Subscriptions, credits, and payments

Tasks:

- Subscription plans.
- Benefits.
- User subscriptions.
- Billing periods.
- Wallets.
- Credit allowances.
- Credit ledger.
- Credit packages.
- Credit purchases.
- Payment transactions.
- JazzCash provider adapter.
- Webhook processing.
- Payment reconciliation.
- Refund handling.

Acceptance:

- Subscription and purchased balances remain separate.
- Subscription allowances expire at billing-period end.
- Purchased credits do not expire while unused.
- Allowances are consumed before purchased credits.
- Payment callbacks are verified and idempotent.
- Concurrent deductions cannot create negative balances.

## 14. Phase 12 — Notifications

Tasks:

- Notification types.
- Templates.
- Preferences.
- Notification records.
- Delivery records.
- Delivery attempts.
- Push devices.
- Transactional outbox.
- Celery tasks.
- Retry policy.
- English and Urdu templates.

Acceptance:

- Notifications are created after successful business transactions.
- Delivery retries work.
- Duplicate processing is safe.
- Sensitive content is not exposed in SMS/push.
- Delivery status is recorded accurately.

## 15. Phase 13 — Moderation and reporting

Tasks:

- Reports.
- Evidence.
- Cases.
- Case grouping.
- Moderator assignment.
- Moderation actions.
- Restrictions.
- Content review.
- Appeals.
- Moderation policies.
- Conflict-of-interest checks.

Acceptance:

- Reports do not automatically suspend users.
- Evidence is private.
- Actions are auditable.
- Restrictions apply across modules.
- Appeals are recorded.
- Critical permanent actions use elevated approval.

## 16. Phase 14 — Data export and account deletion

Tasks:

- Export request.
- Identity confirmation.
- Export sections.
- ZIP generation.
- Temporary download.
- Download history.
- Deletion request.
- 30-day recovery.
- Deletion steps.
- Retention policies.
- Legal/security holds.
- Anonymization and media cleanup.

Acceptance:

- Export contains only authorized data.
- Download links expire.
- Deletion can be cancelled during recovery.
- Processing is idempotent.
- Legal holds are respected.
- Other owners' profiles are not deleted when a manager account is deleted.

## 17. Phase 15 — Audit and platform operations

Tasks:

- Central AuditLog.
- Admin roles.
- Admin permissions.
- Admin role assignments.
- Admin access history.
- Sensitive action approval.
- System configuration.
- Configuration history.
- Feature flags.
- Feature-flag history.
- Support cases.
- Support messages.
- Maintenance windows.

Acceptance:

- Admin access is permission-controlled.
- Sensitive changes are audited.
- Support internal notes remain private.
- Feature-flag changes are traceable.

## 18. Phase 16 — Web frontend

Implement the web frontend feature-by-feature against completed APIs.

Suggested order:

1. Authentication.
2. Profile onboarding.
3. Profile management.
4. Verification.
5. Family management.
6. Search and matching.
7. Interests and requests.
8. Connections.
9. Messaging.
10. Privacy.
11. Subscription and credits.
12. Notifications.
13. Account settings.
14. Data export and deletion.
15. Admin workflows as separately scoped.

Acceptance:

- UI follows API contracts.
- Permission-aware navigation is implemented.
- Backend remains authoritative.
- English and Urdu/RTL work.
- Responsive layouts and error states are tested.

## 19. Phase 17 — Mobile applications

Implement the same core journeys using React Native and Expo.

Prioritize:

- Registration and login.
- Profile onboarding.
- Profile discovery.
- Interests and requests.
- Connections and messaging.
- Push notifications.
- Privacy controls.
- Subscription/credit views.
- Account settings.

Acceptance:

- Secure credential storage.
- Consistent backend permissions.
- Push registration.
- Deep-link access checks.
- RTL support.
- Tested Android/iOS builds.

## 20. Phase 18 — Release preparation

Tasks:

- Full regression testing.
- Security review.
- Performance testing.
- Payment sandbox testing.
- Backup/restore test.
- Deployment rehearsal.
- Production monitoring.
- User support procedures.
- Admin training.
- Operational runbooks.

Acceptance:

- Critical journeys pass.
- No unresolved critical security findings.
- Deployment and rollback work.
- Backups can be restored.
- Monitoring is active.
- Production secrets are configured.

## 21. Suggested milestone deliverables

| Milestone | Deliverable |
|---|---|
| M1 | Repository and backend foundation |
| M2 | Secure accounts and profiles |
| M3 | Verification and family management |
| M4 | Privacy, search, and matching |
| M5 | Requests and connections |
| M6 | Messaging and documents |
| M7 | Subscriptions, credits, and payments |
| M8 | Notifications and moderation |
| M9 | Data export, deletion, and admin operations |
| M10 | Web/mobile integration and release |

## 22. Roadmap management rules

- Do not skip prerequisite security and authorization work.
- Do not begin frontend workflows against unstable API contracts without documenting assumptions.
- Do not activate real payment collection before gateway verification.
- Do not deploy real identity documents until private storage and access controls are verified.
- Keep post-MVP features out of the initial delivery unless separately approved.
- Update this roadmap when actual progress or dependencies change.