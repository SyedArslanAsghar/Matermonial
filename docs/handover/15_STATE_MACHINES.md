# Matermonial — Core State Machines and Transition Rules

**Version:** 1.0 (G1 revision 2026-11-16)  
**Date:** 11 November 2026  
**Document status:** APPROVED_WITH_OPEN_ITEMS (project owner, 2026-11-17, DR-2026-11-17-A; record in doc 20 §5). **Open items:** OPEN ODs: OD-02, OD-03, OD-04, OD-05, OD-06, OD-07, OD-09; PROPOSED TRs: TR-06, TR-21. Listed items keep their own status (doc 19); this document status doesn't approve them.  
**Applied corrections:** DCR-04, 07, 10, 21, 37, 38, 41, 43, 46, 47, 48, 51, 59, 92, 97 (doc 20). Transitions marked [REC-BIZ] depend on an OPEN owner decision (doc 19) and aren't implemented until it is recorded. G1 correction pass 2026-11-17 (DR-2026-11-17-C).

## 1. Purpose

This document defines valid lifecycle transitions for important platform entities.

Claude Code must implement state transitions through domain services. Direct arbitrary status updates through serializers or generic CRUD endpoints are not allowed.

## 2. Matrimonial profile

Statuses: DRAFT, PENDING_REVIEW, ACTIVE, PAUSED, SUSPENDED, CLOSED. Visibility is separate [DECIDED].

| Transition | Actor | Notes |
|---|---|---|
| DRAFT → PENDING_REVIEW | Owner / manager (`edit_*`) | Required fields complete |
| PENDING_REVIEW → ACTIVE | System | Identity APPROVED, review passed, eligibility met. Default visibility "Visible in match search" [DECIDED, FR-PRO-007]. |
| PENDING_REVIEW → DRAFT | Reviewer | Content rejected, with a reason |
| ACTIVE ↔ PAUSED | Owner | |
| ACTIVE / PAUSED → SUSPENDED | Moderation | With a reason |
| SUSPENDED → previous state (ACTIVE or PAUSED) | Moderation | When the restriction is lifted. Stored in `suspended_from_status`. |
| ACTIVE / PAUSED / SUSPENDED → CLOSED | Owner (not while suspended without moderation approval), deletion processing, admin | Terminal through ordinary endpoints [DECIDED] |

Rules:

- Activation requires eligibility and verification conditions.
- Moderation may suspend a profile.
- A user cannot bypass suspension by changing visibility.
- Closed profiles cannot be reactivated through an ordinary update endpoint.
- The account-deletion overlay is not a profile status; it is computed from `AccountDeletionRequest` (doc 03 §22.1 row 22).

## 3. Identity verification

Statuses per cycle: NOT_SUBMITTED, PENDING_REVIEW, UNDER_REVIEW, APPROVED, REJECTED, RESUBMISSION_REQUIRED, CANCELLED.

Each submission is one **cycle** row [DECIDED: resubmission creates a new review cycle].
- Within a cycle: NOT_SUBMITTED → PENDING_REVIEW → UNDER_REVIEW → APPROVED | REJECTED. Then REJECTED → RESUBMISSION_REQUIRED → a new cycle at PENDING_REVIEW. CANCELLED is allowed from PENDING_REVIEW by the owner.
- **The effective identity status** = the latest **decided** cycle, unless a re-verification hold applies.

Rules:

- Review decisions require a reviewer.
- Rejection requires a reason.
- Resubmission creates a new review cycle or submission record.
- Previous review history is preserved.
- Approval does not bypass other profile-activation conditions.

**Re-verification after an approval** (DCR-43) [REC-BIZ, OD-04e OPEN]. A new cycle after an earlier approval is only possible through (a) an approved locked-field correction (TR-06) or (b) an admin-initiated re-verification (document expiry, fraud signal, report). The owner can't voluntarily restart verification while approved.
- **Case (a):** the previous approval stays in force while the new cycle is reviewed. If the new cycle is rejected, the correction isn't applied and the old approval stands.
- **Case (b):** the reviewer chooses NON_RESTRICTIVE (the approval stays in force) or RESTRICTIVE: a profile-level `UserRestriction(type=IDENTITY_REVIEW)` blocks new matrimonial activity and search listing, but existing connections stay readable, until the cycle is decided. If the cycle is rejected, the effective status becomes REJECTED, the profile can't stay ACTIVE (→ SUSPENDED), and the owner can resubmit.
- `identity_verified_at` is cleared only when an approval stops being effective. All cycles are kept [DECIDED].

## 4. Family-manager authorization

