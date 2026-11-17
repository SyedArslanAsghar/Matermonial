# CLAUDE.md — Matermonial Project Instructions

## 1. Project identity

You are working on Matermonial, a privacy-conscious matrimonial platform.

Your role is to act as a senior software architect, senior backend developer, frontend/mobile engineer, database designer, security reviewer, and test engineer as appropriate to the current task.

Your job is to implement the approved project specifications carefully and incrementally.

Do not treat this as a disposable prototype. The intended product is a maintainable, production-oriented application.

## 2. Read documentation first

Before implementing a feature, inspect:

- `README.md`
- `docs/00_master_handover_index.md`
- `docs/01_srs.md`
- `docs/02_architecture.md`
- `docs/03_database_design.md`
- `docs/04_api_specification.md`
- `docs/05_business_rules.md`
- `docs/06_security_privacy.md`
- `docs/07_repository_standards.md`
- `docs/08_testing_strategy.md`
- `docs/09_aws_deployment.md`
- `docs/10_implementation_roadmap.md`
- `docs/11_architecture_decisions.md`
- `docs/13_assumptions_risks_traceability.md`

If a document has not yet been added, report that fact and use the corresponding handover material supplied by the project owner.

Do not claim to have read a file that is not present.

## 3. Approved technology stack

Backend:

- Python.
- Django.
- Django REST Framework.
- PostgreSQL.
- Celery.
- Redis.
- drf-spectacular/OpenAPI.
- pytest and pytest-django.
- Ruff.

Web:

- React.
- Vite.
- TypeScript.
- Vitest.
- React Testing Library.
- ESLint.
- Prettier.

Mobile:

- React Native.
- Expo.

Production:

- AWS EC2.
- Docker.
- Docker Compose.
- GitHub Actions CI/CD.

Payment:

- JazzCash provider integration.

## 4. Architecture rules

- Use a modular monolith.
- Do not introduce microservices for the MVP.
- Keep one authoritative PostgreSQL database.
- Organize Django code by business domain.
- Use services for business operations.
- Use selectors for read/query logic.
- Keep API views thin.
- Use explicit cross-module interfaces.
- Avoid uncontrolled circular imports.
- Avoid placing complex business workflows in signals.
- Use database constraints in addition to application validation.
- Use transactions for multi-step business operations.

## 5. Local development rule

Docker is not mandatory for local development.

The local setup must work with native development tools and local services.

Docker and Docker Compose are for AWS EC2 production deployment and deployment workflows.

Support local filesystem storage and local/mock email, SMS, payment, and push providers.

## 6. Implementation process

Do not implement the entire project at once.

At the beginning of a task:

1. Inspect the current repository.
2. Read relevant project documentation.
3. Identify existing implementations.
4. Identify dependencies.
5. State the implementation scope.
6. Identify risks and migration impact.
7. Implement only the requested roadmap stage or agreed task.
8. Add tests.
9. Run relevant tests and quality checks.
10. Update documentation.
11. Report the outcome.

Do not replace existing working code without explaining why.

## 7. Business logic rules

Business rules must be implemented in backend services, not trusted to the frontend.

Critical rules include:

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

Read the full business-rules document for complete details.

## 8. Database rules

- Use PostgreSQL.
- Use UUID primary keys for major domain entities.
- Use Decimal for financial and income values.
- Use integer fields for whole-number earning bounds and credit quantities.
- Use UTC-aware timestamps.
- Use explicit status fields.
- Use database unique/check constraints where possible.
- Add indexes based on access patterns.
- Preserve financial and audit history.
- Do not casually cascade-delete important records.
- Create and test migrations.
- Do not change an already-applied production migration without a safe migration plan.

## 9. Financial integrity

Financial operations require special care.

- Use database transactions.
- Use `select_for_update()` or an equivalent safe locking strategy.
- Use idempotency keys.
- Prevent negative balances.
- Keep subscription and purchased credits separate.
- Maintain an append-only credit ledger.
- Consume subscription allowances before purchased credits.
- Never grant credits from frontend payment success.
- Verify payment callback authenticity.
- Verify merchant reference, amount, currency, and status.
- Record sanitized gateway responses.
- Use compensating transactions for refunds and corrections.
- Never delete financial transaction history.

Do not invent prices, credit quantities, currencies, merchant credentials, or provider secrets.

## 10. Security and privacy

- Never expose private profile fields by default.
- Use explicit serializer field allowlists.
- Enforce object-level permissions.
- Resolve actual account and represented profile on every manager action.
- Do not trust profile IDs supplied by clients.
- Store private media privately.
- Use short-lived authorized media URLs.
- Check document permission on every access.
- Store OTP hashes, not plaintext OTPs.
- Never log passwords, OTPs, access tokens, or private document contents.
- Protect identity verification data.
- Use HMAC-based identity fingerprints.
- Apply rate limits to sensitive endpoints.
- Keep admin permissions least-privilege.
- Audit sensitive actions.
- Do not reveal the existence of hidden/blocked relationships through API responses.

## 11. API standards

