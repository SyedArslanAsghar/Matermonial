# Matermonial — Documentation Correction Register

**Document status:** REFERENCE (project owner, 2026-11-17, DR-2026-11-17-A; record in doc 20 §5). Historical register of documentation corrections, contradictions and approvals; informative, not a requirements or instruction source. It records, without changing, DCR-20 BLOCKED (OD-02, OD-04) and the OPEN ODs and PROPOSED TRs that its entries cite (status in doc 19).
**Created:** 2026-11-16, G1 step 2 (DCR-34)
**Source of truth for every entry:** the approved baseline in `docs/baseline/v4.6-F3/` (DR-2026-11-16-1)

## 1. Purpose

This register records every documentation correction (DCR), where it was applied, and the source text it was applied from. It also records every contradiction (C) found during specification reconciliation and how it was resolved.

**Rules:**
- An approved DCR authorizes a *documentation change*. It doesn't approve the technical recommendations (TR) or business recommendations (REC-BIZ) it carries. Those keep their own status in doc 19.
- Where baseline packages disagree, the later package wins. Superseded wording is never applied.
- **G1 status values:** `PENDING` (not yet applied), `APPLIED` (applied, with location), `BLOCKED` (can't be applied; reason given).

**Package abbreviations:**

| Code | File |
|---|---|
| v4 | `approved/01_v4.md` |
| v4.1 | `approved/02_v4.1.md` |
| v4.2 | `approved/03_v4.2.md` |
| v4.3 | `approved/04_v4.3.md` |
| v4.4 | `approved/05_v4.4.md` |
| v4.5 | `approved/06_v4.5.md` |
| v4.6 | `approved/07_v4.6.md` |
| F | `approved/08_v4.6-F.md` |
| F1 | `approved/09_v4.6-F1.md` |
| F2 | `approved/10_v4.6-F2.md` |
| F3 | `approved/11_v4.6-F3.md` |
| A2 / A3 / A4 | `referenced/` v1 / v2 / v3 (cited sections only, DR-2026-11-16-P1) |

## 2. Approval history

| Date | Decision | Effect |
|---|---|---|
| 2026-11-16 | DR-2026-11-16-1 | Baseline v4–v4.6-F3 approved. DCR-12/TR-14, DCR-09/DCR-45 and TR-05 approved. OD-01 resolved. |
| 2026-11-16 | DR-2026-11-16-P | A1–A4 kept as reference only. Doc 16 in G1 scope under DCR-74/75/84/86. README deferred. Preservation method approved. |
| 2026-11-16 | DR-2026-11-16-G1 | Offline backup confirmed. G1 authorized. |
| 2026-11-17 | DR-2026-11-17-C | G1 final reconciliation audit reviewed; G1 correction pass authorized and applied (§8). Owner decisions C1–C8 recorded in `docs/decisions/new_architecture_decisions.md`. Final document statuses are still to be set by the owner. |
| 2026-11-17 | DR-2026-11-17-A | **G1 final owner acceptance.** G1 result accepted; final document statuses assigned (§5). G1 COMPLETED. G2–G5 not authorized. All OPEN ODs, PROPOSED TRs, REC-BIZ items and DCR-20 (BLOCKED) keep their status. |
| 2026-11-17 | DR-2026-11-17-G2, DR-2026-11-17-G2D | G2 authorized. G2 decisions: TR-13 **APPROVED** (TR-13 removed from the open-item headers of docs 08, 12, 13 and 19, and its labels updated in docs 08, 12, 13 and 19); branch model and pip-tools recorded in doc 07 §8 and §13; D5–D7 deferred. No document status changed. |
| 2026-11-17 | DR-2026-11-17-G2A, -G2X, -G3 | G2 accepted with carried-forward items; baseline commit `38f491dea79f`; G3-entry exception. TR-09, TR-12, TR-22 **APPROVED**: labels updated in `CLAUDE.md` CC-R20 and docs 02, 07, 08, 11, 12 and 19, and removed from open-item headers. `apps/` layout recorded in doc 07 §1. No document status changed. |
| 2026-11-17 | DR-2026-11-17-G3C | G3 correction pass. Document status changes: `CLAUDE.md`, doc 07, doc 08 → **APPROVED** (§5). No other status changed. |
| 2026-11-18 | DR-2026-11-18-G3A | **G3 accepted by the project owner**, with an accepted exception: the exit criterion "tests green on PostgreSQL" is not fully met. The foundation tests pass; the 3 KI-14 User-model database tests are OPEN and carried forward to G4. The doc 16 §11 Redis/Celery row correction is retained. A G3 status note was added to doc 10 §0.1, and the gate status was updated in `docs/decisions/new_architecture_decisions.md` and `docs/implementation/` (`progress.md`, `known_issues.md`, `pending_features.md`). G4 NOT AUTHORIZED; GitHub remote and push NOT AUTHORIZED; the G2 criterion "CI runs on the baseline" stays OPEN before G4 (DR-2026-11-17-G2X). Following the acceptance, the CI pre-G4 preparation changed the test job in two ways: a guard against a missing `MATERMONIAL_TEST_POSTGRES_URL`, and exactly the 3 KI-14 tests reported as DEFERRED. The README "Formatting, linting and tests" and "CI/CD" sections and `progress.md` were updated to match. No document status changed. |
| 2026-11-18 | DR-2026-11-18-CI | **Scope clarification:** the current objective is CI/CD implementation and validation. AWS deployment and production infrastructure are deferred and out of current scope; the CD boundary and bug-handling policy are recorded in the decision record. Recorded in `docs/decisions/new_architecture_decisions.md` and `progress.md`. No approved decision, requirement or document status changed. Docs 09 and 10 are unchanged; their deployment parts are deferred, not removed. |
| 2026-11-18 | DR-2026-11-18-GH | Owner-performed actions recorded: commit `c5fc346`, remote `origin` (public), push of `main`. First GitHub Actions run `44294474904`: success, 6/6 jobs. The G2 criterion "CI runs on the baseline" stays OPEN pending the owner's decision. Current-state statements were updated in `progress.md`, `known_issues.md` (KI-2, KI-12; new KI-19), the README and the decision register's gate status. Historical records, including DR-2026-11-18-G3A, are unchanged. No document status changed. |
| 2026-11-18 | DR-2026-11-18-G2C | **G2 criterion "CI runs on the baseline" accepted by the owner (Option A)** on the integrated run `44294474904` on commit `c5fc346` (success, 6/6 jobs). The baseline commit `38f491d` itself did not run independently. KI-12 resolved; KI-14 stays OPEN (G4). G4 NOT AUTHORIZED; AWS deployment deferred. Recorded in the decision register (record and gate status), `progress.md`, `known_issues.md` and the README. Doc 10 §0.1's dated "G2 status (2026-11-17)" note was not changed in this commit, which is limited to 5 files; it is to be updated separately. No document status changed. |
| 2026-11-18 | DR-2026-11-18-G2C (follow-up) | Doc 10 §0.1 received a dated "G2 criterion update (2026-11-18)" note: owner acceptance of CI run `44294474904` on `c5fc346`; `38f491d` did not run through CI on its own; the G4-entry CI precondition is met, but G4 is not authorized. The 2026-11-17 G2 status note is unchanged, and no document status changed. |
| 2026-11-18 | DR-2026-11-18-G4 | **G4 and G5 authorized**; G4 decision package adopted. TR-01, TR-07, TR-11, TR-17, TR-23 → APPROVED; TR-21 and TR-24 → APPROVED (schema portions); TR-02 stays for Phase 4 (doc 19 §4). ADR-014 refinements, 022, 023 (doc 11) and ADR-025, 027, 028, 029, 031, 032 → APPROVED; ADR-026 and 030 → direction adopted. No document status changed. |
| 2026-11-18 | DR-2026-11-18-G4-9 | Doc 03 §2.1: `phone_verified` / `email_verified` renamed `is_phone_verified` / `is_email_verified` to match §22.1 and the model; email uniqueness stated as case-insensitive. |

## 3. DCR register

| DCR | Source (final wording) | Target | Correction | G1 status | Applied at |
|---|---|---|---|---|---|
| DCR-01 | v4 §4; A2 B.1 | 01 | Single `FR-<DOMAIN>-NNN` scheme with legacy-ID column; both status columns | APPLIED | doc 01 §0.1, §6, §15, §16, §18, §19 (labels); doc 18 (legacy-ID and both status columns); doc 01 §6 FR-PREF labels completed in the G1 correction pass (see section 8 of this register). The A2 B.1 FR-INT/FR-FAV renaming is **not adopted** (owner decision DR-2026-11-17-C1), so it isn't outstanding DCR-01 work (see section 6, note 1, of this register). |
| DCR-02 | v4 §5; F Part 5.2 | 01 | Approved 22-domain catalogue with module and FR mapping | APPLIED | doc 01 §0.2; doc 00 §5 |
| DCR-03 | v4 §4 | 01 §1.4, 02 §3.1 | Remove SQLAdmin; Django Admin (TR-07, PROPOSED) | APPLIED | doc 01 §1.4; doc 02 §3.1 |
| DCR-04 | v4 §4; A4 §5; v4.1 C16 | 03, 04, 05, 15 | Interest model and state machine | APPLIED | doc 03 §22.7; doc 04 §8; doc 05 §25.1; doc 15 §5 |
| DCR-05 | v4 §7; A4 §6 | 03 | Source-of-truth register | APPLIED | doc 03 §22.1 |
| DCR-06 | A4 §7 | 14 | Permission matrix (OD-05 OPEN) | APPLIED | doc 14 §9 |
| DCR-07 | v4 §11 and later amendments | 15 | Corrected state machines | APPLIED | doc 15 §2–§8, §11, §15, §17–§20 |
| DCR-08 | A4 §11 | 10 | Gated roadmap G1–G5 | APPLIED | doc 10 §0.1–§0.3 |
| DCR-09 | v4 §4, §14.2 | `CLAUDE.md` | Concise authoritative entry point: paths, §20, duplicates, rule IDs, pointers | APPLIED | `CLAUDE.md` (whole file) |
| DCR-10 | v4 §6.1 | All docs | Document-status header | APPLIED | Headers of `CLAUDE.md` and docs 00–20 |
| DCR-11 | v4 §14.1 | New doc 18 | Traceability matrix | APPLIED | doc 18 |
| DCR-12 | v4 §6 | 00 §9, 13 §6, `CLAUDE.md` §19, 12 | Three status dimensions; owner-only `ACCEPTED` | APPLIED | doc 00 §9.1; doc 13 §6; `CLAUDE.md` CC-R69–CC-R70; doc 12 §3 |
| DCR-13 | v4 §4 | 03 §18 | Remove the duplicated "one wallet" item | APPLIED | doc 03 §18 item 17 |
| DCR-14 | v4 §4 | 03 §7.2 | Billing account = owner of the represented profile; `ProfileView.billing_account` | APPLIED | doc 03 §7.2, §22.6 |
| DCR-15 | v4 §4 | 03 §10.7, §11.5 | Partial unique on ACTIVE permissions | APPLIED | doc 03 §10.7, §11.5, §18 item 16, §22.9–§22.10 |
| DCR-16 | v4 §10; v4.2 C17; v4.3 §1 | 06, 01 FR-007/FR-ACC-005 | Authentication lifecycle | APPLIED | doc 06 §22.1–§22.2; doc 01 FR-007, FR-ACC-005; doc 04 §2 |
| DCR-17 | A4 §9 | 04 | Acting-profile algorithm, idempotency, error catalogue | APPLIED | doc 04 §24.1 |
| DCR-18 | v4 §4 | 07 | Docs tree | APPLIED | doc 07 §1 |
| DCR-19 | v4 §4; A2 B.5 | 03 | New models | APPLIED | doc 03 §22.2–§22.14 |
| DCR-20 | v4 §4 | 01 | FR-001, FR-PRO-005, FR-ACC-009 details | **BLOCKED** | Depends on OD-02 and OD-04 (OPEN); BLOCKED notes added at doc 01 FR-001, FR-ACC-009, FR-PRO-005 |
| DCR-21 | v4 §4 | 05 §4.3, 15 §6 | "Recipient (via owner or authorized manager)" | APPLIED | doc 05 §4 rule 3; doc 15 §5–§6 |
| DCR-22 | v4 §4 | 03 M12, 02 §14 | `OutboxEvent` in `common/events` | APPLIED | doc 03 §13.10, §22.12; doc 02 §14 |
| DCR-23 | v4 §4 | 03 §13.3 | Remove `security_notifications_enabled` | APPLIED | doc 03 §13.3 |
| DCR-24 | v4 §4 | 17 | Glossary terms | APPLIED | doc 17 |
| DCR-25 | v4 §4, §10.5 | 03 §2.2, §2.3 | `LoginHistory` retired; AuthSession + AccountSecurityEvent | APPLIED | doc 03 §2.3, §22.2 |
| DCR-26 | A4 §10; v4 §8 | 04 §3 | `POST /profiles/{id}/views/` charges; GET side-effect-free | APPLIED | doc 04 §3, §24.2; doc 05 §18 |
| DCR-27 | A4 §5 | 03 M07 | `MatrimonialRequest.source_interest` canonical link | APPLIED | doc 03 §22.7 |
| DCR-28 | v4 §4 | 11, `docs/decisions/` | ADR-025…032 (PROPOSED); decisions on ADR-014/022/023 | APPLIED | doc 11 §25 and notes on ADR-014/022/023; `docs/decisions/ADR-025…032` (all PROPOSED, including the ADR-029 document, DR-2026-11-17-C6). ADR-014: APPROVED for its core decision only (DR-2026-11-17-C2). ADR-022/023: decisions pending, due before G4. |
| DCR-29 | v4 §9 | 01, 06 | Access levels L0–L3 (OD-03 OPEN) | APPLIED | doc 01 FR-009; doc 06 §22.4 |
| DCR-30 | v4 §15 OD-09 | 01 FR-SUB-008/009, 05 §16 | Subscription scenarios (OD-09 OPEN) | APPLIED | doc 01 FR-SUB-008/009; doc 05 §16, §25.8 |
| DCR-31 | A4 §6 | 03 M11, 05 §17 | Ledger and projections | APPLIED | doc 03 §12.5, §12.7, §22.11; doc 05 §17, §25.7 |
| DCR-32 | A4 §7 | 14 | Permission tiers N/S/H/O | APPLIED | doc 14 §9 |
| DCR-33 | v4 §17; F1/F2/F3 totals | 10, 13 | G1 exit checklist; no implementation from an unanswered OD | APPLIED | doc 10 §0.4–§0.5; doc 13 §4.0; `CLAUDE.md` CC-R25 |
| DCR-34 | v4 §14.1 | New docs 18–20; 00 | Create docs 18–20; add to doc 00 | APPLIED | docs 18, 19, 20 created; doc 00 §4 |
| DCR-35 | v4 §10.5 | 03 §2.2, 06 | Security-event model | APPLIED | doc 03 §2.2, §22.2; doc 06 §22.3 |
| DCR-36 | v4 §7 A | 03 §7.2, §11.6–11.7; 01 FR-PRI-006…008 | ProfileView ↔ VisitorHistory | APPLIED | doc 03 §22.6; doc 01 FR-PRI-006 |
| DCR-37 | v4 §7 B; v4.1 C12 | 03 §9; 15 §7; 01 FR-CON-002/004 | Connection lifecycle vs progress stage | APPLIED | doc 03 §9, §22.8; doc 15 §7, §20; doc 01 FR-CON-002/004 |
| DCR-38 | v4 §7 C; v4.1 C16 | 05, 15 §5–6 | Lazy expiry under the pair lock | APPLIED | doc 05 §25.1; doc 15 §5 |
| DCR-39 | v4 §8 | 04, 06 | Profile-detail revalidation on every GET | APPLIED | doc 04 §24.2; doc 06 §22.5 |
| DCR-40 | v4 §9 | 06, 01 FR-PRO-006 | Visibility and interaction matrix (OD-03 OPEN) | APPLIED | doc 06 §22.4; doc 01 FR-PRO-006 |
| DCR-41 | v4 §10.6 | 05, 06, 15 §15, 04 | Deletion-recovery flow | APPLIED | doc 05 §25.9; doc 06 §18, §22.1; doc 15 §15; doc 04 §15 |
| DCR-42 | v4 §12 → v4.2 → v4.3 §3 → v4.5 §6 | 02, 07 | Global lock-order policy (summary + pointer to doc 12) | APPLIED | doc 02 §14a; doc 07 §4; doc 12 §5 |
| DCR-43 | v4 §11.2 | 15 §3, 03 M04, 01 FR-010 | Identity re-verification (OD-04e OPEN) | APPLIED | doc 15 §3; doc 03 §22.4; doc 01 FR-010 |
| DCR-44 | v4 §16 TR-07 | 03 M15, 06, 02 | Admin authorization single source | APPLIED | doc 03 §16.2, §22.15; doc 06 §16; doc 02 §3.1, §12; ADR-027 |
| DCR-45 | v4 §14.2 | 12 | Detailed companion to `CLAUDE.md` | APPLIED | doc 12 (whole file) |
| DCR-46 | v4.1 C11; v4.3 §2; v4.4 §2 | 03 M07, 05, 15 §6 | Request cancellation triggers and refund obligation | APPLIED | doc 03 §22.7; doc 05 §25.2; doc 15 §6 |
| DCR-47 | v4.1 C12 | 03 §9.1, 15 §7 | COMPLETED → CLOSED; `closed_from_status` | APPLIED | doc 03 §22.8; doc 15 §7 |
| DCR-48 | v4.1 C13 | 03, 05, 15 | Reopen checks and states | APPLIED | doc 03 §22.8; doc 05 §25.10; doc 15 §19 |
| DCR-49 | v4.1 C14 (constraint superseded by DCR-55) | 03 §9.1 | `paused_by_profile` | APPLIED | doc 03 §22.8 |
| DCR-50 | v4.1 C15 → v4.2 → v4.3 §2.4, §3 | 12, ADR-031 | Service lock-order compliance matrix | APPLIED | doc 12 §5.4 |
| DCR-51 | v4.1 C16 | 03 M07, 05, 15 §5 | Interest lifecycle; remove `SUPERSEDED_BY_REQUEST` | APPLIED | doc 03 §22.7; doc 05 §25.1; doc 15 §5 |
| DCR-52 | v4.1 L-1 (amended by DCR-54) | 06 | Refresh lock order | APPLIED | doc 06 §22.1 (amendments) |
| DCR-53 | v4.2 C17/C18; v4.3 §3 | 12, ADR-031, 02 | Global lock order and anchor rules | APPLIED | doc 12 §5.1–§5.3; doc 02 §14a |
| DCR-54 | v4.2 §17.5 | 06 | Auth flows take User `FOR SHARE` first | APPLIED | doc 06 §22.1 (amendments); doc 12 §5.4 |
| DCR-55 | v4.2 C19 | 03 §9.1 | Pause CHECK constraint | APPLIED | doc 03 §22.8 |
| DCR-56 | v4.2 C20 → v4.3 §5 → v4.4 §3 | 03 M11, 05 | Refund operation and lines | APPLIED | doc 03 §22.11; doc 05 §25.3 |
| DCR-57 | v4.2 C20.2 | 05, 03 M12 | T7–T10 notifications | APPLIED | doc 05 §25.4 |
| DCR-58 | v4.2 C21 | 12, 03 §7.2/§11.6 | ProfileView/VisitorHistory lock classification | APPLIED | doc 12 §5.4; doc 03 §22.6 |
| DCR-59 | v4.2 C22 | 05, 06, 15 §7–8 | Effects of entering CLOSED | APPLIED | doc 15 §7; doc 05 §25.10; doc 06 §22.9 |
| DCR-60 | v4.2; v4.3 §1.5; v4.4 §1; v4.5 §2 | 03 M01, M12, M15 | Soft/pseudonymous references in logs | APPLIED | doc 03 §2.2, §16.1, §22.2, §22.15 |
| DCR-61 | v4.2 C17.1 | 03 M14 | One non-terminal deletion request per user | APPLIED | doc 03 §15.5, §22.14 |
| DCR-62 | v4.3 §2 | 05, 03 M11/M12 | Post-commit refund transaction via outbox | APPLIED | doc 05 §25.2–§25.3; doc 03 §22.12 |
| DCR-63 | v4.3 §1.4 F3; v4.5 §6.1 | 12, ADR-031 | Bounded waits (B1) | APPLIED | doc 12 §5.5 |
| DCR-64 | v4.3 §4 → v4.4 §5 | 04, 06 | Profile-detail GET snapshot | APPLIED | doc 06 §22.5; doc 04 §24.2 |
| DCR-65 | v4.3 §5 → v4.4 §3 | 03 M11 | Refund integrity structures | APPLIED | doc 03 §22.11 |
| DCR-66 | v4.3 §6 | 08, 12 | Tracker scope; PostgreSQL concurrency tests | APPLIED | doc 08 §14.2; doc 12 §5.6 |
| DCR-67 | v4.4 §1 → v4.5 §2 | 03 M01/M15, 06, 13 | Log anonymisation model | APPLIED | doc 03 §22.2, §22.15; doc 06 §22.6; doc 13 §4.0 |
| DCR-68 | v4.4 §1.1 → v4.6 §1 | 03 M12, 02 | OutboxEvent is a mutable queue | APPLIED | doc 03 §22.12; doc 02 §14 |
| DCR-69 | v4.4 §2 → v4.5 §1, §3 | 03 M11, 05 | Refund idempotency and atomicity | APPLIED | doc 03 §22.11; doc 05 §25.3 |
| DCR-70 | v4.4 §3 | 03 M11 | Refund composite-FK structure | APPLIED | doc 03 §22.11 |
| DCR-71 | v4.4 §4 → v4.5 §4 | 03 M11/M14, 05, 13 | Late refunds; wallet closure (OD-07g OPEN) | APPLIED | doc 03 §22.11; doc 05 §25.6; doc 13 §4.0 |
| DCR-72 | v4.4 §5 | 04, 06, 12 | GET request deadline | APPLIED | doc 06 §22.5; doc 04 §24.2; doc 12 §7 |
| DCR-73 | v4.5 §1 | 02, 03 M12, 12 | Two-phase outbox processing | APPLIED | doc 12 §6; doc 02 §14; doc 03 §22.12 |
| DCR-74 | v4.5 §2.1 → v4.6 §2 | 06, 09, 13, 16 (DR-2026-11-16-P2) | External compliance registry and restore gate | APPLIED | doc 06 §22.7; doc 09 §19.1, §19.11; doc 13 §4.0; doc 16 §10 |
| DCR-75 | v4.5 §2.2 | 06, 16 (P2) | Key tombstones; KEK lifecycle | APPLIED | doc 06 §22.6; doc 16 §10 |
| DCR-76 | v4.5 §2.3–2.4 | 03 M01/M15, 06 | Per-subject envelopes; linkable-ID rule | APPLIED | doc 03 §22.2; doc 06 §22.6 |
| DCR-77 | v4.5 §3 | 03 M11, 05 | Refund get-or-verify; notification eligibility | APPLIED | doc 05 §25.3; doc 03 §22.11 |
| DCR-78 | v4.5 §4 | 03 M11, 05 | DISPOSED wallet semantics | APPLIED | doc 03 §22.11; doc 05 §25.6 |
| DCR-79 | v4.5 §5 → v4.6 §4 → F1 | 03 M15, 09 | Partitioned logs; hold table; maintenance log | APPLIED | doc 03 §22.15; doc 09 §19.12 |
| DCR-80 | v4.5 §6 | 08, 12 | Concurrency test harness | APPLIED | doc 08 §14.1; doc 12 §8 |
| DCR-81 | v4.5 §6.1 | 12, ADR-031 | Implicit FK-lock inventory | APPLIED | doc 12 §5.5 |
| DCR-82 | v4.5 §6 | 12, ADR-031 | Anchor definition | APPLIED | doc 12 §5.2 |
| DCR-83 | v4.5 §6 | 05, 06 | Closed-history clarifications | APPLIED | doc 05 §25.10; doc 06 §22.9 |
| DCR-84 | v4.6 §1 | 03 M12, 16 (P2) | Outbox identifiers and queue key | APPLIED | doc 03 §22.12; doc 16 §10 |
| DCR-85 | v4.6 §1.4 | 03 M01, M02 | Eager pseudonym and key creation | APPLIED | doc 03 §22.2 |
| DCR-86 | v4.6 §2 | 06, 09, 16 (P2) | Pseudonym-only registry; streams R and M | APPLIED | doc 06 §22.7; doc 09 §19.1; doc 16 §10 |
| DCR-87 | v4.6 §3 → F → F1 | 09, 12 | Maintenance operation protocol | APPLIED | doc 09 §19.2, §19.5; doc 12 §9 |
| DCR-88 | v4.6 §4 | 03 §1, 08 | UUIDv7 functions and partition bounds | APPLIED | doc 03 §22.15; doc 08 §14.1 |
| DCR-89 | v4.6 §5 | 05, 06, 03 M12 | Account-standing predicate; notification categories (OD-02e OPEN) | APPLIED | doc 05 §25.5; doc 06 §22.8; doc 03 §22.12 |
| DCR-90 | v4.6 §6 → F | 09 | Maintenance catalogue and recovery | APPLIED | doc 09 §19.10 |
| DCR-91 | F §A (as corrected by F1 Corr. 1) | 09, 03 M15, 12 | Stream M entry schema and parameters | APPLIED | doc 09 §19.1, §19.8; doc 03 §22.15; doc 12 §9 |
| DCR-92 | F §B | 06, 09, 15 §15 | Stream R intent/completed lifecycle | APPLIED | doc 09 §19.4; doc 15 §15; doc 06 §22.6 |
| DCR-93 | F §C | 06, 09, 05 | `BLOCKED_OPERATOR`; quarantine; startup gate | APPLIED | doc 09 §19.3, §19.7, §19.11; doc 05 §25.5; doc 06 §22.8; doc 03 §22.13 |
| DCR-94 | F Part 2 | 03, 06, 09, 12 | Alignment of superseded wording | APPLIED | doc 03 §22.2; doc 06 §22.3; doc 09 §19; doc 12 §5.3; doc 12 §5.5 (supersession note and F2 amendment added in the G1 correction pass, §8) |
| DCR-95 | F1 Corr. 1 | 09, 03 M15, 12 | Header-as-log-row; canonical hash | APPLIED | doc 03 §22.15; doc 12 §9 |
| DCR-96 | F1 Corr. 2 | 09, 03 M15 | PARTITION_DROP companion | APPLIED | doc 09 §19.8 |
| DCR-97 | F1 Corr. 3 → F2 §1 → F3 §2 | 06, 09, 15 §15, 03 M15, 12 | Stream R parameters; per-key KEK evidence | APPLIED | doc 09 §19.4; doc 03 §22.2; doc 15 §15; doc 12 §9 |
| DCR-98 | F1 Corr. 4 → F2 §2 → F3 §1 | 03 M11/M12, 05, 09 | Financial events; DEAD_UNDECRYPTABLE lifecycle | APPLIED | doc 03 §22.11–§22.12; doc 05 §25.6; doc 09 §19.9 |
| DCR-99 | F1 Corr. 5–8 | 09, 03 M15, 12 | Approvers, companion order, HOLD_RELEASE checks, create/drop restore | APPLIED | doc 09 §19.8; doc 03 §22.15; doc 12 §9 |

## 4. Contradiction register

All contradictions below are **resolved in the baseline**. "Docs aligned" is YES when the resolving DCR has been applied (G1, 2026-11-16). Where the resolution carries an OPEN OD, the documents record the recommendation as OPEN; the contradiction itself no longer exists in the documents.

| C | Contradiction | Resolved by | Docs aligned |
|---|---|---|---|
| C-1 | SRS has two drafts and two ID schemes | DCR-01 | YES |
| C-2 | SQLAdmin listed in a Django stack | DCR-03 | YES |
| C-3 | Interest has no database model | DCR-04 | YES |
| C-4 | Doc 14 templates include Sensitive permissions while §4 forbids automatic grants | DCR-32 (OD-05a OPEN) | YES |
| C-5 | Doc 15 missing transitions | DCR-07 | YES |
| C-6 | Roadmap order | DCR-08 | YES |
| C-7 | `CLAUDE.md` truncated sentence, wrong paths; doc 12 drift | DCR-09, DCR-45 | YES |
| C-8 | FR-SUB-008 describes failed renewal while auto-renewal is excluded | DCR-30 (OD-09 OPEN) | YES |
| C-9 | Doc 03 §7.2 billing wording | DCR-14 | YES |
| C-10 | Unique document permissions conflict with re-issue | DCR-15 | YES |
| C-11 | Toggle for security notifications that can't be disabled | DCR-23 | YES |
| C-12 | Status vocabularies collide | DCR-12 | YES |
| C-13 | Doc 03 `AccountSecurityEvent` vs AuthSession-only history | DCR-25, DCR-35 | YES |
| C-14 | Doc 03 AdminRole models vs Django Groups | DCR-44 | YES |
| C-15 | CLOSED duplicated in progress and connection | DCR-37 (OD-06i OPEN) | YES |
| C-16 | Limited login during recovery vs activity disabled | DCR-41 | YES |
| C-17 | Refund differences could reveal a block | DCR-46 (OD-07 OPEN) | YES |
| C-18 | CANCELLED admin-only vs system cancellations | DCR-46 (OD-07a OPEN) | YES |
| C-19 | Refresh lock order inverted vs deletion | DCR-52, DCR-54 | YES |
| C-20 | Payment rows ordered after the wallet | DCR-53 | YES |
| C-21 | `SUPERSEDED_BY_REQUEST` unreachable | DCR-51 | YES |
| C-22 | Interest daily cap race | DCR-53 | YES |
| C-23 | Accept vs suspension race | DCR-53 | YES |
| C-24 | No account lock anchor when no deletion request exists | DCR-53 | YES |
| C-25 | Messaging/documents/view POST lacked account and profile locks | DCR-50, DCR-53 | YES |
| C-26 | Implicit FK locks from log inserts could deadlock | DCR-54, DCR-60 | YES |
| C-27 | `refund_outcome` duplicated on the request | DCR-56 | YES |
| C-28 | Login racing deactivation could escape revocation | DCR-54 | YES |
| C-29 | Pause CHECK allowed partial state | DCR-55 | YES |
| C-30 | Profile `FOR UPDATE` vs implicit FK locks | DCR-53 | YES |
| C-31 | Block took sender wallet without sender User lock | DCR-62 | YES |
| C-32 | Deletion → PROCESSING held two anchors | DCR-53 | YES |
| C-33 | Stored refund `outcome` duplicated derived data | DCR-65 | YES |
| C-34 | Protective-action FK case not covered | DCR-63 | YES |
| C-35 | OutboxEvent called append-only | DCR-68 | YES |
| C-36 | Refund FK didn't match a unique key | DCR-70 | YES |
| C-37 | `statement_timeout` used as a transaction bound | DCR-72 | YES |
| C-38 | "Published policy" for credits at deletion doesn't exist | DCR-71 (OD-07g OPEN) | YES |
| C-39 | Refund operation kind enforced only by trigger | DCR-70 | YES |
| C-40 | Refund worker locked the outbox row first | DCR-73 | YES |
| C-41 | Shred registry only in the primary database | DCR-74 | YES |
| C-42 | Key destruction implied irreversible despite backups | DCR-75 | YES |
| C-43 | No design for multi-subject events | DCR-76 | YES |
| C-44 | Linkable IDs plaintext in logs | DCR-76 | YES (doc 12 §5.5 aligned in the G1 correction pass: the superseded v4.3 F2 wording is marked; the current rule is in doc 03 §22.2) |
| C-45 | `ON CONFLICT` treated as proof of completion | DCR-77 | YES |
| C-46 | Notification timing contradiction for refunds | DCR-77 | YES |
| C-47 | DISPOSED-wallet rules and T-DEL-010 ambiguous | DCR-78 | YES |
| C-48 | Partition-key uniqueness unspecified | DCR-79 | YES |
| C-49 | Concurrency tests not specified precisely | DCR-80 | YES |
| C-50 | Allowance expiry job lacked User share | DCR-81 | YES |
| C-51 | Staff-actor implicit locks not inventoried | DCR-81 | YES |
| C-52 | Hold-table release path not disclosed | DCR-79 | YES |
| C-53 | Plaintext IDs in outbox vs pseudonymous classification | DCR-84 | YES (doc 12 §5.5 aligned in the G1 correction pass; the current rule is in doc 03 §22.12) |
| C-54 | Registry held plaintext account and request IDs | DCR-86 | YES |
| C-55 | One registry chain with mixed retention | DCR-86 | YES |
| C-56 | Wrong PG18 function name; `uuid_v7_lower` undefined | DCR-88 | YES |
| C-57 | Lazy pseudonym creation could deadlock | DCR-85 | YES |
| C-58 | Notification eligibility not tied to account standing | DCR-89 | YES |
| C-59 | Outbox payload immutability vs redaction | DCR-84 | YES |
| C-60 | v4.4 §1.2 plaintext linkable IDs vs v4.5 §2.4 | DCR-94 | YES (doc 12 §5.5 aligned in the G1 correction pass) |
| C-61 | Stream M outcome written before verification | DCR-91 | YES |
| C-62 | `DELETION_COMPLETED` written before completion | DCR-92 | YES |
| C-63 | ABORTED path existed for Stream R | DCR-93 | YES |
| C-64 | `target_digest` alone insufficient for recovery | DCR-91 | YES |
| C-65 | T-REG-004 implied ABORTED for both streams | DCR-93 | YES |
| C-66 | Circular log-row hash | DCR-95 | YES |
| C-67 | Companion held IDs only | DCR-96 | YES |
| C-68 | Stream R parameters unspecified | DCR-97 | YES |
| C-69 | Financial events depended on a destroyable key | DCR-98 | YES |
| C-70 | Single approver field | DCR-99 | YES |
| C-71 | Companion keyed by unknown `seq` | DCR-99 | YES |
| C-72 | HOLD_RELEASE didn't check retention | DCR-99 | YES |
| C-73 | Create/drop restore ambiguity | DCR-99 | YES |
| C-74 | `dedupe_key` redacted while unresolved | DCR-98 | YES |
| C-75 | KEK version not associated per key | DCR-97 | YES |
| C-76 | `CACHE_INSERT` unspecified | DCR-97 | YES |
| C-77 | Discrepancy resolution stage timing unclear | DCR-98 | YES |
| C-78 | General KEK rotation accepted as evidence | DCR-97 | YES |

## 5. Document status history

| Document | Status before G1 | Status during G1 (Claude, with DCR references) |
|---|---|---|
| `CLAUDE.md`, docs 00–17 | No status header | PROPOSED (G1 revision) |
| Docs 18, 19, 20 | Not present | PROPOSED (created in G1) |

**Final document statuses — G1 owner acceptance.** Assigned by the project owner on 2026-11-17 (decision DR-2026-11-17-A, `docs/decisions/new_architecture_decisions.md`), scope G1 only, under the baseline v4 §6.1 document-status model. Each `APPROVED_WITH_OPEN_ITEMS` header lists that document's OPEN ODs and PROPOSED TRs. A document status approves none of the items inside the document: those keep their status in doc 19, and DCR-20 stays BLOCKED.

| Document | Final status | Reason |
|---|---|---|
| `CLAUDE.md` | APPROVED_WITH_OPEN_ITEMS | Authoritative entry point (DR-2026-11-16-3); CC-R20 refers to the PROPOSED lock-order policy (TR-09, TR-22) |
| 00 Master index | APPROVED | Authoritative index, catalogue and approved status model; no open OD or TR |
| 01 SRS | APPROVED_WITH_OPEN_ITEMS | Approved requirements with OPEN-OD dependencies, DCR-20 BLOCKED notes and TR references |
| 02 System architecture | APPROVED_WITH_OPEN_ITEMS | Approved architecture plus PROPOSED TR refinements (outbox, admin auth, lock order) |
| 03 Database design | APPROVED_WITH_OPEN_ITEMS | §22 structures are PROPOSED TRs; REC-BIZ rows under OPEN ODs |
| 04 API and integrations | APPROVED_WITH_OPEN_ITEMS | §24 mechanics are PROPOSED TRs; OD-02/03/06/08 dependencies |
| 05 Business rules | APPROVED_WITH_OPEN_ITEMS | §25 workflows are TR mechanics with REC-BIZ under OPEN ODs (including OD-07b) |
| 06 Security and privacy | APPROVED_WITH_OPEN_ITEMS | §22 mechanisms are PROPOSED TRs; OD-03 visibility matrix OPEN |
| 07 Repository standards | APPROVED_WITH_OPEN_ITEMS | Standards with the PROPOSED lock-policy summary (TR-09, TR-22) |
| 08 Testing and QA | APPROVED_WITH_OPEN_ITEMS | Approved test strategy; the PostgreSQL harness and tracker scope are PROPOSED (TR-13, TR-22) |
| 09 AWS deployment | APPROVED_WITH_OPEN_ITEMS | §19 registry and maintenance protocol are PROPOSED TRs; legal items under OD-005 |
| 10 Roadmap | APPROVED_WITH_OPEN_ITEMS | Approved gated sequence; phases depend on OPEN ODs and TR approvals |
| 11 ADRs | APPROVED_WITH_OPEN_ITEMS | Mix of approved ADRs and ADRs awaiting decision (ADR-022, ADR-023, ADR-025…032) |
| 12 Claude Code instructions | APPROVED_WITH_OPEN_ITEMS | Detailed companion (DR-2026-11-16-3); procedures for PROPOSED TRs, which are labelled |
| 13 Assumptions and risks | APPROVED_WITH_OPEN_ITEMS | Holds the no-implementation-from-an-open-OD rule and the OPEN legacy decisions OD-001…OD-007 |
| 14 Manager permission matrix | APPROVED_WITH_OPEN_ITEMS | §1–§8 approved; §9 tiers are REC-BIZ under OD-05 and TR-16 |
| 15 State machines | APPROVED_WITH_OPEN_ITEMS | Transitions include REC-BIZ items under OPEN ODs |
| 16 Environment configuration | APPROVED_WITH_OPEN_ITEMS | §10 configuration is PROPOSED (TR-11, TR-23, TR-24); retention under OD-005 |
| 17 Glossary | APPROVED_WITH_OPEN_ITEMS | Normative terminology (including the approved TR-05 vocabulary); the access-level definitions are OD-03 |
| 18 Traceability matrix | APPROVED_WITH_OPEN_ITEMS | Authoritative requirement-status register; OD dependencies and 2 BLOCKED requirements |
| 19 Open decision register | APPROVED_WITH_OPEN_ITEMS | Authoritative OD/TR register; lists every OPEN OD and PROPOSED TR |
| 20 Correction register | REFERENCE | Historical record of corrections, contradictions and approvals; informative, not a requirements or instruction source |

No document is SUPERSEDED.

**Status changes after G1 acceptance**

| Document | From | To | Decision | Reason |
|---|---|---|---|---|
| `CLAUDE.md` | APPROVED_WITH_OPEN_ITEMS | APPROVED | DR-2026-11-17-G3C-4 | Its open items (TR-09, TR-22) were approved; the open-item list was verified empty |
| 07 Repository standards | APPROVED_WITH_OPEN_ITEMS | APPROVED | DR-2026-11-17-G3C-4 | Its open items (TR-09, TR-22) were approved; verified empty |
| 08 Testing and QA | APPROVED_WITH_OPEN_ITEMS | APPROVED | DR-2026-11-17-G3C-4 | Its open items (TR-13, TR-22) were approved; verified empty |

## 6. G1 alignment notes (interpretations and deviations for owner review)

1. **DCR-01 and requirement IDs (resolved, DR-2026-11-17-C1).** The legacy-to-canonical mapping and the new IDs for previously unnumbered sections are applied. The baseline A2 B.1 proposal to rename FR-REQ-001…003 → FR-INT-001…003 and FR-MAT-006 → FR-FAV-001 is **not adopted**: the project owner decided to preserve all existing requirement IDs. DCR-01 is therefore recorded as APPLIED; the renaming isn't outstanding work. (The G1 register has no status for "applied with an owner-withdrawn sub-proposal", so this note carries that fact instead of a new status.)
2. **Deletion endpoints (resolved, DR-2026-11-17-C4):** doc 04 §15 (`/account-deletion/…`) is the canonical catalogue. The baseline v4 §10.6 wording `/account/deletion/…`, kept in the doc 05 §25.9 extract for traceability, doesn't override it (notes at doc 04 §15 and doc 05 §25.9).
3. **Doc 16 scope (DR-2026-11-16-P2):** only configuration required by DCR-74/75/84/86 was added (registry, KEK, queue key, dedupe key, outbox timing). K_rot and `__Host-` cookie settings belong to DCR-16 and are specified in doc 06 §22.2, not doc 16. (The G1 readiness report had listed them for doc 16; that was corrected to stay within P2.)
4. **ADR-014 and the transactional outbox (resolved, DR-2026-11-17-C2):** the core transactional outbox is an approved requirement (SRS FR-NOT-005, Notifications module M12; `CLAUDE.md` CC-R30; doc 02 §14), and the `CLAUDE.md` rule always reflected it. ADR-014 is now APPROVED for that core decision only. The refinements (two-phase processing, queue key, pseudonymous recipients, event classes, redaction and the rest) remain PROPOSED under TR-11 / ADR-028. The distinction is stated in doc 01 FR-NOT-005, doc 02 §14, doc 03 §22.12, doc 11 ADR-014, doc 12 §6, doc 18 and doc 19 TR-11. Decisions on ADR-022 and ADR-023 remain pending (due before G4).
5. **HTTP status codes:** where the baseline names an error code without an HTTP status, doc 04 §24.4 shows "—" instead of inventing one.
6. **Admin role column name:** the existing `AdminUserRole.assigned_by` / `assigned_at` columns are kept; the baseline TR-07 text says `granted_by`.
7. **Verbatim blocks:** to preserve fidelity, several reconciled sections embed baseline text verbatim, each labelled with its source. Where a later package superseded part of a block, the amendment is stated next to it. Since the G1 correction pass every extract ends with "*— End of verbatim extract —*". Four extracts are labelled "*Adapted from …*" because conversational phrases or clashing headings were edited; each label states the exact edit (doc 06 §22.4, doc 12 §5.1 and §5.5, doc 14 §9).

## 7. `CLAUDE.md` ↔ doc 12 consistency cross-check (G1 exit item 8)

| Doc 12 section | `CLAUDE.md` rules referenced | Result |
|---|---|---|
| §1 How to use this document | CC-R06, CC-R25, CC-R26 | Consistent; doc 12 defers to `CLAUDE.md` |
| §2 Working within the gates | CC-R24, CC-R25, CC-R27 | Consistent with doc 10 §0 |
| §3 Status reporting with evidence | CC-R59, CC-R69, CC-R70 | Consistent with doc 00 §9 |
| §4 Coding patterns | CC-R16, CC-R39, CC-R45, CC-R52 | Consistent |
| §5 Transactions and locking | CC-R20, CC-R26 | Consistent; §5 is marked PROPOSED (TR-09, TR-22), matching CC-R20 as qualified in the G1 correction pass |
| §8 Testing procedures | CC-R59 | Consistent |
| §11 Review checklist | CC-R57 | Consistent |
| §10 Documentation update procedure | CC-R63, CC-R64 | Consistent |
| Header | CC-R01…CC-R79 range | Matches the 79 rules in `CLAUDE.md` |

No doc 12 statement restates a `CLAUDE.md` rule in different words or contradicts one.

## 8. G1 correction pass (2026-11-17, DR-2026-11-17-C)

Corrections made after the G1 Final Reconciliation Audit. No baseline or snapshot file, requirement ID, OD status, TR status or approved business rule was changed. No new DCR number was created: each correction completes or aligns the DCR shown.

| Finding | Correction | Location | DCR |
|---|---|---|---|
| B1 Superseded plain-UUID log wording | Supersession note before the extract, F2 amendment with the current rule after it, checklist item | doc 12 §5.5, §11; this doc DCR-94, C-44, C-53, C-60 | DCR-94 |
| B2 `ACCEPTED` delegable | `ACCEPTED` assigned by the project owner personally (C3) | doc 00 §9.1; doc 19 §2; ADR-029 | DCR-12 |
| M1 Outbox framed as pending | Approved core vs PROPOSED refinements (C2); ADR-014 APPROVED (core only) | doc 01 §15; doc 02 §14; doc 03 §22.12; doc 11 ADR-014, §25; doc 12 §6; doc 18; doc 19 TR-11; ADR-028; §6 note 4 | DCR-22, DCR-28 |
| M2 Two deletion path forms | doc 04 §15 canonical (C4); notes added | doc 04 §15; doc 05 §25.9; §6 note 2 | DCR-41 |
| M3 T2 refund labelled outside OD-07 | T2 refund shown as OD-07b OPEN (C5) | doc 05 §25.2; doc 03 §22.7; doc 12 §5.4 | DCR-46 |
| M4 Stale decisions register | Purpose, current status, baseline location and historical labels updated; DR-2026-11-17-C added | `docs/decisions/new_architecture_decisions.md` | DCR-34 |
| M5 Superseded A4 OD-03 row | Row removed; OD-03a definitions kept as a list; historical note with source | doc 06 §22.4 | DCR-29, DCR-40 |
| J1 ADR-029 APPROVED | ADR document PROPOSED; TR-14 stays APPROVED (C6) | ADR-029; doc 11 §25 | DCR-28 |
| J5 CC-R20 | Lock-order policy qualified as PROPOSED (C7) | `CLAUDE.md` CC-R20; doc 12 §5, §11 | DCR-09, DCR-42 |
| J6 OD-06g cooldown scope | OD-06g labelled OPEN | doc 15 §5 | DCR-04 |
| J7 402 for zero view credits | Status and body labelled as the OD-08b recommendation | doc 04 §24.4 | DCR-17 |
| Minor 1 Conversational phrases | Removed; extracts relabelled "Adapted from" with the edit stated | doc 06 §22.4; doc 12 §5.1, §5.5; doc 14 §9 | DCR-94 |
| Minor 2 `Retry-After` | Added for `503 request_deadline_exceeded` | doc 04 §24.2, §24.4; doc 12 §7 | DCR-72 |
| Minor 3 ADR deadlines | ADR decisions due before G4 (baseline v4.6 approval-by-gate table) | doc 11 ADR-022, ADR-023, §25; ADR-025…032 | DCR-28 |
| Minor 4 BLOCKED rule | Whole-requirement BLOCKED only (C8) | `CLAUDE.md` CC-R25; doc 10 §0.4; doc 12 §2; doc 13 §4.0; doc 18 §1 | DCR-33 |
| Minor 5 Progress counts | Counts aligned with doc 18 | `docs/implementation/progress.md` | DCR-33 |
| Minor 6 DCR-01 status | FR-PREF labels completed; status APPLIED with note | doc 01 §0.1, §6; §3 DCR-01; §6 note 1 | DCR-01 |
| Minor 7 Duplicate §7 in doc 14 | Inserted headings renumbered 9.1–9.1.3 with A4 numbers in brackets | doc 14 §9 | DCR-06, DCR-32 |
| Minor 8 DCR citations | DCR-02 (doc 00), DCR-42 (doc 12 header), DCR-62/89/93 (doc 03), CC-R57 reference (§7) | doc 00; doc 12; doc 03 §22, §22.12, §22.13; this doc §7 | — |
| Minor 9 Doc 15 labels | Recovery cancellation DECIDED (mechanism REC-BIZ); OD-03j label; shared-notes effect restored with its baseline label [REC-BIZ, OD-06l] | doc 15 §7, §15 | DCR-07, DCR-41, DCR-59 |
| Minor 10 Obsolete doc 11 purpose label in doc 00 | Replaced; ADR status vocabulary mapped | doc 00 §4; doc 11 introduction | DCR-10 |
| Minor 11 Old `Status:` lines | Relabelled as pre-G1 origin labels, not statuses | doc 01 header and detailed-draft header; doc 02 header | DCR-10 |
| Minor 12 Verbatim delimiting | End markers after every extract; header notes | docs 03, 04, 05, 06, 09, 12, 14 | DCR-94 |
