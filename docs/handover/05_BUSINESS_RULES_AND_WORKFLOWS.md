# Matermonial — Business Rules and End-to-End Workflows

**Version:** 1.0 (G1 revision 2026-11-16)  
**Date:** 11 November 2026  
**Document status:** APPROVED_WITH_OPEN_ITEMS (project owner, 2026-11-17, DR-2026-11-17-A; record in doc 20 §5). **Open items:** OPEN ODs: OD-02, OD-04, OD-06, OD-07, OD-09; PROPOSED TRs: TR-03, TR-15, TR-18, TR-21. Listed items keep their own status (doc 19); this document status doesn't approve them.  
**Applied corrections:** DCR-04, 10, 21, 30, 31, 38, 41, 46, 48, 51, 56, 57, 59, 62, 69, 71, 77, 78, 83, 89, 93, 98 (doc 20). Reconciled workflows are in **§25**, which wins where it differs from §1–§24. G1 correction pass 2026-11-17 (DR-2026-11-17-C). Verbatim extracts start with a "*Verbatim from …*" line and end with "*— End of verbatim extract —*"; text outside those markers is editorial.

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
3. Only the recipient (via owner or authorized manager) may accept or decline.
4. The sender or an authorized manager may withdraw a pending request.
5. Pending requests expire after three calendar months.
6. Active requests between the same two profiles in either direction are mutually exclusive.
7. A decline or expiration creates a 30-day directional cooldown for the original sender.
8. Withdrawal does not create a cooldown by default.
9. Administrative cancellation does not create a cooldown by default. System cancellation triggers and their refund consequences: §25.2 [OD-07, OPEN].
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

