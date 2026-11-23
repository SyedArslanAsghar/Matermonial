# Completed Features

**Last updated:** 2026-11-23 (DR-2026-11-23-K ACCEPTED, DR-2026-11-23-KA)

Implementation status per requirement is in `docs/handover/18_REQUIREMENTS_TRACEABILITY_MATRIX.md`. Nothing here is REVIEWED or ACCEPTED: those statuses are set by the reviewer and the project owner (CC-R70).

## G5 Phase 2 — Authentication and admin access (TESTED, 2026-11-19)

Branch `feature/g5-phase2-auth`; evidence in `progress.md` (347/347 tests on Python 3.12 and 3.13 × PostgreSQL 16 and 18).

| Feature | Requirement | Status |
|---|---|---|
| Registration (phone + password, enumeration-safe) | FR-ACC-001 | TESTED |
| Phone OTP service and endpoints | FR-ACC-002 (gating of protected activities pending, Phase 3+) | IN_PROGRESS |
| Login, logout, web sessions, mobile tokens with rotation, session management, step-up (password only, OD-04c), password reset/change, rate limits, security events | FR-ACC-005, TR-01 | TESTED |
| AdminRole authorization, audited role changes, two-superuser limit, admin MFA, admin session limits | FR-ADM-002 (part), TR-07 | TESTED (FR-ADM-002 stays IN_PROGRESS for Phase 16) |

## G5 Phase 3 — Profiles, preferences and photos (TESTED, 2026-11-19)

Evidence in `progress.md` (404/404 tests on Python 3.12 and 3.13 × PostgreSQL 16 and 18).

| Feature | Requirement | Status |
|---|---|---|
| Own profile creation (one per account), sections, completion, submit for review | FR-PRO-001, 003, 004, 010, 011, 013 | TESTED |
| Sections needing owner value lists; visibility; lifecycle; family and lifestyle visibility | FR-PRO-002, 006, 009, 012 | IN_PROGRESS |
| Partner preferences | FR-PREF-002 TESTED; FR-PREF-001, 003 IN_PROGRESS | — |
| Photos through the TR-10 pipeline | FR-PRO-008 | IN_PROGRESS (delivery Phase 6) |

## Owner decisions DR-2026-11-19-O and G5 Phase 4 (TESTED, 2026-11-19)

| Feature | Requirement | Status |
|---|---|---|
| Approved vocabularies, denomination, "prefer not to say", approved required fields | FR-PRO-002 | IN_PROGRESS (KI-29, KI-37) |
| Two-person admin MFA recovery, SMS-only codes, emergency CLI | TR-07, ADR-033 A1 | TESTED |
| Invitation, acceptance, permissions and templates, owner controls, expiry, activity tracking | FR-FAM-001/002/003/007/008/009 | TESTED |
| Templates, sensitive permissions, lifecycle remainder | FR-FAM-004/005/006 | IN_PROGRESS (OD-05, TR-16) |
| Acting-profile resolution in the profile endpoints | TR-02 (APPROVED, DR-2026-11-20-C-5) | TESTED |

## G5 Phases 2–4 final corrections (TESTED, 2026-11-20, DR-2026-11-20-C)

| Feature | Requirement / issue | Status |
|---|---|---|
| Employment-status options active; valid profiles submit | KI-37; FR-PRO-002 | TESTED (FR-PRO-002 stays IN_PROGRESS: KI-29) |
| Enumeration-safe manager invitations, owner cancel | KI-34; FR-FAM-001, FR-FAM-006 | TESTED |
| First admin MFA enrollment code by SMS only | KI-39; TR-07, ADR-033 Amendment 2 | TESTED |
| Fail-safe test database configuration | KI-38 | TESTED |
| Sensitive manager use fails closed until TR-16 | TR-02 review; FR-FAM-005 | TESTED |

## Owner decisions DR-2026-11-20-O (TESTED, 2026-11-20)

| Feature | Requirement / decision | Status |
|---|---|---|
| Permission selection at invitation; requests to manage a profile (Flow B) | FR-FAM-001/002/003; O-1 | TESTED |
| Owner-only grant/revoke of individual permissions; manager restrictions | FR-FAM-003; O-1 | TESTED |
| 30-day expiry of invitations and requests with history and notices | FR-FAM-006; OD-05e, O-2 | TESTED |
| Account authenticator and per-action manager step-up | FR-FAM-005; TR-16, O-3 | TESTED |
| Owner-only identity verification (permissions and guard) | FR-VER-002; OD-05c, O-4 | TESTED (guard; Phase 5 not started) |
| Separate religion/denomination/caste/sub-caste/community | FR-PRO-002; KI-29, O-5 | TESTED |
| Photo limits and scan outcomes, ClamAV adapter | FR-PRO-008; O-6, O-8 | TESTED |
| SMS/email/push adapters, in-app notifications, push delivery | FR-NOT-001/004; O-7 | TESTED (FR rows IN_PROGRESS) |
| OpenAPI zero errors and warnings | KI-40; O-9 | TESTED |

## DR-2026-11-20-P (ACCEPTED, 2026-11-20)

| Feature | Requirement / decision | Status |
|---|---|---|
| Religion optional; "prefer not to say" default for new profiles; all five identity fields optional; existing profiles unchanged | FR-PRO-002; P-1 | **ACCEPTED** (DR-2026-11-20-PA-1, `c7fe7e5`) |
| Vocabulary admin parent choices per list; database validation kept | P-2 | **ACCEPTED** (DR-2026-11-20-PA-2, `c7fe7e5`) |
| Existing vocabulary values preserved without modification | P-3 | **ACCEPTED** (DR-2026-11-20-PA-3) |

## DR-2026-11-23-K (ACCEPTED, 2026-11-23)

| Feature | Requirement / decision | Status |
|---|---|---|
| Identity vocabularies accepted unchanged for the MVP | FR-PRO-002; K-1 | **ACCEPTED** (DR-2026-11-23-KA) |
| Withheld caste clears or refuses a sub-caste that names a caste; sub-caste notice served by the API | FR-PRO-002; K-2 | **ACCEPTED** (DR-2026-11-23-KA) |
| `GET /api/v1/profiles/vocabularies/` | FR-PRO-002; K-3 | **ACCEPTED** (DR-2026-11-23-KA) |
| Admin identity-list changes need an owner decision ID, audited | K-4 | **ACCEPTED** (DR-2026-11-23-KA) |

Documentation work completed under G1 is recorded in `docs/handover/20_DOCUMENTATION_CORRECTION_REGISTER.md`.