| Transition | Actor |
|---|---|
| PENDING → ACTIVE | Manager accepts [DECIDED] |
| PENDING → REJECTED | Manager |
| PENDING → EXPIRED | System, at the invitation TTL [REC-BIZ, OD-05e] |
| PENDING → REVOKED | Owner cancels the invitation |
| ACTIVE ↔ PAUSED | Owner [DECIDED] |
| ACTIVE / PAUSED → REVOKED | Owner [DECIDED]; manager resigns, reason RESIGNED [REC-BIZ, OD-05f]; manager account deletion [DECIDED, FR-DAT-010] |
| ACTIVE → EXPIRED | System (scheduled job), plus the runtime check on every request |

Rules:

- Only the owner initiates an invitation.
- Manager must accept.
- Owner controls pause, resume, and revocation.
- Expiry is processed by a scheduled job and also checked at runtime.
- Revoked, expired and rejected authorizations cannot be reactivated; a new invitation is required.
- Paused, pending, expired, revoked and rejected authorizations grant no access [DECIDED].

## 5. Interest

Statuses (DCR-04, DCR-51): PENDING, RECIPROCATED, CONVERTED_TO_REQUEST, DECLINED, WITHDRAWN, EXPIRED, CLOSED. Model: doc 03 §22.7.

| State | Live? | Expires? | Allowed exits | Cooldown on entry |
|---|---|---|---|---|
| PENDING | Yes, until `expires_at` | Yes, if OD-06e is approved | → RECIPROCATED, CONVERTED_TO_REQUEST, DECLINED, WITHDRAWN, EXPIRED, CLOSED | — |
| RECIPROCATED | Yes | **Never** | → CONVERTED_TO_REQUEST (either party, OD-06c), WITHDRAWN (either party, OD-06m), CLOSED | — |
| CONVERTED_TO_REQUEST | No (terminal) | — | None. The request lifecycle takes over; request outcomes never change the interest. | Per request outcome [DECIDED] |
| DECLINED | No (terminal) | — | None | **30 days, sender → receiver [DECIDED]** |
| WITHDRAWN | No (terminal) | — | None | None (OD-06d) |
| EXPIRED | No (terminal) | — | None | None |
| CLOSED | No (terminal) | — | None. Unblocking doesn't revive it. | None |

| From | Event | Actor | To | Notes |
|---|---|---|---|---|
| — | Express interest | Sender (`send_interests`) | PENDING | |
| — | Express interest while the reverse interest is PENDING | Sender | Reverse row → RECIPROCATED, no new row | [REC-BIZ, OD-06a] |
| PENDING | Show interest back | Receiver | RECIPROCATED | [DECIDED: FR-REQ-002] |
| PENDING | Send formal request | Receiver | CONVERTED_TO_REQUEST | [DECIDED: FR-REQ-002]; the receiver's owning account pays |
| PENDING | Send formal request | Original sender | CONVERTED_TO_REQUEST | [REC-BIZ, OD-06b] |
| RECIPROCATED | Send formal request | Either party | CONVERTED_TO_REQUEST | Initiator's owning account pays [REC-BIZ, OD-06c] |
| PENDING | Decline | Receiver ("recipient, via owner or authorized manager") | DECLINED | 30-day directional cooldown [DECIDED] |
| PENDING | Withdraw | Sender | WITHDRAWN | No cooldown [REC-BIZ, OD-06d] |
| PENDING | Expiry (worker or lazy path) | System | EXPIRED | Only if OD-06e is approved. No cooldown. |
| PENDING / RECIPROCATED | Block (either direction), profile CLOSED, deletion PROCESSING | System | CLOSED | Counterparty sees "No longer pending" [REC-BIZ, OD-06f] |
| PENDING / RECIPROCATED | Profile PAUSED, SUSPENDED, deactivated, in deletion recovery or under a restrictive identity hold | — | Unchanged (frozen); actions by both parties refused; the expiry clock keeps running | [REC-BIZ, OD-06f] |
| PENDING / RECIPROCATED | Hide (either direction) | — | **Unchanged** | [DECIDED: hiding prevents only new approaches] |

Rules:

- Declined interest is historical.
- Decline cooldown is directional for 30 days.
- Formal request credit is charged only when a formal request is created.
- Repeated actions must not create duplicate active interest records (partial unique index, doc 03 §22.7).
- **Expiry** (DCR-38): `expires_at` is set once at creation and is immutable; expiry applies only to PENDING. Expiry goes through one shared function, called by the worker or lazily under the pair lock before any create (doc 05). Every action on a logically expired PENDING interest first expires it and then fails with `interest_not_pending`, without charging.
- Creating a request while the pair has a live interest converts and links that interest in the same transaction; there is no unlinked "superseded" path. If OD-06b is rejected, the original sender's direct request is refused with `interest_pending` until the interest is withdrawn or expires.
- Creating an interest is rejected generically if the pair has a PENDING request in either direction, a connection, or an active interest-decline cooldown in that direction [DECIDED: FR-REQ-003, 30-day directional cooldown]. **Whether a cooldown from a request (decline or expiry) also blocks new interests, and whether an interest cooldown also blocks requests, is OD-06g [REC-BIZ, OPEN]**; that wider scope isn't implemented until OD-06g is decided.

