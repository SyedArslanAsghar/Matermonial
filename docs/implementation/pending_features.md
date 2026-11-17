# Pending Features

**Last updated:** 2026-11-17

All features are pending. The authoritative per-requirement list, with domain, module, approval status, implementation status and owner-decision dependencies, is `docs/handover/18_REQUIREMENTS_TRACEABILITY_MATRIX.md`.

## Sequence (doc 10 §0)

| Gate / phase | Scope | Implementation status |
|---|---|---|
| G2 | Repository governance (Git, CI with PostgreSQL 16/18, virtual environment) | IN PROGRESS (authorized 2026-11-17). Finalization applied (DR-2026-11-17-G2D); baseline commit waiting for the author identity; owner acceptance pending (progress.md). |
| G3 | Backend foundation, no migrations | NOT_STARTED (not authorized) |
| G4 | First migration (kernel models) | NOT_STARTED (not authorized) |
| G5 Phase 2 | Auth flows + Django Admin MFA | NOT_STARTED |
| G5 Phase 3 | Profiles, preferences, uploads | NOT_STARTED |
| G5 Phase 4 | Family management and ActorContext | NOT_STARTED |
| G5 Phase 5 | Identity verification | NOT_STARTED |
| G5 Phase 6 | Privacy, central eligibility, restrictions | NOT_STARTED |
| G5 Phase 7 | Credit ledger and projections | NOT_STARTED |
| G5 Phase 8 | Search, matching, view billing | NOT_STARTED |
| G5 Phase 9 | Interests and requests | NOT_STARTED |
| G5 Phase 10 | Connections | NOT_STARTED |
| G5 Phase 11 | Messaging and documents | NOT_STARTED |
| G5 Phase 12 | Notification delivery | NOT_STARTED |
| G5 Phase 13 | Subscriptions and payments | NOT_STARTED |
| G5 Phase 14 | Moderation | NOT_STARTED |
| G5 Phase 15 | Export and deletion | NOT_STARTED |
| G5 Phase 16 | Admin operations | NOT_STARTED |
| G5 Phase 17 | Web | NOT_STARTED |
| G5 Phase 18 | Mobile | NOT_STARTED |
| G5 Phase 19 | Release | NOT_STARTED |

Requirements fully blocked by an OPEN owner decision: FR-ACC-009 (OD-02a/b) and FR-PRO-005 (OD-04a). Partially dependent requirements are listed in doc 18.
