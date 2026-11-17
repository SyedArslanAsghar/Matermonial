# Matermonial — AWS Deployment and CI/CD Strategy

**Version:** 1.0 (G1 revision 2026-11-16)  
**Date:** 11 November 2026  
**Document status:** APPROVED_WITH_OPEN_ITEMS (project owner, 2026-11-17, DR-2026-11-17-A; record in doc 20 §5). **Open items:** OPEN legacy ODs (doc 13 series): OD-005; PROPOSED TRs: TR-07, TR-23, TR-24. Listed items keep their own status (doc 19); this document status doesn't approve them.  
**Applied corrections:** DCR-10, 74, 79, 86, 87, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99 (doc 20). The compliance registry, maintenance protocol and restore procedure are in **§19**. G1 correction pass 2026-11-17 (DR-2026-11-17-C): verbatim extracts start with a "*Verbatim from …*" line and end with "*— End of verbatim extract —*"; text outside those markers is editorial.

## 1. Deployment objectives

Deploy the Matermonial application to AWS EC2 using Docker and Docker Compose.

The deployment must support:

- Secure production configuration.
- HTTPS.
- PostgreSQL persistence.
- Django API workers.
- Celery workers.
- Redis.
- Private media storage.
- Background scheduling.
- Monitoring and logging.
- Automated CI/CD.
- Database backups.
- Rollback and recovery.

## 2. Deployment architecture

Recommended initial production topology:

```text
                 Internet
                    |
                    v
              DNS / Domain
                    |
                    v
               HTTPS / TLS
                    |
                    v
             Nginx Reverse Proxy
                    |
             +------+------+
             |             |
             v             v
         React Web     Django API
          Frontend       Workers
                            |
                  +---------+---------+
                  |         |         |
                  v         v         v
              PostgreSQL  Redis    Private S3
                  |         |
                  |         v
                  |       Celery
                  |       Workers
                  |       Beat/Scheduler
                  |
                  v
              Backups
```

This is a recommended initial topology. Database and Redis hosting may be moved to managed AWS services when budget, reliability, and operational requirements justify it.

## 3. AWS services

Recommended services:

- EC2: application deployment host.
- EBS: persistent storage where required.
- S3: private media and export storage.
- IAM: least-privilege permissions.
- CloudWatch: logs, metrics, and alarms.
- Route 53: DNS if selected.
- AWS Certificate Manager or another suitable certificate process depending on the chosen ingress architecture.
- AWS Backup or a documented PostgreSQL backup process.

RDS PostgreSQL and managed Redis are future operational options, not mandatory assumptions for the first EC2 deployment.

## 4. Docker strategy

Docker is required for production deployment, not mandatory for local development.

Recommended production services:

- `nginx`
- `backend`
- `celery_worker`
- `celery_beat`
- `redis`
- `frontend` or a static frontend deployment service
- `postgres` only if the selected initial deployment topology intentionally hosts PostgreSQL on EC2

For production, evaluate whether PostgreSQL should run on EC2 or a managed database service. Do not put a production database in an ephemeral container without persistent storage and a tested backup/recovery plan.

## 5. Container requirements

- Use production Dockerfiles.
- Use non-root users where practical.
- Pin base images.
- Avoid embedding secrets in images.
- Use `.dockerignore`.
- Keep images reasonably small.
- Use health checks.
- Use persistent volumes only where required.
- Do not expose internal service ports publicly.
- Use explicit container restart policies.
- Keep application and database lifecycles separate.

## 6. Environment configuration

Maintain separate configurations for:

- Local.
- Test.
- Staging.
- Production.

Production environment variables include:

- Django secret key.
- Debug disabled.
- Allowed hosts.
- Database connection.
- Redis connection.
- Celery configuration.
- Email credentials.
- SMS credentials.
- JazzCash credentials.
- Object-storage settings.
- Domain and trusted origins.
- Logging configuration.

Inject secrets through a secure deployment mechanism. Do not commit production environment files.

## 7. Network security

- Expose only required public ports.
- Restrict SSH access.
- Prefer restricted administrative access or a secure management channel.
- Do not expose PostgreSQL publicly.
- Do not expose Redis publicly.
- Use security groups with least privilege.
- Enforce HTTPS.
- Configure appropriate firewall rules.
- Keep OS packages and container images updated.

## 8. Nginx responsibilities

Nginx should:

- Terminate or route HTTPS according to the selected TLS design.
- Route API traffic to Django.
- Serve or route frontend assets.
- Apply upload-size limits.
- Forward appropriate headers.
- Configure request timeouts.
- Avoid exposing private media directories.
- Support health checks.
- Use secure headers where appropriate.

## 9. Database operations

- Use PostgreSQL.
- Persist database data.
- Back up regularly.
- Encrypt backups at rest.
- Restrict backup access.
- Monitor disk usage.
- Test restore procedures.
- Apply migrations as a controlled deployment step.
- Avoid running multiple competing migration processes.

## 10. Media storage

Production should use private object storage.

Separate storage prefixes or buckets for:

- Profile photos.
- Identity verification documents.
- Message attachments.
- Shared documents.
- Moderation evidence.
- Data exports.

Apply least-privilege IAM policies and retention rules.

## 11. Celery deployment

Run separate processes for:

- General asynchronous tasks.
- Scheduled tasks through Celery Beat.
- Specialized queues where task volume or priority requires them.

Requirements:

- Worker health monitoring.
- Retry policy.
- Task time limits.
- Idempotency.
- Dead-letter or failed-task visibility.
- Safe shutdown.
- No duplicate scheduler instances unless the scheduler architecture explicitly supports them.

## 12. CI/CD workflow

Recommended GitHub Actions pipeline:

```text
Developer Push / Pull Request
             |
             v
        Install Dependencies
             |
             v
       Lint and Static Checks
             |
             v
          Run Tests
             |
             v
      Build Frontend/Backend
             |
             v
       Validate Migrations
             |
             v
        Build Images
             |
             v
       Publish Images
             |
             v
       Deploy to Staging
             |
             v
       Smoke Tests
             |
             v
      Production Approval
             |
             v
      Deploy to Production
             |
             v
       Health Verification
```

## 13. CI requirements

Pull request checks should include:

- Ruff.
- Backend tests.
- Frontend lint.
- Frontend tests.
- TypeScript checks.
- Build checks.
- Migration checks.
- OpenAPI schema validation.
- Dependency/security checks where configured.

## 14. Deployment requirements

The deployment process should:

1. Verify the target branch and release.
2. Build immutable images.
3. Publish versioned images.
4. Back up the database where appropriate.
5. Pull the approved image version.
6. Apply reviewed migrations.
7. Restart application services.
8. Restart or update Celery workers.
9. Verify health endpoints.
10. Run smoke tests.
11. Report deployment status.
12. Retain the previous known-good image for rollback.

Avoid uncontrolled destructive database migrations.

## 15. Rollback strategy

Application rollback should use a previous immutable image.

Database rollback is not always safely reversible. Prefer backward-compatible migrations:

1. Add new schema.
2. Deploy code that supports old and new fields.
3. Migrate data.
4. Switch application usage.
5. Remove obsolete schema in a later release.

Do not automatically reverse a destructive migration during emergency rollback.

## 16. Monitoring

Monitor:

- API availability.
- HTTP error rates.
- Response times.
- CPU and memory.
- Disk usage.
- Database connections.
- Redis availability.
- Celery queue length.
- Task failures.
- Payment callback failures.
- Notification delivery failures.
- Export/deletion task failures.
- Backup success/failure.

Set alerts for critical operational failures.

## 17. Backup and disaster recovery

Define:

- Backup frequency.
- Retention duration.
- Encryption.
- Backup location.
- Access permissions.
- Recovery Point Objective (RPO).
- Recovery Time Objective (RTO).
- Restore test schedule.

RPO/RTO values must be confirmed according to the business's actual availability and budget requirements. Do not invent guarantees.

Test restoring both database and required media references.

## 18. Production launch checklist

- Domain and DNS configured.
- HTTPS working.
- Debug disabled.
- Allowed hosts configured.
- Secrets securely injected.
- Database protected.
- Redis protected.
- Private storage verified.
- Admin MFA enabled.
- Payment callbacks verified.
- Celery worker and scheduler healthy.
- Monitoring active.
- Backups enabled.
- Restore test completed.
- CI/CD production approval enabled.
- Rollback procedure documented.
- Security and privacy checks passed.
- Smoke tests passed.

## 19. Compliance registry, maintenance protocol and restore (G1)

**Status:** [TR-24, TR-23] PROPOSED (doc 19). The external storage resource needs owner approval before production (doc 19 §5). Database structures: doc 03 §22.15. Privacy of the registry content: doc 06 §22.7.

### 19.1 Registry storage and access (DCR-74)

- The registry lives **outside the primary database**, in a write-once location. Recommended: a separate S3 bucket with Object Lock in compliance mode, versioning and replication to a second region. If that resource isn't approved, the alternative is a separate PostgreSQL instance with its own backup chain, append-only by trigger and privileges.
- The application role can only **add** objects; it can't delete or overwrite them. Only the restore role can read them.
- Each entry carries a monotonic `seq`, `prev_hash` and an HMAC signature made with a registry key held in the deployment secret store (doc 16).
- **Streams:** R (restore: deletion and shred entries, retained for the longest backup retention + 30 days) and M (maintenance, long-term retention), each with its own `seq` and hash chain, plus daily signed checkpoints of stream R written to stream M (doc 06 §22.7).
- The local table `ShreddedPseudonym` is a **cache** of the registry, not the authority. A reconciler (hourly and at startup) re-applies registry entries missing from the database.

**What may appear in a registry entry (DCR-91):**

> *Verbatim from `docs/baseline/v4.6-F3/approved/08_v4.6-F.md` §A.2. Section references inside this block refer to that package.*

##### A.2 What may appear in a registry entry

| Class | Examples | Allowed in |
|---|---|---|
| **Operational metadata** | Table and partition names (from a fixed allowlist), UUIDv7 range bounds, UTC timestamps, row counts, digests, key version numbers, secret-store **reference names** (never key material), job and role names, ticket IDs | M and R |
| **Opaque internal IDs** | `hold_case_id`, log event IDs (UUIDv7), `op_id`s. These can only be resolved inside the database and carry no identity on their own. | M only |
| **Subject pseudonyms** | `account_pseudonym`, `profile_pseudonym`, `pseudonym` | **R only** (v4.6 §2.1). Staff `approved_by_pseudonym` may also appear in M. |
| **Personal data** | Names, phone numbers, emails, user, profile or request IDs, IP addresses, free text | **Never** |

*— End of verbatim extract —*

**Amendments:** opaque key IDs (`SubjectDataKey.key_id`) are allowed in Stream R (SHRED parameters) and in Stream M (KEK_ROTATE companions). The entry structure, canonical hash input and local log reconstruction are defined in doc 03 §22.15 (DCR-95).

### 19.2 Operations, sequence numbers and concurrency (DCR-87)

Every maintenance action is a row in `maintenance_operation` (doc 03 §22.15) with a UUIDv7 `op_id` generated before the job starts, and `UNIQUE (kind, target_digest) WHERE status <> 'ABORTED'`.

> *Verbatim from `docs/baseline/v4.6-F3/approved/07_v4.6.md` §3.2–3.3. Section references inside this block refer to that package.*

##### 3.2 Serialised sequence numbers and hash chain

- **`registry_stream_head`:** `(stream PK, last_seq, last_hash, pending_op_id NULL)`.
- **Allocating an entry** takes `FOR UPDATE` on the head row:
  - **Refused** while `pending_op_id` is set to a *different* operation. So each stream has at most one external write in flight.
  - Otherwise: `seq = last_seq + 1`, `prev_hash = last_hash`, `entry_hash = SHA-256(canonical entry including prev_hash)`, set `pending_op_id`, set `last_seq` / `last_hash`, store `seq` and `hash` on the operation. Commit.
- **Confirmation** (after the external write succeeds) clears `pending_op_id`.

##### 3.3 Concurrency between maintenance jobs

- Each job holds a **session-level advisory lock** `pg_advisory_lock(NS_MAINT, hash(stream))` while it works on that stream.
- On top of that: the partial unique index (§3.1), the single pending entry per stream (§3.2), and a **conditional external create** (`If-None-Match: *` on object key `<stream>/<seq>`). Two writers therefore can't use the same `seq`.
- **Maintenance tables are their own lock domain.** No business transaction touches them.
- Inside an apply transaction the lock order is: operation row → stream head → target objects (partition DDL locks, or `SubjectPseudonym` / `SubjectDataKey` rows).

