# Matermonial — Core State Machines and Transition Rules

**Version:** 1.0  
**Date:** 11 November 2026

## 1. Purpose

This document defines valid lifecycle transitions for important platform entities.

Claude Code must implement state transitions through domain services. Direct arbitrary status updates through serializers or generic CRUD endpoints are not allowed.

## 2. Matrimonial profile

Statuses:

- DRAFT
- PENDING_REVIEW
- ACTIVE
- PAUSED
- SUSPENDED
- CLOSED

Typical transitions:

```text
DRAFT -> PENDING_REVIEW
PENDING_REVIEW -> ACTIVE
ACTIVE -> PAUSED
PAUSED -> ACTIVE
ACTIVE -> SUSPENDED
PAUSED -> SUSPENDED
ACTIVE -> CLOSED
PAUSED -> CLOSED
```

Rules:

- Activation requires eligibility and verification conditions.
- Moderation may suspend a profile.
- A user cannot bypass suspension by changing visibility.
- Closed profiles cannot be reactivated through an ordinary update endpoint.

## 3. Identity verification

Statuses:

```text
NOT_SUBMITTED
    |
    v
PENDING_REVIEW
    |
    v
UNDER_REVIEW
   / \
  v   v
APPROVED  REJECTED
             |
             v
     RESUBMISSION_REQUIRED
             |
             v
       PENDING_REVIEW
```

Rules:

- Review decisions require a reviewer.
- Rejection requires a reason.
- Resubmission creates a new review cycle or submission record.
- Previous review history is preserved.
- Approval does not bypass other profile-activation conditions.

## 4. Family-manager authorization

Statuses:

```text
PENDING -> ACTIVE -> PAUSED -> ACTIVE
                 \           /
                  \         /
                   -> REVOKED

PENDING -> REJECTED
ACTIVE -> EXPIRED
PAUSED -> REVOKED
```

Rules:

- Only the owner initiates an invitation.
- Manager must accept.
- Owner controls pause, resume, and revocation.
- Expiry is processed by a scheduled job.
- Revoked and expired authorizations cannot be reactivated; a new invitation is required.

## 5. Interest

The interest workflow must distinguish lightweight interest from formal request.

Typical lightweight interest outcomes:

- Pending response.
- Interest shown back.
- Formal request initiated.
- Declined.
- Withdrawn or closed, if supported by the final interest model.

Rules:

- Declined interest is historical.
- Decline cooldown is directional for 30 days.
- Formal request credit is charged only when a formal request is created.
- Repeated actions must not create duplicate active interest records.

## 6. Formal matrimonial request

Statuses:

- PENDING
- ACCEPTED
- DECLINED
- WITHDRAWN
- EXPIRED
- CANCELLED

Valid transitions:

```text
PENDING -> ACCEPTED
PENDING -> DECLINED
PENDING -> WITHDRAWN
PENDING -> EXPIRED
PENDING -> CANCELLED
```

All final states are terminal by default.

Rules:

- Only recipient can accept/decline.
- Sender can withdraw.
- Scheduled expiry handles expired requests.
- Administrative cancellation requires authorized action and reason.
- Every transition creates history.
- Acceptance creates a connection atomically.

## 7. Connection

Statuses:

- ACTIVE
- PAUSED
- COMPLETED
- CLOSED

Rules:

- Accepted request creates ACTIVE connection.
- Either authorized party may pause according to product policy.
- Resume is allowed only if no block/restriction prevents it.
- CLOSED can reopen only through mutual confirmation.
- COMPLETED is not reopened by default.
- All transitions create history.

## 8. Conversation

Statuses:

- ACTIVE
- PAUSED
- CLOSED

Rules:

- Conversation is tied to one connection.
- A paused or closed connection prevents new messages.
- Blocking prevents communication.
- Existing messages remain subject to retention and access rules.
- Conversation state must not be more permissive than its connection state.

## 9. Shared document permission

Statuses:

- ACTIVE
- EXPIRED
- REVOKED

Rules:

- Expiry is enforced during every access attempt.
- Revocation immediately denies new access.
- Expired permission cannot be renewed by simply changing its status.
- A new permission may be issued.
- Access history is preserved.

## 10. Payment

Recommended statuses:

- PENDING
- PROCESSING
- SUCCEEDED
- FAILED
- CANCELLED
- REFUNDED
- PARTIALLY_REFUNDED, if supported by gateway policy

Rules:

- A pending payment may be processed.
- Only verified successful payment can grant benefits.
- Duplicate callbacks cannot repeat the financial effect.
- Refunds create corresponding compensating financial transactions.
- A failed payment cannot grant credits or activate paid benefits.

## 11. Credit allowance

Statuses:

- ACTIVE
- EXHAUSTED
- EXPIRED

Rules:

- Active allowances can be consumed.
- Fully consumed allowance becomes exhausted.
- Period-end expiry creates an expiry transaction.
- Purchased credits use a separate non-expiring-until-used bucket.

## 12. Notification delivery

Statuses:

- PENDING
- PROCESSING
- SENT
- DELIVERED
- FAILED
- RETRY_SCHEDULED
- CANCELLED

Rules:

- Provider acceptance does not prove delivery.
- Retries must be bounded.
- Delivery attempts are separately recorded.
- Duplicate tasks must not duplicate the underlying business event.

## 13. Moderation case

Recommended statuses:

- OPEN
- UNDER_REVIEW
- ACTION_REQUIRED
- RESOLVED
- CLOSED

Rules:

- Case assignments and status changes are audited.
- Reports can be grouped into cases.
- Moderation actions must include a reason.
- Appeals are separate records.
- Conflicted reviewers must be prevented from reviewing the case.

## 14. Data export

Statuses:

- REQUESTED
- IDENTITY_VERIFICATION_REQUIRED
- VERIFIED
- PROCESSING
- COMPLETED
- FAILED
- EXPIRED
- CANCELLED

Rules:

- Processing begins only after required verification.
- Export generation is asynchronous.
- Generated files are private.
- Download expires according to policy.
- Expired files are deleted according to retention rules.

## 15. Account deletion

Statuses:

- REQUESTED
- IDENTITY_VERIFICATION_REQUIRED
- PENDING_RECOVERY
- CANCELLED
- PROCESSING
- COMPLETED
- REJECTED

Rules:

- A 30-day recovery period applies.
- Cancellation is allowed during recovery.
- Processing begins after recovery ends unless a valid cancellation or policy exception applies.
- Processing steps are idempotent.
- Legal/security holds are evaluated.
- Completed deletion is not reversed through an ordinary API.

## 16. Transition implementation

For every stateful entity:

- Define permitted transitions.
- Define the actor allowed to perform each transition.
- Define required fields/reasons.
- Define side effects.
- Define transaction boundaries.
- Define history creation.
- Define notification events.
- Define idempotency behavior.
- Write tests for valid and invalid transitions.