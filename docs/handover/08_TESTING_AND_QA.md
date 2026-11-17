# Matermonial — Testing and Quality Assurance Strategy

**Version:** 1.0 (G1 revision 2026-11-16)  
**Date:** 11 November 2026  
**Document status:** APPROVED_WITH_OPEN_ITEMS (project owner, 2026-11-17, DR-2026-11-17-A; record in doc 20 §5). **Open items:** PROPOSED TRs: TR-22. Listed items keep their own status (doc 19); this document status doesn't approve them. TR-13 approved 2026-11-17 (DR-2026-11-17-G2D-2).  
**Applied corrections:** DCR-10, DCR-66, DCR-80, DCR-88 (doc 20). Test catalogue and harness rules: **§14**.

## 1. Testing objectives

Testing must verify business correctness, authorization, privacy, financial integrity, integration reliability, and production readiness.

A feature is not complete because its endpoint returns HTTP 200.

## 2. Testing layers

### 2.1 Unit tests

Test:

- Model validation.
- Utility functions.
- Eligibility calculations.
- Matching criteria.
- Credit calculations.
- Status-transition rules.
- Permission evaluation.
- Date and expiry calculations.

### 2.2 Service tests

Test complete domain operations:

- Account registration.
- OTP verification.
- Profile activation.
- Manager authorization.
- Request creation and acceptance.
- Credit deduction.
- Connection creation.
- Document sharing.
- Subscription activation.
- Export generation.
- Deletion processing.

### 2.3 API tests

Test:

- Authentication.
- Permissions.
- Request validation.
- Response structure.
- Pagination.
- Error codes.
- Object-level authorization.
- Rate limits where practical.
- File upload behavior.

### 2.4 Integration tests

Test:

- PostgreSQL transactions.
- Redis/Celery.
- Email provider adapter.
- SMS provider adapter.
- Payment provider adapter.
- Object storage adapter.
- Push notification adapter.

Use mocks or sandbox providers in tests. Do not make tests depend on live payment or SMS credentials.

### 2.5 End-to-end tests

Test complete user journeys across the backend and frontend.

Mobile critical journeys should also be tested on supported devices/emulators.

## 3. Backend test stack

Use:

- pytest.
- pytest-django.
- Django test utilities.
- DRF API test client.
- Factories/fixtures.
- Mocking utilities.
- PostgreSQL test database.

Use Ruff for linting and formatting.

## 4. Frontend test stack

Use:

- Vitest.
- React Testing Library.
- ESLint.
- Prettier.

Test rendering, interactions, form validation, loading states, errors, and authorization-aware navigation.

## 5. Mobile testing

Test:

- Authentication and token expiry.
- Secure token storage.
- API error handling.
- Deep-link authorization.
- Push token registration.
- RTL layout.
- Network interruption.
- Upload/download handling.

## 6. Critical business test scenarios

### Accounts

- Duplicate phone registration is rejected.
- Phone normalization works.
- OTP expires correctly.
- OTP attempt limits are enforced.
- Inactive/deactivated accounts cannot perform protected actions.
- Login history is recorded.

### Profiles

- One account cannot create multiple personal profiles.
- Age is calculated without exposing DOB.
- Inactive profiles do not appear in search.
- Verified fields cannot be modified without the approved process.
- Education/profession editing remains permitted.

### Family management

- Invitation requires owner action.
- Manager must accept.
- Manager cannot self-authorize.
- Paused manager loses access.
- Expired manager loses access.
- Revoked manager loses access.
- Manager without a specific permission cannot perform that action.
- Sensitive manager actions create audit records.
- Actual manager and represented profile are recorded.

### Matching and privacy

- Hidden profiles are excluded in the correct direction.
- Blocked profiles are excluded.
- Suspended profiles are excluded.
- Optional preferences do not automatically disqualify.
- Private notes are not visible to other accounts.
- Search impressions do not consume view credits.

### Interests and requests

- Interest creation checks eligibility.
- Decline creates directional cooldown.
- Reverse-direction interest is not incorrectly blocked.
- Formal request credit is deducted exactly once.
- Duplicate active requests are prevented in both directions.
- Request expiry is calculated correctly.
- Withdrawn requests do not create cooldown by default.
- Expired and declined requests create the correct cooldown.

### Connections

- Acceptance creates exactly one connection.
- Concurrent acceptance does not create duplicates.
- Non-recipient cannot accept.
- Paused connections cannot send messages.
- Closed connections cannot send messages.
- Reopening requires mutual confirmation.

