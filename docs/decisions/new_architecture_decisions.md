# New Architecture Decisions

**Register status:** ACTIVE
**Last updated:** 2026-11-18 (G4 accepted, DR-2026-11-18-G4A)

This register holds the project's approval decision records (DR-…) and the approved OD-01 domain catalogue. The decisions recorded here up to DR-2026-11-16-G1 have been applied to the handover documents during G1 (Documentation Reconciliation); where each was applied is recorded in `docs/handover/20_DOCUMENTATION_CORRECTION_REGISTER.md`. Owner decisions (OD) and technical recommendations (TR) and their statuses are tracked in `docs/handover/19_OPEN_DECISION_REGISTER.md`.

The decision records below are historical: each describes the situation **at the date it was made**. The current state is in "Current status of related registers".

---

## Decision record DR-2026-11-16: Documentation baseline approval

- **Date:** 2026-11-16
- **Approved by:** Project architecture reviewer, acting under delegation from the project owner
- **Subject:** Specification Reconciliation Package v4 through v4.6-F3 (v4, v4.1, v4.2, v4.3, v4.4, v4.5, v4.6, v4.6-F, v4.6-F1, v4.6-F2, v4.6-F3)

### Approved decisions

| # | Decision ID | Item | Status | Scope of approval |
|---|---|---|---|---|
| 1 | DR-2026-11-16-1 | Documentation baseline v4–v4.6-F3 | APPROVED | Approved as the Matermonial documentation reconciliation baseline. This approves DCR-01…DCR-99 as the basis for documentation changes. It does **not** approve the proposed technical recommendations (TR) or business recommendations (REC-BIZ) inside the baseline. |
| 2 | DR-2026-11-16-2 | DCR-12 / TR-14: status model | APPROVED | Three independent status dimensions (document status, requirement approval status, implementation status). `ACCEPTED` replaces implementation `APPROVED`, and only the project owner may assign it. |
| 3 | DR-2026-11-16-3 | DCR-09 / DCR-45: instruction documents | APPROVED | Root `CLAUDE.md` is the authoritative project entry point. `docs/handover/12_CLAUDE_CODE_INSTRUCTIONS.md` is its detailed companion and refers to `CLAUDE.md` rules by ID. Doc 12 is **not** superseded. |
| 4 | DR-2026-11-16-4 | TR-05: subscription vocabulary | APPROVED | Approved terms: billing term, allowance period, `duration_months`. "Recovery period" is reserved for account deletion. Use of "renewal window" depends on OD-09b, which remains OPEN. |
| 5 | DR-2026-11-16-5 | OD-01: functional-domain catalogue | APPROVED (OD-01 RESOLVED) | The reconstructed 22-domain catalogue (v4.6-F Part 5.2, reproduced below) is approved as the project's domain reference. |

### Approval boundaries

- Approving the baseline does not automatically approve any proposed technical recommendation in it.
- No approved business requirement is changed by these decisions.
- Approving the catalogue resolves OD-01 only. OD-02…OD-10 keep their existing OPEN status.
- Unapproved TRs remain PROPOSED.
- **G1 is NOT authorized** (at the time of this record; G1 was later authorized by DR-2026-11-16-G1).
- No implementation, coding, migrations, dependency installation, database changes, Git operations or environment changes are authorized.

---

## Current status of related registers

*As of 2026-11-17, after G1 final owner acceptance (DR-2026-11-17-A).*

### Technical recommendations (TR)

| Status | Items |
|---|---|
| APPROVED | TR-05, TR-14, TR-13 (DR-2026-11-17-G2D-2), TR-09, TR-12, TR-22 (DR-2026-11-17-G3) |
| PROPOSED | TR-01, TR-02, TR-03, TR-04, TR-06, TR-07, TR-08, TR-10, TR-11, TR-15, TR-16, TR-17, TR-18, TR-19, TR-20, TR-21, TR-23, TR-24 |

### Owner decisions (OD)

| OD | Topic | Status |
|---|---|---|
| OD-01 | Functional-domain catalogue | **RESOLVED** (DR-2026-11-16-5) |
| OD-02 | Participation and account lifecycle (sub-items a–e, including OD-02e notification categories by account standing) | OPEN |
| OD-03 | Visibility (sub-items a–j) | OPEN |
| OD-04 | Identity rules (sub-items a–e) | OPEN |
| OD-05 | Manager arrangement (sub-items a–f) | OPEN |
| OD-06 | Interest, request and connection interaction (sub-items a–n) | OPEN |
| OD-07 | Request cancellation, refunds and credit disposition (sub-items a–g) | OPEN |
| OD-08 | View exemptions and zero credit (sub-items a–c) | OPEN |
| OD-09 | Subscription scenarios (sub-items a–d, including OD-09b) | OPEN |
| OD-10 | Matching hard rules (sub-items a–b) | OPEN |

The legacy open decisions in `docs/handover/13_ASSUMPTIONS_RISKS_TRACEABILITY.md` §4 (OD-001…OD-007) are unchanged by this record.

### Documentation corrections (DCR) and contradictions

| Register | Status |
|---|---|
| DCR-01…DCR-99 | Approved as the documentation baseline (DR-2026-11-16-1). **Applied during G1:** 98 APPLIED, DCR-20 BLOCKED (OD-02, OD-04 OPEN). Locations in doc 20 §3. |
| Contradictions C-1…C-78 | Resolved in the baseline and aligned in the handover documents (doc 20 §4). |
| Docs 18, 19, 20 | Created in G1 (DCR-34). Final document statuses: docs 18 and 19 APPROVED_WITH_OPEN_ITEMS, doc 20 REFERENCE (DR-2026-11-17-A). |
| Document status headers (DCR-10) | Final statuses assigned by the project owner (DR-2026-11-17-A): doc 00 APPROVED; `CLAUDE.md` and docs 01–19 APPROVED_WITH_OPEN_ITEMS; doc 20 REFERENCE. Details in doc 20 §5. |
| ADRs | ADR-025…032 created in G1, all PROPOSED (ADR-029: the ADR document is PROPOSED; the decision it records, TR-14, is APPROVED). ADR-014 is APPROVED for its core decision only (DR-2026-11-17-C2). ADR-022 and ADR-023 await a decision before G4. |

### Gate status

