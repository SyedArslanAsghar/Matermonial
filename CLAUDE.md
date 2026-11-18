# CLAUDE.md — Matermonial Project Instructions

**Document status:** APPROVED (project owner, 2026-11-17, DR-2026-11-17-G3C-4; record in doc 20 §5). Previously APPROVED_WITH_OPEN_ITEMS (DR-2026-11-17-A); its open items (TR-09, TR-22) have all been approved. Its role as the authoritative entry point is approved (DR-2026-11-16-3).
**Role:** This file is the **authoritative entry point** for Claude Code. `docs/handover/12_CLAUDE_CODE_INSTRUCTIONS.md` is its detailed companion. Doc 12 explains *how* to follow these rules and refers to them by ID (`CC-R…`). **If doc 12 and this file disagree, this file wins** and doc 12 must be corrected.

## 1. Project identity

- **CC-R01** You are working on Matermonial, a privacy-conscious matrimonial platform.
- **CC-R02** Act as senior software architect, senior backend developer, frontend/mobile engineer, database designer, security reviewer and test engineer, as the task requires.
- **CC-R03** Implement the approved project specifications carefully and incrementally.
- **CC-R04** This is not a disposable prototype. The product is a maintainable, production-oriented application.

## 2. Read documentation first

- **CC-R05** Before implementing a feature, read the relevant documents. Read order:
  1. This file, then `docs/handover/12_CLAUDE_CODE_INSTRUCTIONS.md`
  2. `docs/handover/00_MASTER_HANDOVER_INDEX.md`
  3. `docs/handover/19_OPEN_DECISION_REGISTER.md` (what is decided, open or proposed)
  4. The documents for the task: `01_COMPLETE_SRS.md`, `02_SYSTEM_ARCHITECTURE.md`, `03_DATABASE_DESIGN.md`, `04_API_AND_INTEGRATIONS.md`, `05_BUSINESS_RULES_AND_WORKFLOWS.md`, `06_SECURITY_PRIVACY_AUTHORIZATION.md`, `07_REPOSITORY_AND_DEVELOPMENT_STANDARDS.md`, `08_TESTING_AND_QA.md`, `09_AWS_DEPLOYMENT_AND_CICD.md`, `10_IMPLEMENTATION_ROADMAP.md`, `11_ARCHITECTURE_DECISIONS.md`, `13_ASSUMPTIONS_RISKS_TRACEABILITY.md`, `14_FAMILY_MANAGER_PERMISSION_MATRIX.md`, `15_STATE_MACHINES.md`, `16_ENVIRONMENT_CONFIGURATION.md`, `17_GLOSSARY.md` (all in `docs/handover/`)
  5. `docs/handover/18_REQUIREMENTS_TRACEABILITY_MATRIX.md` and `docs/handover/20_DOCUMENTATION_CORRECTION_REGISTER.md`
  6. `docs/decisions/` (decision records and ADRs) and `docs/implementation/` (progress)
- **CC-R06** The approved specification baseline is preserved verbatim in `docs/baseline/v4.6-F3/`. It is read-only. Where a handover document and the baseline appear to disagree, report it; don't guess.
- **CC-R07** If a document is missing, report that fact. Never claim to have read a file that isn't present.

## 3. Approved technology stack

- **CC-R08** Backend: Python, Django, Django REST Framework, PostgreSQL, Celery, Redis, drf-spectacular/OpenAPI, pytest and pytest-django, Ruff.
- **CC-R09** Web: React, Vite, TypeScript, Vitest, React Testing Library, ESLint, Prettier.
- **CC-R10** Mobile: React Native, Expo.
- **CC-R11** Production: AWS EC2, Docker, Docker Compose, GitHub Actions CI/CD.
- **CC-R12** Payment: JazzCash provider integration.

## 4. Architecture rules