*— End of verbatim extract —*

### 19.3 Operation state machines (DCR-93)

> *Verbatim from `docs/baseline/v4.6-F3/approved/08_v4.6-F.md` §C.3. Section references inside this block refer to that package.*

###### C.3 State machines (replace the v4.6 §3.1 status list)

**Stream R:**

```
INTENT_PENDING → INTENT_REGISTERING → INTENT_REGISTERED → APPLYING → APPLIED → VERIFIED_LOCAL → COMPLETION_REGISTERING → COMPLETED
```

Any non-terminal state can move to `BLOCKED_OPERATOR`, and returns to its prior state through RESUME. There is no ABORTED in Stream R.

**Stream M:**

```
INTENT_PENDING → INTENT_REGISTERING → INTENT_REGISTERED → APPLIED → VERIFIED_LOCAL → COMPLETION_REGISTERING → COMPLETED
```

Plus: `INTENT_REGISTERED → ABORT_REGISTERING → ABORTED` (proven not applied), and any non-terminal state → `BLOCKED_OPERATOR` → RESUME or ABORT_WITH_EVIDENCE.

*— End of verbatim extract —*

### 19.4 Stream R: deletion and key destruction (DCR-92, DCR-97)

> *Verbatim from `docs/baseline/v4.6-F3/approved/08_v4.6-F.md` §B. Section references inside this block refer to that package.*

###### B.1 Event names in Stream R

| Event | Meaning | Written |
|---|---|---|
| `DELETION_INTENT` | The irreversible decision to process the deletion of `{account_pseudonym, profile_pseudonym}` has been taken (recovery period over, no cancellation possible) | **Before** the transition to PROCESSING |
| `SHRED_INTENT` | Irreversible decision to destroy `{pseudonym, key_ids, kek_version}` | **Before** the key-destruction transaction |
| `SHRED_COMPLETED` | The key destruction and unlink committed **and** verification passed | After verification |
| `DELETION_COMPLETED` | Every deletion step committed, `AccountDeletionRequest = COMPLETED` committed, **and** final verification passed | After verification |

A SHRED operation is a child of its deletion operation (`parent_op_id`).

###### B.2 Exact sequence

| Step | Action | Operation state after |
|---|---|---|
| 1 | Job (runs only when `now ≥ recovery_ends_at`; cancellation is refused from then on by the existing time check under the User lock): insert the operation | `INTENT_PENDING` |
| 2 | Allocate `seq` (stream head lock, single pending per stream) | `INTENT_REGISTERING` |
| 3 | Conditional put `DELETION_INTENT` → read back and compare the hash | `INTENT_REGISTERED` |
| 4 | Database transaction (account anchor): `AccountDeletionRequest → PROCESSING`. **A CHECK plus a service rule require the linked operation to be `INTENT_REGISTERED` or later.** | `APPLYING` |
| 5 | Idempotent deletion steps (fan-outs, anonymisation, profile closure, outbox cancellation, AuthSession deletion, financial step), each recorded as a step marker on the operation | `APPLYING` |
| 6 | For each subject key: SHRED child operation, steps 1–3 with `SHRED_INTENT` | child `INTENT_REGISTERED` |
| 7 | Key-destruction transaction (tombstone, unlink, local cache). **A CHECK requires the child operation to be `INTENT_REGISTERED` or later.** | child `APPLIED` |
| 8 | Verify the child (tombstone, unlink, no live wrapped key) | child `VERIFIED_LOCAL` |
| 9 | Allocate `seq`, put `SHRED_COMPLETED`, read back | child `COMPLETED` |
| 10 | When every child is COMPLETED and every step marker is done: transaction `AccountDeletionRequest → COMPLETED` | parent `APPLIED` |
| 11 | Final verification (all step effects, all children COMPLETED, standing = DELETED) | `VERIFIED_LOCAL` |
| 12 | Allocate `seq`, put `DELETION_COMPLETED`, read back | **`COMPLETED`** (terminal) |

**Guarantee kept:** PROCESSING (step 4) and key destruction (step 7) can't happen without their INTENT entry already in the registry, and the CHECK constraints enforce that order. **The registry never claims completion early:** `*_COMPLETED` entries are written only after commit **and** verification. The database may briefly be ahead of the registry (between steps 10 and 12), which is safe and gets reconciled.

###### B.3 Retry at every crash window

| Window | Recovery (reconciler, idempotent) |
|---|---|
| After 1 | Allocate `seq` |
| After 2 | Put the same bytes again |
| After the 3 put, before the state is committed | Read back. If the hash matches → `INTENT_REGISTERED`. A different hash → integrity alarm, stream halts. |
| After 3 | Run step 4 |
| During 4 or 5 (rolled back) | Re-run from the last completed step marker |
| After 7 commits | Verify (step 8) |
| After 8 / 9 | Allocate or put again, read back |
| After 10 commits | Final verification, then step 12 |
| After the 12 put, before the state is committed | Read back → `COMPLETED` |

###### B.4 Restore behaviour (replaces the v4.5 §2.1 step 3 and v4.6 §2.2 wording)

During restore reconciliation (application stopped):
1. For every R **INTENT** entry newer than the backup, in `seq` order: if the operation row is missing, recreate it from the entry (same `op_id`, state `INTENT_REGISTERED`).
2. **Re-apply from the INTENT, not from COMPLETED.** If the restored database is from before the deletion request (account ACTIVE or PENDING_RECOVERY), a dedicated restore path sets `AccountDeletionRequest = PROCESSING` with reason `RESTORE_REAPPLY`. The original decision is already recorded and its recovery period has already passed. Then run steps 5–11.
3. If the registry already has the `*_COMPLETED` entry for that `op_id`, mark the operation COMPLETED locally **without writing a second entry**. Otherwise write it (step 12).
4. Every re-application is listed in the RESTORE_RECONCILE operation (stream M).
5. Matching works through the restored `SubjectPseudonym` (v4.6 §2.2). A pseudonym not found in the restored database is skipped and recorded as `NOT_PRESENT_IN_BACKUP`.

