# Pending Features

**Last updated:** 2026-11-20 (owner decisions DR-2026-11-20-O)

Phases 2–4 are implemented and tested; everything after them is pending (Phase 5 not authorized). The authoritative per-requirement list, with domain, module, approval status, implementation status and owner-decision dependencies, is `docs/handover/18_REQUIREMENTS_TRACEABILITY_MATRIX.md`.

## Sequence (doc 10 §0)

| Gate / phase | Scope | Implementation status |
|---|---|---|
| G2 | Repository governance | **ACCEPTED** with carried-forward items (DR-2026-11-17-G2A); baseline commit `38f491dea79f`; "CI runs on the baseline" OPEN until before G4 |
| G3 | Backend foundation, no migrations | **ACCEPTED** by the owner on 2026-11-18 with an accepted exception (DR-2026-11-18-G3A); KI-14's 3 User-model database tests are OPEN and carried forward to G4 |
| G4 | First migration (kernel models) | **ACCEPTED** (DR-2026-11-18-G4A) |
| G5 Phase 2 | Auth flows + Django Admin MFA | **TESTED** (2026-11-19, `feature/g5-phase2-auth`; first-enrollment SMS correction 2026-11-20; owner review pending) |
| G5 Phase 3 | Profiles, preferences, uploads | **TESTED** (2026-11-19; KI-37 resolved 2026-11-20; owner review pending; KI-29, KI-31, KI-32) |
| G5 Phase 4 | Family management and ActorContext | **TESTED** (2026-11-19; authorized DR-2026-11-19-O-10; KI-34 and KI-36 resolved; DR-2026-11-20-O implemented (requests, selection, 30-day expiry, TR-16 step-up, OD-05c); owner review pending; open: OD-05a/b/d/f) |
| G5 Phase 5 | Identity verification | NOT_STARTED (**not authorized**; OD-05c decided: owner-only, guard ready) |
| G5 Phase 6 | Privacy, central eligibility, restrictions | NOT_STARTED |
| G5 Phase 7 | Credit ledger and projections | NOT_STARTED |
| G5 Phase 8 | Search, matching, view billing | NOT_STARTED |
| G5 Phase 9 | Interests and requests | NOT_STARTED |
| G5 Phase 10 | Connections | NOT_STARTED |
| G5 Phase 11 | Messaging and documents | NOT_STARTED |
| G5 Phase 12 | Notification delivery | IN_PROGRESS (in-app and push delivery, provider adapters done under DR-2026-11-20-O-7; preferences, Urdu templates, receipts open, KI-41) |
| G5 Phase 13 | Subscriptions and payments | NOT_STARTED |
| G5 Phase 14 | Moderation | NOT_STARTED |
| G5 Phase 15 | Export and deletion | NOT_STARTED |
| G5 Phase 16 | Admin operations | NOT_STARTED |
| G5 Phase 17 | Web | NOT_STARTED |
| G5 Phase 18 | Mobile | NOT_STARTED |
| G5 Phase 19 | Release | NOT_STARTED |

Requirements fully blocked by an OPEN owner decision: FR-ACC-009 (OD-02a/b) and FR-PRO-005 (OD-04a). Partially dependent requirements are listed in doc 18.
