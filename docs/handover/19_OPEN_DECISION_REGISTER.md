# Matermonial — Open Decision Register

**Document status:** APPROVED_WITH_OPEN_ITEMS (project owner, 2026-11-17, DR-2026-11-17-A; record in doc 20 §5). **Open items:** OPEN ODs: OD-02, OD-03, OD-04, OD-05, OD-06, OD-07, OD-08, OD-09, OD-10; OPEN legacy ODs (doc 13 series): OD-001, OD-002, OD-003, OD-004, OD-005, OD-006, OD-007; PROPOSED TRs: TR-01, TR-02, TR-03, TR-04, TR-06, TR-07, TR-08, TR-10, TR-11, TR-15, TR-16, TR-17, TR-18, TR-19, TR-20, TR-21, TR-23, TR-24. Listed items keep their own status (doc 19); this document status doesn't approve them. TR-09, TR-12, TR-22 approved 2026-11-17 (DR-2026-11-17-G3). TR-13 approved 2026-11-17 (DR-2026-11-17-G2D-2).
**Created:** 2026-11-16, G1 step 2 (DCR-34)
**Source:** approved baseline `docs/baseline/v4.6-F3/` and decision records in `docs/decisions/new_architecture_decisions.md`

## 1. Purpose and rules

This register holds every business decision (OD) and technical recommendation (TR) with its status and decision record.

- **[DECIDED]** = an already approved requirement. **[TR]** = technical recommendation. **[REC-BIZ]** = business recommendation that needs owner approval. **[OD]** = owner decision.
- Status values follow the requirement-approval dimension (doc 00 §9): `PROPOSED`, `RECOMMENDED`, `APPROVED`, `REJECTED`, `DEFERRED`, `POST_MVP`, `SUPERSEDED`. An OD is `OPEN` until decided, then `RESOLVED`.
- **No implementation may rely on an unanswered OD sub-item.** Requirements that depend on one are recorded as BLOCKED (doc 10, doc 13).
- Recommended defaults below are **not approved**. They become requirements only through a recorded decision.

## 2. Approvers

| Role | Holder |
|---|---|
| Business decisions (OD, REC-BIZ) | Project owner, or the project architecture reviewer acting under the owner's delegation (as for DR-2026-11-16) |
| Technical approver (TR) | Project owner, or the delegated project architecture reviewer |
| Code reviewer (sets `REVIEWED`) | Not yet named. Until named, the project owner. |
| `ACCEPTED` implementation status | Project owner personally; not delegable (DR-2026-11-16-2, DR-2026-11-17-C3). A delegated reviewer may review and recommend acceptance but can't assign `ACCEPTED`. |

## 3. Owner decisions (OD-01…OD-10)

The ten bundles below follow the ten-question limit. Each sub-item can be approved separately. The source column points to the final wording in the baseline (package codes as in doc 20 §1).

| OD | Topic | Status | Needed by |
|---|---|---|---|
| OD-01 | Functional-domain catalogue | **RESOLVED** (DR-2026-11-16-5; catalogue in `docs/decisions/new_architecture_decisions.md` and doc 01) | — |
| OD-02 | Participation and account lifecycle | OPEN | Phases 2–3, 6, 12, 15 |
| OD-03 | Visibility | OPEN | Phases 3, 6 |
| OD-04 | Identity rules | OPEN | Phases 3–5, 15 |
| OD-05 | Manager arrangement | **PARTLY RESOLVED** (DR-2026-11-20-O, 2026-11-20): OD-05c and OD-05e decided (below); OD-05a, b, d, f stay OPEN. Report: `docs/implementation/od05_tr16_decision_report.md` | Phase 4 |
| OD-06 | Interest, request and connection interaction | OPEN | Phases 9–10 |
| OD-07 | Request cancellation, refunds, credit disposition | OPEN | Phases 9, 12, 15 |
| OD-08 | View exemptions and zero credit | OPEN | Phase 8 |
| OD-09 | Subscription scenarios | OPEN | Phase 13 |
| OD-10 | Matching hard rules | OPEN | Phase 8 |