| Gate | Status |
|---|---|
| G1 Documentation reconciliation | **COMPLETED. ACCEPTED by the project owner** (DR-2026-11-17-A, 2026-11-17). All 12 exit criteria met. |
| G2 Repository governance | **ACCEPTED by the project owner with carried-forward items** (DR-2026-11-17-G2A). Baseline commit `38f491dea79fb9bb10fd2010b1c2cb8a68d545f9`. Exit criterion "CI runs on the baseline", carried forward OPEN under exception DR-2026-11-17-G2X: **satisfied by owner acceptance (DR-2026-11-18-G2C, 2026-11-18)** on the integrated run `44294474904` on commit `c5fc346` (success, 6/6 jobs). The baseline commit `38f491d` itself did not run independently. |
| G3 Backend foundation | **ACCEPTED by the project owner** on 2026-11-18, with an accepted exception and a carried-forward item (DR-2026-11-18-G3A). Exit criterion "tests green on PostgreSQL" is not fully met: the foundation tests pass, but the 3 KI-14 User-model database tests are OPEN and carried forward to G4. |
| G4 First migration | **ACCEPTED by the project owner** (DR-2026-11-18-G4A, 2026-11-18). |
| G5 Features | **AUTHORIZED and IN PROGRESS** (DR-2026-11-18-G4): Phase 2 (authentication). |

### Baseline source

The full text of the approved baseline (v4–v4.6-F3) is preserved verbatim and read-only in `docs/baseline/v4.6-F3/` (G1 step 1; hashes below and in its `SHA256SUMS`). It was extracted from the review session record (Claude Code session `5b02b07d-8604-414d-a821-668198cd3b4b`), of which the project owner holds an offline backup (DR-2026-11-16-P5). A pre-G1 rollback snapshot is in `docs/baseline/pre-g1-snapshot/`.

---

## Decision record DR-2026-11-16-P: G1 preparation decisions

- **Date:** 2026-11-16
- **Approved by:** Project architecture reviewer, acting under delegation from the project owner
- **Subject:** G1 preparation report

| # | Decision ID | Item | Decision | Scope |
|---|---|---|---|---|
| 1 | DR-2026-11-16-P1 | Referenced historical packages A1–A4 | APPROVED for preservation as supporting reference material | **A1** (Project Assessment Report) is historical assessment and context. **A2–A4** (Reconciliation Packages v1, v2, v3) are incorporated by reference **only** where v4–v4.6-F3 explicitly depends on their earlier sections. **The approved baseline remains v4–v4.6-F3.** A1–A4 do not become approved requirements or an approved baseline on their own. Superseded content must never be restored. Proposed TRs remain PROPOSED. Unresolved business decisions remain OPEN unless explicitly approved. |
| 2 | DR-2026-11-16-P2 | `docs/handover/16_ENVIRONMENT_CONFIGURATION.md` | APPROVED for update during G1 | Under the existing DCR-74, DCR-75, DCR-84 and DCR-86 only, and only as far as their baseline content requires: configuration names, purposes, security requirements and environment-variable handling. No DCR-100. No secret values are ever copied or exposed. The root `.env` stays untouched. |
| 3 | DR-2026-11-16-P3 | Root `README.md` | DEFERRED | Excluded from G1 because it's outside the approved DCR scope. To be revisited in G2 or G3. |
| 4 | DR-2026-11-16-P4 | Baseline preservation method | APPROVED | Each package is extracted verbatim from the original session transcript. SHA-256 is calculated from the transcript text and from the extracted file, and the two must match exactly. Each file is read back to verify its beginning and end. Full hashes are recorded in `SHA256SUMS` and the manifest. A1–A4 are kept separate from v4–v4.6-F3. **Any mismatch stops the extraction and is reported.** |
| 5 | DR-2026-11-16-P5 | Offline backup of the session transcript | REQUIRED before G1 | The project owner will make an offline backup of the complete session transcript. It is **not** treated as done until the project owner explicitly confirms it. |

**Gate status at the time of this record (historical):** G1 is NOT STARTED and NOT AUTHORIZED. It needs (a) the owner's confirmation of the offline backup and (b) explicit G1 authorization.

## Decision record DR-2026-11-16-G1: G1 authorization

- **Date:** 2026-11-16
- **Decided by:** Project owner
- **Offline backup (DR-2026-11-16-P5):** CONFIRMED by the project owner. The transcript backup is stored independently of the repository.
- **G1 Documentation Reconciliation:** AUTHORIZED, strictly within DR-2026-11-16-1, DR-2026-11-16-P and the v4–v4.6-F3 baseline.
- **Not authorized:** G2, G3, G4, G5; code, database, migrations, dependencies, Git; reading or modifying `.env`.
- **Preserved:** every proposed TR stays PROPOSED and every OPEN business decision stays OPEN.

### G1 step 1 record: baseline preserved

- **Location:** `docs/baseline/v4.6-F3/` (manifest `README.md`, `SHA256SUMS`, `approved/`, `referenced/`)
- **Result:** 15 of 15 files extracted verbatim. The source hash, file hash and read-back checks all matched. No mismatch.
- **Rollback snapshot:** `docs/baseline/pre-g1-snapshot/` (20 files, `SHA256SUMS` verified)

| File | SHA-256 |
|---|---|
| approved/01_v4.md | 90a740bedef9a4c9815995bdecbf3764b595e58724257919263c59757584c2c6 |
| approved/02_v4.1.md | 2f6206886cf6ef80a6519aacf722f08688c665f701a8bf243a7cac7bb66b69a8 |
| approved/03_v4.2.md | 661cf74557f75812cbec3e89b50e82873cb626da359bd072f31603d185429410 |
| approved/04_v4.3.md | 28eb8c1321aea947a63858e618160e232d44e1b9a1ea619a0b9d658c20193816 |
| approved/05_v4.4.md | 12fe9e7adbd8a503ebe9ad9c98966131fccb48cd378e30c2d2d9f25bfa294df5 |
| approved/06_v4.5.md | 3b115f874754acb00a50bc3751e3d420403d16a4ebf8f79b7eb958a63814f944 |
| approved/07_v4.6.md | f9da3988e4c1fdadc3543ba7d2b7dd669fc5b77b537b870dff55416518a840bb |
| approved/08_v4.6-F.md | bea7683aa3173e225a1821f7fd9f3b42252e61412b470849a80c8d6350b0800a |
| approved/09_v4.6-F1.md | 7adbed6f328a689f5a208144c9214a4c4ef8ab57cfdb887d31d253fca40c3cc5 |
| approved/10_v4.6-F2.md | 20e0dca9cd62f44ef1d6371487797f56b0dd09d0d6c19005d3b91eb4d83f7304 |
| approved/11_v4.6-F3.md | 3a35e06710e2e251390cf02ab505f4ff59ddcb0d5636750b1f7416f0e8e09c05 |
| referenced/A1_assessment.md | ec8f820f6d86aac4f9d4fbfbde8c16ec8b8ad7058e1a7a2897d1fa428bf4d9df |
| referenced/A2_v1.md | b56c4b2442cb5469cb78bf5f7b03d438e2572dd877dc5b5c8777cba08fe7ef95 |
| referenced/A3_v2.md | 330e146262dc0c69c865844fca6576e9f2698a16513ee15c42391214b06fe19a |
| referenced/A4_v3.md | 6a9c227379ba54445fb308198906c7d4c6e9039f5fc5643c08dab06c999e17fd |