*— End of verbatim extract —*

**`DELETION_INTENT` params** (DCR-97; from baseline v4.6-F1 Correction 3):
- `account_pseudonym`
- `profile_pseudonyms` (array; at most one personal profile per account [DECIDED])
- `expected_shred_subjects`: array of `{pseudonym, subject_type: ACCOUNT|PROFILE}`
- `recovery_ends_at` (UTC)
- `requested_on` (date only)
- `identity_confirmed: true`
- `holds_active_at_intent` (count)
- `deletion_step_plan_version` (the catalogue version of idempotent deletion steps)
- `reason: "USER_REQUEST"`

The header has `parent_op_id = null` and `target_digest = SHA-256(account_pseudonym)`. `DELETION_COMPLETED` params: `{ "completed_steps": [...], "children_completed": [op_ids] }`.

**`SHRED_INTENT` / `SHRED_COMPLETED` params and key destruction** (final wording):

> *Verbatim from `docs/baseline/v4.6-F3/approved/10_v4.6-F2.md` §1. Section references inside this block refer to that package.*

#### Revised specification text (replaces the SHRED_INTENT / SHRED_COMPLETED params in v4.6-F1 Correction 3)

> **`SHRED_INTENT` params (Stream R):**
> ```json
> {
>   "pseudonym": "<subject pseudonym>",
>   "subject_type": "ACCOUNT | PROFILE",
>   "keys": [
>     { "key_id": "<opaque key id>", "kek_version": "<kek version at intent>" }
>   ],
>   "actions": ["DESTROY_KEYS", "UNLINK_PSEUDONYM", "CACHE_INSERT"],
>   "cache_insert": {
>     "table": "shredded_pseudonym",
>     "key": "<same pseudonym>",
>     "row": { "subject_type": "ACCOUNT | PROFILE", "keys_digest": "<sha256 of JCS(keys)>" },
>     "expiry": "NONE"
>   },
>   "holds_active_at_intent": 0
> }
> ```
>
> **Rules for `keys`:**
> - At least one entry.
> - Sorted by `key_id`, with `key_id` unique within the array.
> - Each entry pairs one data key with the KEK version that wrapped it **when the INTENT was written**.
> - The separate `key_ids` and `kek_versions` arrays from v4.6-F1 are **removed**.
>
> **Privacy:** only a pseudonym, opaque key IDs, KEK version labels and operational values appear. No direct identifiers (v4.6-F §A.2).
>
> **`CACHE_INSERT` is fully specified. Recovery derives nothing by guesswork.**
> - **Target:** table `shredded_pseudonym`, primary key `pseudonym`.
> - **Row values:**
>   - `subject_type` and `keys_digest`, taken from `params.cache_insert.row`
>   - `op_id`, `intent_seq` and `intent_entry_hash`, taken from the **verified header** of the SHRED_INTENT entry. They're not in `params`, so there's no circular dependency (v4.6-F1 Correction 1).
>   - `shredded_at`, set to the apply time
> - **Expiry: `NONE`.** The row is never removed automatically. It holds only an unlinked random pseudonym and opaque digests. It keeps shredding idempotent and stops re-linking if a restored backup still contains the pseudonym. Any shorter retention can only come from the legal-review retention decision (doc 13 OD-005), applied as a Stream M maintenance operation.
> - **Re-apply:** `INSERT … ON CONFLICT (pseudonym) DO NOTHING`. If a row exists, its `op_id` and `keys_digest` must match. A different `op_id` or digest → integrity alarm, and the operation goes to `BLOCKED_OPERATOR`.
>
> **Key destruction, including after a restore.** For each entry in `keys`:
> 1. Look up the `SubjectDataKey` row by `key_id`.
> 2. **Absent:** record it in `not_present_keys`. That's not a failure (v4.6-F1 rule 4).
> 3. **Present with `kek_version` = the recorded version:** destroy it (tombstone, v4.5 §2.2).
> 4. **Present with a different `kek_version`:** that's allowed **only if** Stream M has a COMPLETED `KEK_ROTATE` chain connecting the observed version to the recorded version, in either direction. That chain is how re-wrapping legitimately changes a key's version, for example a rotation after the INTENT, or a backup taken before an earlier rotation. If such a chain exists, destroy the key and record `observed_kek_version`. If not → integrity alarm and `BLOCKED_OPERATOR`. **The association is never guessed.**
>
> **`SHRED_COMPLETED` params:**
> ```json
> {
>   "destroyed_keys": [
>     { "key_id": "…", "recorded_kek_version": "…", "observed_kek_version": "…" }
>   ],
>   "not_present_keys": [ { "key_id": "…", "recorded_kek_version": "…" } ],
>   "cache_row": { "pseudonym": "…", "op_id": "…", "keys_digest": "…" }
> }
> ```
>
> **Verification (step 8 in v4.6-F B.2):**
> - Every recorded key is either tombstoned or listed as not present.
> - The pseudonym is unlinked.
> - The cache row exists with matching `op_id` and `keys_digest`.
> - No live wrapped key remains for the pseudonym.

*— End of verbatim extract —*

**Key-specific rewrap evidence** (replaces step 4 of "Key destruction" above):

> *Verbatim from `docs/baseline/v4.6-F3/approved/11_v4.6-F3.md` §2. Section references inside this block refer to that package.*

#### Revised specification text

