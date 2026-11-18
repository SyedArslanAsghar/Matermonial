# Matermonial — Claude Code Detailed Instructions (Companion to CLAUDE.md)

**Document status:** APPROVED_WITH_OPEN_ITEMS (project owner, 2026-11-17, DR-2026-11-17-A; record in doc 20 §5). **Open items:** OPEN ODs: OD-07; PROPOSED TRs: TR-01, TR-02, TR-11, TR-17, TR-19, TR-23, TR-24. Listed items keep their own status (doc 19); this document status doesn't approve them. TR-09, TR-22 approved 2026-11-17 (DR-2026-11-17-G3). TR-13 approved 2026-11-17 (DR-2026-11-17-G2D-2). Its role as the detailed companion is approved (DR-2026-11-16-3).
**Matches:** root `CLAUDE.md` G1 revision (rule IDs CC-R01…CC-R79)
**Applied corrections:** DCR-45, DCR-12, DCR-42, DCR-50, DCR-53, DCR-58, DCR-63, DCR-66, DCR-72, DCR-73, DCR-80, DCR-81, DCR-82, DCR-87, DCR-91, DCR-94, DCR-95, DCR-97, DCR-99 (doc 20); G1 correction pass 2026-11-17 (DR-2026-11-17-C)
**Verbatim extracts:** each starts with a "*Verbatim from …*" (or "*Adapted from …*") line and ends with "*— End of verbatim extract —*". Text outside those markers is editorial.

## 1. How to use this document

- Root `CLAUDE.md` defines **what** Claude Code must and must not do. Each rule there has an ID (`CC-Rnn`).
- This document explains **how** to follow those rules in practice. It refers to rules by ID and **never restates them in different words**. If anything here appears to contradict `CLAUDE.md`, `CLAUDE.md` wins and this document must be corrected (record the correction in doc 20).
- Content marked [TR] is a **PROPOSED technical recommendation** unless doc 19 records it as approved. Follow it as the intended design, but don't describe it as an approved requirement (CC-R26). Content marked [REC-BIZ] belongs to an OPEN owner decision and must not be implemented (CC-R25).
- The approved baseline text is in `docs/baseline/v4.6-F3/` (CC-R06). Where this document copies baseline text verbatim, the block says so.

## 2. Working within the gates (CC-R24, CC-R25)

| Gate | Work allowed once authorized | Not allowed before this gate |
|---|---|---|
| G1 Documentation reconciliation | Apply DCR-01…DCR-99 to the documentation; create docs 18–20; record decisions | Any code, dependency, database, migration or Git change |
| G2 Repository governance | `git init` and baseline commit, branch policy, `.gitignore`, virtual environment in `backend/`, CI skeleton with PostgreSQL | App moves, migrations |
| G3 Backend foundation | Layout, settings, error envelope, logging, health checks, provider mocks, storage abstraction, Celery wiring. **No migrations.** | Domain models |
| G4 First migration | `User` (final), `AuthSession`, `AuthToken`, `AuditLog`, `OutboxEvent`, `IdempotencyRecord` and the G4 parts of TR-17/21/23/24 → migration `0001`, tested from an empty database | Feature models |
| G5 Features | Phases 2–19 (doc 10), each with its own scope approval | Behaviour depending on an unanswered OD sub-item; frontend work without an approved API contract |

**Procedure at the start of any task:**
1. Check `docs/implementation/progress.md` and `docs/decisions/` for the current gate and authorization.
2. Check doc 19 for every OD and TR the task touches. If a needed OD sub-item is OPEN, leave the dependent behaviour out of scope. In doc 18, record the dependency in the requirement's OD-dependency column; set the implementation status to BLOCKED only if the whole requirement depends on it (CC-R25).
3. Follow CC-R27 for the task steps.

## 3. Status reporting with evidence (CC-R69, CC-R70)

The three status dimensions are defined in doc 00 §9. In practice:

| Implementation status | Evidence Claude Code must attach |
|---|---|
| PLANNED | Phase reference; requirement APPROVED in doc 19 |
| BLOCKED | Blocker ID (OD, TR or dependency) |
| IN_PROGRESS | Branch name (from G2) |
| IMPLEMENTED | Files changed; commit hash |
| TESTED | The exact command, the actual result output, test IDs and commit hash. **Never set without real execution (CC-R59).** |
| REVIEWED / ACCEPTED | Not set by Claude Code (CC-R70) |

## 4. Coding patterns

- **Services and selectors (CC-R16):** a service performs one business operation inside one transaction, following the lock plan in §5. Selectors are read-only.
- **Acting profile (CC-R45):** every profile-scoped request builds an immutable `ActorContext` through the acting-profile algorithm in doc 04 [TR-02]. Services accept an `ActorContext`, never raw actor or profile IDs from the client. `billing_account` is always the owner of the represented profile.
- **Idempotency (CC-R39, CC-R52):** financial and retry-sensitive operations accept an `Idempotency-Key` and use deterministic idempotency keys internally (for example `refund:request:<request_id>`, doc 05).
- **Conflict handling:** inside a transaction, use `INSERT … ON CONFLICT` rather than catching `IntegrityError`, which would abort the PostgreSQL transaction.
- **No external calls inside a transaction.** Use the outbox (§6).

