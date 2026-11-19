# Completed Features

**Last updated:** 2026-11-19

Implementation status per requirement is in `docs/handover/18_REQUIREMENTS_TRACEABILITY_MATRIX.md`. Nothing here is REVIEWED or ACCEPTED: those statuses are set by the reviewer and the project owner (CC-R70).

## G5 Phase 2 — Authentication and admin access (TESTED, 2026-11-19)

Branch `feature/g5-phase2-auth`; evidence in `progress.md` (347/347 tests on Python 3.12 and 3.13 × PostgreSQL 16 and 18).

| Feature | Requirement | Status |
|---|---|---|
| Registration (phone + password, enumeration-safe) | FR-ACC-001 | TESTED |
| Phone OTP service and endpoints | FR-ACC-002 (gating of protected activities pending, Phase 3+) | IN_PROGRESS |
| Login, logout, web sessions, mobile tokens with rotation, session management, step-up (password only, OD-04c), password reset/change, rate limits, security events | FR-ACC-005, TR-01 | TESTED |
| AdminRole authorization, audited role changes, two-superuser limit, admin MFA, admin session limits | FR-ADM-002 (part), TR-07 | TESTED (FR-ADM-002 stays IN_PROGRESS for Phase 16) |

Documentation work completed under G1 is recorded in `docs/handover/20_DOCUMENTATION_CORRECTION_REGISTER.md`.