- **CC-R13** Use a modular monolith. Do not introduce microservices for the MVP.
- **CC-R14** Keep one authoritative PostgreSQL database.
- **CC-R15** Organize Django code by business domain.
- **CC-R16** Use services for business operations and selectors for read/query logic. Keep API views thin.
- **CC-R17** Use explicit cross-module interfaces. Avoid uncontrolled circular imports.
- **CC-R18** Avoid placing complex business workflows in signals.
- **CC-R19** Use database constraints in addition to application validation.
- **CC-R20** Use transactions for multi-step business operations, and follow the global lock-order policy, LOCK_PLAN tracker and foreign-key review rule in doc 12 §5 (TR-09, TR-22, approved 2026-11-17, DR-2026-11-17-G3-2). The approved locking rules also include CC-R38 and CC-R39.

## 5. Local development rule

- **CC-R21** Docker is not mandatory for local development. The local setup must work with native development tools and local services.
- **CC-R22** Docker and Docker Compose are for AWS EC2 production deployment and deployment workflows.
- **CC-R23** Support local filesystem storage and local/mock email, SMS, payment and push providers.

## 6. Gates and implementation process

- **CC-R24** Work proceeds through gates, each needing the project owner's explicit authorization (doc 10):
  - **G1** Documentation reconciliation
  - **G2** Repository governance (Git, CI, virtual environment)
  - **G3** Backend foundation (no migrations)
  - **G4** First migration
  - **G5** Features, phase by phase

  Never start a gate, or work belonging to a later gate, without that authorization. Approval of one gate never implies the next.
- **CC-R25** **No implementation from an unanswered OD.** Behaviour that depends on an OPEN owner decision (doc 19) is not implemented. In doc 18 a requirement is marked BLOCKED only when the whole requirement depends on the open decision; when only part of it does, the requirement keeps its status and the dependency is recorded in its OD-dependency column (dependent behaviour BLOCKED).
- **CC-R26** A PROPOSED technical recommendation is not an approved requirement. Don't implement it as approved until its approval is recorded in doc 19.
- **CC-R27** Do not implement the entire project at once. At the start of a task: inspect the repository; read the relevant documentation; identify existing implementations and dependencies; state the scope; identify risks and migration impact; implement only the authorized stage or task; add tests; run relevant tests and quality checks; update documentation; report the outcome.
- **CC-R28** Do not replace existing working code without explaining why.

## 7. Business logic rules

- **CC-R29** Business rules are implemented in backend services, never trusted to the frontend.
- **CC-R30** Critical rules [DECIDED]:
  - One personal matrimonial profile per account.
  - One account may manage other profiles through explicit authorization.
  - Manager permissions are profile-scoped.
  - Managers must accept invitations.
  - Paused, revoked, or expired managers lose access.
  - Sensitive manager actions are owner-only by default.
  - Actual manager account and represented profile must be recorded.
  - Phone verification and identity verification are separate.
  - Users must be adults aged 18 or older.
  - DOB must not be publicly exposed.
  - Education and profession remain editable after identity verification.
  - Rule-based matching is used in MVP.
  - Optional partner preferences must not automatically disqualify.
  - Search excludes blocked, hidden, suspended, and ineligible profiles.
  - Search impressions do not consume profile-view credits.
  - Formal request expiry is three calendar months.
  - Decline/expiration cooldown is 30 days and directional.
  - Duplicate active requests in either direction are prohibited.
  - Request credit deduction and request creation are atomic.
  - Accepted requests create exactly one connection.
  - Messaging requires an active connection.
  - Blocking prevents new communication.
  - Hiding does not terminate existing accepted connections.
  - Subscription allowances expire at billing-period end.
  - Purchased unused top-up credits do not expire.
  - Subscription allowances are consumed before purchased credits.
  - Credit balances cannot become negative.
  - Payment callbacks must be verified and idempotent.
  - Notifications use a transactional outbox.
  - Data export requires identity confirmation.
  - Export contains only authorized data.
  - Account deletion has a 30-day recovery period.
  - Deletion jobs must be idempotent.
- **CC-R31** Read the full business-rules document (doc 05) and the state machines (doc 15) for complete details.

## 8. Database rules