## 5. Transactions and locking [TR-09, TR-22, APPROVED]

**Status:** TR-09 and TR-22 are **APPROVED** (2026-11-17, DR-2026-11-17-G3-2; `CLAUDE.md` CC-R20). G3 builds the shared foundations (lock helpers, LOCK_PLAN tracker, lint rule, FK-inventory review). Their use in feature services starts with each G5 phase.

### 5.1 Account and profile locks

> *Verbatim from `docs/baseline/v4.6-F3/approved/03_v4.2.md` §17.1–17.2. Section references inside this block (for example "§3") refer to that package.*

##### 17.1 The anchor row [TR]

**The `User` row is the account's lock anchor.** It always exists, unlike `AccountDeletionRequest`.

**Every account-state change takes `User FOR UPDATE` before doing anything else.** That covers:
- deactivation and reactivation
- creating a deletion request, cancelling it, and moving it to PROCESSING
- applying or lifting an account-level `UserRestriction`
- an admin changing `is_active`

Creating an `AccountDeletionRequest` happens **while holding the User row lock**.

**Every operation that depends on an account's state takes `User FOR SHARE`** on each relevant account, then reads `is_active`, the restrictions and the deletion request.

**Why this closes the "no deletion request yet" race.** A dependent operation holding `User FOR SHARE` blocks the creation of a deletion request, because creation needs `FOR UPDATE` on the same row. The reverse also holds: a deletion request being created blocks the dependent operation until it commits, and the dependent operation then sees the new request. A partial unique index allowing one non-terminal deletion request per user (`status IN (REQUESTED, IDENTITY_VERIFICATION_REQUIRED, PENDING_RECOVERY, PROCESSING)`) is the backstop (DCR-61).

##### 17.2 Which accounts each operation locks

`ACC(...)` means: `SELECT … FROM user WHERE id IN (…) ORDER BY id FOR SHARE`. PostgreSQL locks rows in the order they're returned, so ordering by ID gives a deterministic order. Duplicates are removed first.