None of OD-02…OD-10 blocks migration 0001.

### 3.1 Sub-items (all OPEN; recommended default shown as [REC-BIZ])

| Sub-item | Recommended default [REC-BIZ] | Source |
|---|---|---|
| OD-02a | Phone-verified accounts may create a profile and see L1 cards. Interests, requests, L2 views and messaging need identity APPROVED, profile ACTIVE and no restriction. | v4 §15 |
| OD-02b | Logged-out visitors see no profiles | v4 §15 |
| OD-02c | Self-deactivation reversible by login + OTP; admin deactivation needs an admin | v4 §15 |
| OD-02d | Deletion-recovery flow: recovery-scoped session, no export during recovery, neutral notice to managers, access restored on cancellation | v4 §10.6, §15 |
| OD-02e | Notification categories by account standing (`can_notify` matrix) | v4.6 §5.2 |
| OD-03a | L0–L3 access-level definitions | v4 §15; A4 §13 |
| OD-03b | `VISIBLE_AFTER_ACCEPTANCE` per the visibility matrix | v4 §9 |
| OD-03c | HIDDEN semantics | v4 §9.3 |
| OD-03d | Block suspends existing connection access without closing the connection | v4 §9.1 |
| OD-03e | PENDING_REVIEW = content/photo moderation before first activation | v4 §15; A4 §13 |
| OD-03f | Discovery display name = first name + last initial | v4 §15; A4 §13 |
| OD-03g | Private visits shown to the owner as an anonymous "Private visitor" entry (alternative: not shown) | v4 §7 A |
| OD-03h | Answers to the HIDDEN / reciprocal / request / L3 questions | v4 §9.3 |
| OD-03i | Lifecycle overlay | v4 §9.2 |
| OD-03j | CLOSED connection: back to the unrelated-viewer row; VAA → L1 history card | v4 §9.1; v4.2 C22 |
| OD-04a | Locked fields: legal name, DOB, gender (nationality if the document proves it) | v4 §15 |
| OD-04b | Underage DOB: generic rejection, security event, DOB not kept | v4 §15 |
| OD-04c | Identity confirmation = password + OTP | v4 §15 |
| OD-04d | Phone freed after deletion; keyed hash only under a ban or hold | v4 §15 |
| OD-04e | Identity re-verification after approval | v4 §11.2 |
| OD-05a | Templates may pre-select Sensitive communication permissions, granted only after owner confirmation with step-up | A4 §7; v4 §15 |
| OD-05b | Counterparty sees "Sent by an authorized family member"; the owner sees the identity | A4 §7 |
| OD-05c | `manage_family_authorizations` and `manage_verification_submission` become Owner-only. **DECIDED (DR-2026-11-20-O-4): yes; only the owner submits identity verification, personally; no permission overrides it** | A4 §7 |
| OD-05d | Owner approval per document share | A4 §7 |
| OD-05e | Invitation TTL ~~14 days~~ **DECIDED (DR-2026-11-20-O-2): 30 days for invitations and requests (supersedes the 14-day proposal)** | A4 §13 |
| OD-05f | Managers may resign | A4 §13 |
| OD-06a–g | Interest rules (auto-reciprocation, conversion by sender, either party may request after reciprocation, no cooldown on withdrawal, pending expiry, freeze/close behaviour, cooldown blocks both interests and requests; free interests with a daily cap set by the owner) | A4 §13; v4.1 C16 |
| OD-06h | Only the pausing party resumes; pause edge cases | v4 §11.6; v4.1 C14 |
| OD-06i | COMPLETED needs mutual confirmation and is independent of ENGAGED; "Closed" progress label derived from the connection lifecycle (FR-CON-004 storage change) | v4 §15 |
| OD-06j | No new request after CLOSED; reopening only | A4 §13 |
| OD-06k | Progress: any stage to any stage, either party, only while ACTIVE | v4 §11.7 |
| OD-06l | COMPLETED → CLOSED allowed, not reopenable; effects on documents and notes | v4.1 C12; v4.2 C22 |
| OD-06m | Either party may withdraw a RECIPROCATED interest | v4.1 C16 |
| OD-06n | Reopen rules: non-reopenable closure reasons, hidden party can't initiate, 14-day TTL | v4.1 C13 |
| OD-07a | CANCELLED used for system triggers T3–T10 | v4.1 C11 |
| OD-07b | Refund table by trigger | v4.1 C11 |
| OD-07c | Recipient block refunds the sender, with a uniform reason code | v4.1 C11 |
| OD-07d | Expired-allowance refund portions lapse | v4.1 C11 |
| OD-07e | No cancellation on pause, deactivation or deletion recovery | v4.1 C11 |
| OD-07f | Notification behaviour for T3–T10; suppression for ineligible senders | v4.2 C20.2; v4.5 §3.3; v4.6 §5 |
| OD-07g | Credit balance at deletion, including late refunds: **retain, no forfeiture** until an approved policy exists | v4.4 §4; v4.5 §4 |
| OD-08a | Free re-views: own profile, connections, senders of a pending interest or request (billing only) | v4 §15 |
| OD-08b | Zero credits: L1 card + `402` | v4 §15 |
| OD-08c | No refund of a view credit when access is later lost | v4 §8 |
| OD-09a | Manual renewal for the MVP; FR-SUB-008 implementation DEFERRED until auto-renewal is approved | v4 §15 |
| OD-09b | Remove the 3-day post-expiry window | v4 §15 |
| OD-09c | Early renewal queued from `ends_at` | v4 §15 |
| OD-09d | No mid-term plan changes | v4 §15 |
| OD-10a | Gender compatibility is a hard rule | A4 §13 |
| OD-10b | Strict-capable criteria: age range, marital status, religion, country of residence | A4 §13 |