### Messaging

- Non-participants cannot read messages.
- Managers require communication permission.
- Blocked parties cannot send messages.
- Attachments are validated.
- Read receipts are unique.
- Document access is denied after expiry or revocation.

### Credits and payments

- Subscription allowances are consumed first.
- Purchased credits remain separate.
- Monthly allowances expire at billing-period end.
- Purchased credits do not expire while unused.
- Concurrent deductions cannot create negative balances.
- Duplicate payment callbacks do not grant duplicate credits.
- Invalid callback signatures are rejected.
- Amount and currency mismatch is rejected.
- Refund creates a compensating transaction.
- Manager actions are charged to the owner's account.

### Notifications

- Outbox event is created in the same transaction.
- Failed delivery is retried.
- Duplicate task execution does not duplicate the business event.
- Provider responses are sanitized.
- Essential security notifications are not disabled.
- SMS/push payloads do not contain private information.

### Moderation

- Reporters cannot view other users' reports.
- Reports do not automatically suspend users.
- Evidence is private.
- Conflicted moderators cannot review a case.
- Temporary restrictions expire.
- Appeals preserve original actions and history.

### Export and deletion

- Export requires identity confirmation.
- Export excludes unauthorized data.
- Export link expires.
- Expired files cannot be downloaded.
- Deletion recovery works.
- Repeated deletion tasks are safe.
- Legal holds prevent prohibited deletion.
- Deleting a manager does not delete other profiles.
- Other participants' legitimate message history is handled correctly.

## 7. Concurrency testing

Concurrency tests are mandatory for:

- Credit deductions.
- Request creation.
- Request acceptance.
- Connection creation.
- Payment callback processing.
- Subscription allowance issuance.
- Export request processing.
- Account deletion steps.

Use PostgreSQL for tests that depend on row locking. SQLite is not an adequate substitute for validating PostgreSQL locking behavior.

> **G1 (DCR-66, DCR-80):** concurrency tests follow the harness rules in §14.1 and doc 12 §8 [TR-13, APPROVED 2026-11-17, DR-2026-11-17-G2D-2].

## 8. Security testing

Include tests for:

- Broken object-level authorization.
- Cross-account data leakage.
- Manager permission escalation.
- IDOR.
- OTP brute force.
- Rate-limit bypass.
- Payment callback forgery.
- Private file access.
- Revoked permission access.
- Insecure admin endpoints.
- Sensitive serializer fields.
- Information leakage in errors and logs.

## 9. Performance testing

Measure:

- Search endpoint response time.
- Profile detail queries.
- Conversation pagination.
- Notification list queries.
- Credit ledger queries.
- Admin dashboards.
- Background queue throughput.

Use realistic data volumes and document the test environment.

Do not invent production performance claims without measurement.

## 10. Test data and fixtures

Use factories for:

- Users.
- Profiles.
- Managers and authorizations.
- Verification records.
- Requests.
- Connections.
- Conversations.
- Credit wallets.
- Subscriptions.
- Payments.

Avoid fixtures containing real personal data.

## 11. CI quality gates

The CI pipeline should run:

1. Dependency installation.
2. Formatting/lint checks.
3. Static checks.
4. Backend unit tests.
5. Backend integration tests.
6. Frontend lint.
7. Frontend tests.
8. Mobile checks where configured.
9. Migration checks.
10. OpenAPI schema generation/validation.
11. Build verification.

Do not deploy when mandatory checks fail.

## 12. Release criteria

A release candidate must:

- Pass mandatory automated tests.
- Have no unresolved critical security findings.
- Have migrations reviewed.
- Have API documentation updated.
- Have environment configuration verified.
- Have backup/rollback procedures documented.
- Have critical user journeys manually verified.
- Have known limitations recorded.

## 13. Bug severity

Recommended classifications:

- Critical: data exposure, financial corruption, authentication bypass, destructive data loss.
- High: major user journey blocked or incorrect permissions.
- Medium: significant feature malfunction with workaround.
- Low: minor UI or non-critical behavior.

Critical and high defects must be resolved before production release unless a formally authorized exception is recorded.

## 14. Test reporting

For every implementation stage, report:

- Tests added.
- Commands executed.
- Number passed.
- Number failed.
- Skipped tests and reasons.
- Known limitations.
- Relevant migration and security impact.