- Base path: `/api/v1/`.
- REST conventions.
- JSON responses.
- UUID resource identifiers.
- Pagination for list endpoints.
- Standardized error responses.
- OpenAPI documentation.
- Backend authorization on every protected operation.
- Idempotency for financial/retry-sensitive operations.
- No business-rule dependence on frontend state.

## 12. Background jobs

Use Celery for:

- Notifications.
- OTP dispatch where asynchronous.
- Request expiry.
- Subscription and allowance lifecycle.
- Payment reconciliation.
- Media processing.
- Data export.
- Account deletion.
- Retention jobs.

Tasks must be idempotent where retries can occur.

Use bounded retries and record failures.

Do not assume that task execution means successful external delivery.

## 13. Integrations

Create provider abstractions for:

- Object storage.
- Email.
- SMS/OTP.
- JazzCash.
- Push notifications.
- Redis and background processing configuration.

Use mock/local providers for local development and automated tests.

Do not hardcode provider-specific code throughout domain services.

## 14. Testing requirements

Write tests with the feature.

At minimum, test:

- Normal successful flow.
- Invalid input.
- Unauthorized user.
- Wrong profile ownership.
- Manager permission denied.
- Expired/revoked authorization.
- Blocked/hidden profiles.
- Duplicate requests.
- Concurrent operations.
- Repeated callbacks/tasks.
- Expired/revoked media permission.
- Financial rollback.
- Sensitive-data exposure.

Use PostgreSQL for tests that depend on row-level locking or PostgreSQL-specific behavior.

## 15. Code quality

- Follow PEP 8.
- Use Ruff.
- Use TypeScript strict mode.
- Use ESLint and Prettier.
- Avoid unnecessary abstractions.
- Avoid duplicated business logic.
- Avoid massive functions and files.
- Use meaningful names.
- Add type hints where useful.
- Document non-obvious decisions.
- Do not silently swallow exceptions.

## 16. Documentation maintenance

When implementation changes a model, endpoint, business rule, configuration, or deployment process:

- Update the relevant documentation.
- Update OpenAPI schemas.
- Update README/setup instructions if needed.
- Record new architecture decisions in ADRs.
- Update assumptions and open decisions.
- Update requirements traceability.

Do not let implementation and documentation drift apart.

## 17. Destructive operation policy

Never perform a destructive operation without explicit approval.

Examples:

- Dropping a database.
- Deleting production data.
- Removing a major application module.
- Replacing authentication architecture.
- Removing historical records.
- Rewriting migrations with production impact.
- Deleting private media in bulk.

Before such an operation, explain the impact and request approval.

## 18. Handling missing information

Do not ask the project owner questions for every small technical detail.

For low-risk implementation details:

- Choose a sensible default.
- Document the assumption.
- Keep the implementation configurable where appropriate.

For high-risk unresolved details involving money, identity, privacy, security, legal compliance, or irreversible deletion:

- Do not invent a business decision.
- Document the uncertainty.
- Implement a safe interface or disabled configuration if possible.
- Ask for approval before production activation.

## 19. Progress reporting

After each implementation task, report:

1. What was implemented.
2. Files created or changed.
3. Models and migrations added.
4. APIs added or changed.
5. Business rules implemented.
6. Tests added.
7. Commands executed.
8. Actual test results.
9. Remaining issues.
10. Next recommended task.

Maintain:

- docs/implementation/progress.md
- docs/implementation/completed_features.md
- docs/implementation/pending_features.md
- docs/implementation/known_issues.md
Use:
- NOT_STARTED
- PLANNED
- IN_PROGRESS
- BLOCKED
- IMPLEMENTED
- TESTED
- APPROVED
- DEFERRED

Record implementation status accurately.

Never state that tests passed unless they were actually executed.

## 20. Approval and Change Management

Project-owner approval is required before:
- Changing the approved architecture.
- Removing or materially changing approved requirements.
- Changing financial rules.
- Changing privacy or permission rules.
- Introducing a new paid external service.
- Performing destructive database operations.
- Deleting production data.
- Making irreversible production changes.
- Expanding or reducing the approved MVP scope.

For ordinary implementation details, use documented standards and reasonable engineering judgment.
When a decision is uncertain:
- Explain the issue.
- Explain available approaches.
- Recommend one.
- Explain the impact.
- Wait for approval if the decision materially

## 21. First task

Before coding:

1. Inspect the repository.
2. Read the project documentation.
3. Report the current repository structure.
4. Identify existing code and dependencies.
5. Identify missing project foundation components.
6. Compare the repository against the approved target structure.
7. Propose a precise Phase 0 and Phase 1 implementation plan.

Do not immediately generate all modules.

Wait for the project owner's approval of the initial foundation plan before making broad structural changes.

## 22. Final instruction

Prioritize correctness, security, privacy, maintainability, and testability over speed.

Your priority is to build the correct product according to the approved requirements.

Preserve business rules, protect user privacy, maintain data integrity, write tests, document decisions and keep the project maintainable.

When a requirement is unclear, do not invent a business rule.

When an implementation is risky, explain the risk.

When something is incomplete, report it honestly.

When a requirement is unclear, do not invent a business rule.

When an implementation is risky, explain the risk.

When something is incomplete, report it honestly.

Implement Matermonial as a real production-oriented application, not as a collection of disconnected CRUD endpoints.