---

## Decision record DR-2026-11-17-C: G1 final corrections

- **Date:** 2026-11-17
- **Decided by:** Project owner
- **Subject:** G1 Final Reconciliation Audit (2026-11-17) and the corrections it identified
- **Authorization:** a G1 correction pass only, within DR-2026-11-16-G1. G2–G5 remain NOT AUTHORIZED. Final document statuses remain a separate owner decision.

| # | Decision ID | Item | Decision |
|---|---|---|---|
| 1 | DR-2026-11-17-C1 | Requirement IDs | All existing requirement IDs are preserved. The baseline A2 B.1 proposal to rename FR-REQ-001…003 → FR-INT-001…003 and FR-MAT-006 → FR-FAV-001 is not adopted. |
| 2 | DR-2026-11-17-C2 | Transactional outbox | The core transactional-outbox requirement (SRS FR-NOT-005, Notifications module; `CLAUDE.md` CC-R30) is already approved and doesn't await a further decision. ADR-014 is APPROVED **for that core decision only**. The refinements (TR-11 / ADR-028: two-phase processing, queue key, pseudonymous recipients, event classes, redaction and the rest) stay PROPOSED. |
| 3 | DR-2026-11-17-C3 | `ACCEPTED` | Only the project owner personally may assign the implementation status `ACCEPTED`. A delegated architecture reviewer may review and recommend, but can't assign it. |
| 4 | DR-2026-11-17-C4 | Deletion endpoint paths | The doc 04 §15 catalogue (`/account-deletion/…`) is the canonical endpoint reference. The baseline v4 §10.6 wording `/account/deletion/…` doesn't override it. No endpoint behaviour changes. |
| 5 | DR-2026-11-17-C5 | T2 refund | Confirmed: the T2 refund remains under OD-07b (OPEN). Only the administrative cancellation itself is approved. No financial rule changes. |
| 6 | DR-2026-11-17-C6 | ADR-029 | The ADR-029 document is PROPOSED. TR-14 / DCR-12 remains APPROVED (DR-2026-11-16-2). |
| 7 | DR-2026-11-17-C7 | `CLAUDE.md` CC-R20 | The global lock-order policy (TR-09, TR-22) is qualified as PROPOSED and not binding until its approval is recorded. |
| 8 | DR-2026-11-17-C8 | BLOCKED rule | A requirement is marked BLOCKED in doc 18 only when the whole requirement depends on an OPEN decision; partial dependencies are recorded in its OD-dependency column. |

**Boundaries:** no OD is resolved, no TR is promoted, no requirement ID is changed, and no approved business requirement is changed. Where each correction was applied is recorded in doc 20 §6.

---

## Decision record DR-2026-11-17-A: G1 Documentation Reconciliation — Final Owner Acceptance

- **Decision ID:** DR-2026-11-17-A
- **Date:** 2026-11-17
- **Decided by:** Project owner (personally)
- **Decision status:** APPROVED
- **Scope:** G1 only
- **Approved baseline:** v4–v4.6-F3 (`docs/baseline/v4.6-F3/`, DR-2026-11-16-1)
- **Reviewed before acceptance:** the G1 execution report (2026-11-16), the G1 Final Reconciliation Audit (2026-11-17), the G1 correction report (DR-2026-11-17-C, doc 20 §8) and the G1 status vocabulary confirmation (2026-11-17; document statuses per baseline v4 §6.1).

**Decision:** the project owner accepts the G1 Documentation Reconciliation result. G1 exit item 12 is met, and G1 is COMPLETED. Final document statuses are assigned individually, under the baseline v4 §6.1 document-status model:

| Document status | Documents |
|---|---|
| APPROVED | doc 00 |
| APPROVED_WITH_OPEN_ITEMS (open OD/TR IDs listed in each header) | `CLAUDE.md`; docs 01–19 |
| REFERENCE | doc 20 |
| SUPERSEDED | none |

The full assignment, with reasons, is recorded in doc 20 §5. `CLAUDE.md` remains the authoritative entry point, and doc 12 remains its detailed companion (DR-2026-11-16-3).

**Boundaries:**
- **G2, G3, G4 and G5 are NOT AUTHORIZED.** Each needs separate, explicit owner authorization.
- Accepting the documents changes no underlying status. Every OPEN OD (OD-02…OD-10, and the legacy OD-001…OD-007), every PROPOSED TR (all except TR-05 and TR-14), every REC-BIZ item, every ADR status and DCR-20 (BLOCKED on OD-02 and OD-04) keep their existing statuses. OD-01 stays RESOLVED, and TR-05 and TR-14 stay APPROVED.
- Specifically confirmed as unchanged: ADR-029 is PROPOSED; the shared-notes effect under OD-06l is REC-BIZ, not approved; the T2 refund under OD-07b is OPEN.
- No implementation status changes: 124 NOT_STARTED and 2 BLOCKED (doc 18).

---

## Decision record DR-2026-11-17-G2: G2 authorization