Claude Code must never claim that a test was run or passed unless the command actually executed successfully.

## 14. Reconciled test catalogue and harness (G1)

**Status:** every test ID below is a **specification**. None has been written or executed. A test may be reported as passed only after it has actually run (`CLAUDE.md` CC-R59).

### 14.1 PostgreSQL concurrency harness (DCR-80) [TR-13, APPROVED, DR-2026-11-17-G2D-2]

- Every T-CONC and T-LOCK test uses **pytest-django `@pytest.mark.django_db(transaction=True)`** (Django `TransactionTestCase` semantics: real COMMITs, tables flushed between tests).
- Each thread uses **its own connection** from `django.db.connections` and closes it in `finally`. No test runs inside the `TestCase` wrapping `atomic` block.
- Barriers are PostgreSQL advisory locks taken by the test harness. `lock_timeout` is set per connection.
- Every test asserts on **committed** state read through a fresh connection.
- **T-HARNESS-001:** a deliberately uncommitted write must not be visible to the checking connection, which proves real separation.
- **CI runs the PostgreSQL suites on PostgreSQL 16 and 18** (DCR-88), covering both UUIDv7 code paths. SQLite is not used for these suites.

### 14.2 What the lock tracker can't prove (DCR-66) [TR-22]

The `LOCK_PLAN` tracker sees only explicit locks taken through the project's lock helpers. It can't detect implicit foreign-key checks, row locks from plain UPDATE/DELETE outside the helpers, unique-index insertion waits, trigger locks or raw SQL. Those are covered by design (doc 12 §5.5), by a lint rule on raw SQL in service modules, by the T-CONC suite, and in production by `log_lock_waits=on`, a deadlock alert and a retry-rate metric.

### 14.3 Test suites defined by the baseline

| Suite | IDs | Covers | Baseline source |
|---|---|---|---|
| T-AUTH | 001–042 | Login, web session linkage, refresh rotation, revocation, abuse | v3 §8.5 (A4) |
| T-ACT | 001–018 | Acting-profile algorithm and cross-resource access | v3 §9 (A4) |
| T-SEC | 001–020 | Security events; log anonymisation; backup restore and shred re-application | v4 §10.5; v4.4 §1; v4.5 §2.5 |
| T-INT | 001–030 | Interest transitions, conversion, expiry, freeze vs close | v3 §5; v4.1 C16 |
| T-REQ | 030–051 | Cancellation triggers, refunds, refund integrity constraints | v4.1 C11; v4.2 C20; v4.3 §5; v4.4 §3 |
| T-CON | 040–097 | Connection close/complete, reopen checks, pause constraint and behaviour, closed-history effects | v4.1 C12–C14; v4.2 C19, C22; v4.5 §6 |
| T-MAT | 010–026 | View billing, GET revalidation, snapshot and deadline | v3 §10; v4 §8; v4.4 §5 |
| T-DEL | 001–012 | Deletion recovery, late refunds, wallet disposition | v4 §10.6; v4.4 §4; v4.5 §4 |
| T-LOCK | 001–004 | Lock order, deadlock retry, tracker coverage | v4 §12; v4.1 C15 |
| T-CONC | 001–061 | PostgreSQL concurrency scenarios (auth vs account state, block/refund, profile status vs messaging and views, refund fan-out, view billing, retry behaviour, GET consistency) | v4.3 §6.2; v4.5 §1, §3 |
| T-HARNESS | 001 | Harness separation | v4.5 §6 |
| T-OUT | 001–023 | Outbox privacy, redaction, financial obligations, `DEAD_UNDECRYPTABLE` lifecycle | v4.6 §1; v4.6-F1; v4.6-F2; v4.6-F3 |
| T-UUID | 001–010 | UUIDv7 generation, `uuid_v7_lower`, partition routing | v4.6 §4 |
| T-NOT | 001–031 | Account standing × notification category | v4.6 §5 |
| T-LOG | 001–010 | Partitioned logs, hold table, maintenance log | v4.5 §5.4 |
| T-REG | 001–056 | Compliance registry, maintenance protocol, Stream R/M failure injection, restore | v4.6 §3; v4.6-F; v4.6-F1; v4.6-F2; v4.6-F3 |

The exact scenario and pass condition for each ID are in the cited baseline section (`docs/baseline/v4.6-F3/`). When a test is implemented, record its ID, file and result in doc 18.