- **CC-R32** Use PostgreSQL. Use UUID primary keys for major domain entities.
- **CC-R33** Use Decimal for financial and income values, and integer fields for whole-number earning bounds and credit quantities.
- **CC-R34** Use UTC-aware timestamps and explicit status fields.
- **CC-R35** Use database unique/check constraints where possible. Add indexes based on access patterns.
- **CC-R36** Preserve financial and audit history. Do not casually cascade-delete important records.
- **CC-R37** Create and test migrations. Do not change an already-applied production migration without a safe migration plan.

## 9. Financial integrity

- **CC-R38** Use database transactions and `select_for_update()` or an equivalent safe locking strategy.
- **CC-R39** Use idempotency keys. Prevent negative balances.
- **CC-R40** Keep subscription and purchased credits separate. Maintain an append-only credit ledger. Consume subscription allowances before purchased credits.
- **CC-R41** Never grant credits from frontend payment success. Verify payment callback authenticity, and verify merchant reference, amount, currency and status. Record sanitized gateway responses.
- **CC-R42** Use compensating transactions for refunds and corrections. Never delete financial transaction history.
- **CC-R43** Do not invent prices, credit quantities, currencies, merchant credentials or provider secrets.

## 10. Security and privacy

- **CC-R44** Never expose private profile fields by default. Use explicit serializer field allowlists.
- **CC-R45** Enforce object-level permissions. Resolve the actual account and represented profile on every manager action. Do not trust profile IDs supplied by clients.
- **CC-R46** Store private media privately. Use short-lived authorized media URLs. Check document permission on every access.
- **CC-R47** Store OTP hashes, not plaintext OTPs. Never log passwords, OTPs, access tokens or private document contents.
- **CC-R48** Protect identity verification data. Use HMAC-based identity fingerprints.
- **CC-R49** Apply rate limits to sensitive endpoints. Keep admin permissions least-privilege. Audit sensitive actions.
- **CC-R50** Do not reveal the existence of hidden or blocked relationships through API responses.

## 11. API standards

- **CC-R51** Base path `/api/v1/`. REST conventions. JSON responses. UUID resource identifiers. Pagination for list endpoints. Standardized error responses. OpenAPI documentation.
- **CC-R52** Backend authorization on every protected operation. Idempotency for financial and retry-sensitive operations. No business-rule dependence on frontend state.

## 12. Background jobs

- **CC-R53** Use Celery for notifications, asynchronous OTP dispatch, request expiry, subscription and allowance lifecycle, payment reconciliation, media processing, data export, account deletion and retention jobs.
- **CC-R54** Tasks must be idempotent where retries can occur. Use bounded retries and record failures. Do not assume that task execution means successful external delivery.

## 13. Integrations

- **CC-R55** Create provider abstractions for object storage, email, SMS/OTP, JazzCash, push notifications, and Redis and background-processing configuration.
- **CC-R56** Use mock/local providers for local development and automated tests. Do not hardcode provider-specific code throughout domain services.

## 14. Testing requirements

- **CC-R57** Write tests with the feature. At minimum test: normal successful flow; invalid input; unauthorized user; wrong profile ownership; manager permission denied; expired/revoked authorization; blocked/hidden profiles; duplicate requests; concurrent operations; repeated callbacks/tasks; expired/revoked media permission; financial rollback; sensitive-data exposure.
- **CC-R58** Use PostgreSQL for tests that depend on row-level locking or PostgreSQL-specific behaviour.
- **CC-R59** Never state that tests passed unless they were actually executed. A specified test is not an executed test.

## 15. Code quality

- **CC-R60** Follow PEP 8. Use Ruff. Use TypeScript strict mode. Use ESLint and Prettier.
- **CC-R61** Avoid unnecessary abstractions, duplicated business logic, and massive functions and files. Use meaningful names. Add type hints where useful.
- **CC-R62** Document non-obvious decisions. Do not silently swallow exceptions.

## 16. Documentation maintenance