## 6. Formal matrimonial request

Statuses: PENDING, ACCEPTED, DECLINED, WITHDRAWN, EXPIRED, CANCELLED.

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

- Only the recipient (via owner or authorized manager with `respond_to_requests`) can accept or decline.
- Sender (via owner or authorized manager) can withdraw.
- Expiry at `sent_at + 3 calendar months` [DECIDED], computed in UTC (doc 05). Scheduled expiry and the lazy path use the same expiry function; the expiry cooldown starts at the logical expiry time.
- Administrative cancellation requires authorized action and reason [DECIDED]; no cooldown by default [DECIDED].
- **System cancellation triggers** (recipient or sender deletion processing, suspension, closure, block) use CANCELLED with a reason code and a post-commit refund obligation where applicable (DCR-46, doc 05) [REC-BIZ, OD-07a/b, OPEN]. Pause, deactivation, deletion recovery, hide and manager-authorization changes don't cancel a request.
- Every transition creates history.
- Acceptance creates a connection atomically.

## 7. Connection

Connection lifecycle (`ProfileConnection.status`): ACTIVE, PAUSED, COMPLETED, CLOSED. The relationship progress stage is a separate state machine (§20) and never changes the lifecycle (DCR-37).

| Transition | Actor | Rule |
|---|---|---|
| (accept) → ACTIVE | System | Same transaction as the acceptance [DECIDED] |
| ACTIVE → PAUSED | Either party (`manage_connections`) | [DECIDED: either authorized party may pause]. Records `paused_by_profile`. |
| PAUSED → ACTIVE | The **pausing party only** [REC-BIZ, OD-06h] | Not while a block or restriction applies [DECIDED] |
| ACTIVE / PAUSED → COMPLETED | Both parties confirm [REC-BIZ, OD-06i] | Independent of the progress stage. Not reopened by default [DECIDED]. |
| ACTIVE / PAUSED → CLOSED | Either party, moderation, deletion processing, profile closure | With a reason |
| COMPLETED → CLOSED | Either party (`PARTY_ENDED`), moderation, deletion processing, profile closure | [REC-BIZ, OD-06l]. Sets `closed_from_status = COMPLETED`; never reopenable. |
| CLOSED → ACTIVE | Both parties confirm through `ConnectionReopenRequest` (§19) [DECIDED: mutual confirmation] | Only if every reopen check passes (§19) |

**Pause behaviour** (DCR-49): pause and resume run under the pair lock and a connection row lock. A second pause by the same party is a no-op; a pause by the other party while paused returns `409 connection_already_paused`; a resume by the non-pausing party returns `403 action_not_allowed`. The pause fields are consistent by database constraint (doc 03 §22.8).

**Effects** (DCR-59):
- ACTIVE: L3 access and messaging.
- PAUSED / COMPLETED: L2 and read-only history; no contact details, new messages or new shares.
- **Entering CLOSED:** connection-derived access ends (visibility matrix, doc 06) [REC-BIZ, OD-03j]; new communication ends [DECIDED: messaging requires an active connection]; **conversation history is kept** and stays readable read-only to both participants under the existing access rules and retention (no message is deleted because of closure); document permissions aren't deleted but new access is denied while CLOSED [REC-BIZ, OD-06l]; photo permissions are unaffected [DECIDED]; the progress stage is frozen and shown as "Closed", and shared notes stay readable to both parties as history but can't be edited [REC-BIZ, OD-06l] (baseline v4.2 C22).

Rules:

- Accepted request creates ACTIVE connection.
- Resume is allowed only if no block/restriction prevents it.
- CLOSED can reopen only through mutual confirmation.
- COMPLETED is not reopened by default.
- All transitions create history.

## 8. Conversation

There's **no stored conversation status** (DCR-05). State is derived from the connection and blocks:
- Connection ACTIVE: send and read.
- Connection PAUSED or COMPLETED: read only.
- Connection CLOSED: read only, per retention.
- Block in either direction: no access.

Rules:

- Conversation is tied to one connection.
- A paused or closed connection prevents new messages.
- Blocking prevents communication.
- Existing messages remain subject to retention and access rules.
- Conversation state must not be more permissive than its connection state (guaranteed by derivation).

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

