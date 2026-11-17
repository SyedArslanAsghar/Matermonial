# Matermonial — Implementation Roadmap and Development Backlog

**Version:** 1.0  
**Date:** 11 November 2026

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