| Shorthand | Accounts included |
|---|---|
| **ACC-pair** | The actual account (if it's a manager) + the owner of the represented profile + the owner of the counterparty profile |
| **ACC-self** | The actual account (if it's a manager) + the owner of the represented profile |

*— End of verbatim extract —*

> *Adapted from `docs/baseline/v4.6-F3/approved/03_v4.2.md` §18.1–18.2. Section references inside this block (for example "§3") refer to that package. Editorial change: a conversational phrase addressed to the reviewer was removed from one sentence in §18.1; the text is otherwise verbatim.*

##### 18.1 Two separate lock types [TR]

| Lock | What it is | What it protects | Modes |
|---|---|---|---|
| **Profile lock** | A row lock on `MatrimonialProfile` (level 3) | Profile status, visibility mode, profile-level restrictions and the identity hold. Anything that changes these takes `FOR UPDATE` on that one profile row (§17.3). | `FOR SHARE` for dependent operations, on all relevant profiles, ascending ID, **always before pair locks** |
| **Pair advisory lock** | A transaction-level advisory lock on a synthetic key built from the pair (level 4) | Pair relationship state: blocks, hides, cooldowns, interests, requests, connection, reopen requests | Exclusive for changes. Shared for operations that need that state to stay put but don't change it. |

They don't stand in for each other. A profile lock doesn't stabilise pair state, and a pair lock doesn't stabilise profile status.

Profile-status changes use **`FOR UPDATE`**. These include the owner pausing or resuming the profile, suspension and its lifting, closure, an identity decision that changes `identity_verified_at` or creates the restrictive hold, profile-level restrictions, and visibility-mode changes.

##### 18.2 Protective actions [TR]

Some actions must always succeed, whatever state the counterparty is in, because they reduce exposure:
- block, unblock
- add or remove from Hide My Profile From
- close a connection, pause a connection
- revoke a document permission
- authorization pause, revoke, resign

These take **ACC-self only, no profile locks**, plus the exclusive pair lock where pair state changes. Unblocking still doesn't restore eligibility on its own [DECIDED, FR-PRI-002], because eligibility is re-checked by every dependent operation.

*— End of verbatim extract —*

### 5.2 Exclusive-lock anchors (DCR-82)

**Definition:** "anchor" means only an exclusive `FOR UPDATE` on a `User` row (account-state anchor) or a `MatrimonialProfile` row (profile-state anchor). A transaction holds **at most one** anchor. The prerequisite `FOR SHARE` locks listed below are allowed. Other exclusive row locks (authorization `FOR UPDATE`, wallet, allowances, domain rows, the level 9 outbox row) aren't anchors; they follow the level order in §5.3.

> *Verbatim from `docs/baseline/v4.6-F3/approved/04_v4.3.md` §3. Section references inside this block (for example "§3") refer to that package.*

There are two kinds of anchor. **A transaction holds at most one anchor.**

| | **Account-state anchor** | **Profile-state anchor** |
|---|---|---|
| Anchor row | One `User` row, `FOR UPDATE` | One `MatrimonialProfile` row, `FOR UPDATE` |
| Used by | Deactivation and reactivation; deletion request create, cancel and move to PROCESSING; account-level restriction apply or lift; admin `is_active` change | Profile pause and resume by the owner; suspension and its lifting; closure; visibility-mode change; identity decision (`identity_verified_at`, restrictive hold); profile-level restriction |
| **Allowed before the anchor** | **None.** The User row is the first lock. Admin actors aren't locked. | Level 1: the authorization row `FOR SHARE` (manager path, if the action can be delegated). Level 2: ACC-self User rows `FOR SHARE` (owner or manager actor), **not** for staff actions. **Nothing else.** |
| **Allowed after the anchor** | Only that account's own level 2 rows, in order: AccountDeletionRequest → account-level UserRestriction → AuthSession → AuthToken. Then level 8 inserts. | Only that profile's own level 3 rows: profile-level UserRestriction, the identity-verification cycle row, the identity-hold row. Then level 8 inserts. |
| **Prohibited after the anchor** | Any other User row. Any profile row. Pair locks. Wallet. Allowances. Level 7 domain rows. Account-scoped financial rows. | **Pair advisory locks (shared or exclusive), wallets, allowances, any other profile row, any account row, and any level 7 domain row.** |
| Effects on other parties | Separate fan-out transactions after commit, through the outbox | Same |

**Deletion → PROCESSING is now split into two transactions**, so no transaction holds two anchors (replaces the v4.2 matrix row):
- **Tx 1, account anchor:** User U → AccountDeletionRequest (→ PROCESSING) → AuthSession → AuthToken.
- **Tx 2, profile anchor:** ACC-self `FOR SHARE` → own profile U → CLOSED.

Between the two, dependent operations already refuse, because they read the PROCESSING state under User `FOR SHARE`. Then come the fan-out transactions: one per pair, one per authorization, one per refund.

**Consistency with the matrix:** every row taking `Ac U` or `Pr U` has been rechecked. Each shows no Pair, W, Al or D column, and each fans out effects afterwards. The protective action "Profile status change (owner)" already matches: A S*, Ac sh ACC-self, then Pr U self.

*— End of verbatim extract —*

### 5.3 Global lock order (ADR-031)

Locks are acquired in this order. Levels can be skipped, never revisited. (Merged final wording of baseline v4.2 "Revised global lock order", v4.3 §5 insert order and v4.5 §1.1 level 9.)

| Level | Locks |
|---|---|
| 1 | **Authorization row:** `FOR SHARE` (delegated action) or `FOR UPDATE` (pause, revoke, permission change) |
| 2 | **Account:** `User` rows first (`FOR SHARE`, ascending, for dependents; `FOR UPDATE` on a single account for state changes). Then, for one account only: AccountDeletionRequest → account-level UserRestriction → UserSubscription → SubscriptionBillingPeriod → Payment / RefundRequest / AdjustmentRequest → AuthSession → AuthToken |
| 3 | **Profile:** `MatrimonialProfile` rows (`FOR SHARE`, ascending, for dependents; `FOR UPDATE` on a single profile for status changes). Then profile-level restriction, identity-verification cycle or identity-hold rows. Then profile quota advisory locks. |
| 4 | **Pair advisory locks:** shared or exclusive, ascending key |
| 5 | **Wallet** `FOR UPDATE` (only one per transaction) |
| 6 | **Allowances** `FOR UPDATE`, ordered by `expires_at, id` |
| 7 | **Domain rows**, in type order: ProfileBlock → HiddenProfile → DirectionalCooldown → Interest → MatrimonialRequest → ProfileConnection → ConnectionReopenRequest → RelationshipProgress → Conversation → DocumentPermission |
| 8 | **Inserts only**, in this order: CreditOperation → CreditRefundOperation → CreditTransaction → CreditRefundLine → domain records (history, ProfileView, VisitorHistory, Message, access history, ManagerActionLog, ProfileAccessHistory) → AccountSecurityEvent → AuditLog → OutboxEvent |
| 9 | **The transaction's own claimed outbox row, completion only.** Always the last lock taken (§6). |

**General rules:**
- One aggregate per transaction for bulk jobs and fan-out work.
- No external calls inside a locking transaction.
- Never take `FOR SHARE` and then `FOR UPDATE` on the same row in one transaction.
- Never take a pair lock after a wallet lock.
- Use READ COMMITTED for pair-scoped writes, so reads after the pair lock see the latest committed rows (doc 05, lazy expiry).
- **Separate lock domains:** maintenance tables (`maintenance_operation`, `registry_stream_head`) are locked only by maintenance jobs (doc 09). `ReconciliationDiscrepancy` rows are locked only by reconciliation transactions, after the outbox rows they concern (doc 05).

**Deadlock and retry policy:**
- Each transaction sets `lock_timeout = 5s` (configurable).
- A `@retry_on_contention` decorator on service entry points retries the **whole transaction** on SQLSTATE 40P01 (deadlock), 40001 (serialization failure) and 55P03 (lock not available): up to 3 attempts with jittered backoff (50–400 ms). If they all fail, return `503 temporarily_unavailable` with `Retry-After`.
- Retrying is safe because every side effect (ledger, history, outbox) is inside the transaction, and financial operations also carry idempotency keys.
- Each retry is logged with a metric.

### 5.4 Service-level lock-order compliance matrix (DCR-50, DCR-53, DCR-58)

**Column codes:**

| Code | Meaning |
|---|---|
| A | Authorization row: S* = FOR SHARE on the manager path only; U = FOR UPDATE |
| Ac | User rows: sh = FOR SHARE (ascending), U = FOR UPDATE (single account) |
| Ac+ | Other account-scoped rows (one account) |
| Pr | Profile rows: sh = FOR SHARE (ascending), U = FOR UPDATE |
| Pair | Pair advisory lock: X = exclusive, S = shared |
| W / Al | Wallet / allowances |
| D | Domain row locks |

(Final merged matrix: baseline v4.2 matrix, with the rows replaced by v4.3 §2.4 and §3, v4.5 §6.1 and the v4.5/v4.6-F3 outbox and reconciliation transactions.)

| Service | A | Ac | Ac+ | Pr | Pair | W | Al | D | Level 8–9 |
|---|---|---|---|---|---|---|---|---|---|
| Express interest (+ auto-reciprocate) | S* | sh ACC-pair | — | sh both + sender quota | X | — | — | Block, Hidden, Cooldown (read) → Interest | History, audit, outbox |
| Reciprocate / decline / withdraw interest | S* | sh ACC-pair | — | sh both | X | — | — | Interest | Cooldown, history, audit, outbox |
| Create request | S* | sh ACC-pair | — | sh both | X | billing | ✓ | Block, Hidden, Cooldown (read) → Interest → Request | Ledger → request, history → audit → outbox |
| Convert interest → request | S* | sh ACC-pair | — | sh both | X | billing | ✓ | Interest → Request | Same |
| Accept request | S* | sh ACC-pair | — | sh both | X | — | — | Request | Connection, progress, conversation, history, audit, outbox |
| Decline / withdraw request | S* | sh ACC-pair | — | sh both | X | — | — | Request | Cooldown (decline), history, audit, outbox |
| Expiry worker | — | sh both owners | — | sh both | X | — | — | Interest / Request | Cooldown, history, outbox |
| Admin cancel request (T1/T2) | — | sh both owners | — | — | X | — | — | Request | History, audit, outbox (REFUND_DUE for T2) |
| Cancellation fan-out (T3–T10) | — | sh both owners | — | sh both | X | — | — | Request | History, audit, outbox (REFUND_DUE for T3–T6) |
| Request refund (outbox handler) | — | sh debit account | — | — | — | ✓ | ✓ | Request (read) | CreditOperation → CreditRefundOperation → ledger → lines → audit → outbox; then level 9 completion |
| Block | S* | sh ACC-self | — | — | X | — | — | Interest → Request | ProfileBlock, history, audit, outbox (REFUND_DUE) |
| Unblock / hide / unhide | S* | sh ACC-self | — | — | X | — | — | Block / Hidden | History, audit |
| Pause / close connection | S* | sh ACC-self | — | — | X | — | — | Connection | History, audit, outbox |
| Resume / complete connection | S* | sh ACC-pair | — | sh both | X | — | — | Connection | Same |
| Reopen initiate / confirm | S* | sh ACC-pair | — | sh both | X | — | — | Connection → ReopenRequest | Same |
| Progress update | S* | sh ACC-pair | — | sh both | X | — | — | Connection (read) → Progress | History, outbox |
| Send message / upload attachment | S* | sh ACC-pair | — | sh both | **S** | — | — | Conversation (read) | Message, ManagerActionLog, audit (S tier), outbox |
| Document share | S* | sh ACC-pair | — | sh both | X | — | — | DocumentPermission | History, audit, outbox |
| Document access | S* | sh ACC-pair | — | sh both | **S** | — | — | DocumentPermission (read) | Access history, audit |
| Document revoke | S* | sh ACC-self | — | — | X | — | — | DocumentPermission | History, audit, outbox |
| Profile-view POST | S* | sh ACC-pair | — | sh viewer + target | **S** | billing | ✓ | — | CreditTransaction → ProfileView → VisitorHistory → AuditLog → OutboxEvent |
| Profile-detail GET | S* (read) | — | — | — | — | — | — | — | None. Read-only REPEATABLE READ snapshot with request deadline (§7). |
| Profile status change (owner) | S* | sh ACC-self | — | **U** self | — | — | — | — | History, audit, outbox (fan-out afterwards) |
| Suspension / identity decision / profile restriction (staff) | — | — | — | **U** self | — | — | — | — | Same |
| Account deactivation / reactivation | — | **U** self | Session → Token | — | — | — | — | — | Security event, audit, outbox |
| Account restriction apply / lift | — | **U** self | Restriction → Session → Token | — | — | — | — | — | Same |
| Deletion request create / cancel | — | **U** self | DelReq → Session → Token | — | — | — | — | — | Same |
| Deletion → PROCESSING, Tx 1 (account anchor) | — | **U** self | DelReq → Session → Token | — | — | — | — | — | Same |
| Deletion → PROCESSING, Tx 2 (profile anchor) | — | sh self | — | **U** own profile | — | — | — | — | History, audit; fan-out per pair, per authorization, per refund afterwards |
| Deletion financial step | — | sh self | — | — | — | ✓ | ✓ | — | Expiry ledger entries; wallet → CLOSED_RETAINED |
| Login / refresh / logout | — | sh self | Session → Token | — | — | — | — | — | Security event |
| Payment confirmation | — | sh self | Sub → Period → Payment | — | — | ✓ | ✓ (insert) | — | Ledger, audit, outbox |
| Payment refund / admin adjustment | — | sh self | Payment / Adjustment | — | — | ✓ | ✓ | — | Ledger, audit |
| Allowance expiry job | — | sh self | — | — | — | ✓ | ✓ | — | Ledger |
| Reconciliation job (checks) | — | — | — | — | — | — | — | — | Discrepancy rows (read-only snapshot) |
| Reconciliation resolution (financial discrepancy) | — | — | — | — | — | — | — | — | Locks outbox row(s) ascending → discrepancy row(s); reads financial records only; inserts replacement event and audit |
| Outbox claim (Tx-C) | — | — | — | — | — | — | — | — | Outbox rows only, `SKIP LOCKED`, committed before business work |
| Authorization pause / revoke / resign / permission change | **U** | sh ACC-self | — | — | — | — | — | Permission rows | ManagerActionLog, audit, outbox |
| K_rot mass revocation | — | sh per account | Session → Token | — | — | — | — | — | Security event |

**Business-rule dependencies in the matrix:** the `REFUND_DUE` entries (T2, T3–T6) and the refund-handler row describe locking only. Whether a given cancellation trigger refunds, including the T2 administrative cancellation, is **OD-07b (OPEN)**; only the administrative cancellation itself (CANCELLED with a reason, no cooldown) is DECIDED (doc 05 §25.2).

### 5.5 Implicit foreign-key locks (DCR-63, DCR-81)

> **Superseded in part — read this first (DCR-94; C-44, C-53, C-60).** Row **F2** of the extract below is the original v4.3 wording. Its statement that `AuditLog`, `AccountSecurityEvent` and `OutboxEvent` store `actor_user_id`, `user_id`, `subject_*_id`, `represented_profile_id`, `session_id`, `authorization_id` and recipient IDs as **plain UUID columns** is **superseded** and is **not** the current design. Only F2's "no database FK on these log columns" part still applies. The current rule is in the amendment directly after the extract.

> *Adapted from `docs/baseline/v4.6-F3/approved/04_v4.3.md` §1.1–1.4. Section references inside this block (for example "§3") refer to that package. Editorial change: a conversational phrase addressed to the reviewer was removed from one sentence in §1.1; the text is otherwise verbatim, including the superseded F2 row kept for traceability.*

##### 1.1 How PostgreSQL behaves

**When a row with a foreign key is inserted** (or its FK column is updated), PostgreSQL checks the referenced row with `SELECT 1 … FOR KEY SHARE`. That implicit lock:
- conflicts with **`FOR UPDATE`** on the referenced row, and with `DELETE` or an update of a key column
- does **not** conflict with `FOR SHARE`, `FOR KEY SHARE` or `FOR NO KEY UPDATE`

A plain UPDATE of non-key columns takes `FOR NO KEY UPDATE`, so it doesn't conflict with that check.

**v4.2 uses explicit `FOR UPDATE`** on `User` (account-state changes) and `MatrimonialProfile` (status changes). So **any insert anywhere that references a User or profile row being changed will wait** for that state change to finish.

**On delete actions:** `ON DELETE CASCADE` or `SET NULL` on a referenced row locks and changes the rows that point to it.

##### 1.2 The hazard

An implicit FK lock is taken at **level 8** (the insert), but it lands on a **level 2 or level 3 row**. In effect, a lock is acquired late and out of order. This is how a deadlock forms:
- Transaction T1 holds some lock L and then inserts a row pointing to User U, so it waits for `KEY SHARE` on U.
- Transaction T2 holds U `FOR UPDATE` and then asks for L.

Each is waiting for the other. The confirmed case from v4.2 is **refresh vs. deletion**: refresh held `AuthSession` and inserted an `AccountSecurityEvent` pointing at User, while deletion held User and waited for `AuthSession`.

##### 1.3 Where implicit FK locks occur

| Inserted row | Points to | Already safe? |
|---|---|---|
| Domain history `performed_by` (all history tables) | Actor's User | Yes. The actor is always in the ACC set, so the transaction already holds `FOR SHARE`. |
| History `performed_for_profile`, Interest, Request, Connection, Message rows | Represented and counterparty profiles | Yes for dependent operations (PRF set). For protective actions, see F3. |
| `ProfileBlock.blocked_profile`, `HiddenProfile.hidden_profile` | Counterparty profile | F3 (bounded wait) |
| `ProfileView` (viewer user, viewer profile, target profile, credit transaction) | All share-locked or inserted in the same transaction | Yes (v4.2 C21) |
| `AuthSession.user`, `AuthToken.session` | User, AuthSession | F5 |
| `ManagerActionLog`, `ProfileAccessHistory` (manager, profile, authorization) | Locked at levels 1–3 in the same transaction | Yes |
| `AuditLog` actor and subject, `AccountSecurityEvent.user`, `OutboxEvent` recipients | Any account or profile, including counterparties and accounts not otherwise locked | **No.** Fixed by F2. |

##### 1.4 Fixes [TR]

| # | Fix | TR / DCR |
|---|---|---|
| **F1** | **"Reference means prior lock" rule:** every User or profile row that a transaction's inserts will point to (through a database FK) must already be locked by that transaction at its proper level (`FOR SHARE` or stronger) before any later-level lock is taken. A transaction never waits against its own lock, and a competing `FOR UPDATE` holder would have blocked the earlier, correctly ordered share lock instead. | TR-09 / DCR-53 |
| **F2** | **Soft references for append-only logs:** `AuditLog`, `AccountSecurityEvent` and `OutboxEvent` store `actor_user_id`, `user_id`, `subject_*_id`, `represented_profile_id`, `session_id`, `authorization_id` and recipient IDs as **plain UUID columns with no database FK**. That removes implicit locks from the tables written in almost every flow, including flows that mention accounts which aren't locked. It also keeps these records valid after deletion anonymises identifiers (doc 03 §19, FR-DAT-009). Integrity comes from: the service writes only IDs from its own ActorContext or locked rows; a nightly check reports dangling IDs; and the logs are append-only by trigger. | **TR-23 / DCR-60** |
| **F3** | **Allowed bounded waits:** protective actions (block, hide) insert rows pointing to the **counterparty profile** without share-locking it, so the block never depends on the counterparty's state. Their FK check can **wait** while a counterparty profile-anchor transaction finishes. **That can't become a deadlock**, because a profile-anchor transaction takes no further locks after its anchor (§3). The wait is bounded by the anchor transaction's length and `lock_timeout`. | TR-09 / DCR-63 |
| **F4** | **No cascading deletes on hot referenced rows.** FKs to `User` and `MatrimonialProfile` use `PROTECT` (or `SET NULL` only on log-like tables, which use soft references anyway). Accounts are anonymised, not hard-deleted, during business transactions [doc 03 §19]. | TR-09 / DCR-53 |
| **F5** | **Authentication flows take User `FOR SHARE` first** (login, refresh, logout, session revocation), before AuthSession or AuthToken | TR-01 / DCR-54 |
| **F6** | **Detection:** the LOCK_PLAN tracker only sees explicit locks (§6), so implicit locks are covered by F1–F5 by design and checked by the PostgreSQL concurrency tests in §6 | TR-22 / DCR-66 |

*— End of verbatim extract —*

**Amendment to F2 — current rule (supersedes the F2 identifier wording above; baseline v4.4 §1 "revises TR-23", v4.5 §2.4, v4.6 §1; DCR-60, DCR-67, DCR-76, DCR-84, DCR-94) [TR-23, TR-11 PROPOSED]:**
- **Still applies from F2:** these log and queue tables have **no database foreign keys** on their identity columns, so their inserts take no implicit FK locks (inventory class S, below).
- **`AuditLog` and `AccountSecurityEvent`** never store a raw `user_id`, `profile_id` or other account/profile ID. Actor, subject and represented-profile references are **pseudonyms** (`actor_pseudonym`, `subject_pseudonym`, `represented_profile_pseudonym`). Personal context (IP address, user agent, location) and every **linkable identifier** (`session_id`, `authorization_id`, IDs of person-owned resources, ledger `account_id`) are stored **only inside the owning subject's encrypted envelope** in `enc_parts`. Plaintext is limited to event facts, pseudonyms, `resource_type` and `request_id`. Definitions: doc 03 §22.2 and §22.15; doc 06 §22.3 (amendment) and §22.6.
- **`OutboxEvent`** never stores raw user, profile or resource IDs. It holds `recipient_pseudonym`, an HMAC `dedupe_key`, and `payload_enc` (aggregate ID and handler parameters encrypted with the queue key). Definition: doc 03 §22.12.
- If anything in the extract above conflicts with these points, these points and doc 03 §22.2/§22.12 apply.

> *Verbatim from `docs/baseline/v4.6-F3/approved/06_v4.5.md` §6.1. Section references inside this block (for example "§3") refer to that package.*

##### 6.1 Implicit FK-lock inventory (doc 12, DCR-81)

| Class | Meaning | Members |
|---|---|---|
| **P: prior-locked** | The transaction already holds `FOR SHARE` or stronger on the referenced row, so it can't wait on its own lock | History `performed_by` (actor in ACC). `performed_for_profile` / domain-row profile FKs in dependent operations (PRF). ProfileView FKs. `CreditTransaction.account_id` in request, refund, payment and **allowance-expiry** transactions (debit-account User share). DocumentPermission and Message actor and profile FKs. ManagerActionLog and ProfileAccessHistory. AuthSession and AuthToken (User share, F5). |
| **S: soft reference** | No FK, no implicit lock | AuditLog, AccountSecurityEvent, OutboxEvent (pseudonyms and envelopes), MaintenanceAuditLog, compliance-registry cache |
| **B1: counterparty profile in a protective action** | Can wait only on that profile's profile-anchor transaction, which takes nothing afterwards (§3 rules), so the wait is bounded and can't form a cycle | `ProfileBlock.blocked_profile`, `HiddenProfile.hidden_profile` |
| **B2: staff actor User** | Can wait only on that staff member's account anchor, which locks only the staff member's own level 2 rows, so it can't form a cycle | `performed_by`, `reviewed_by`, `created_by` and `updated_by` where the actor is staff, in staff-initiated profile-anchor, account-anchor and moderation transactions (including the `User.updated_by` self-FK) |
| **N: holds no other locks** | The transaction holds no row or advisory locks when the FK check runs, so waiting can't contribute to a cycle | Reconciliation's discrepancy inserts. Retention or maintenance inserts. |

**Rule:** any new FK added later must be assigned a class in doc 12 at design review. Anything unclassified fails the review checklist.

*— End of verbatim extract —*

---

### 5.6 What the LOCK_PLAN tracker covers (DCR-66)

Each service declares a `LOCK_PLAN`. In test and debug settings, a lock-acquisition tracker raises an error on any out-of-order explicit acquisition. Service modules use the project's lock helpers; a lint rule flags `raw()`, `extra()` and `cursor.execute` in service modules.

> *Verbatim from `docs/baseline/v4.6-F3/approved/04_v4.3.md` §6.1. Section references inside this block (for example "§3") refer to that package.*

##### 6.1 What the tracker can and can't do [TR-22, clarified]

- **Detects:** explicit locks taken through the project's lock helpers (`select_for_update` / `FOR SHARE` wrappers, advisory-lock helpers), checked against each service's declared LOCK_PLAN and the global order.
- **Can't detect on its own:**
  - implicit FK `KEY SHARE` checks
  - row locks taken by plain UPDATE or DELETE outside the helpers
  - unique-index insertion waits
  - locks from database triggers
  - locks taken by raw SQL that bypasses the helpers
- **How those are covered instead:**
  - by design: F1–F5 and the anchor rules in §3
  - by convention and review: business locks must go through the helpers, and a lint rule flags `raw()`, `extra()` and `cursor.execute` in service modules
  - by the PostgreSQL integration tests below
  - in production: `log_lock_waits=on`, a deadlock-count alert, and a metric on retry rate
- Selected tests also take `pg_locks` snapshots, as a diagnostic aid. **That isn't a completeness guarantee.**

*— End of verbatim extract —*

## 6. Outbox processing (DCR-73) [TR-11]

**Approved core vs proposed refinements (DR-2026-11-17-C2):**
- **Approved core** [DECIDED; FR-NOT-005, `CLAUDE.md` CC-R30, ADR-014 core]: a business transaction that needs asynchronous follow-up writes an outbox record **in the same database transaction**; a background worker processes it after commit with bounded, retryable delivery; processing is idempotent, so duplicates don't repeat the business effect.
- **Proposed refinements** [TR-11, ADR-028, PROPOSED]: everything else in this section and in doc 03 §22.12, including the two-phase claim/lease processing, level 9 completion, event classes, the queue key and encrypted payload, pseudonymous recipients, dedupe key and redaction. Follow them as the intended design, but don't describe them as approved (CC-R26).

> *Verbatim from `docs/baseline/v4.6-F3/approved/06_v4.5.md` §1.1–1.2. Section references inside this block (for example "§3") refer to that package.*

##### 1.1 Two-phase outbox processing (applies to every outbox handler, not just refunds)

**Tx-C (claim): short, on its own, committed before any business work.**

```sql
UPDATE outbox_event SET status='CLAIMED', lease_token=:new_token,
       lease_expires_at = now() + :lease, attempts = attempts + 1
WHERE id IN (SELECT id FROM outbox_event
             WHERE status='PENDING'
                OR (status='CLAIMED' AND lease_expires_at < now())
             ORDER BY id LIMIT :n FOR UPDATE SKIP LOCKED)
RETURNING id, lease_token;
```

Then COMMIT. Tx-C locks only outbox rows, never waits for them (`SKIP LOCKED`), and acquires nothing else.

**Tx-R (refund handler): one atomic transaction.** Locks are taken in the global order, and the outbox row is touched **last**:

| Step | Level | Action |
|---|---|---|
| 1 | 2 | Debit account `User FOR SHARE` |
| 2 | 5 | Wallet `FOR UPDATE` |
| 3 | 6 | Allowances `FOR UPDATE` |
| 4 | 7 | Request read |
| 5 | 8 | Get-or-verify the refund (§3), ledger, lines, audit, conditional notification (§3.3) |
| 6 | **9 (new)** | `UPDATE outbox_event SET status='DONE' WHERE id=:id AND lease_token=:token AND status='CLAIMED'`. **If 0 rows are updated, the lease was lost: raise, and the whole of Tx-R rolls back.** |
| 7 | — | COMMIT |

**Level 9** is added to the global order: "the transaction's own claimed outbox row, completion only". It is always the last lock taken.

**Retry behaviour:**

| Failure | What happens |
|---|---|
| Any failure in Tx-R | Full rollback. The event stays CLAIMED until its lease expires, then Tx-C claims it again. |
| Worker crash between Tx-C and Tx-R | The lease expires and the event is claimed again |
| Crash after Tx-R commits | The event is already DONE |
| `attempts` reaches its maximum | → `DEAD`, and an alert fires. **Financial events (`REQUEST_REFUND_DUE`) are never dropped.** `DEAD` needs operator action. |
| Account deletion | Cancels **notification-class** events only. **Financial events are never cancelled.** |

##### 1.2 Why there can't be an outbox ↔ financial lock cycle

Only these transactions lock **existing** outbox rows:

| Transaction | Holds while touching outbox rows | Waits on |
|---|---|---|
| Tx-C (claim) | Nothing else | Nothing (`SKIP LOCKED`). So it has **no outgoing wait edges.** |
| Handler completion (level 9) | Levels 1–8 locks, already acquired | Its own single outbox row. It acquires **nothing after** that row, only commits. So once it holds an outbox row it has **no outgoing edges.** |
| Deletion's notification cancellation | Nothing else | Other outbox rows, in ID order |
| Retention purge | Nothing else | DONE / CANCELLED / DEAD rows, `SKIP LOCKED` |

Outbox **inserts** (level 8) create new rows. They take no locks on existing outbox rows, and OutboxEvent uses soft references (no FKs).

For a cycle, some transaction would have to hold an outbox row and then wait for a financial (or any other) lock. None of the transactions above does that. So no cycle can include an outbox row.

**Tests:**
- **T-CONC-033:** a handler holding wallet locks while another transaction claims or cancels events → no deadlock.
- **T-CONC-034:** the lease expires mid-handler and the event is claimed again → the old handler rolls back at step 6, and the new handler completes exactly once.
- **T-CONC-035:** a financial event survives deletion's event cancellation.

*— End of verbatim extract —*

Event classes, the queue key, redaction and the financial-obligation rules are specified in doc 03 (OutboxEvent) and doc 05 (refunds).

## 7. Read paths: profile-detail GET (DCR-64, DCR-72) [TR-19]

The specification is in doc 04 and doc 06. Implementation procedure:
- Open one `READ ONLY, REPEATABLE READ` transaction per GET. Re-check the session and account gate and every access rule inside that snapshot; read the data from the same snapshot.
- Set the request deadline D (default 3 s, `PROFILE_DETAIL_DEADLINE_MS`). A Django `execute_wrapper` computes the remaining time before every statement, raises `DeadlineExceeded` when it reaches zero, and otherwise runs `SET LOCAL statement_timeout = min(remaining, 5000 ms)`.
- Build the whole response in memory, check the deadline once more, then commit and release it. On any deadline failure, roll back and return `503 request_deadline_exceeded` with `Retry-After`, an error envelope and no profile data (baseline v4.4 §5.2).
- Backstops: `idle_in_transaction_session_timeout = 5 s`, the web-server worker timeout, and `SET LOCAL transaction_timeout` on PostgreSQL 17 or later.

## 8. Testing procedures (DCR-80) [TR-13, APPROVED 2026-11-17, DR-2026-11-17-G2D-2]

- Concurrency tests (T-CONC, T-LOCK) use **pytest-django `@pytest.mark.django_db(transaction=True)`** (Django `TransactionTestCase` semantics: real COMMITs, tables flushed between tests).
- Each thread uses **its own connection** from `django.db.connections` and closes it in `finally`. No test runs inside the `TestCase` wrapping `atomic` block.
- Barriers are PostgreSQL advisory locks taken by the test harness. `lock_timeout` is set per connection.
- Every test asserts on **committed** state read through a fresh connection.
- **T-HARNESS-001:** a deliberately uncommitted write must not be visible to the checking connection, which proves real separation.
- CI runs on PostgreSQL 16 and 18 (doc 08).
- The full test catalogue and suites are listed in doc 08. A test ID in any document is a **specification** until it has been written and executed (CC-R59).

## 9. Maintenance, registry and recovery operations (DCR-87, DCR-91, DCR-95, DCR-97, DCR-99) [TR-24]

The protocol is specified in doc 09. Procedure rules for Claude Code:
- Never run a maintenance action outside the maintenance-operation protocol. Every kind must be in the catalogue (doc 09).
- Registry entries are written **before** any irreversible database effect, and completion entries only **after** verification.
- **Stream R operations are never aborted.** If one can't complete, it goes to `BLOCKED_OPERATOR`, which needs an `OPERATOR_INTERVENTION` with two distinct approvers (neither of them the requester).
- Never guess a key-to-KEK association, a companion's content or a cache row. Missing evidence means `BLOCKED_OPERATOR`.
- Never copy, print or log secret values (keys, tokens, passwords, provider credentials).

## 10. Documentation update procedure (CC-R63, CC-R64)

1. Change the relevant handover document(s).
2. Record the change in doc 20 (DCR and location). For a new decision, add a decision record in `docs/decisions/new_architecture_decisions.md` and, where it is architectural, an ADR (doc 11).
3. Update doc 19 statuses only when an approval is recorded.
4. Update doc 18 rows (requirement status, implementation status, tests).
5. Update `docs/implementation/*`.

## 11. Review checklist

- [ ] Every service has a `LOCK_PLAN` that follows §5.3 and matches §5.4 [TR-09/TR-22, APPROVED].
- [ ] No raw user, profile, session, authorization or resource ID is written in plaintext to `AuditLog`, `AccountSecurityEvent` or `OutboxEvent` rows (§5.5 amendment; doc 03 §22.2, §22.12).
- [ ] Every new foreign key is assigned an implicit-lock class (§5.5). Unclassified foreign keys fail review.
- [ ] No external call inside a transaction; side effects go through the outbox.
- [ ] No implementation depends on an OPEN OD sub-item or an unapproved TR presented as approved.
- [ ] Serializers use explicit field allowlists; no hidden or blocked relationship is revealed.
- [ ] No secrets, OTPs, tokens or document contents in logs.
- [ ] Tests cover the CC-R57 minimum; concurrency tests follow §8; results reported only if executed.
- [ ] Documentation updated per §10.