> **KEK_ROTATE evidence is per key.** Every KEK_ROTATE operation writes a **companion** (following the v4.6-F1 Correction 6 write order). It's a canonical JSON Lines object listing every data key it rewrapped:
> - header: `{"format":"matreg-companion-v1","op_id":…,"kind":"KEK_ROTATE","from_version":…,"to_version":…,"count":n}`
> - then, sorted by `key_id`: `{"t":"rewrap","key_id":…,"from_version":…,"to_version":…,"rewrapped_at":…}`
>
> The KEK_ROTATE COMPLETED entry's header carries the companion's `{key, sha256, count}`. The digest is covered by `entry_hash` and the signature. **Companion retention** is the same as Stream M's.
>
> **Locally**, the rewrap transaction also inserts rows into an append-only `kek_rewrap_log (key_id, from_version, to_version, rotate_op_id, rewrapped_at)`. After a restore, the registry companion is authoritative.
>
> **Data class:** `key_id` values are opaque random IDs. They're allowed in Stream M alongside the other opaque IDs (v4.6-F §A.2). No pseudonyms or direct identifiers appear.
>
> **Destruction rule** (replaces v4.6-F2 §1 step 4). If the observed `kek_version` differs from the recorded one, destruction can go ahead **only if** there's an unbroken sequence of **key-specific rewrap records for that exact `key_id`** that connects the recorded version to the observed version, in either direction in time. Each record must come from a KEK_ROTATE operation that:
> - is **COMPLETED**, and
> - has a companion that has been verified (digest and line count)
>
> **A rotation between the two KEK versions that doesn't list this `key_id` isn't evidence.**
>
> - **Rotation still in progress** (a KEK_ROTATE that touches either version isn't terminal yet): the SHRED apply **waits and retries**. It isn't blocked, because evidence is expected once the rotation completes.
> - **Every relevant rotation is terminal and no key-specific chain exists**, or a companion is missing or altered: integrity alarm, and the SHRED operation goes to `BLOCKED_OPERATOR`. **No key is destroyed on an assumed link.** The operator resolves it per v4.6-F C.1.

*— End of verbatim extract —*

**Recovery rules when the database operation rows are missing (restore):**
1. Process Stream R in `seq` order. A child's INTENT is always written after its parent's INTENT, so a parent is rebuilt before its children.
2. Rebuild the parent operation from `DELETION_INTENT` (same `op_id`, state `INTENT_REGISTERED`, step markers empty) and run every step of `deletion_step_plan_version` idempotently, including the `RESTORE_REAPPLY` path.
3. Rebuild each child from `SHRED_INTENT`. Required: the parent exists, and the child's `pseudonym` is in the parent's `expected_shred_subjects`. Otherwise → integrity alarm, and the child goes to `BLOCKED_OPERATOR`.
4. Each key is handled by the key-destruction rule above (a missing key is recorded as not present; a version mismatch needs key-specific rewrap evidence).
5. If the matching `*_COMPLETED` entry already exists, the operation is marked COMPLETED locally without writing a second entry.

### 19.5 Stream M write order (DCR-91, DCR-99)

1. If the operation has a companion: build it, compute its SHA-256, conditionally create it at the content-addressed key `M/companions/<op_id>/<sha256>.jsonl` with object lock, and read it back (§19.8, item 6).
2. Allocate the `seq` and write the INTENT entry (with `companion_ref` where applicable) → `INTENT_REGISTERED`.
3. Apply transaction (with the local `maintenance_audit_log` INTENT row) → `APPLIED`.
4. Verify (§19.6) → `VERIFIED_LOCAL`.
5. Allocate the `seq` and write the COMPLETED entry → `COMPLETED`.

**Stream M writes COMPLETED only after verification.** If the apply transaction rolled back and the effect is provably absent, an ABORTED entry is written instead (§19.7). The database never reaches an irreversible state the registry doesn't already record.

### 19.6 What "complete" means

> *Verbatim from `docs/baseline/v4.6-F3/approved/07_v4.6.md` §3.5. Section references inside this block refer to that package.*

##### 3.5 What "complete" means

An operation is `VERIFIED` only when all of these hold:
- (a) Every registry entry the operation needs exists, and a read-back of its hash matches the hash stored in the database.
- (b) The operation's effect is confirmed by its own check: the partition is gone and the hold-table count equals the recorded count; or the key is tombstoned and the pseudonym unlinked; or the deletion steps are complete.
- (c) The local `maintenance_audit_log` has the matching row(s) with the same `op_id`, `seq` and hash.

*— End of verbatim extract —*

### 19.7 Failure handling and reconciliation (DCR-93)

> *Verbatim from `docs/baseline/v4.6-F3/approved/08_v4.6-F.md` §C.1–C.2. Section references inside this block refer to that package.*

###### C.1 The `BLOCKED_OPERATOR` state (both streams; never terminal)

| Question | Answer |
|---|---|
| **When it's entered** | (a) Verification fails 5 times with backoff. (b) A non-retryable error during apply: a constraint violation, or an unexpected state such as a key row missing without a tombstone. (c) A legal or security hold is detected after the INTENT. (d) An external dependency (registry or secret store) keeps failing for more than 24 h (configurable). (e) In M only: **the effect of an external step is unknown**, for example a secret-store destroy call that timed out. |
| **Can it be retried?** | Not automatically. It resumes **only** through an `OPERATOR_INTERVENTION` (RESUME) with two approvals, recorded in stream M. After that, the reconciler carries on from the recorded state and step markers. |
| **Does it block the stream?** | **No.** Other operations on the stream keep going, so one stuck deletion doesn't delay everyone else's. **Exceptions that halt the whole stream:** a registry integrity alarm (hash conflict, broken chain), or an operation stuck in `*_REGISTERING` (single pending per stream, v4.6 §3.2). |
| **Operator must check before resuming** | (1) The operation's state and step markers. (2) The actual database effects: deletion-request status, profile closed, sessions deleted, pseudonym unlinked, key tombstone. (3) Registry read-back and full chain check. (4) Hold status. A hold leaves the shred deferred until released (v4.4 §1.5). (5) The root cause is fixed. (6) Evidence digest recorded. |
| **How the reconciler resumes** | From the operation's last committed state. Every step is idempotent (B.3). |
| **What restore does with it** | The operation is re-attempted. If it fails again, it goes back to `BLOCKED_OPERATOR`, and the subject is **quarantined** in a `restore_quarantine` table that `get_account_standing` checks (standing `RESTORE_QUARANTINED`, handled exactly like `DELETION_PROCESSING`: no login, no visibility, no notifications other than none). **Updated startup gate:** traffic may start only when every R INTENT newer than the backup is either COMPLETED or BLOCKED_OPERATOR with quarantine applied. Any unprocessed INTENT keeps the application down. |
| **Why an R operation is never "aborted"** | An R INTENT records a decision that can't be undone. The deletion was requested, identity-confirmed, and its recovery period ended [DECIDED: completed deletion isn't reversed]. A shred may already have destroyed key material partway. Marking it ABORTED would let a restore skip re-applying it, bringing deleted personal data back, or would claim data is recoverable when its key may already be gone. The only allowed outcomes are **COMPLETED**, or **BLOCKED_OPERATOR until COMPLETED**. |

