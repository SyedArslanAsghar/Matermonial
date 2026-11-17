# Matermonial — Testing and Quality Assurance Strategy

**Version:** 1.0  
**Date:** 11 November 2026

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