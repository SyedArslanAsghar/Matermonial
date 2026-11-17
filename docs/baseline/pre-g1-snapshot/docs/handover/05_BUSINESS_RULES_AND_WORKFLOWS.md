# Matermonial — Business Rules and End-to-End Workflows

**Version:** 1.0  
**Date:** 11 November 2026

## 1. Account and profile rules

1. One account owns at most one personal matrimonial profile.
2. One account may manage multiple other profiles through separate authorizations.
3. Account ownership and profile-management authority are separate.
4. Only adults aged 18 or older may participate in matrimonial activities.
5. Phone verification is separate from identity verification.
6. Unverified users may browse limited information but cannot perform protected matrimonial actions.
7. Identity approval does not bypass profile completion, moderation, account status, or other activation checks.
8. Full date of birth is private; public age is calculated.
9. Identity-verified fields cannot be freely changed.
10. Education and professional information remain editable subject to normal controls.
11. Profile visibility, photo visibility, and document access are separate controls.

## 2. Family-manager rules

1. The owner initiates manager authorization.
2. The invited account must accept.
3. An account cannot authorize itself as manager of another person's profile without the owner's invitation.
4. Authorization is scoped to one profile.
5. Permission groups are configurable templates.
6. Individual permissions may be granted or revoked.
7. Sensitive permissions are owner-only by default.
8. Authorization expiry is optional; default is no expiry.
9. The owner may pause, resume, or revoke authorization.
10. Paused, expired, revoked, or rejected authorizations grant no access.
11. Manager actions record both the actual account and represented profile.
12. The manager's personal account is not the billing identity for actions performed on behalf of the owner.
13. A manager cannot transfer profile ownership.
14. Deleting a manager account revokes that manager's authorizations but does not delete other users' profiles.

## 3. Interest rules

1. An eligible profile may express interest in another eligible profile.
2. The recipient may show interest back, send a formal request, or decline.
3. A declined interest is retained in history.
4. A decline creates a 30-day cooldown from the original sender to the original recipient.
5. The cooldown is directional.
6. A cooldown in one direction does not automatically prohibit the reverse direction.
7. The system must check blocking, hidden-profile rules, account restrictions, and profile eligibility before accepting an interest.
8. Duplicate active interests should be prevented according to the defined interest-state model.
9. The formal-request credit rules apply to formal requests, not automatically to every lightweight interest action.

## 4. Formal request rules

1. A formal request has a sender profile and receiver profile.
2. A profile cannot send a request to itself.
3. Only the recipient or an authorized manager may accept or decline.
4. The sender or an authorized manager may withdraw a pending request.
5. Pending requests expire after three calendar months.
6. Active requests between the same two profiles in either direction are mutually exclusive.
7. A decline or expiration creates a 30-day directional cooldown for the original sender.
8. Withdrawal does not create a cooldown by default.
9. Administrative cancellation does not create a cooldown by default.
10. Request creation, credit deduction, and request history are atomic.
11. No automatic credit refund occurs merely because a request expires.
12. All state transitions are preserved.

## 5. Request state machine

```text
              +-----------+
              |  PENDING  |
              +-----------+
                /   |   \
               /    |    \
              v     v     v
         ACCEPTED DECLINED WITHDRAWN
              |
              v
        CONNECTION CREATED

PENDING -- expiry job --> EXPIRED
PENDING -- admin action --> CANCELLED
```

Only permitted transitions may be executed. A transition service must reject invalid or repeated transitions safely.

## 6. Request acceptance workflow

1. Recipient submits acceptance.
2. Backend identifies actual account and represented profile.
3. Backend verifies ownership or active manager authorization.
4. Backend verifies the recipient is the receiver profile.
5. Backend locks the request row.
6. Backend checks that request is still pending and not expired.
7. Backend checks blocking and restrictions.
8. Backend changes request status to accepted.
9. Backend creates one connection for the unordered profile pair.
10. Backend creates request and connection history.
11. Backend creates the conversation/participants as appropriate.
12. Backend creates notification outbox events.
13. Backend commits the transaction.
14. Background processing delivers notifications.

If any required database operation fails, the request must remain unaccepted and no duplicate connection may be created.

## 7. Connection rules

1. An accepted request creates a connection.
2. A connection has two profiles.
3. Profile ordering is normalized for uniqueness.
4. A connection may be active, paused, completed, or closed.
5. Paused connections retain history but do not allow new messages.
6. Closed connections retain history and do not allow new messages.
7. Reopening a closed connection requires mutual confirmation.
8. Completed/engaged connections are not reopened by default.
9. Blocking overrides normal communication access.
10. Every connection state change creates history.