Statuses: ACTIVE, EXHAUSTED, EXPIRED.

- ACTIVE → EXHAUSTED when fully consumed.
- ACTIVE / EXHAUSTED → EXPIRED at the period end, writing the expiry ledger entry for any remainder [DECIDED].
- EXHAUSTED → ACTIVE only through a refund to that allowance before it expires [REC-BIZ, OD-07].

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

Statuses: REQUESTED, IDENTITY_VERIFICATION_REQUIRED, PENDING_RECOVERY, CANCELLED, PROCESSING, COMPLETED, REJECTED.

- REQUESTED → IDENTITY_VERIFICATION_REQUIRED → PENDING_RECOVERY. Entering PENDING_RECOVERY revokes all sessions (DCR-41).
- PENDING_RECOVERY → CANCELLED, by the user while `now < recovery_ends_at` [DECIDED: the user may cancel during the 30-day recovery period]. The mechanism used to cancel, a recovery-scoped session (doc 05 §25.9, doc 06), is [TR-21; flow REC-BIZ, OD-02d, OPEN].
- PENDING_RECOVERY → PROCESSING at `recovery_ends_at`, by the job under the User row lock. **The transition requires the deletion's Stream R `DELETION_INTENT` to be registered first** (DCR-92, doc 09).
- PROCESSING → COMPLETED after every idempotent deletion step and key-destruction (SHRED) child operation has completed and been verified; the registry `DELETION_COMPLETED` entry is written only after that (doc 09).
- REJECTED from verification failure or a legal hold.
- After a restore from an older backup, a recorded `DELETION_INTENT` is re-applied through the restore path (reason `RESTORE_REAPPLY`), even if the restored data shows the account as active (doc 09).

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

## 17. Authentication session and token

`AuthSession` (doc 03 §22.2):
- ACTIVE → REVOKED, with a reason (logout, user revocation, password reset or change, deactivation, deletion request, admin, refresh reuse, key compromise).
- ACTIVE → EXPIRED (idle or absolute limit; enforced at runtime and swept by a job).

Both end states are terminal. `AuthToken`: issued → used, revoked or expired.

## 18. Subscription (manual renewal for the MVP)

[REC-BIZ, OD-09a OPEN; the payment-confirmation and period-end rules are DECIDED]

- PENDING_PAYMENT → ACTIVE (payment verified [DECIDED]).
- PENDING_PAYMENT → CANCELLED.
- ACTIVE → EXPIRED at `ends_at`.
- ACTIVE → CANCELLED: stops future renewal; benefits continue to the period end [DECIDED, FR-SUB-009].

An early renewal creates a queued term that starts at `ends_at`. PAYMENT_FAILED and GRACE exist in the schema but stay **dormant** (FR-SUB-008) until auto-renewal is approved.

## 19. Connection reopen request

States: PENDING → CONFIRMED | DECLINED | WITHDRAWN (by the initiator) | EXPIRED | INVALIDATED (DCR-48).

- One PENDING request per connection (partial unique index).
- If the other party already has a PENDING request, creating one counts as confirming it (under the pair lock).
- Reopen checks run at initiation **and again in the confirming transaction**, for both profiles: acting-profile permission `manage_connections` with step-up; both accounts active; no deletion in recovery or processing; both profiles ACTIVE; effective identity APPROVED with no restrictive hold; no block in either direction; no restriction on connections or messaging; `closed_from_status <> COMPLETED`; closure reason reopenable; the hide rule; no other live connection or pending request; within the time-to-live. Non-reopenable closure reasons, the hide rule and the TTL are [REC-BIZ, OD-06n].
- A failed check at confirmation → INVALIDATED; nothing is reopened.
- Confirmation: connection → ACTIVE with closure fields cleared; progress stage keeps its frozen value; conversation becomes writable; history written.

## 20. Relationship progress stage

Stages (`RelationshipProgress.stage`): REQUEST_ACCEPTED (initial), INITIAL_COMMUNICATION, DISCUSSION_IN_PROGRESS, MEETING_PLANNED, MEETING_COMPLETED, PROPOSAL_SERIOUS_DISCUSSION, ENGAGED. The "Closed" item of FR-CON-004 is displayed when the connection is CLOSED; it is not stored (DCR-37) [storage change: OD-06i, OPEN].

[REC-BIZ, OD-06k OPEN]
- Any stage can move to any other stage.
- Either participant (owner, or a manager with `manage_relationship_progress`) can update it, **only while the connection is ACTIVE**. The other party is notified.

[DECIDED] Every change writes history: previous stage, new stage, actor, represented profile, timestamp (FR-CON-005).