### 3.2 Legacy open decisions (doc 13 §4)

Doc 13 §4 lists **OD-001…OD-007** (commercial structure, credit packages, JazzCash production configuration, identity verification policy, legal and privacy policy, production infrastructure, operational administration). They are a **separate series** from OD-01…OD-10 above and keep their status in doc 13. The legal review items in §5 are tracked there under OD-005.

## 4. Technical recommendations (TR-01…TR-24)

| TR | Topic | Status | Approval due | Main source |
|---|---|---|---|---|
| TR-01 | Authentication lifecycle (sessions, tokens, rotation, K_rot, cookies, lifetimes, lock order) | **APPROVED** (DR-2026-11-18-G4, 2026-11-18) | G4 | v4 §10; v4.2; v4.3 §1 |
| TR-02 | Acting-profile authorization algorithm | **APPROVED** (DR-2026-11-20-C-5, 2026-11-20, after review of the G5 Phase 4 implementation against doc 04 §24.1) for steps 1–9, 11 and 13–17. Step 10 followed with TR-16's approval (DR-2026-11-20-O-3) and is implemented: per-action step-up with the manager's authenticator (ADR-036). The fail-closed interim (`sensitive_use_unavailable`, 2026-11-20) is superseded. *History:* PROPOSED; direction of ADR-026 adopted (DR-2026-11-18-G4); implemented in G5 Phase 4 (2026-11-19) | Phase 4 | A4 §9 |
| TR-03 | Central eligibility service, including `get_account_standing` | PROPOSED | Phase 6 | v4.6 §5; F §C |
| TR-04 | Calendar arithmetic in UTC | PROPOSED | Phase 9 | v4 §13 |
| TR-05 | Subscription vocabulary | **APPROVED** (DR-2026-11-16-4) | — | v4 §16 |
| TR-06 | Locked-field correction requests | PROPOSED | Phase 5 | A4 §3 |
| TR-07 | Admin authorization from a single source | **APPROVED** (DR-2026-11-18-G4, 2026-11-18) | G4 | v4 §16 |
| TR-08 | View billing mechanics | PROPOSED | Phase 8 | A4 §10; v4 §8 |
| TR-09 | Constraints, global lock order, anchors | **APPROVED** (DR-2026-11-17-G3-2, 2026-11-17) | — | v4.2; v4.3 §3; v4.5 §6 |
| TR-10 | Upload pipeline | **APPROVED** (DR-2026-11-19-P3-1, 2026-11-19; with Pillow and filetype; scanner disabled when deployed until a real one is approved) | Phase 3 | A4 §3 |
| TR-11 | Audit and outbox refinements (two-phase processing, queue key, redaction, event classes). The core transactional outbox itself is an approved requirement (FR-NOT-005; ADR-014 core, DR-2026-11-17-C2) and is not part of this TR. | **APPROVED** (DR-2026-11-18-G4, 2026-11-18) | G4 | v4.5 §1; v4.6 §1; F1 Corr. 4 |
| TR-12 | Same-origin deployment | **APPROVED** (DR-2026-11-17-G3-1, 2026-11-17; architectural direction only, no deployment) | — | A4 §3 |
| TR-13 | PostgreSQL tests and concurrency harness (CI on PostgreSQL 16 and 18) | **APPROVED** (DR-2026-11-17-G2D-2, 2026-11-17) | — | v4.5 §6; v4.6 §4 |
| TR-14 | Status model | **APPROVED** (DR-2026-11-16-2) | — | v4 §6 |
| TR-15 | Ledger projections, refund integrity, wallet closure, financial events | PROPOSED | Phase 7 / 9 | v4.4; v4.5; F1; F2; F3 |
| TR-16 | Step-up windows | **APPROVED** (DR-2026-11-20-O-3, 2026-11-20): fresh step-up with the manager's own authenticator before **each** Sensitive action, bound to manager, profile and action, valid at most 5 minutes, single use (ADR-036). Supersedes the proposal (12 h communication / 10 min other). *History:* PROPOSED; fail-closed interim (DR-2026-11-20-C-5) | Phase 4 | A4 §3 |
| TR-17 | Security-event model | **APPROVED** (DR-2026-11-18-G4, 2026-11-18) | G4 | v4 §10.5 |
| TR-18 | Lazy expiry | PROPOSED | Phase 9 | v4 §7 C |
| TR-19 | Profile-detail revalidation, GET snapshot and deadline | PROPOSED | Phase 8 | v4 §8; v4.4 §5 |
| TR-20 | Connection / progress separation | PROPOSED | Phase 10 | v4 §7 B |
| TR-21 | Recovery-scoped session | **APPROVED — schema portion only** (DR-2026-11-18-G4; the recovery flow stays with OD-02d, OPEN) | G4 (schema); flow Phase 2 | v4 §10.6 |
| TR-22 | LOCK_PLAN tracker and implicit-FK inventory | **APPROVED** (DR-2026-11-17-G3-2, 2026-11-17) | — | v4.3 §6; v4.5 §6.1 |
| TR-23 | Log pseudonymisation, envelopes, UUIDv7 partitioning | **APPROVED** (DR-2026-11-18-G4, 2026-11-18) | G4 | v4.5 §2, §5; v4.6 §4 |
| TR-24 | Compliance registry and maintenance protocol | **APPROVED — schema portion with a local/mock registry** (DR-2026-11-18-G4); external storage resource still needs approval before production | G4 (schema); before production (storage resource) | v4.6 §2–3; F; F1; F2; F3 |

## 5. Legal and operational decisions pending before production

Tracked under doc 13 OD-005 / OD-006 / OD-007 unless noted:
- retention periods (security events, sessions, ProfileView and financial records, messages, VisitorHistory, maintenance log, outbox, backups and WAL)
- KEK and queue-key destruction schedule
- acceptability of pseudonymous event grouping after unlinking (risk R-19)
- whether financial records must stay identifiable under FR-DAT-009
- a published credit-and-refund policy (needed for OD-07g)
- the TR-24 external write-once storage resource (new AWS cost; `CLAUDE.md` approval rule)
- external providers EP-01…09
- backup policy, RPO and RTO
- reviewed Urdu legal and security texts
- the doc 06 security release gate
- measured performance targets
- enough qualified staff for the two-independent-approver rule (DCR-99)
