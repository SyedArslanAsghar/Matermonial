# Matermonial — Requirements Traceability Matrix

**Document status:** APPROVED_WITH_OPEN_ITEMS (project owner, 2026-11-17, DR-2026-11-17-A; record in doc 20 §5). **Open items:** OPEN ODs: OD-02, OD-03, OD-04, OD-05, OD-06, OD-07, OD-08, OD-09, OD-10; PROPOSED TRs: TR-11; 2 requirements BLOCKED (FR-ACC-009, FR-PRO-005). Listed items keep their own status (doc 19); this document status doesn't approve them.
**Created:** 2026-11-16, G1 (DCR-11, DCR-34)

## 1. Purpose and rules

One row per requirement, from the SRS (doc 01) to its domain, module, status and tests.

- **Requirement IDs** are the canonical IDs in doc 01 §0.1. Legacy IDs FR-001…FR-021 are shown in their own column.
- **Domain** uses the approved catalogue (D01–D22, OD-01 RESOLVED, doc 01 §0.2). **Module** uses the doc 03 modules M01–M16.
- **Requirement approval status** and **implementation status** follow the separate dimensions in doc 00 §9. SRS requirements are the approved handover baseline (`APPROVED`). Technical recommendations and business recommendations are tracked in doc 19 and are not listed here as requirements.
- **OD dependency:** where a requirement depends on an OPEN owner decision, only the dependent behaviour is blocked (`CLAUDE.md` CC-R25, doc 10 §0.4). `BLOCKED` in the implementation column means the whole requirement depends on one; a partially dependent requirement keeps NOT_STARTED and shows "(dependent behaviour BLOCKED)" in the OD-dependency column.
- **Requirement IDs are preserved** (owner decision DR-2026-11-17-C1). The baseline A2 B.1 proposal to rename FR-REQ-001…003 → FR-INT-001…003 and FR-MAT-006 → FR-FAV-001 is not adopted.
- **Tests** list the specified test suites (doc 08 §14). A suite listed here is specified, not executed.
- Implementation status may move beyond PLANNED only for APPROVED requirements and only with evidence (doc 12 §3). No implementation has started.

## 2. Matrix