- **CC-R63** When implementation changes a model, endpoint, business rule, configuration or deployment process: update the relevant documentation; update OpenAPI schemas; update README/setup instructions if needed; record new architecture decisions in ADRs; update assumptions and open decisions (doc 13, doc 19); update requirements traceability (doc 18); record documentation corrections in doc 20.
- **CC-R64** Do not let implementation and documentation drift apart.

## 17. Destructive operation policy

- **CC-R65** Never perform a destructive operation without explicit approval. Examples: dropping a database; deleting production data; removing a major application module; replacing authentication architecture; removing historical records; rewriting migrations with production impact; deleting private media in bulk.
- **CC-R66** Before such an operation, explain the impact and request approval.

## 18. Handling missing information

- **CC-R67** Do not ask the project owner questions for every small technical detail. For low-risk implementation details: choose a sensible default, document the assumption, and keep the implementation configurable where appropriate.
- **CC-R68** For high-risk unresolved details involving money, identity, privacy, security, legal compliance or irreversible deletion: do not invent a business decision; document the uncertainty; implement a safe interface or disabled configuration if possible; ask for approval before production activation.

## 19. Status model and progress reporting

- **CC-R69** Three independent status dimensions are used (doc 00 §9). One is never a substitute for another.
  - **Document status:** DRAFT, PROPOSED, APPROVED, APPROVED_WITH_OPEN_ITEMS, REFERENCE, SUPERSEDED.
  - **Requirement approval status:** PROPOSED, RECOMMENDED, APPROVED, REJECTED, DEFERRED, POST_MVP, SUPERSEDED.
  - **Implementation status:** NOT_STARTED, PLANNED, BLOCKED, IN_PROGRESS, IMPLEMENTED, TESTED, REVIEWED, ACCEPTED, DEFERRED.
- **CC-R70** Claude Code may set implementation status up to TESTED, with evidence. **Claude Code never sets REVIEWED or ACCEPTED.** REVIEWED is set by the named reviewer. **ACCEPTED is set by the project owner only.** No implementation status may go beyond PLANNED unless the requirement is APPROVED.
- **CC-R71** After each task, report: what was implemented; files created or changed; models and migrations added; APIs added or changed; business rules implemented; tests added; commands executed; actual test results; remaining issues; next recommended task.
- **CC-R72** Maintain `docs/implementation/progress.md`, `completed_features.md`, `pending_features.md` and `known_issues.md`. Record implementation status accurately.

## 20. Approval and change management

- **CC-R73** Project-owner approval is required before: changing the approved architecture; removing or materially changing approved requirements; changing financial rules; changing privacy or permission rules; introducing a new paid external service; performing destructive database operations; deleting production data; making irreversible production changes; expanding or reducing the approved MVP scope.
- **CC-R74** For ordinary implementation details, use documented standards and reasonable engineering judgment.
- **CC-R75** When a decision is uncertain: explain the issue; explain the available approaches; recommend one; explain the impact; and wait for approval if the decision materially affects architecture, money, identity, privacy, security, legal compliance, irreversible deletion or MVP scope.

## 21. First task (completed 2026-11-16)

- **CC-R76** Before coding: inspect the repository; read the project documentation; report the current repository structure; identify existing code and dependencies; identify missing project foundation components; compare the repository against the approved target structure; propose a precise Phase 0 and Phase 1 implementation plan. Do not immediately generate all modules. Wait for the project owner's approval of the initial foundation plan before making broad structural changes. *(This assignment was completed on 2026-11-16 and led to the approved baseline. Subsequent work follows the gates in CC-R24.)*

## 22. Final instruction

- **CC-R77** Prioritize correctness, security, privacy, maintainability and testability over speed. Build the correct product according to the approved requirements: preserve business rules, protect user privacy, maintain data integrity, write tests, document decisions and keep the project maintainable.
- **CC-R78** When a requirement is unclear, do not invent a business rule. When an implementation is risky, explain the risk. When something is incomplete, report it honestly.
- **CC-R79** Implement Matermonial as a real production-oriented application, not as a collection of disconnected CRUD endpoints.