###### C.2 Stream M keeps ABORTED, used only where it's truly safe

`ABORTED` is written **only** when the effect is **proven not to have happened**:
- a single database transaction rolled back, with the partition present and hold rows unchanged, or
- an external step that never ran

If an external effect is unknown, the operation goes to `BLOCKED_OPERATOR`. The operator then checks the real state and records either an `OPERATOR_INTERVENTION RESUME` (to complete it) or `ABORT_WITH_EVIDENCE` (proof the effect didn't happen).

*— End of verbatim extract —*

**Reconciler** (hourly, at startup and after a restore; holds the stream advisory lock):

| Found | Action |
|---|---|
| `*_REGISTERING` | Read `<stream>/<seq>`. Present with matching hash → registered. Missing → put again (same bytes). Present with a **different hash** → integrity alarm, the stream halts. |
| `INTENT_REGISTERED` (not applied) | Re-run the apply transaction (idempotent). Stream R: if it can't complete, `BLOCKED_OPERATOR` (never aborted). Stream M: ABORTED only if the effect is proven absent; otherwise `BLOCKED_OPERATOR`. |
| `APPLIED` / `VERIFIED_LOCAL` / `COMPLETION_REGISTERING` | Verify, then write the completion entry |
| Anything not terminal | Verify. After repeated failures, `BLOCKED_OPERATOR` and an alert. |
| Nightly | Both streams verified end to end (seq continuity, hashes, signatures, checkpoints) against the database |

### 19.8 Recoverable parameters for each operation kind (DCR-91, DCR-96, DCR-99)

> *Verbatim from `docs/baseline/v4.6-F3/approved/08_v4.6-F.md` §A.3. Section references inside this block refer to that package.*

###### A.3 Recoverable parameters for each kind

Each row lists the INTENT `params`, what the COMPLETED entry adds, how the operation is re-applied idempotently, and how its result is verified.

**PARTITION_CREATE**
- **INTENT params:** `table` (allowlist), `partition_name`, `range_from_ts`, `range_to_ts`, `range_from_uuid`, `range_to_uuid`
- **COMPLETED adds:** `created_at`
- **Re-apply:** `CREATE TABLE IF NOT EXISTS … PARTITION OF … FOR VALUES FROM … TO …`. Skipped if a later PARTITION_DROP for the same range is recorded in M, because entries are processed in `seq` order.
- **Verify:** `pg_class` / `pg_inherits` bounds equal the parameters

**PARTITION_DROP** (includes copying held rows)
- **INTENT params:** `table`, `partition_name`, the range bounds, `held_event_ids` (companion), `hold_links` [(event_id, hold_case_id)] (companion), `ids_digest_pre` (SHA-256 of the sorted IDs present when the drop was planned), `row_count_pre`
- **COMPLETED adds:** `held_row_count`, `dropped_row_count`
- **Re-apply:** in one transaction, copy exactly `held_event_ids` (if present) into `audit_log_hold` with `ON CONFLICT DO NOTHING`, insert `hold_links`, then DETACH and DROP if the partition is present
- **Verify:** the partition is absent, and every held ID plus every link is present. The digest is compared **for information only**: a backup older than the drop may contain fewer rows, and that's reported as `RESTORE_DIVERGENCE`, not a failure. A hold case missing from the restored database raises an operator alert.

**HOLD_RELEASE**
- **INTENT params:** `hold_case_id`, `released_event_ids` (companion), `retention_category`, `retention_days`, `released_at`
- **COMPLETED adds:** `released_row_count`
- **Re-apply:** delete the links for `hold_case_id`, then delete only those `released_event_ids` that have no remaining links
- **Verify:** none of the listed IDs remain in the hold table without a link

**KEK_ROTATE**
- **INTENT params:** `kek_version_old`, `kek_version_new`, `secret_ref_new`, `scope_tables`, `expected_rewrap_count`
- **COMPLETED adds:** `rewrapped_count`, `rewrapped_key_ids_digest`
- **Re-apply:** re-wrap every data key still wrapped with `old` using `new`. That's possible because `old` isn't destroyed yet (invariant in KEK_DESTROY).
- **Verify:** no live data-key row has `kek_version = old`

**KEK_DESTROY**
- **INTENT params:** `kek_version`, `secret_ref`, `precondition`: `{rotate_op_id, rotate_completed_at, oldest_retained_backup_at, remaining_wrapped = 0}`
- **COMPLETED adds:** `destroyed_at`, `secret_store_receipt`
- **Re-apply:** confirm the secret-store version is destroyed (the call is idempotent). **Invariant:** `oldest_retained_backup_at > rotate_completed_at`, so no restorable backup holds keys wrapped only by this version.
- **Verify:** the secret store reports the version destroyed, and the restored database has no live rows using it

**QUEUE_KEY_ROTATE**
- **INTENT params:** `queue_key_version_old`, `queue_key_version_new`, `secret_ref_new`
- **COMPLETED adds:** `activated_at`
- **Re-apply:** set the active version
- **Verify:** new events use `new`

**QUEUE_KEY_DESTROY**
- **INTENT params:** `queue_key_version`, `secret_ref`, `precondition`: `{outbox_rows_with_version_unredacted = 0, oldest_retained_backup_at}`
- **COMPLETED adds:** `destroyed_at`, `secret_store_receipt`
- **Re-apply:** confirm destroyed. Rows in a restored database using this version get redacted.
- **Verify:** the destroyed version is no longer referenced by any unredacted row

**RESTORE_RECONCILE**
- **INTENT params:** `backup_id`, `backup_taken_at`, `registry_heads_at_start {R, M}`
- **COMPLETED adds:** `reapplied_op_ids` (companion), counts per kind, `blocked_op_ids`, `quarantined_pseudonyms_count`, `divergences`
- **Re-apply:** none; it's an audit record. Only its log row is rebuilt.
- **Verify:** the heads recorded in the database equal the registry heads

**REGISTRY_CHECKPOINT**
- **INTENT params:** none (a single entry)
- **COMPLETED adds:** `checkpointed_stream`, `seq`, `head_hash`, `signature`
- **Re-apply:** none. The log row is rebuilt.
- **Verify:** the signature is valid, and `head_hash` matches that stream at `seq`

**MAINT_LOG_PARTITION_DROP**
- **INTENT params:** `partition_name`, year range bounds, `ids_digest_pre`, `row_count_pre`, `precondition`: every operation inside the range is a terminal state (COMPLETED or ABORTED), and retention has passed
- **COMPLETED adds:** `dropped_row_count`
- **Re-apply:** DROP if the partition is present
- **Verify:** the partition is absent. The current partition holds this operation's row.

**OPERATOR_INTERVENTION** (new kind; see Correction C)
- **INTENT params:** `target_op_id`, `action` (RESUME \| ABORT_WITH_EVIDENCE), `evidence_digest`, `approval_ref`, `approved_by_pseudonym` (two approvers)
- **COMPLETED adds:** `result`
- **Re-apply:** none. The log row is rebuilt.
- **Verify:** the target operation's state matches the result

**Stream M is now written in this order: apply → verify → COMPLETED.** v4.6 §3.4 wrote COMPLETED before verifying, which is corrected here as C-61.

*— End of verbatim extract —*

**Amendments to the block above (later packages win):**
1. **PARTITION_DROP companion:** replaced by the full held-event companion below (F1 Correction 2).
2. **HOLD_RELEASE:** deletes only rows that pass the three eligibility checks below; a new kind `HOLD_RETENTION_PURGE` removes rows later (F1 Correction 7).
3. **KEK_ROTATE:** writes a per-key rewrap companion (§19.4, key-specific evidence).
4. **QUEUE_KEY_DESTROY precondition:** replaced by §19.9.
5. **OPERATOR_INTERVENTION:** two distinct approvers, below (F1 Correction 5).
6. **Companion keys:** content-addressed, written and verified before the INTENT (F1 Correction 6).
7. **PARTITION_CREATE followed by a later PARTITION_DROP:** restore rule below (F1 Correction 8).

> *Verbatim from `docs/baseline/v4.6-F3/approved/09_v4.6-F1.md` Correction 2. Section references inside this block refer to that package.*

##### Revised specification text

> **Companion for PARTITION_DROP:** a canonical JSON Lines object, UTF-8, `\n`-terminated:
> - **Line 1 (header):** `{"format":"matreg-companion-v1","op_id":…,"kind":"PARTITION_DROP","table":…,"partition_name":…,"event_count":n,"link_count":m}`
> - **Then one line per held event**, sorted by `id`: `{"t":"event","row":{…every column of the audit_log row exactly as stored…}}`. This includes the plaintext event facts, the pseudonyms and `enc_parts` (ciphertext). These are the same pseudonymous or encrypted values the log already holds, and **no direct identifiers** (v4.5 §2.3–2.4).
> - **Then one line per hold link**, sorted by (`event_id`, `hold_case_id`): `{"t":"link","event_id":…,"hold_case_id":…}`
>
> `companion_ref.sha256` = SHA-256 of the whole object. It's in the header, so it's protected by `entry_hash` and the signature.
>
> **Companion retention:** object lock = the longest backup retention + 30 days. The companion only matters for restoring from a backup taken before the drop, and every later backup already contains `audit_log_hold`.
>
> **Reconstruction on restore:**
> 1. Fetch the companion and verify its digest and line counts.
> 2. In one transaction, insert every event row into `audit_log_hold` and every link into `audit_log_hold_link`, both with `ON CONFLICT DO NOTHING`.
> 3. If the restored partition contains a held event, its stored row must be byte-equal (in canonical JSON) to the companion row. If it isn't → integrity alarm.
> 4. DETACH and DROP the partition if present.
> 5. Verify: every companion event and link is present, and the partition is absent.
>
> Rows inserted into that partition after the backup and **not** held are legitimately gone, because their retention had ended. That difference is recorded as `RESTORE_DIVERGENCE` and doesn't count as a failure.
>
> **Missing or altered companion:** integrity alarm. The operation goes to `BLOCKED_OPERATOR`, and **the partition isn't dropped**, because it may be the only remaining copy of held data. Stream M doesn't halt. The operator recovers the companion from a replica or a previous object version, then records an `OPERATOR_INTERVENTION RESUME`.
>
> **The held set changes between INTENT and apply** (a new hold or a release): the apply transaction rolls back, the operation is `ABORTED` (proven not applied), and the drop is planned again.

*— End of verbatim extract —*

> *Verbatim from `docs/baseline/v4.6-F3/approved/09_v4.6-F1.md` Correction 5. Section references inside this block refer to that package.*

##### 5. Two distinct approvers for OPERATOR_INTERVENTION (C-70)

> **Header field `approvals`:** an array of exactly two entries, `{approver_pseudonym, approved_at, approval_ref}`.
>
> **Database:** table `maintenance_approval (op_id, approver_user_id, approved_at, permission_code)` with:
> - `PRIMARY KEY (op_id, approver_user_id)`
> - a CHECK trigger ensuring the approver isn't the `requested_by` account
>
> **Service rule:** RESUME or ABORT_WITH_EVIDENCE needs **two rows from distinct staff accounts**, each holding `maintenance.approve_intervention` at approval time (checked against the single admin-authorization source, TR-07), and neither may be the requester.
>
> **Registry:** both approver pseudonyms and timestamps appear in the header.

*— End of verbatim extract —*

> *Verbatim from `docs/baseline/v4.6-F3/approved/09_v4.6-F1.md` Correction 6. Section references inside this block refer to that package.*

##### 6. Order for writing companion objects (C-71)

> Applies to every operation with a companion (PARTITION_DROP, HOLD_RELEASE, RESTORE_RECONCILE):
> 1. Build the companion and compute its SHA-256.
> 2. Conditionally create it at the **content-addressed** key `M/companions/<op_id>/<sha256>.jsonl` with object lock. This replaces v4.6-F's `<stream>/<seq>.c`, because the `seq` isn't known yet at this point.
> 3. Read it back and verify the digest.
> 4. Only then allocate the `seq` and write the INTENT entry with `companion_ref`.
>
> A crash after step 2 leaves an unreferenced companion. That's harmless: it's reported by the nightly check and expires with its retention.

*— End of verbatim extract —*
>

> *Verbatim from `docs/baseline/v4.6-F3/approved/09_v4.6-F1.md` Correction 7. Section references inside this block refer to that package.*

##### 7. Checking retention before HOLD_RELEASE deletes anything (C-72)

> **HOLD_RELEASE apply,** per candidate event in `released_event_ids`:
> - (a) after removing this hold's links, **no active hold link remains**
> - (b) the event's pseudonyms aren't under any other active hold
> - (c) `occurred_at + retention(category) ≤ now`, using the **stricter** of the retention values in force at INTENT time and at apply time
>
> Only events meeting all three are deleted. Events that fail (c) stay in `audit_log_hold` with no link and `retain_until` set.
>
> **New M kind `HOLD_RETENTION_PURGE`:**
> - params: `event_ids` (companion), `evaluated_at`
> - re-apply: the same three checks, then delete
>
> On re-apply after a restore, the checks are evaluated again, and the deleted set must be a subset of the listed IDs.

*— End of verbatim extract —*

> *Verbatim from `docs/baseline/v4.6-F3/approved/09_v4.6-F1.md` Correction 8. Section references inside this block refer to that package.*

##### 8. Restoring a PARTITION_CREATE that was later dropped (C-73)

> During restore, Stream M is processed in `seq` order with an intended-state rule for each (`table`, `range`):
> - **A later PARTITION_DROP exists for the range (COMPLETED, or in flight with a verified companion):** CREATE is **skipped**, and the drop is re-applied per Correction 2. If the partition is missing from the restored database, only the held records are rebuilt.
> - **CREATE is COMPLETED and no drop exists:** the partition is created if missing. This is the **only** allowed exception to the "never create a past range" rule (v4.5 §5.1), and it's recorded in RESTORE_RECONCILE.
> - **CREATE is in flight with no COMPLETED:** it's re-applied normally.

*— End of verbatim extract —*

### 19.9 Queue-key destruction and financial events (DCR-98)

A `QUEUE_KEY_DESTROY` INTENT is refused unless all of these are zero:
- (a) NOTIFICATION rows using the version that are non-terminal or unredacted;
- (b) FINANCIAL_OBLIGATION rows using the version in any status other than redacted `DONE`;
- (c) outstanding refund obligations found by reconciliation;
- (d) unresolved `DEAD_UNDECRYPTABLE` events.

**Restore when a queue-key version is already destroyed:** undecryptable NOTIFICATION events → `CANCELLED (KEY_DESTROYED)`; undecryptable FINANCIAL_OBLIGATION events → `DEAD_UNDECRYPTABLE` (with `dedupe_key` kept) and a `ReconciliationDiscrepancy`. **Financial obligation re-derivation** runs as a mandatory restore step: every outstanding obligation gets a replacement event encrypted with the current queue key. Resolution then follows the two-stage lifecycle in doc 05 §25.6.

### 19.10 Maintenance catalogue (DCR-90)

| Kind | Stream | Registry entries |
|---|---|---|
| `DELETION` (`DELETION_INTENT` / `DELETION_COMPLETED`) | R | INTENT + COMPLETED |
| `SHRED` (`SHRED_INTENT` / `SHRED_COMPLETED`; child of a deletion) | R | INTENT + COMPLETED |
| `PARTITION_CREATE` | M | INTENT + COMPLETED or ABORTED |
| `PARTITION_DROP` (includes copying held events) | M | INTENT + COMPLETED or ABORTED |
| `HOLD_RELEASE`, `HOLD_RETENTION_PURGE` | M | INTENT + COMPLETED or ABORTED |
| `KEK_ROTATE`, `KEK_DESTROY` | M | INTENT + COMPLETED or ABORTED |
| `QUEUE_KEY_ROTATE`, `QUEUE_KEY_DESTROY` | M | INTENT + COMPLETED or ABORTED |
| `RESTORE_RECONCILE` | M | INTENT + COMPLETED |
| `REGISTRY_CHECKPOINT` | M | 1 |
| `MAINT_LOG_PARTITION_DROP` | M | INTENT + COMPLETED or ABORTED (recorded in the current year's maintenance partition) |
| `OPERATOR_INTERVENTION` | M | INTENT + COMPLETED |

**Rule:** no maintenance action may run outside this protocol. A startup check confirms every maintenance command is registered in the catalogue.

### 19.11 Restore procedure and startup gate (DCR-74, DCR-92, DCR-93)

1. Restore the database **with the application stopped** (Nginx maintenance page; web and worker containers not started).
2. Fetch both registry streams. Verify every signature, `seq` continuity and the hash chain (from the newest usable checkpoint for stream R). **Any gap or bad signature halts the restore.** If the registry is unavailable, the restore stops until it is recovered from a replica or a previous object version.
3. Re-apply every stream R INTENT newer than the backup, in `seq` order (§19.4 recovery rules and the B.4 behaviour above).
4. Re-apply the effects of stream M operations newer than the backup, in `seq` order, using their recorded parameters (§19.8).
5. Run financial obligation re-derivation (§19.9).
6. Insert missing `maintenance_audit_log` rows from the registry (`restored_from_registry = true`).
7. Record the RESTORE_RECONCILE operation and write `restore_reconciled_seq` for both streams.
8. **Startup gate:** web and workers refuse to start unless `restore_reconciled_seq` is at least the registry head for both streams; every stream R INTENT newer than the backup is COMPLETED or `BLOCKED_OPERATOR` with the subject quarantined; and there are zero outstanding financial obligations without a live event.
9. Start traffic.

**Key material in backups:** data keys are wrapped by a versioned KEK. Each KEK version is destroyed only after the longest backup and WAL retention that could hold keys it wrapped has passed, which makes old backup copies permanently undecryptable (doc 06 §22.6).

### 19.12 Partitioned logs and maintenance-log retention (DCR-79)

- AuditLog and AccountSecurityEvent are partitioned monthly by UUIDv7 `id`; partitions are created 3 months ahead, with an alert below 2 months of headroom (doc 03 §22.15).
- At the end of retention a partition is dropped whole by the maintenance role (PARTITION_DROP), after its held events are copied to the hold table in the same transaction.
- The maintenance audit log is partitioned yearly; dropping its oldest partition is itself an M-stream operation recorded in the current partition and the registry. Its retention (placeholder 7 years) is subject to legal review (doc 13 OD-005).