| Requirement | Legacy | Title | Domain | Module(s) | Approval | Implementation | OD dependency | Tests (specified) |
|---|---|---|---|---|---|---|---|---|
| FR-ACC-001 | FR-002 | Registration | D01 | M01 | APPROVED | TESTED (G5 Phase 2b, `b53d1bd`: phone + password registration, enumeration-safe; `apps/accounts/tests/test_auth_api.py`) | — | T-AUTH |
| FR-ACC-002 | FR-003 | Phone verification | D03 | M04, M01 | APPROVED | IN_PROGRESS (G5 Phases 2a–2b: OTP service and endpoints TESTED, `apps/verification/tests`; gating of protected matrimonial activities arrives with those features, Phase 3+) | — | T-AUTH |
| FR-ACC-003 | — | Email | D01 | M01 | APPROVED | NOT_STARTED | — | T-AUTH |
| FR-ACC-004 | FR-001 | Adult eligibility | D01 | M01 | APPROVED | NOT_STARTED | OD-04b (underage handling) (dependent behaviour BLOCKED) | T-AUTH |
| FR-ACC-005 | FR-007 | Authentication | D02 | M01, M15 | APPROVED | TESTED (G5 Phases 2b–2e: login, logout, web sessions, mobile tokens and rotation, session management, password-only step-up (OD-04c), password reset/change, rate limits, security events; Django Admin MFA and admin session; `apps/accounts/tests`, `apps/admin_access/tests`) | — | T-AUTH, T-SEC, T-CONC-001…004 |
| FR-ACC-006 | FR-004 | Account/profile separation | D01 | M01 | APPROVED | NOT_STARTED | — | T-AUTH |
| FR-ACC-007 | FR-005 | Account audit fields | D01 | M01 | APPROVED | IN_PROGRESS (G4: created_by/updated_by fields with PROTECT; set by services from G5) | — | T-AUTH |
| FR-ACC-008 | FR-002 | Phone normalization | D01 | M01 | APPROVED | TESTED (G4, DR-2026-11-18-G4: E.164 normalisation, unique, DB CHECK; tests in apps/accounts/tests) | — | T-AUTH |
| FR-ACC-009 | — | Limited browsing | D01 | M01 | APPROVED | BLOCKED | OD-02a/b (whole requirement) | T-AUTH |
| FR-ACC-010 | FR-006 | Account deactivation (from FR-006) | D01 | M01 | APPROVED | NOT_STARTED | OD-02c (dependent behaviour BLOCKED) | T-AUTH |
| FR-ADM-001 | — | Administrative capabilities | D22 | M15, M16 | APPROVED | NOT_STARTED | — | T-LOG, T-REG |
| FR-ADM-002 | — | Least-privilege, audited administration | D22 | M15, M16 | APPROVED | IN_PROGRESS (G4: audit log, maintenance protocol, DB grant model. G5 Phase 2e TESTED: AdminRole authorization (deny by default, audited assignment and revocation, no escalation), two-superuser limit, mandatory admin MFA, admin session limits. Remaining: role permissions per later phase, dual approval and access reviews, Phase 16) | — | T-LOG, T-REG |
| FR-CON-001 | — | Connection creation | D14 | M08 | APPROVED | NOT_STARTED | — | T-CON |
| FR-CON-002 | — | Connection states | D14 | M08 | APPROVED | NOT_STARTED | OD-06h/i/l (dependent behaviour BLOCKED) | T-CON |
| FR-CON-003 | — | Reopening | D14 | M08 | APPROVED | NOT_STARTED | OD-06n (dependent behaviour BLOCKED) | T-CON |
| FR-CON-004 | — | Relationship progress | D14 | M08 | APPROVED | NOT_STARTED | OD-06i/k (dependent behaviour BLOCKED) | T-CON |
| FR-CON-005 | — | Progress history | D14 | M08 | APPROVED | NOT_STARTED | — | T-CON |
| FR-CON-006 | — | Shared notes | D14 | M08 | APPROVED | NOT_STARTED | — | T-CON |
| FR-DAT-001 | — | Download My Data | D21 | M14 | APPROVED | NOT_STARTED | — | T-DEL, T-REG, T-SEC-013…020 |
| FR-DAT-002 | — | Export format | D21 | M14 | APPROVED | NOT_STARTED | — | T-DEL, T-REG, T-SEC-013…020 |
| FR-DAT-003 | — | Export identity confirmation | D21 | M14 | APPROVED | NOT_STARTED | OD-04c (dependent behaviour BLOCKED) | T-DEL, T-REG, T-SEC-013…020 |
| FR-DAT-004 | — | Export scope | D21 | M14 | APPROVED | NOT_STARTED | — | T-DEL, T-REG, T-SEC-013…020 |
| FR-DAT-005 | — | Download expiry | D21 | M14 | APPROVED | NOT_STARTED | — | T-DEL, T-REG, T-SEC-013…020 |
| FR-DAT-006 | — | Account deletion | D21 | M14 | APPROVED | NOT_STARTED | OD-04c (dependent behaviour BLOCKED) | T-DEL, T-REG, T-SEC-013…020 |
| FR-DAT-007 | — | Recovery period | D21 | M14 | APPROVED | NOT_STARTED | OD-02d (dependent behaviour BLOCKED) | T-DEL, T-REG, T-SEC-013…020 |
| FR-DAT-008 | — | Deletion processing | D21 | M14 | APPROVED | NOT_STARTED | — | T-DEL, T-REG, T-SEC-013…020 |
| FR-DAT-009 | — | Retention exceptions | D21 | M14 | APPROVED | IN_PROGRESS (G4: audit hold tables and release function; hold cases G5 Phase 15) | — | T-DEL, T-REG, T-SEC-013…020 |
| FR-DAT-010 | — | Manager deletion | D21 | M14 | APPROVED | NOT_STARTED | — | T-DEL, T-REG, T-SEC-013…020 |
| FR-FAM-001 | — | Authorization invitation | D08 | M05 | APPROVED | TESTED (G5 Phase 4: owner invites a registered, active, phone-verified account; rate limited. 2026-11-20, KI-34: enumeration-safe, with a uniform `202` and invitation record, resolution in a background task, and the authorization visible to the owner only after acceptance; ADR-034; 2026-11-20, DR-2026-11-20-O-1: permission selection at invitation; requests to manage a profile (Flow B), enumeration-safe; ADR-035, TESTED) | — | T-ACT |
| FR-FAM-002 | — | Acceptance | D08 | M05 | APPROVED | TESTED (G5 Phase 4: only the invitee accepts or rejects; pending grants nothing; 2026-11-20: owner accepts requests choosing permissions; nobody accepts for another person, TESTED) | — | T-ACT |
| FR-FAM-003 | — | Permission assignment | D08 | M05 | APPROVED | TESTED (G5 Phase 4: template plus individual permissions; Sensitive with confirmation and owner step-up; Owner-only never; 2026-11-20: owner-only grant/revoke of individual permissions later, PERMISSIONS_GRANTED/REVOKED history, manager notified; managers never manage managers, TESTED) | — | T-ACT |
| FR-FAM-004 | — | Starter permission groups | D08 | M05 | APPROVED | IN_PROGRESS (G5 Phase 4: configurable Standard/Communication/Advanced templates TESTED; pre-selection semantics OD-05a) | OD-05a (dependent behaviour BLOCKED) | T-ACT |
| FR-FAM-005 | — | Sensitive permissions | D08 | M05 | APPROVED | IN_PROGRESS (G5 Phase 4: Sensitive owner-only by default, explicit grant with step-up, owner notified, audited, TESTED. 2026-11-20: TR-16 approved and implemented — per-action step-up with the manager's authenticator, 5 min, single use, owner notified after (DR-2026-11-20-O-3, ADR-036), TESTED; OD-05c decided and enforced. Open: H tier and per-share approval OD-05a/d) | OD-05a/d (dependent behaviour BLOCKED) | T-ACT |
| FR-FAM-006 | — | Authorization lifecycle | D08 | M05 | APPROVED | IN_PROGRESS (G5 Phase 4: PENDING, ACTIVE, PAUSED, EXPIRED, REVOKED, REJECTED TESTED; owner cancels pending invitations TESTED. 2026-11-20: 30-day expiry of invitations and requests with history and notices (OD-05e decided, DR-2026-11-20-O-2) TESTED; resignation OD-05f not implemented) | OD-05f (dependent behaviour BLOCKED) | T-ACT |
| FR-FAM-007 | — | Expiry | D08 | M05 | APPROVED | TESTED (G5 Phase 4: optional expiry, none by default, job plus runtime check, renewal) | — | T-ACT |
| FR-FAM-008 | — | Owner control | D08 | M05 | APPROVED | TESTED (G5 Phase 4: pause, resume, revoke, renew by the owner only; immediate loss of access) | — | T-ACT |
| FR-FAM-009 | — | Activity tracking | D08 | M05 | APPROVED | TESTED (G5 Phase 4: ManagerActionLog and ProfileAccessHistory, append-only; device/browser shown, IP not shown; approximate location empty until a source exists) | — | T-ACT |
| FR-MAT-001 | — | Search | D09 | M06 | APPROVED | NOT_STARTED | — | T-MAT |
| FR-MAT-002 | FR-013 | Worldwide search | D09 | M06 | APPROVED | NOT_STARTED | — | T-MAT |
| FR-MAT-003 | FR-021 | Rule-based matching | D09 | M06 | APPROVED | NOT_STARTED | OD-10 (dependent behaviour BLOCKED) | T-MAT |
| FR-MAT-004 | FR-021 | Optional criteria | D09 | M06 | APPROVED | NOT_STARTED | OD-10b (dependent behaviour BLOCKED) | T-MAT |
| FR-MAT-005 | — | Eligibility filters | D09 | M06 | APPROVED | NOT_STARTED | OD-10a (dependent behaviour BLOCKED) | T-MAT |
| FR-MAT-006 | — | Favorites | D10 | M06 | APPROVED | NOT_STARTED | — | T-ACT-013 |
| FR-MAT-007 | — | Profile views | D11 | M06, M11 | APPROVED | NOT_STARTED | OD-08 (dependent behaviour BLOCKED) | T-MAT-010…026, T-CONC-040…043 |
| FR-MOD-001 | — | Reportable content | D20 | M13 | APPROVED | NOT_STARTED | — | — |
| FR-MOD-002 | — | Authenticated reporting | D20 | M13 | APPROVED | NOT_STARTED | — | — |
| FR-MOD-003 | — | No automatic action on a report alone | D20 | M13 | APPROVED | NOT_STARTED | — | — |
| FR-MOD-004 | — | Moderation capabilities | D20 | M13 | APPROVED | NOT_STARTED | — | — |
| FR-MOD-005 | — | Reporter confidentiality | D20 | M13 | APPROVED | NOT_STARTED | — | — |
| FR-MOD-006 | — | Conflict of interest | D20 | M13 | APPROVED | NOT_STARTED | — | — |
| FR-MSG-001 | — | Conversation creation | D15 | M09 | APPROVED | NOT_STARTED | — | T-CONC-020 |
| FR-MSG-002 | — | Participants | D15 | M09 | APPROVED | NOT_STARTED | — | T-CONC-020 |
| FR-MSG-003 | — | Messaging eligibility | D15 | M09 | APPROVED | NOT_STARTED | — | T-CONC-020 |
| FR-MSG-004 | — | Manager communication | D15 | M09 | APPROVED | NOT_STARTED | OD-05a/b (dependent behaviour BLOCKED) | T-CONC-020 |
| FR-MSG-005 | — | Message history | D15 | M09 | APPROVED | NOT_STARTED | — | T-CONC-020 |
| FR-MSG-006 | — | Attachments | D15 | M09 | APPROVED | NOT_STARTED | — | T-CONC-020 |
| FR-MSG-007 | — | Shared documents | D15 | M09 | APPROVED | NOT_STARTED | — | T-CONC-020 |
| FR-MSG-008 | — | Document permission | D15 | M09 | APPROVED | NOT_STARTED | — | T-CONC-020 |
| FR-MSG-009 | — | Sensitive sharing | D15 | M09 | APPROVED | NOT_STARTED | OD-05d (dependent behaviour BLOCKED) | T-CONC-020 |
| FR-MSG-010 | — | MVP exclusions | D15 | M09 | APPROVED | NOT_STARTED | — | T-CONC-020 |
| FR-NOT-001 | — | Notification channels | D19 | M12 | APPROVED | IN_PROGRESS (2026-11-20, DR-2026-11-20-O-7: in-app notifications and Expo push from outbox events TESTED; SMS (Twilio) and email (SMTP) adapters TESTED with mocked clients; channel policy per event type in ADR-037) | — | T-NOT, T-OUT |
| FR-NOT-002 | — | Notification preferences | D19 | M12 | APPROVED | NOT_STARTED | OD-02e (dependent behaviour BLOCKED) | T-NOT, T-OUT |
| FR-NOT-003 | — | Security notifications can't be disabled | D19 | M12 | APPROVED | NOT_STARTED | — | T-NOT, T-OUT |
| FR-NOT-004 | — | Generic SMS/push content | D19 | M12 | APPROVED | IN_PROGRESS (2026-11-20: generic notice texts without private data for in-app and push, TESTED) | — | T-NOT, T-OUT |
| FR-NOT-005 | — | Transactional outbox and retryable delivery (approved core; ADR-014 core. Refinements are TR-11 / ADR-028, PROPOSED, not part of this row's approval) | D19 | M12 | APPROVED | IN_PROGRESS (G4: outbox core and TR-11 processing tested; provider delivery G5 Phase 12) | — | T-NOT, T-OUT |
| FR-NOT-006 | — | English and Urdu templates | D19 | M12 | APPROVED | NOT_STARTED | — | T-NOT, T-OUT |
| FR-PREF-001 | FR-018 | Partner preference management (FR-018) | D07 | M03 | APPROVED | IN_PROGRESS (G5 Phase 3c: preferences TESTED; vocabulary options await approval and activation; FR-018 "profession" preference has no doc 03 §4 table yet) | — | — |
| FR-PREF-002 | FR-019 | Nullable Boolean preferences (FR-019) | D07 | M03 | APPROVED | TESTED (G5 Phase 3c: three-state own_house / job / business) | — | — |
| FR-PREF-003 | FR-020 | Financial preference range (FR-020) | D07 | M03 | APPROVED | IN_PROGRESS (G5 Phase 3c: range, currency and frequency TESTED; compatibility-aware comparison is matching, Phase 8) | — | — |
| FR-PREF-004 | FR-021 | Optional criteria (FR-021) | D07 | M03 | APPROVED | NOT_STARTED | OD-10b (dependent behaviour BLOCKED) | — |
| FR-PRI-001 | — | Blocking | D16 | M10 | APPROVED | NOT_STARTED | — | T-MAT-017…022 |
| FR-PRI-002 | — | Unblocking | D16 | M10 | APPROVED | NOT_STARTED | — | T-MAT-017…022 |
| FR-PRI-003 | — | Hide My Profile From | D16 | M10 | APPROVED | NOT_STARTED | — | T-MAT-017…022 |
| FR-PRI-004 | — | Hidden-profile management | D16 | M10 | APPROVED | NOT_STARTED | — | T-MAT-017…022 |
| FR-PRI-005 | — | Photo permissions | D16 | M10 | APPROVED | NOT_STARTED | — | T-MAT-017…022 |
| FR-PRI-006 | — | Visitor history | D16 | M10 | APPROVED | NOT_STARTED | OD-03g (dependent behaviour BLOCKED) | T-MAT-017…022 |
| FR-PRI-007 | — | Private browsing | D16 | M10 | APPROVED | NOT_STARTED | OD-03g (dependent behaviour BLOCKED) | T-MAT-017…022 |
| FR-PRI-008 | — | Visitor history removal | D16 | M10 | APPROVED | NOT_STARTED | — | T-MAT-017…022 |
| FR-PRI-009 | — | Private media | D05 | M02, M10, M13 | APPROVED | NOT_STARTED | — | — |
| FR-PRO-001 | FR-008 | Profile creation | D04 | M02 | APPROVED | TESTED (G5 Phase 3b: one profile per account; creation needs an active, phone-verified account; final gate wording OD-02a) | OD-02a (FR-008 wording) (dependent behaviour BLOCKED) | T-ACT |
| FR-PRO-002 | FR-008 | Profile sections | D04 | M02 | APPROVED | TESTED (G5 Phase 3 sections; vocabularies: gender, marital status, religion (DR-2026-11-19-O), employment status (DR-2026-11-20-C-1); religion, denomination, caste, sub-caste and community separate and optional with initial lists and prefer-not-to-say flags (DR-2026-11-20-O-5, KI-29 resolved; religion optional with "prefer not to say" as the default for new profiles (DR-2026-11-20-P-1), ACCEPTED by the owner for this item (DR-2026-11-20-PA-1); identity vocabularies accepted unchanged for the MVP, withheld caste clears or refuses a sub-caste that names a caste, read-only vocabulary endpoint `GET /profiles/vocabularies/` (DR-2026-11-23-K-1..4, ACCEPTED by the owner for these items, DR-2026-11-23-KA); the requirement as a whole stays TESTED) | — | T-ACT |
| FR-PRO-003 | — | Date of birth privacy | D04 | M02 | APPROVED | TESTED (G5 Phase 3b: DOB only in the owner's own view; age computed; under-age DOB rejected and not stored) | — | T-ACT |
| FR-PRO-004 | FR-014 | Education and profession | D04 | M02 | APPROVED | TESTED (G5 Phase 3b: editable in every non-closed state) | — | T-ACT |
| FR-PRO-005 | FR-012 | Verified information | D04 | M02 | APPROVED | BLOCKED | OD-04a (whole requirement) | T-ACT |
| FR-PRO-006 | — | Profile visibility | D04 | M02 | APPROVED | IN_PROGRESS (G5 Phase 3b: visibility stored separately and set by the owner, frozen while suspended; behaviour for viewers OD-03, Phases 6/8) | OD-03 (dependent behaviour BLOCKED) | T-ACT |
| FR-PRO-007 | FR-011 | Profile activation | D04 | M02 | APPROVED | NOT_STARTED | OD-03e (dependent behaviour BLOCKED) | T-ACT |
| FR-PRO-008 | FR-017 | Profile photographs | D05 | M02, M10, M13 | APPROVED | IN_PROGRESS (G5 Phase 3d: upload pipeline TR-10, multiple photos, primary, private storage, moderation status, soft delete TESTED; controlled delivery Module 10, Phase 6; moderation Phase 14; 2026-11-20: owner-approved limits (5 MB, 4096 px, JPEG/PNG/WebP, no SVG or animation, 6 photos, one primary) and explicit scan outcomes with ClamAV adapter (DR-2026-11-20-O-6, -8), TESTED) | — | — |
| FR-PRO-009 | FR-009 | Profile lifecycle (from FR-009) | D04 | M02 | APPROVED | IN_PROGRESS (G5 Phase 3b: DRAFT → PENDING_REVIEW TESTED; activation Phase 5, suspension Phase 14) | — | T-ACT |
| FR-PRO-010 | FR-013 | Profile location (from FR-013) | D04 | M02 | APPROVED | TESTED (G5 Phase 3b: worldwide ISO country, state, city, area, residence type; nationality separate) | — | T-ACT |
| FR-PRO-011 | FR-014 | Income (from FR-014) | D04 | M02 | APPROVED | TESTED (G5 Phase 3b: Decimal income with ISO currency and frequency, DB CHECK) | — | T-ACT |
| FR-PRO-012 | FR-015 | Family and lifestyle (from FR-015) | D04 | M02 | APPROVED | IN_PROGRESS (G5 Phase 3b: family and lifestyle fields TESTED; visibility rules for sensitive fields Phase 6) | — | T-ACT |
| FR-PRO-013 | FR-016 | Profile languages (from FR-016) | D04 | M02 | APPROVED | TESTED (G5 Phase 3b: multiple languages with proficiency, unique per profile) | — | T-ACT |
| FR-REQ-001 | — | Express interest | D12 | M07 | APPROVED | NOT_STARTED | OD-06a–g (dependent behaviour BLOCKED) | T-INT |
| FR-REQ-002 | — | Interest response | D12 | M07 | APPROVED | NOT_STARTED | OD-06a–c (dependent behaviour BLOCKED) | T-INT |
| FR-REQ-003 | — | Declined interest history | D12 | M07 | APPROVED | NOT_STARTED | OD-06g (dependent behaviour BLOCKED) | T-INT |
| FR-REQ-004 | — | Formal requests | D13 | M07, M11 | APPROVED | NOT_STARTED | — | T-REQ, T-CONC-010…013, T-CONC-030…038 |
| FR-REQ-005 | — | Duplicate requests | D13 | M07, M11 | APPROVED | NOT_STARTED | — | T-REQ, T-CONC-010…013, T-CONC-030…038 |
| FR-REQ-006 | — | Request expiry | D13 | M07, M11 | APPROVED | NOT_STARTED | OD-07e (dependent behaviour BLOCKED) | T-REQ, T-CONC-010…013, T-CONC-030…038 |
| FR-REQ-007 | — | Withdrawal | D13 | M07, M11 | APPROVED | NOT_STARTED | OD-06 (dependent behaviour BLOCKED) | T-REQ, T-CONC-010…013, T-CONC-030…038 |
| FR-REQ-008 | — | History | D13 | M07, M11 | APPROVED | NOT_STARTED | — | T-REQ, T-CONC-010…013, T-CONC-030…038 |
| FR-REQ-009 | — | Atomic financial operation | D13 | M07, M11 | APPROVED | NOT_STARTED | — | T-REQ, T-CONC-010…013, T-CONC-030…038 |
| FR-SUB-001 | — | Subscription plans | D17 | M11 | APPROVED | NOT_STARTED | — | T-DEL-007…012 |
| FR-SUB-002 | — | Subscription allowances | D17 | M11 | APPROVED | NOT_STARTED | — | T-DEL-007…012 |
| FR-SUB-003 | — | Allowance expiry | D17 | M11 | APPROVED | NOT_STARTED | — | T-DEL-007…012 |
| FR-SUB-004 | — | Purchased top-ups | D17 | M11 | APPROVED | NOT_STARTED | — | T-DEL-007…012 |
| FR-SUB-005 | — | Separate balances | D17 | M11 | APPROVED | NOT_STARTED | — | T-DEL-007…012 |
| FR-SUB-006 | — | Consumption order | D17 | M11 | APPROVED | NOT_STARTED | — | T-DEL-007…012 |
| FR-SUB-007 | — | Payment history | D18 | M11 | APPROVED | NOT_STARTED | — | T-REQ-035…051 |
| FR-SUB-008 | — | Failed renewal | D17 | M11 | APPROVED | NOT_STARTED | OD-09a (dependent behaviour BLOCKED) | T-DEL-007…012 |
| FR-SUB-009 | — | Cancellation | D17 | M11 | APPROVED | NOT_STARTED | OD-09 (dependent behaviour BLOCKED) | T-DEL-007…012 |
| FR-SUB-010 | — | Refunds | D18 | M11 | APPROVED | NOT_STARTED | OD-07 (dependent behaviour BLOCKED) | T-REQ-035…051 |
| FR-SUB-011 | — | Account billing identity | D17 | M11 | APPROVED | NOT_STARTED | — | T-DEL-007…012 |
| FR-SUB-012 | — | Profile-view billing | D11 | M06, M11 | APPROVED | NOT_STARTED | OD-08 (dependent behaviour BLOCKED) | T-MAT-010…026, T-CONC-040…043 |
| FR-VER-001 | FR-003 | Phone verification | D03 | M04, M01 | APPROVED | NOT_STARTED | — | T-AUTH |
| FR-VER-002 | — | Identity submission | D06 | M04 | APPROVED | NOT_STARTED (Phase 5, not authorized). 2026-11-20: owner-only submission guard `verification.services.identity_access` TESTED (OD-05c, DR-2026-11-20-O-4); the Phase 5 endpoints must call it | — | — |
| FR-VER-003 | FR-010 | Review workflow | D06 | M04 | APPROVED | NOT_STARTED | — | — |
| FR-VER-004 | FR-010 | Rejection and resubmission | D06 | M04 | APPROVED | NOT_STARTED | OD-04e (dependent behaviour BLOCKED) | — |
| FR-VER-005 | — | Duplicate document detection | D06 | M04 | APPROVED | NOT_STARTED | — | — |
| FR-VER-006 | — | Reviewer audit | D06 | M04 | APPROVED | NOT_STARTED | — | — |
| NFR-SEC | — | SRS §19 non-functional | Cross-cutting | All | APPROVED | NOT_STARTED | — | T-CONC, T-SEC |
| NFR-PRIV | — | SRS §19 non-functional | Cross-cutting | All | APPROVED | NOT_STARTED | — | — |
| NFR-REL | — | SRS §19 non-functional | Cross-cutting | All | APPROVED | NOT_STARTED | — | T-CONC, T-SEC |
| NFR-PERF | — | SRS §19 non-functional | Cross-cutting | All | APPROVED | NOT_STARTED | Targets need measurement (R-12) | — |
| NFR-SCAL | — | SRS §19 non-functional | Cross-cutting | All | APPROVED | NOT_STARTED | — | — |
| NFR-MAINT | — | SRS §19 non-functional | Cross-cutting | All | APPROVED | NOT_STARTED | — | — |
| NFR-L10N | FR-016 (part) | SRS §19 non-functional | Cross-cutting | All | APPROVED | NOT_STARTED | — | — |

## 3. Counts

- Requirements listed: 126 (119 functional, 7 non-functional).
- Implementation status: 2 BLOCKED, 124 NOT_STARTED. Nothing is PLANNED or beyond, because no G5 phase has been authorized.
- Every functional requirement maps to exactly one domain and at least one module.