## 8. Relationship progress rules

Progress states:

1. Request Accepted.
2. Initial Communication.
3. Discussion in Progress.
4. Meeting Planned.
5. Meeting Completed.
6. Proposal / Serious Discussion.
7. Engaged.
8. Closed.

Rules:

- Both connected profiles can view shared progress.
- Updates require an active connection and valid authorization.
- The actual account and represented profile are recorded.
- Progress history is append-only.
- Shared notes must not be confused with private notes or internal admin notes.

## 9. Messaging rules

1. One conversation per connection.
2. Exactly two profile participants in MVP.
3. Messaging requires an active connection.
4. Paused or closed connections cannot send new messages.
5. A block prevents new communication.
6. Authorized managers may act through a represented profile where permission permits.
7. Actual sender account is recorded.
8. Message attachments use private storage and validation.
9. Read receipts are enabled by default.
10. Voice/video calls are excluded from MVP.
11. Message deletion must not silently erase the other participant's legitimate history.
12. Message access must be checked on every read/download operation.

## 10. Shared document rules

1. Shared documents are separate from verification documents.
2. The owner controls sharing.
3. A recipient requires an active document-access permission.
4. Permission may expire or be revoked.
5. Access is checked on every download.
6. Manager sharing requires explicit permission and additional security controls.
7. Owner notification is required for manager sharing.
8. Owner approval is the recommended default.
9. Document views and downloads are logged.
10. Previously downloaded copies cannot be remotely recalled.

## 11. Blocking rules

Blocking is unilateral and private.

A block:

- Prevents discovery through search and recommendations.
- Prevents new interests and requests.
- Prevents new communication.
- Disables applicable media and shared-document access.
- Preserves historical records.
- Does not notify the blocked person.

Unblocking restores eligibility only if no other restriction applies.

## 12. Hide My Profile From rules

Hiding is separate from blocking.

A hidden profile:

- Cannot discover the owner's profile through search or recommendations.
- Cannot send new interests or matrimonial requests to the owner.
- Is not notified.
- Does not automatically lose an existing accepted connection.
- Does not automatically lose existing communication access.
- Does not automatically lose existing photo/document permissions.

The owner may unhide the profile later.

## 13. Profile photo access rules

1. Photo access is separate from profile visibility.
2. Owners may grant access for 7 days, 30 days, or manually controlled periods.
3. Owners can revoke access.
4. Access must be revalidated on every request.
5. Manager photo-permission actions require explicit permission and audit.
6. Private media must not have permanent public URLs.
7. Previously downloaded copies cannot be remotely recalled.

## 14. Visitor-history rules

1. Visitor history is a paid Advance/Premium feature.
2. Recommended retention is 90 days, configurable.
3. Private browsing keeps the visitor anonymous in visible visitor history.
4. The owner may remove a visitor from the visible list.
5. Removal does not block the visitor.
6. The visitor may appear again on a later visit.
7. Removal does not erase security or audit records.
8. Managers may view history only when authorized.
9. Owner-only removal/clear is the default.
10. Explicit delegation is required before a manager can remove or clear visitor history.

## 15. Matching rules

1. Rule-based matching is used in MVP.
2. Strict eligibility rules are applied before ranking.
3. Optional preferences should not automatically disqualify a candidate.
4. NULL nullable Boolean preference means no preference.
5. Search supports worldwide locations.
6. Nationality must not become an unintended global exclusion.
7. Blocked and hidden profiles are excluded in the relevant direction.
8. Suspended, inactive, or non-visible profiles are excluded.
9. Search-result impressions do not consume profile-view credits.
10. A billable detail view is charged according to the account-target 24-hour rule.

## 16. Subscription rules

1. Administrators configure plan prices and benefits.
2. Only one active paid subscription is permitted per account.
3. Subscription allowances are issued for billing periods.
4. Monthly subscription allowances expire at the end of their period.
5. Subscription allowances do not roll over.
6. Purchased top-up credits remain until used.
7. Purchased credits remain separate from subscription allowances.
8. Subscription allowances are consumed before purchased credits.
9. A failed renewal has a three-day grace period.
10. Paid benefits and new allowances remain suspended until payment confirmation.
11. Cancellation stops future renewal.
12. Paid benefits continue through the paid period unless a refund or other exception applies.

## 17. Credit rules