- **Date:** 2026-11-17
- **Decided by:** Project owner
- **G2 Repository Governance:** AUTHORIZED, following the completion of G1 (DR-2026-11-17-A).
- **Not authorized:** G3, G4 and G5. Within G2, also not authorized: commits, pushes, publishing or remote repository settings without separate owner authorization; Django apps, models, migrations, authentication, APIs, frontend and mobile functionality; production infrastructure and deployment; reading or exposing `.env`.
- **Preserved:** every OPEN OD stays OPEN, every PROPOSED TR stays PROPOSED, and no approved business requirement changes.
- **Conflict reported, not resolved:** doc 10 §0.1 lists a "baseline commit" as a G2 activity, while this authorization excludes commits without separate authorization. The commit is held for an owner decision (G2 decision D1, `docs/implementation/progress.md`).

---

## Decision record DR-2026-11-17-G2D: G2 owner decisions (finalization)

- **Date:** 2026-11-17
- **Decided by:** Project owner
- **Subject:** G2 final report, decisions D1–D7
- **Scope:** G2 only. **G3 is NOT AUTHORIZED.**

| # | Decision ID | Item | Decision |
|---|---|---|---|
| 1 | DR-2026-11-17-G2D-1 | D1 Local baseline commit | APPROVED with conditions: exactly one local commit of the approved G2 repository state, after the staging area is reviewed; `.env`, secrets, virtual environments, caches and generated files excluded. The author identity is to be supplied by the owner; the commit isn't made while the identity is a placeholder. No remote, push or publication. |
| 2 | DR-2026-11-17-G2D-2 | D2 TR-13 | **APPROVED:** PostgreSQL-based application testing; CI test coverage on PostgreSQL 16 and 18; SQLite-only test configuration replaced where required. TR-13 changes from PROPOSED to APPROVED. No other TR is affected. |
| 3 | DR-2026-11-17-G2D-3 | D3 Branch model | APPROVED: `main` primary; short-lived `feature/`, `fix/` and `hotfix/` branches; no permanent `develop` branch. |
| 4 | DR-2026-11-17-G2D-4 | D4 Dependency locking | APPROVED: pip-tools; `.in` inputs and hashed lockfiles generated by `pip-compile`; development and production kept separate; the update procedure documented. |
| 5 | DR-2026-11-17-G2D-5 | D5 Existing Ruff failures (KI-11) | DEFERRED to G3. |
| 6 | DR-2026-11-17-G2D-6 | D6 GitHub remote and branch protection | DEFERRED. No repository creation, remote, push or protection changes without separate authorization. |
| 7 | DR-2026-11-17-G2D-7 | D7 LICENSE | DEFERRED. The owner chooses a licence before public distribution or when otherwise required; no file is created. |

**Boundaries:** no OD is resolved, and no TR other than TR-13 changes status. No approved business requirement changes.

---

## Decision record DR-2026-11-17-G2A: G2 Repository Governance — Owner Acceptance with Carried-Forward Items