PENDING -- expiry job or lazy expiry --> EXPIRED
PENDING -- admin action or system trigger --> CANCELLED
```

The authoritative request and interest state machines are in doc 15 §5–§6. System cancellation triggers are [REC-BIZ, OD-07a, OPEN].

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

> **G1 (DCR-30):** rules 9–10 (FR-SUB-008) apply to automatic renewal, which is not approved. The recommended MVP model is manual renewal, with FR-SUB-008's implementation DEFERRED until auto-renewal is approved, and removal of any post-expiry window [REC-BIZ, OD-09a–d, OPEN]. Scenarios: §25.8.
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

> **G1 (DCR-31):** the ledger is the permanent record and wallet/allowance balances are projections of it (doc 03 §22.1, §22.11). Ledger operation types: §25.7.

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

> **G1 (DCR-26, DCR-39):** charging happens only through `POST /profiles/{id}/views/`; `GET /profiles/{id}/` never charges and re-evaluates access on every request. A paid view never overrides current privacy or authorization rules (doc 04, doc 06).

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

## 25. Reconciled workflows (G1)

**Status:** workflow mechanics are **[TR] PROPOSED** (doc 19). Behaviour tagged [REC-BIZ] belongs to an OPEN owner decision and is not implemented until that decision is recorded. [DECIDED] rules are approved requirements. Lock order for every workflow: doc 12 §5.

### 25.1 Interests: lazy expiry and stale rows (DCR-38, DCR-51) [TR-18]

> *Verbatim from `docs/baseline/v4.6-F3/approved/01_v4.md` §7 C. Section references inside this block refer to that package.*

**Shared function:** `expire_if_due(row, now)`. It's the **only** code that moves a PENDING interest or request to EXPIRED. It does all of the following in one step:
- a conditional `UPDATE … SET status='EXPIRED' WHERE id=? AND status='PENDING' AND expires_at <= now`
- if exactly one row changed, it writes the history row (actor SYSTEM, `trigger` = WORKER or LAZY)
- for **requests**, it creates the `DirectionalCooldown` with `starts_at = expires_at` (the logical expiry time, not now) and `ends_at = expires_at + 30×24h` [DECIDED cooldown; TR timing]
- it writes the outbox event (expiry notification)

If zero rows changed, it does nothing, so it's idempotent.

**Create-interest and create-request service, in one transaction (READ COMMITTED):**
1. Run the acting-profile algorithm (v3 §9). For a delegated write, take `FOR SHARE` on the authorization row.
2. **Take the pair advisory lock:** `pg_advisory_xact_lock(NS_PAIR, hash(least_id ‖ greatest_id))`.
3. **Re-read after the lock.** Each statement gets a fresh snapshot under READ COMMITTED, so this sees everything committed by whoever held the lock before. Select every interest and request for the pair with status ∈ {PENDING, RECIPROCATED} `FOR UPDATE`.
4. Call `expire_if_due` on each row whose `expires_at <= now`. Interests only do this if OD-06e is approved; otherwise interests have `expires_at` NULL. RECIPROCATED doesn't expire (REC-BIZ, OD-06e).
5. Check the cooldown, including any cooldown just created in step 4. Then apply the remaining rules (live request in either direction, connection, block, hide, eligibility).
6. Create the new row, or convert the live interest (§12 conversion). The partial unique indexes are the backstop: if one fires, it means a lock was skipped (a bug), and the result is a generic 409, never a duplicate.
7. Write history, audit and outbox. Commit.

**Under concurrency:**

| Case | Behaviour |
|---|---|
| Two creates for the same pair | Serialised by the advisory lock. The second one sees the first's row in step 3 and is rejected generically. |
| Worker vs create | The worker also takes the pair lock before calling `expire_if_due`, so only one of them performs the transition. The other sees EXPIRED, or zero rows updated. Exactly one history row, one cooldown and one notification. |
| Read paths (lists, detail) | Never write. They apply the row 21 liveness predicate, so a logically expired row shows as expired before the worker gets to it. |
| Unrelated pairs | Never contend |

**Must use READ COMMITTED.** Under REPEATABLE READ, the snapshot would be taken before the lock and could miss rows.

*— End of verbatim extract —*

> *Verbatim from `docs/baseline/v4.6-F3/approved/02_v4.1.md` §16.3. Section references inside this block refer to that package.*

##### 16.3 Rules for actions on stale or frozen interests [TR unless marked]

1. **Every action** on an interest (reciprocate, decline, withdraw, convert, auto-reciprocate) runs lazy expiry under the pair lock first. If the interest is now EXPIRED, the action fails with `interest_not_pending`, and nothing is charged.
2. **Auto-reciprocation (OD-06a)** when the reverse interest is logically expired: the reverse row is expired first, then a new forward PENDING row is created. Auto-reciprocation doesn't count toward the daily cap [REC-BIZ, OD-06g].
3. **A request created while an interest is live always converts and links that interest.** If OD-06b is rejected, the original sender's direct request is refused with `interest_pending` until they withdraw the interest or it expires. There's no unlinked "superseded" path.
4. **Frozen** (either party PAUSED, SUSPENDED, deactivated, in deletion recovery, or under a restrictive identity hold): the status doesn't change, actions by **both** parties are refused generically, and **the expiry clock keeps running** [REC-BIZ, OD-06f].
5. **Hide** (either direction): unchanged [DECIDED].
6. **Block, closure, deletion processing:** a live interest (PENDING or RECIPROCATED) → CLOSED with the matching reason, in the triggering transaction or its per-pair fan-out [REC-BIZ, OD-06f].
7. **Uniqueness:** the partial unique index on `status IN ('PENDING','RECIPROCATED')` is resolved by lazy expiry before any insert. RECIPROCATED rows never go stale.

**Tests:**
- T-INT-021…030: every action on a logically expired row; expiry while frozen.
- RECIPROCATED never expires; withdrawal from RECIPROCATED by either party.
- No retroactive expiry.
- Request outcomes leave CONVERTED unchanged.
- The `SUPERSEDED_BY_REQUEST` value no longer exists.

*— End of verbatim extract —*

### 25.2 Formal-request cancellation triggers (DCR-46) [REC-BIZ, OD-07, OPEN]

**What is decided and what isn't (DR-2026-11-17-C5):** only the administrative cancellation itself is DECIDED: for T1 and T2, the request becomes CANCELLED through an authorized admin action with a reason, and no cooldown applies by default. **Whether any trigger refunds the sender, including T2's "Yes", is OD-07b (OPEN)**, as are the system triggers T3–T10 (OD-07a) and their notifications (OD-07f). The table below is the recommended default. No refund behaviour is approved by it.

> *Verbatim from `docs/baseline/v4.6-F3/approved/02_v4.1.md` §11.2. Section references inside this block refer to that package.*

##### 11.2 Trigger table (every row except T1 is REC-BIZ under OD-07)

| # | Trigger | Actor | Request outcome | Reason code | Refund to sender's billing account | Cooldown |
|---|---|---|---|---|---|---|
| T1 | Admin cancellation for sender misconduct | Admin with `requests.cancel` + a moderation case reference | CANCELLED [DECIDED] | `ADMIN_SENDER_MISCONDUCT` | No | None [DECIDED default] |
| T2 | Admin cancellation for any other reason (error, support, recipient misconduct) | Admin with `requests.cancel` | CANCELLED [DECIDED] | `ADMIN_OTHER` | Yes | None [DECIDED default] |
| T3 | Recipient account deletion reaches **PROCESSING** | System | CANCELLED | `RECIPIENT_UNAVAILABLE` | Yes | None |
| T4 | Recipient profile **SUSPENDED** | System (fan-out after suspension) | CANCELLED | `RECIPIENT_UNAVAILABLE` | Yes | None |
| T5 | Recipient profile **CLOSED** | System | CANCELLED | `RECIPIENT_UNAVAILABLE` | Yes | None |
| T6 | **Recipient blocks sender** | System | CANCELLED | `RECIPIENT_UNAVAILABLE` | **Yes** (see contradiction C-17) | None. The block itself prevents new requests. |
| T7 | Sender account deletion reaches PROCESSING | System | CANCELLED | `SENDER_UNAVAILABLE` | No | None |
| T8 | Sender profile SUSPENDED | System | CANCELLED | `SENDER_UNAVAILABLE` | No | None |
| T9 | Sender profile CLOSED | System | CANCELLED | `SENDER_UNAVAILABLE` | No | None |
| T10 | Sender blocks recipient | System | CANCELLED | `SENDER_UNAVAILABLE` | No | None |
| — | Either party PAUSED, deactivated, in deletion **recovery**, or under a restrictive identity hold | — | **Not cancelled.** Frozen: both parties' actions are refused generically, and the expiry clock keeps running. | — | If it expires: no refund [DECIDED] | Expiry cooldown [DECIDED] |
| — | Hide My Profile From (either direction) | — | **Unchanged** [DECIDED: hide affects only new approaches] | — | — | — |
| — | Manager authorization revoked or paused | — | Unchanged. Requests belong to profiles. | — | — | — |

**Uniform reason codes.** The recipient-side triggers T3–T6 deliberately share one code, and the sender sees the same "No longer pending, credit returned" message for all of them. That way a refund pattern can't reveal a block, a suspension or a deletion [DECIDED: no disclosure of blocked relationships]. Internally, `cancellation_ref_type` records the real trigger, visible to admins only.

*— End of verbatim extract —*

**Records for every cancellation:** request history (action CANCELLED, reason, actor type, actor, reference); AuditLog for T1/T2 and for every refund or lapse; for T2–T6, if OD-07b approves a refund for that trigger [REC-BIZ, OPEN], a `REQUEST_REFUND_DUE` outbox event written atomically with the cancellation (the refund itself runs in a separate transaction, §25.3); the linked interest stays CONVERTED_TO_REQUEST. Fan-out triggers (T3–T10) run as one transaction per request after the triggering transition commits.

### 25.3 Request refunds (DCR-56, DCR-62, DCR-69, DCR-77) [TR-15]

1. **Obligation:** the cancelling transaction records the refund obligation as an outbox event (`event_class = FINANCIAL_OBLIGATION`, `REQUEST_REFUND_DUE`). The obligation itself is defined by domain records: a request that is CANCELLED with a refundable reason and has no verified `CreditRefundOperation` (§25.6).
2. **Claim (Tx-C):** a short separate transaction claims the event with a lease (doc 12 §6).
3. **Refund transaction (Tx-R), one atomic transaction, locks in the global order:** debit account `User FOR SHARE` → wallet `FOR UPDATE` → allowances named in the original debit rows → request read → insert the refund `CreditOperation` with key `refund:request:<request_id>` using `ON CONFLICT DO NOTHING` → get-or-verify (below) → `CreditRefundOperation` → refund ledger rows and projection updates → `CreditRefundLine` per original debit row (REFUNDED, or LAPSED if that allowance has expired [REC-BIZ, OD-07d]) → AuditLog → conditional sender notification → mark the claimed outbox event DONE (lease check; if the lease was lost, roll back everything).
4. Any failure rolls back everything, including the operation header; the event is redelivered after the lease expires.

**Get-or-verify when the operation already exists:**

> *Verbatim from `docs/baseline/v4.6-F3/approved/06_v4.5.md` §3.1. Section references inside this block refer to that package.*

##### 3.1 Get-or-verify

1. Run `INSERT … ON CONFLICT (account_id, idempotency_key) DO NOTHING RETURNING id`. **Inserted:** continue with a fresh refund as in v4.4 §2.2 steps 4–6.
2. **Not inserted:** `SELECT` the existing operation. This is a new statement under READ COMMITTED, so it sees the committed row that caused the conflict. **Verify all of the following**:

| # | Check |
|---|---|
| V1 | `op.account_id` = the request's debit account, and `op.kind = 'REFUND'` |
| V2 | Exactly one `CreditRefundOperation` with `refund_credit_operation_id = op.id`, `source_type = 'REQUEST_CANCELLATION'`, `request_id` = the expected request, `original_operation_id = request.debit_operation_id`, and the same account |
| V3 | Number of lines = number of the original operation's USAGE rows, with each USAGE row covered exactly once |
| V4 | Every REFUNDED line's refund ledger row exists with matching account, bucket, amount, `direction='CREDIT'`, `entry_type='REFUND'` and `operation_id = op.id` (re-checked defensively, even though FK-L1…L4 already guarantee it) |
| V5 | The request is CANCELLED, and its reason qualifies for a refund (OD-07) |

3. **All checks pass:** mark the outbox event DONE (level 9 lease check, §1.1) and COMMIT. No financial writes happen.
4. **Any check fails:** write **no** financial changes. In the same transaction:
   - insert `ReconciliationDiscrepancy(type=REFUND_INTEGRITY, request_id, details)`
   - set the outbox event to `BLOCKED_INTEGRITY` (never retried automatically)
   - commit and alert

*— End of verbatim extract —*

**Sender notification:** the "credit returned" event is created only if `can_notify(debit_account, FINANCIAL)` is true (§25.5). In every other case the refund is still recorded and shows in the account's financial history.

### 25.4 Notifications for cancellation triggers (DCR-57) [REC-BIZ, OD-07f, OPEN]

- Recipient-side triggers T3–T6 share one reason code, and the sender sees the same "No longer pending, credit returned" message for all of them, so a refund pattern can't reveal a block, suspension or deletion [DECIDED: no disclosure of blocked relationships].

> *Verbatim from `docs/baseline/v4.6-F3/approved/03_v4.2.md` §20.2. Section references inside this block refer to that package.*

| Trigger | Sender | Recipient |
|---|---|---|
| T7 Sender deletion PROCESSING | No notification (already told about deletion; account being removed) | **No notification.** The item shows "No longer pending" in their list. |
| T8 Sender suspended | No per-request notice. The moderation notice (owned by D20) says pending requests were cancelled without a refund. The in-app list shows "Cancelled". | Same as T7 |
| T9 Sender closes profile | **The closure confirmation warns** beforehand that pending requests will be cancelled without a refund. No notice afterwards. | Same as T7 |
| T10 Sender blocks recipient | None (the sender did it) | Same as T7. **Must not reveal the block** [DECIDED]. |

**Consistency rule:** for every sender-side cancellation (T7–T10), the recipient sees the **same** neutral item status and receives no push, SMS or email. For recipient-side cancellations (T3–T6), the uniform "No longer pending, credit returned" message to the sender from v4.1 still applies.

*— End of verbatim extract —*

### 25.5 Account standing and notification eligibility (DCR-89) [TR-03; categories REC-BIZ, OD-02e, OPEN]

> *Verbatim from `docs/baseline/v4.6-F3/approved/07_v4.6.md` §5.1–5.2. Section references inside this block refer to that package.*

It lives in the central eligibility service (TR-03), reads the authoritative records, and **is the same predicate** used by:
- the account-state gate (v3 §8.4)
- v3 §9 step 8 (delegated access)
- the recovery-scope login (v4 §10.6)
- notification eligibility

| Standing (first match wins) | Source |
|---|---|
| `DELETED` | `AccountDeletionRequest.status = COMPLETED` |
| `DELETION_PROCESSING` | … `= PROCESSING` |
| `DELETION_RECOVERY` | … `= PENDING_RECOVERY` |
| `RESTRICTED_FULL` | An active `UserRestriction(FULL_ACCOUNT)`. This is an account-level suspension. |
| `RESTRICTED_LOGIN` | An active `UserRestriction(LOGIN)` |
| `DEACTIVATED` | `User.deactivated` / `is_active = false` |
| `ACTIVE` | None of the above |

**Profile-level conditions** are a separate input: profile SUSPENDED, PAUSED or CLOSED; a profile-level restriction; a restrictive identity hold (v4 §11.2). Write transactions evaluate standing under User `FOR SHARE` (and profile `FOR SHARE` where relevant). Delivery handlers evaluate it again.

##### 5.2 `can_notify(account, category, profile=None)` [REC-BIZ, OD-02e new sub-item]

| Category | Allowed standings | Profile conditions |
|---|---|---|
| **SECURITY** (sign-in, password, session revoked, deletion requested or cancelled) | All except `DELETION_PROCESSING` and `DELETED`. Security notices can't be turned off in preferences [DECIDED]. | Ignored |
| **ACCOUNT** (deletion-recovery reminders, restriction notices) | `ACTIVE`, `RESTRICTED_*`, `DEACTIVATED`, `DELETION_RECOVERY` | Ignored |
| **FINANCIAL** (refund returned, payment confirmed) | **`ACTIVE` only** | **Ignored:** credits belong to the account (FR-SUB-011), so a suspended or held profile doesn't hide account finance notices |
| **MATRIMONIAL_ACTIVITY** (interests, requests, messages, connections) | `ACTIVE` only | The profile must be `ACTIVE`, with no profile-level restriction and no restrictive identity hold. PAUSED → suppressed. |

Ordinary preferences (channel AND category) are applied after this check, as before.

**Effect on refunds (reconciles v4.5 §3.3):** the "credit returned" event is created only if `can_notify(debit_account, FINANCIAL)` is true. In every other case the refund is still recorded and shows in the account's financial history.

*— End of verbatim extract —*

**Addition (DCR-93):** the standing `RESTORE_QUARANTINED` is checked immediately after `DELETED` and is handled exactly like `DELETION_PROCESSING` (doc 09).

### 25.6 Financial events, late refunds and wallet closure (DCR-71, DCR-78, DCR-98) [TR-15; final treatment OD-07g, OPEN]

**Event classes:** an outbox event is either NOTIFICATION or FINANCIAL_OBLIGATION. **A financial event is a wake-up signal, never the record of the obligation**; every financial event type must be re-derivable from authoritative domain records. Nightly reconciliation checks that every qualifying CANCELLED request has a refund operation or a live event, and re-creates the event if not.

**Refunds during or after deletion PROCESSING:**

> *Verbatim from `docs/baseline/v4.6-F3/approved/06_v4.5.md` §4.1–4.2. Section references inside this block refer to that package.*

##### 4.1 Four separate steps

| Step | Who | What | When |
|---|---|---|---|
| **Record** the late refund | Refund transaction (§1, §3) | CreditOperation, CreditRefundOperation, lines, refund ledger rows (`post_closure=true`) | Always, for wallets in ACTIVE, CLOSED_RETAINED or DISPOSED |
| **Update** the projection | Same transaction | The purchased balance goes up. Allowance portions lapse because those allowances have expired. **The wallet status doesn't change.** | Same transaction |
| **Detect** the discrepancy | Nightly reconciliation | DISPOSED wallet with a balance above zero → `ReconciliationDiscrepancy(POST_DISPOSITION_CREDIT)`, plus an alert | Next run. **No automatic remediation.** |
| **Resolve** it | Finance, under dual approval | A new `DISPOSITION` operation applying **the approved OD-07g policy** → balance back to 0, discrepancy resolved with a reference to that operation | Manual |

##### 4.2 Database rules

- The wallet CHECKs are **only** `purchased_* ≥ 0`. There's deliberately **no** CHECK tying DISPOSED to a zero balance.
- **The trigger on non-ACTIVE wallets** rejects new rows with `entry_type IN ('USAGE','GRANT','PURCHASE')`. It **allows** `REFUND` credits and `DISPOSITION` / `ADJUSTMENT` operations.
- CreditTransaction CHECK: `entry_type='DISPOSITION' ⇒ operation_kind='DISPOSITION' AND direction='DEBIT'`.
- **DISPOSED can't be reached until OD-07g is approved,** because a final disposition needs an approved policy. Until then, closed wallets stay `CLOSED_RETAINED`. The recommended default is still: **retain balances, no forfeiture until there's an approved policy** (OD-07g, OPEN).

*— End of verbatim extract —*

**Undecryptable financial events after a restore:** an event whose queue-key version has been destroyed becomes `DEAD_UNDECRYPTABLE` (its `dedupe_key` is kept), a `ReconciliationDiscrepancy` is opened, and the obligation is re-derived before the restore startup gate opens (doc 09). The two-stage resolution:

> *Verbatim from `docs/baseline/v4.6-F3/approved/11_v4.6-F3.md` §1. Section references inside this block refer to that package.*

##### Revised specification text

> **ReconciliationDiscrepancy** (type `FINANCIAL_EVENT_UNDECRYPTABLE`) gains these columns:
> - `replacement_event_id` (nullable)
> - `last_check_at`
> - `last_check_result`: `AWAITING_REPLACEMENT` | `REPLACEMENT_PENDING` | `REPLACEMENT_FAILED` | `VERIFIED`
>
> Its `status` is OPEN or RESOLVED.
>
> **Locking:** only reconciliation transactions lock discrepancy rows. Such a transaction locks the outbox row(s) involved, in ascending ID order, then the discrepancy row(s). It holds no financial locks and only reads financial records. Refund handlers never lock discrepancy rows or other events' outbox rows, so no lock cycle is possible (consistent with v4.5 §1.2).
>
> **Stage 1: replacement created** (obligation still outstanding). In one transaction:
> 1. Lock the original outbox row, then its discrepancy row.
> 2. Re-derive the obligation from domain records: the request is CANCELLED with a refundable reason and has no verified `CreditRefundOperation`.
> 3. Insert the replacement FINANCIAL_OBLIGATION event, encrypted with the current queue key. The partial unique dedupe index allows only one live replacement.
> 4. Set the original's `replaced_by_event_id`. Its `obligation_resolution` **stays `PENDING`**.
> 5. Set the discrepancy's `replacement_event_id` and `last_check_result = REPLACEMENT_PENDING`. It **stays OPEN**.
> 6. **Don't write `FINANCIAL_EVENT_UNDECRYPTABLE_RESOLVED`.**
>
> **Stage 2: replacement verified.** This is triggered by a `FINANCIAL_RESOLUTION_CHECK` system event that the replacement's refund transaction emits when it commits as DONE, and by the nightly reconciliation. In one atomic transaction:
> 1. Lock the original outbox row, then its discrepancy row.
> 2. Require the replacement status to be `DONE`.
> 3. Re-run refund verification V1–V5 (v4.5 §3.1) against the request's `CreditRefundOperation`.
> 4. If both pass: `UPDATE original SET obligation_resolution='REPLACED_VERIFIED', resolved_at=now() WHERE id=:id AND obligation_resolution='PENDING'`.
> 5. **Only if exactly one row was updated:** mark the discrepancy RESOLVED (`last_check_result = VERIFIED`) and insert the AuditLog event `FINANCIAL_EVENT_UNDECRYPTABLE_RESOLVED` (plaintext: original and replacement event IDs and the resolution type; inside the debit account subject's envelope: the request and refund-operation IDs).
> 6. COMMIT. All four changes happen together or not at all.
>
> The conditional update makes this idempotent. A retry that finds the event already resolved changes nothing and writes no second audit event.
>
> **Replacement not yet done, failed, or unavailable:**
>
> | Situation | Discrepancy | Original event | What happens next |
> |---|---|---|---|
> | Replacement `PENDING` / `CLAIMED` | OPEN, `REPLACEMENT_PENDING` | `PENDING`, not redactable | Reconciliation checks again |
> | Replacement `DEAD` or `BLOCKED_INTEGRITY` | OPEN, `REPLACEMENT_FAILED`, alert | `PENDING`, not redactable | The replacement is requeued **in place** through an operator intervention. No second replacement is created while it exists. |
> | Replacement itself becomes `DEAD_UNDECRYPTABLE` (for example after another restore) | OPEN. The replacement gets its own discrepancy. | `PENDING` | Stage 1 runs for that replacement. Stage 2 for the original requires that the **last event in the replacement chain** is `DONE` and passes V1–V5. Every chain link's event and discrepancy then resolve in the same transaction, locked in ascending ID order. |
>
> **Obligation already satisfied** (`OBLIGATION_SATISFIED_VERIFIED`). In one transaction:
> 1. Lock the original outbox row, then its discrepancy row.
> 2. Run V1–V5 against the existing `CreditRefundOperation`.
> 3. If it passes: conditionally update the original to `OBLIGATION_SATISFIED_VERIFIED` and set `resolved_at`.
> 4. Only if exactly one row was updated: mark the discrepancy RESOLVED and insert the resolution audit event.
>
> **No replacement event and no refund are created.** If V1–V5 fails, the existing refund goes down the `BLOCKED_INTEGRITY` investigation path (v4.5 §3.1), and the discrepancy stays OPEN.

*— End of verbatim extract —*
>

### 25.7 Ledger operations (DCR-31) [TR-15]

| Operation | Ledger rows | Projection change |
|---|---|---|
| Debit | One row per bucket touched; a multi-bucket debit shares one `CreditOperation`. Allowance is consumed before purchased [DECIDED]. | Bucket decreased |
| Allowance grant | CREDIT, GRANT (subscription allowance) | New `CreditAllowance` with remaining = granted |
| Period-end expiry | EXPIRY, zeroing the remainder | Allowance → EXPIRED |
| Refund | CREDIT, REFUND, linked to the original debit through `CreditRefundLine` | Bucket increased |

Purchased credits have no expiry entry [DECIDED]. Corrections are compensating ADJUSTMENT operations under dual approval; nightly reconciliation never fixes anything automatically.

### 25.8 Subscription scenarios (DCR-30) [REC-BIZ, OD-09, OPEN]

- (a) Manual renewal for the MVP. Automatic renewal stays unapproved. The PAYMENT_FAILED/grace model stays in the schema, dormant; FR-SUB-008 applies unchanged if automatic renewal is ever approved.
- (b) Recommended: **remove the 3-day post-expiry window**. It gives no user benefit: it can't carry benefits [DECIDED: no paid benefits while expired], can't grant allowances for unpaid time [DECIDED], and backdating would charge users for days they didn't use. After expiry the user can renew at any time; the new term starts when payment is confirmed.
- (c) Early renewal is queued from the current `ends_at`, with no overlap.
- (d) No mid-term plan changes.

### 25.9 Account deletion recovery (DCR-41) [TR-21; flow REC-BIZ, OD-02d, OPEN]

**Endpoint paths (DR-2026-11-17-C4):** the canonical endpoints are those in doc 04 §15: `GET /account-deletion/` (status and end date) and `POST /account-deletion/{id}/cancel/`, plus `POST /auth/logout/`. The extract below keeps the baseline v4 §10.6 wording `/account/deletion/` and `/account/deletion/cancel/` for traceability only; those paths don't override the doc 04 catalogue. Endpoint behaviour is unchanged.

> *Verbatim from `docs/baseline/v4.6-F3/approved/01_v4.md` §10.6. Section references inside this block refer to that package.*

The doc 05 and doc 06 rule is [DECIDED]: "during recovery, public visibility and new activity are disabled; the user may cancel".

| Concern | Rule during PENDING_RECOVERY |
|---|---|
| 1. **Authentication to cancel** | Login with phone + password, **followed by a mandatory OTP**, creates a session with `scope=DELETION_RECOVERY` and a 15-minute absolute limit, with no refresh token (mobile gets a single 15-minute access token). Allowed endpoints: `GET /account/deletion/` (status and end date), `POST /account/deletion/cancel/`, `POST /auth/logout/`. Everything else returns `403 account_pending_deletion`. A FULL session can't be created. |
| 2. **Ordinary profile access** | None, including for the owner. Profile, search, settings and wallet endpoints aren't reachable in recovery scope. Data export during recovery isn't offered (REC-BIZ, OD-02d). The user should export before requesting deletion. |
| 3. **New matrimonial activity** | Disabled. The profile has no L0/L1/L2 for anyone (§9.2). Incoming approaches are rejected generically. Existing pending interests and requests stay as they are, and their expiry clocks keep running. They're closed if processing starts (OD-06f). Connections are frozen and shown as "No longer available". Messaging is denied. |
| 4. **Family-manager access** | Denied at runtime by v3 §9 step 8, with no change to the authorizations. Active managers get a neutral "profile unavailable" notice with no reason given (REC-BIZ, OD-02d). Access comes back automatically on cancellation, and the owner gets a notice suggesting they review their managers. |
| 5. **Sessions and tokens** | When the deletion request is confirmed (after the identity confirmation in OD-04c), **every** session is revoked in the same transaction, including the current one (`DELETION_REQUESTED`), with events and a security notification that includes how to cancel. |

**Cancellation:** in the recovery session, take a lock on `AccountDeletionRequest` FOR UPDATE and require status PENDING_RECOVERY and `now < recovery_ends_at`. Then:
- status → CANCELLED
- revoke the recovery session
- record the event and audit entry, and send a notification

The user then logs in normally. The profile's effective state returns automatically, because the deletion overlay (§7 row 22) never changed the profile status.

**Race with processing:** the PROCESSING job takes the same row lock and moves the request only when `now ≥ recovery_ends_at`. Whichever commits first wins. A cancel after the end time is refused with "recovery period ended".

**Processing:** login is denied, the processing steps are idempotent [DECIDED], and legal holds are evaluated [DECIDED].

**Tests (T-DEL):**
- 001: recovery login without OTP is denied.
- 002: a recovery session can't reach any other endpoint.
- 003: a manager is denied, then restored after cancellation.
- 004: a cancel racing processing has exactly one winner.
- 005: the profile is never visible during recovery.
- 006: the 15-minute recovery session limit is enforced.

*— End of verbatim extract —*

**Registry lifecycle (DCR-92, DCR-93):** the move to PROCESSING requires the Stream R `DELETION_INTENT` to be registered first; `DELETION_COMPLETED` is written only after every step has committed and been verified; a deletion that can't complete automatically goes to `BLOCKED_OPERATOR`, never to an aborted state (doc 09).

### 25.10 Closed connections, reopening and history (DCR-48, DCR-59, DCR-83)

- Reopen checks and states: doc 15 §19 [REC-BIZ, OD-06n, OPEN].
- Effects of entering CLOSED: doc 15 §7. Conversation history is kept read-only for both participants under the existing access and retention rules; no message is deleted because of closure.
- After one party's account is deleted, the other participant keeps read-only history per doc 03 §19, with the deleted party shown as anonymised.
- A manager reading closed history still needs `view_conversations` (Sensitive tier, 12-hour step-up), unchanged.