1. Maintain separate request and profile-view credit types.
2. Maintain separate subscription and purchased credit buckets.
3. Record every credit change in an append-only ledger.
4. Do not permit negative balances.
5. Use row-level locking during deductions.
6. Use idempotency keys for operations that may be retried.
7. Subscription allowances are consumed before purchased credits.
8. Expired allowances are recorded as expiry transactions.
9. Purchased top-ups do not expire while unused.
10. Credit correction uses compensating transactions, not deletion of history.
11. Manager actions are charged to the owner's account.
12. Record the actual manager and represented profile.
13. Refund unused purchased credits through a compensating transaction.
14. Consumed credits require review rather than negative balances.

## 18. Profile-view billing workflow

1. User requests a profile detail view.
2. Backend authenticates the account.
3. Backend resolves the represented profile.
4. Backend checks search visibility, blocking, hidden-profile restrictions, and other eligibility.
5. Backend checks whether the account already has a billable view for the target within the previous 24 hours.
6. If not previously billed, backend locks the relevant credit records.
7. Backend consumes subscription profile-view allowance first.
8. If insufficient, backend consumes purchased profile-view credits.
9. Backend creates a credit transaction and ProfileView record.
10. Backend returns only the profile fields the viewer may access.

The system must prevent duplicate billing caused by retries or concurrent requests.

## 19. Payment rules

1. Create a local pending payment before redirecting or initiating the gateway flow.
2. Use a unique merchant reference.
3. Verify gateway callbacks.
4. Match callback amount, currency, reference, and transaction identity.
5. Process each payment once.
6. Do not grant benefits based on frontend success.
7. Record sanitized gateway events.
8. Reconcile payments whose callbacks are delayed or missing.
9. Use compensating transactions for refunds and reversals.
10. Never store raw card credentials or other prohibited payment secrets.

## 20. Notification rules

1. Create business events and outbox records in the same transaction.
2. Deliver notifications asynchronously.
3. Retry temporary failures with bounded retry/backoff.
4. Record each delivery attempt.
5. Distinguish sent from delivered.
6. Do not put sensitive profile or message content in SMS/push.
7. Support language-specific templates.
8. Keep security notifications enabled.
9. Respect ordinary user preferences for non-essential categories.
10. Prevent duplicate delivery through idempotency and provider references.

## 21. Moderation rules

1. Authenticated users can submit reports.
2. Reports may target accounts, profiles, photos, messages, and documents.
3. Reports do not automatically suspend accounts by default.
4. Evidence is private and scanned where supported.
5. Multiple reports may be grouped into one case.
6. Moderation actions require a reason.
7. Temporary restrictions expire or are reviewed.
8. Appeals are supported.
9. Appeals do not automatically remove restrictions.
10. Permanent termination requires elevated approval.
11. Moderators must not review cases where they have a conflict of interest.
12. Reporter identity is not disclosed to the reported person.
13. Restriction enforcement must be consistent across all modules.

## 22. Data export rules

1. The account holder requests the export.
2. Identity confirmation is required.
3. Export includes only authorized data.
4. Export excludes other people's private information.
5. Identity-verification documents and internal moderation evidence are excluded by default.
6. Package data as ZIP with structured JSON and eligible media.
7. Notify the user when ready.
8. Export availability lasts 7 days.
9. Download URL expires after 24 hours.
10. Log successful and failed downloads.

## 23. Account deletion rules

1. The user submits a deletion request.
2. Identity confirmation is required.
3. A 30-day recovery period applies.
4. During recovery, public profile visibility and new activity are disabled.
5. The user may cancel during recovery.
6. Deletion processing is asynchronous and idempotent.
7. Sessions and manager authorizations are revoked at processing.
8. Own profile/media are handled according to retention policy.
9. Other users' legitimate conversation history is preserved or anonymized as appropriate.
10. Legal/security holds preserve only necessary records.
11. Deleting a manager does not delete the profile they managed.
12. No automatic profile ownership transfer occurs.
13. Purchased credit and refund treatment follows the published policy.
14. Backup deletion follows the documented backup lifecycle.

## 24. Workflow acceptance criteria

Each workflow must be implemented through backend services, tested for authorization and concurrency, and documented with valid and invalid transitions.

Tests must include:

- Unauthorized actor.
- Wrong represented profile.
- Expired authorization.
- Paused authorization.
- Blocked profile.
- Hidden profile.
- Duplicate request.
- Concurrent request acceptance.
- Concurrent credit deduction.
- Repeated payment callback.
- Expired media permission.
- Revoked document permission.
- Retried background task.
- Duplicate deletion step.
- Expired export link.