- **Decision ID:** DR-2026-11-17-G2A
- **Date:** 2026-11-17
- **Decided by:** Project owner
- **Decision status:** APPROVED (a gate decision; the document-status value APPROVED_WITH_OPEN_ITEMS isn't used for gates)
- **Scope:** G2 only
- **Decision:** G2 is accepted, with the items below explicitly carried forward. Baseline commit: `38f491dea79fb9bb10fd2010b1c2cb8a68d545f9` (author Syed Arslan Asghar; 113 files; no remote, no push).

| Carried-forward item | Status / destination |
|---|---|
| doc 10 §0.1 G2 exit criterion "CI runs on the baseline" (CI execution on GitHub) | **OPEN.** Must be satisfied before G4 entry (DR-2026-11-17-G2X) |
| GitHub remote and push | Deferred; needs separate authorization (D6) |
| D6 Remote and branch protection | Deferred |
| KI-11 Existing Ruff failures | G3 |
| KI-14 Tests need the custom User model migration | G4 |
| KI-15 / D7 LICENSE | Deferred; owner decision |

Every other OPEN OD and PROPOSED TR keeps its status.

## Decision record DR-2026-11-17-G2X: Narrow G3-entry exception to the G2 exit criterion

- **Date:** 2026-11-17
- **Decided by:** Project owner
- **Decision status:** APPROVED
- **Exception:** G3 may begin before the doc 10 §0.1 G2 exit criterion "CI runs on the baseline" is satisfied.
- **Conditions:**
  - The criterion stays OPEN and **unchanged**; it isn't completed or permanently waived.
  - The exception covers **G3 entry only**.
  - The criterion **must be satisfied before G4 entry**.
  - No GitHub remote or push is authorized under this exception.
  - The known CI failures keep their assignments: KI-11 to G3, KI-14 to G4.

## Decision record DR-2026-11-17-G3: G3 authorization and the approvals due before G3

- **Date:** 2026-11-17
- **Decided by:** Project owner
- **G3 Backend Foundation:** AUTHORIZED, entered under DR-2026-11-17-G2X. **G4 and G5 are NOT AUTHORIZED.**
- **Not authorized within G3:**
  - generating or applying migrations, or running `migrate`
  - business feature workflows, frontend, mobile
  - deployment, AWS
  - GitHub remote, push or commits without separate authorization

The approvals required before G3 (baseline v4.6 approval-by-gate table, "Before G3"):

| # | Decision ID | Item | Decision |
|---|---|---|---|
| 1 | DR-2026-11-17-G3-1 | TR-12 Same-origin deployment | **APPROVED** as the architectural direction for web/API origin, CORS and cookie/CSRF configuration. It doesn't authorize deployment or infrastructure changes. |
| 2 | DR-2026-11-17-G3-2 | TR-09 / TR-22 Lock policy, LOCK_PLAN tracker, lint rule, FK-inventory review rule | **APPROVED.** G3 builds the shared technical foundations only; no business workflows, and no premature use across feature domains. |
| 3 | DR-2026-11-17-G3-3 | `apps/` layout (doc 07 §1–§3) | **APPROVED:** domain apps in `backend/apps/`, shared infrastructure in `backend/common/`, `accounts` moved to `backend/apps/accounts`, existing behaviour preserved. |
| 4 | DR-2026-11-17-G3-4 | Dependency list | **APPROVED with restrictions:** Celery and Redis only. `django-otp` is **not** added in G3 (deferred to TR-07 at G4). Any other package needs separate approval, with its purpose, necessity, maintenance status and alternatives. |

**Boundaries:** no other OD or TR changes status. ADR-031 stays PROPOSED as a document. The headers of `CLAUDE.md`, doc 07 and doc 08 now have no open items left; changing their document status from APPROVED_WITH_OPEN_ITEMS is a separate owner decision.

---

## Decision record DR-2026-11-17-G3C: G3 controlled correction

- **Date:** 2026-11-17
- **Decided by:** Project owner
- **Scope:** G3 correction only. G3 is NOT accepted. G4 is NOT AUTHORIZED.

| # | Decision ID | Item | Decision |
|---|---|---|---|
| 1 | DR-2026-11-17-G3C-1 | D-1 Celery broker | APPROVED: staging and production require `CELERY_BROKER_URL` or `REDIS_URL` to be set explicitly; no localhost fallback |
| 2 | DR-2026-11-17-G3C-2 | D-2 Python policy | APPROVED: Python 3.12 and 3.13 supported (`requires-python >=3.12,<3.14`); Ruff targets 3.12; lockfiles compiled with 3.12; CI tests both |
| 3 | DR-2026-11-17-G3C-3 | G-3 PostgreSQL foundation tests | APPROVED: automated tests on disposable PostgreSQL only; no migrations, no tables; the 3 User tests stay in G4 |
| 4 | DR-2026-11-17-G3C-4 | Document statuses | `CLAUDE.md`, doc 07 and doc 08 changed from APPROVED_WITH_OPEN_ITEMS to **APPROVED** after their open-item lists were verified empty |

---

## Decision record DR-2026-11-18-G3A: G3 Backend Foundation — Owner Acceptance with an Accepted Exception and Carried-Forward Item

- **Decision ID:** DR-2026-11-18-G3A
- **Date:** 2026-11-18
- **Decided by:** Project owner
- **Decision status:** APPROVED (a gate decision)
- **Scope:** G3 only
- **Decision:** **G3 is ACCEPTED** by the project owner on 2026-11-18, on the evidence of the G3 final verification (2026-11-18; `docs/implementation/progress.md`).

**G3 exit criteria (doc 10 §0.1: "Lint and tests green on PostgreSQL. No migration files.") as accepted:**

| Criterion | Result at acceptance |
|---|---|
| Lint green | Met |
| No migration files | Met |
| Tests green on PostgreSQL | **Not fully met. Accepted by the owner as an exception, with a carry-forward.** The PostgreSQL foundation tests are verified and pass: 77 tests that don't need Django's test database, including the 9 automated PostgreSQL foundation tests, on Python 3.12 and 3.13 × PostgreSQL 16 and 18. The 3 KI-14 User-model database tests **do not pass yet**: the initial User-model migration doesn't exist, so their test-database setup fails. This criterion is **not** recorded as fully met. |

| Owner decision | Detail |
|---|---|
| DR-2026-11-18-G3A-1 | G3 ACCEPTED (2026-11-18). |
| DR-2026-11-18-G3A-2 | **KI-14 carried forward to G4 as an OPEN item.** The 3 migration-dependent User-model database tests must be completed (passing) as part of G4. |
| DR-2026-11-18-G3A-3 | The doc 16 §11 Redis/Celery row correction made during G3 finalization is **retained** (it documents DR-2026-11-17-G3C-1). |
| DR-2026-11-18-G3A-4 | **G4 is NOT AUTHORIZED.** G3 acceptance does not authorize G4 or any part of it. |
| DR-2026-11-18-G3A-5 | Creating or configuring a GitHub remote is **NOT AUTHORIZED**. Pushing any branch or commit is **NOT AUTHORIZED**. |

**Carried forward and still open:**
- The doc 10 §0.1 G2 exit criterion "CI runs on the baseline" stays **OPEN, unchanged**, and must be satisfied before G4 entry (DR-2026-11-17-G2X). Satisfying it needs a remote and a push, which DR-2026-11-18-G3A-5 does not authorize.
- KI-14 (3 User-model database tests): OPEN, G4.

**Boundaries:** no prior decision changes meaning. No OD, TR, requirement or document status changes. The baseline commit `38f491dea79fb9bb10fd2010b1c2cb8a68d545f9` is unchanged, and the G3 changes remain uncommitted.

---

## Decision record DR-2026-11-18-CI: Current delivery scope — CI/CD implementation and validation; AWS deployment deferred

- **Decision ID:** DR-2026-11-18-CI
- **Date:** 2026-11-18
- **Decided by:** Project owner
- **Decision status:** APPROVED (scope clarification)
- **Decision:** the current objective is to **implement and validate CI/CD** for Matermonial. **AWS deployment and production infrastructure are not part of the current scope.**

**In current scope:**
1. Repository governance and Git workflow.
2. GitHub remote configuration, once explicitly authorized.
3. GitHub Actions CI implementation and validation.
4. Automated backend testing.
5. Lint and format checks.
6. Dependency and lockfile integrity checks.
7. Build and integration validation.
8. CD workflow design and implementation.
9. Pipeline documentation.
10. Validation of the complete CI/CD workflow.

**Deferred (out of current scope; each needs separate authorization when deployment is actually required):**
- AWS EC2 provisioning and AWS infrastructure configuration
- production deployment
- production Docker/Compose infrastructure
- production PostgreSQL and Redis provisioning
- domain and DNS; SSL certificates
- production monitoring and backup infrastructure
- AWS-specific deployment automation

No speculative infrastructure tasks are added.

**CD boundary:**
- The CD workflow structure may be designed and implemented. Deployment execution stays disabled, manual or protected until a deployment target and an authorization exist.
- No AWS deployment is executed, no AWS resource is provisioned, and no AWS credential or secret is introduced.
- Documentation says which parts are implemented and which are deferred. CI/CD work is never presented as a completed production deployment.

**Bug handling:** a bug found during CI/CD work is investigated. It is fixed if that is needed to complete or validate the CI/CD scope; otherwise it is recorded in `docs/implementation/known_issues.md`. No unrelated refactoring and no scope expansion.

**Boundaries:**
- This clarification sequences work; it changes no approved decision or requirement. The approved production stack (`CLAUDE.md` CC-R11, CC-R22) and the target pipeline in doc 09 §12–§13 remain the approved targets. Their deployment parts are deferred, not removed.
- It does **not** authorize a GitHub remote, a push, a commit, G4, or any deployment. Each still needs explicit owner authorization.
- Unchanged: G3 ACCEPTED (DR-2026-11-18-G3A); KI-14 OPEN (G4); the G2 criterion "CI runs on the baseline" OPEN (DR-2026-11-17-G2X); G4 NOT AUTHORIZED.

---

## Decision record DR-2026-11-18-GH: Owner-performed GitHub remote, commit and push; first CI evidence

- **Decision ID:** DR-2026-11-18-GH
- **Date:** 2026-11-18
- **Recorded from:** the project owner's confirmation (2026-11-18)
- **Nature:** a record of actions the **project owner performed manually**. They happened after DR-2026-11-18-G3A-5 (which said Claude Code was not authorized to create a remote or push) and are recorded as of the date they occurred. Earlier records are unchanged and are not reinterpreted as prior authorization.

| Owner action (2026-11-18) | Detail |
|---|---|
| Commit | `c5fc346cb8b6f871c4056a0938f7bd2bc603212f`, "added first commit", parent `38f491dea79fb9bb10fd2010b1c2cb8a68d545f9` (baseline, unchanged). It contains the G2-to-G3 working-tree changes: 69 files, including the G3 foundation, the G3 correction, the CI pre-G4 preparation and the related documentation. A content check found no `.env` (only `.env.example`), no caches, no virtual environment, no key files and no migrations. |
| Remote | `origin` = `https://github.com/SyedArslanAsghar/Matermonial.git`. The repository is **public** (GitHub API, 2026-11-18). |
| Push | `main` pushed; `origin/main` = `c5fc346`. |

**First GitHub Actions evidence (read-only review via the public GitHub API, 2026-11-18):**
- Workflow "CI", run `44294474904`, event `push`, branch `main`, commit `c5fc346`: **completed, conclusion success**.
- 6 of 6 jobs succeeded: Backend quality on Python 3.12 and 3.13; Backend tests on Python 3.12 and 3.13 × PostgreSQL 16 and 18.
- Every step succeeded. The lockfile consistency step was skipped on 3.13 by design, because it runs on 3.12 only.
- Each test job carries the notice "3 tests DEFERRED to G4 (KI-14) … not run and not passed".
- Warnings: actions `checkout@v4` and `setup-python@v5` target the deprecated Node.js 20; the `ubuntu-latest` label is migrating to a newer Ubuntu release.
- Not reviewable without authentication: the job logs, so per-test counts on GitHub weren't read.
- No workflow run exists for the baseline commit `38f491d` itself; only the head commit of the push triggered CI.

**G2 criterion "CI runs on the baseline" (doc 10 §0.1; DR-2026-11-17-G2X):** **still OPEN**. CI evidence now exists for `c5fc346`, which builds on the baseline `38f491d`. Whether that satisfies the criterion is the **owner's decision**; it isn't recorded as complete here.

**Boundaries:**
- Claude Code still performs no commit, push, remote or branch-protection operation without explicit authorization.
- G4 NOT AUTHORIZED. AWS deployment deferred (DR-2026-11-18-CI).
- KI-15 (no LICENSE) is unchanged, but its trigger "before public distribution" is now relevant, because the repository is public.

---

## Decision record DR-2026-11-18-G2C: G2 criterion "CI runs on the baseline" — accepted on the integrated run (Option A)

- **Decision ID:** DR-2026-11-18-G2C
- **Date:** 2026-11-18
- **Decided by:** Project owner
- **Decision status:** APPROVED (a gate-criterion decision)
- **Original criterion:** doc 10 §0.1 G2 exit criterion "CI runs on the baseline". It was carried forward OPEN by DR-2026-11-17-G2A, under the G3-entry exception DR-2026-11-17-G2X, which required it to be satisfied before G4 entry.
- **Evidence:** GitHub Actions workflow "CI", run `44294474904` (push to `main`), on commit `c5fc346cb8b6f871c4056a0938f7bd2bc603212f`: **success**, 6/6 jobs (DR-2026-11-18-GH).
  - Backend quality passed on Python 3.12 and 3.13.
  - Backend tests passed on Python 3.12 and 3.13 × PostgreSQL 16 and 18.
  - The 3 KI-14 tests were explicitly reported as DEFERRED, not as passed.
- **Decision (D1, Option A):** the owner **accepts the successful integrated run on `c5fc346` as satisfying the criterion**. `c5fc346` contains the G2 baseline together with the approved G3 implementation.
- **Qualification:** the exact G2 baseline commit `38f491dea79fb9bb10fd2010b1c2cb8a68d545f9` **did not run** through GitHub Actions on its own. The criterion is satisfied by owner acceptance of the integrated run, not by a test of `38f491d` itself.
- **Effect:**
  - The G2 carried-forward item "CI runs on the baseline" is **closed**.
  - The G4-entry precondition in DR-2026-11-17-G2X is met.
  - G4 itself is **NOT AUTHORIZED** (D3) and needs its own owner authorization.
- **Unchanged:**
  - KI-14: the 3 User-model database tests stay **OPEN**, carried forward to G4 (DR-2026-11-18-G3A-2).
  - AWS deployment stays **DEFERRED** (D4; DR-2026-11-18-CI).
  - D6 (branch protection) and KI-15 (licence) stay deferred.
  - No other OD, TR, requirement or document status changes.
- **Related authorization (D2):** commit the governance records on the short-lived branch `docs/ci-governance-acceptance`, push it, and open a pull request to `main`. Merging is **not** authorized and waits for owner review.

---

## Decision record DR-2026-11-18-G4: G4 and G5 authorized; G4 decision package adopted

- **Decision ID:** DR-2026-11-18-G4
- **Date:** 2026-11-18
- **Decided by:** Project owner
- **Decision status:** APPROVED
- **Decision:** **G4 (First migration and complete backend kernel) and G5 (Features, per the roadmap) are AUTHORIZED** for development and validation. Not authorized: AWS and production deployment, production secrets and key management, CI/CD changes (the owner handles CI/CD separately), production release, public launch, live payment processing.
- **Baseline:** the G4 owner decision package (2026-11-18) is the implementation baseline unless it conflicts with an approved requirement or reveals a material security, data-integrity or legal issue.

| # | ID | Item | Decision |
|---|---|---|---|
| 1 | DR-2026-11-18-G4-1 | D-1 scope | Full G4 kernel (doc 10 §0.1), built in reviewable internal stages; every kernel component complete before G4 exit; one initial migration per app at G4 exit |
| 2 | DR-2026-11-18-G4-2 | D-4 | Option A′: keep `PermissionsMixin`; `AdminRole` tables the only permission source; Django groups and `user_permissions` unused, enforced by database trigger and tests; `is_staff` a projection; `is_superuser` break-glass only |
| 3 | DR-2026-11-18-G4-3 | D-5 | `django-otp` deferred to its G5 phase (Django 5.2 compatibility verified before use). `cryptography` and its transitive dependencies approved for G4; local development keys only |
| 4 | DR-2026-11-18-G4-4 | D-7 | G3 no-migrations guard replaced by a migrations-in-sync guard |
| 5 | DR-2026-11-18-G4-5 | D-8 | Disposable PostgreSQL 16 and 18 containers; the owner's server on port 5432 is never used |
| 6 | DR-2026-11-18-G4-6 | D-9 | App placement: `apps/accounts` (User, AuthSession, AuthToken, AccountSecurityEvent, SubjectPseudonym, SubjectDataKey); `apps/audit` (AuditLog, hold tables); `common/events` (OutboxEvent); `common/idempotency` (IdempotencyRecord); `apps/platform_ops` (TR-24 tables); admin-authorization models in the accounts / admin-access domain |
| 7 | DR-2026-11-18-G4-7 | D-10 | G4 kernel test list per the decision package (KI-14, UUIDv7, logs, audit and security events, outbox, registry, lock order, migrations) |
| 8 | DR-2026-11-18-G4-8 | D-11 | Append-only enforced by database triggers in G4; GRANT model documented and tested; production role separation is deployment work |
| 9 | DR-2026-11-18-G4-9 | User refinements | E.164 CHECK; deactivation consistency CHECK; nullable `deactivated_reason`; case-insensitive unique email with normalisation; UUID primary-key architecture test; doc 03 verification-field naming corrected |
| 10 | DR-2026-11-18-G4-10 | TRs | **APPROVED:** TR-01, TR-07, TR-11, TR-17, TR-23; TR-21 schema portion only; TR-24 schema portion with a local/mock registry. TR-02 stays for Phase 4 |
| 11 | DR-2026-11-18-G4-11 | ADRs | **APPROVED:** ADR-014 refinements, ADR-022, ADR-023, ADR-025, ADR-027, ADR-028, ADR-029, ADR-031, ADR-032. **Direction adopted:** ADR-026, ADR-030 (later-phase functionality not implemented early) |

**Clarification policy:** ordinary implementation decisions use engineering judgment and are documented. The owner is asked only when an approved requirement would change, approved requirements conflict, business rules would materially change, a material security, privacy, data-loss or legal risk can't be resolved within the approved design, or work needs AWS, production deployment, production credentials or a financial commitment.

**Unchanged:** OD-02…OD-10 stay OPEN; behaviour depending on them isn't implemented (CC-R25). AWS deployment stays deferred (DR-2026-11-18-CI).

---

## Decision record DR-2026-11-18-G4A: G4 accepted by the owner

- **Decision ID:** DR-2026-11-18-G4A
- **Date:** 2026-11-18
- **Decided by:** Project owner
- **Decision status:** APPROVED (gate decision)
- **Decision:** **G4 (First migration and backend kernel) is ACCEPTED**, on the evidence recorded in `docs/implementation/progress.md` (G4 section): 220/220 tests on Python 3.12/3.13 × PostgreSQL 16/18, five initial migrations validated from empty and reversible, KI-14 resolved. Branch `feature/g4-kernel` (9 commits) is pushed; the PR is opened by the owner.
- **Owner responsibilities:** KI-21 (remove the obsolete KI-14 CI step) is the owner's; CI/CD stays with the owner.
- **Unchanged:** G5 authorized (DR-2026-11-18-G4); OD-04c OPEN, so step-up re-authentication is password-only; AWS deferred.

---

## Decision record DR-2026-11-19-P3: G5 Phase 3 decisions (TR-10, value lists)

- **Decision ID:** DR-2026-11-19-P3
- **Date:** 2026-11-19
- **Decided by:** Project owner (answers given in the Claude Code session at the start of G5 Phase 3)
- **Decision status:** APPROVED (items 1–2); item 3 is an implementation ASSUMPTION awaiting owner confirmation

| # | ID | Item | Decision |
|---|---|---|---|
| 1 | DR-2026-11-19-P3-1 | TR-10 upload pipeline | **APPROVED** with the dependencies **Pillow** and **filetype**. Pipeline: quarantine, byte-level type detection, malware scan, re-encode to strip EXIF/GPS, discard originals, private storage. The scanner is a provider interface: mock locally and in tests, **disabled (uploads refused) when deployed** until a real scanner is approved |
| 2 | DR-2026-11-19-P3-2 *(implementation superseded by DR-2026-11-19-R-1)* | Profile and preference value lists | Reference lists defined in code (like the admin catalogue). Only neutral lists are seeded, as documented assumptions. **Gender, marital status, religion, community and caste stay empty until the owner supplies or approves them**; those fields accept no value until then |
| 3 | DR-2026-11-19-P3-3 *(superseded by DR-2026-11-19-R-2)* | Required fields for completion and DRAFT → PENDING_REVIEW | *Not answered.* Configurable default, recorded as an assumption: basic info (name, DOB 18+, gender, marital status, religion, nationality), location (country, city), at least one language, employment status. Education, family and lifestyle count toward the percentage only. Photos are excluded |

**Consequence:** until item 2's sensitive lists are supplied, no profile can complete basic info, so none can be submitted for review.

---

## Decision record DR-2026-11-19-R: owner review of G5 Phases 2 and 3

- **Decision ID:** DR-2026-11-19-R
- **Date:** 2026-11-19
- **Decided by:** Project owner (review of the Phase 2/3 completion report)
- **Decision status:** item 1 APPROVED (direction) and implemented; items 2–3 PROPOSED, awaiting owner confirmation; items 4–5 standing instructions

| # | ID | Item | Decision |
|---|---|---|---|
| 1 | DR-2026-11-19-R-1 | Profile value lists | **Supersedes DR-2026-11-19-P3-2's hardcoded lists.** Admin-managed controlled vocabularies: stable codes separate from labels, ordering, deactivation, existing data preserved, new options without code changes. No religion, community or caste value is invented, and no new mandatory disclosure is added. Proposals are seeded **inactive**; nothing unapproved is active. Implemented in `414ec8e` |
| 2 | DR-2026-11-19-R-2 | Required profile fields | **Proposed MVP baseline, subject to owner confirmation** (replaces assumption DR-2026-11-19-P3-3): name, date of birth, gender, marital status, religion, nationality, country, city, at least one language, employment status. Submission stays unavailable while a required vocabulary has no active option (`vocabulary_not_configured`) |
| 3 | DR-2026-11-19-R-3 | Admin MFA recovery | Review requested. **ADR-033 Amendment 1 (PROPOSED)** prepared; the current behaviour stays until the owner decides A1-1…A1-5 |
| 4 | DR-2026-11-19-R-4 | Malware scanner | TR-10 and fail-closed behaviour preserved: deployed environments refuse the mock scanner, and uploads are refused while no real scanner exists. A real scanner (and any infrastructure for it) needs owner approval before production |
| 5 | DR-2026-11-19-R-5 | Scope | Phase 4 is **not authorized** until the owner says so explicitly. No push, PR, CI/CD, AWS or port 5432 work |

---

## OD-01 approved functional-domain catalogue

**Source key:**
- **H** = the name follows an SRS section heading
- **C** = coined by splitting an SRS section

All names are reconstructed (no original approved list existed) and are now approved by DR-2026-11-16-5.

| # | Domain | Description | Source | Modules | Related FRs |
|---|---|---|---|---|---|
| D01 | Accounts and Eligibility | Registration, account/profile separation, audit fields, phone normalisation, adult eligibility, deactivation, limited browsing | H | M01 | FR-001, 002, 004, 005, 006; FR-ACC-001, 003, 004, 006–009 |
| D02 | Authentication and Session Security | Login/logout, password recovery, sessions and tokens, step-up, security events, rate limits | C | M01, M15 | FR-007; FR-ACC-005 |
| D03 | Phone Verification | OTP issuance and verification, resend and attempt limits | C | M04, M01 flag | FR-003; FR-ACC-002; FR-VER-001 |
| D04 | Matrimonial Profiles | Creation, sections, lifecycle, location, education and profession, family and lifestyle, languages, completion, DOB privacy, activation, locked fields | H | M02 | FR-008, 009, 011–016; FR-PRO-001…007 |
| D05 | Profile Media | Photo upload, processing, moderation status, private storage | C | M02, M10, M13 | FR-017; FR-PRO-008; FR-PRI-009 |
| D06 | Identity Verification | Submission, review, rejection and resubmission, duplicate detection, reviewer audit, re-verification | H | M04 | FR-010; FR-VER-002…006 |
| D07 | Partner Preferences | Preferences, nullable booleans, financial range, optional criteria | H | M03 | FR-018…021 |
| D08 | Family Management | Invitation, acceptance, permissions, templates, sensitive permissions, lifecycle, expiry, owner control, activity tracking | H | M05 | FR-FAM-001…009 |
| D09 | Search and Matching | Search, worldwide search, rule-based matching, optional criteria, eligibility filters | H | M06 | FR-MAT-001…005 |
| D10 | Favorites and Private Notes | Account-scoped favorites and notes | C | M06 | FR-MAT-006 |
| D11 | Profile Views and View Billing | View grants, 24-hour window, allowance-then-purchased consumption | C | M06, M11 | FR-MAT-007; FR-SUB-012 |
| D12 | Interests | Express interest, responses, decline history and cooldown | C | M07 | FR-REQ-001…003 |
| D13 | Formal Requests | Creation, duplicate prevention, expiry, withdrawal, cancellation, history, atomic charge | C | M07, M11 | FR-REQ-004…009 |
| D14 | Connections and Relationship Progress | Connection lifecycle, reopening, progress stages, history, shared notes | H | M08 | FR-CON-001…006 |
| D15 | Messaging and Shared Documents | Conversations, participants, eligibility, manager communication, attachments, document sharing and permissions | H | M09 | FR-MSG-001…010 |
| D16 | Privacy and Media Access | Blocking, unblocking, Hide My Profile From, photo permissions, visitor history, private browsing, visibility | H | M10 | FR-PRI-001…008; FR-PRO-006 |
| D17 | Subscriptions and Credits | Plans, allowances, expiry, top-ups, separate balances, consumption order, cancellation, billing identity | H | M11 | FR-SUB-001…006, 008, 009, 011 |
| D18 | Payments | JazzCash integration, callbacks, payment history, refunds, reconciliation | C | M11 | FR-SUB-007, 010; SRS §2.1 |
| D19 | Notifications | In-app, email, SMS, push; preferences; security notices; outbox; templates | H | M12 | SRS §15 (proposed FR-NOT-*) |
| D20 | Moderation and Reporting | Reports, evidence, cases, assignment, restrictions, appeals, conflict of interest | H | M13 | SRS §16 (proposed FR-MOD-*) |
| D21 | Data Export and Account Deletion | Download my data, recovery period, deletion processing, retention exceptions, manager deletion | H | M14 | FR-DAT-001…010 |
| D22 | Administration, Audit and Platform Operations | Admin roles, configuration, plans and packages, templates, feature flags, support, maintenance, audit history, compliance registry | H | M15, M16 | SRS §18 (proposed FR-ADM-*); NFR §19.1 |

**Coverage:** 14 H + 8 C = 22 domains. Every database module M01–M16 is mapped. Cross-cutting concerns, not counted as domains: localization (NFR §19.7), security, privacy, reliability, performance, and the family-manager ActorContext.

**Owner of each overlap:**

| Overlap | Owner rule |
|---|---|
| D03 ↔ D01 | D03 writes `is_phone_verified` |
| D05 ↔ D20 | D05 owns photo moderation status. D20 owns reports. |
| D11 ↔ D09 / D17 | Search impressions never charge. D17 owns the ledger. |
| D11 ↔ D16 | ProfileView is billing and security. VisitorHistory is display. |
| D13 ↔ D17 | Only D17 writes the ledger |
| D08 ↔ D15 | Manager communication is defined in D08 and enforced in D15 |
| D02 ↔ D22 | Security events vs. admin audit |
| D21 ↔ all | Each domain provides an idempotent deletion handler |
| D18 ↔ D17 | Payment confirmation leads to grants through the outbox |
