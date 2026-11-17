# Progress

**Last updated:** 2026-11-17 (G2)

## Governance status

| Item | Status |
|---|---|
| Documentation baseline (v4–v4.6-F3) | APPROVED (see `docs/decisions/new_architecture_decisions.md`, DR-2026-11-16) |
| G1 Documentation reconciliation | **COMPLETED. ACCEPTED by the project owner** (DR-2026-11-17-A, 2026-11-17). Final document statuses assigned (doc 20 §5). |
| G2 Repository governance | IN PROGRESS. AUTHORIZED (2026-11-17). Decisions recorded (DR-2026-11-17-G2D); finalization applied; baseline commit waiting for the author identity. **Not owner-accepted.** |
| G3 Backend foundation | NOT STARTED. NOT AUTHORIZED. |
| G4 First migration | NOT STARTED. NOT AUTHORIZED. |
| G5 Features | NOT STARTED. NOT AUTHORIZED. |

## Implementation status

No implementation work has been authorized or started. Doc 18 lists 126 requirements: 124 NOT_STARTED and 2 BLOCKED (FR-ACC-009 by OD-02a/b, FR-PRO-005 by OD-04a). Nothing is PLANNED or beyond.

The existing `backend/` scaffold (settings, a custom `User` model, 3 unit tests) predates the baseline. It has never been executed or verified in this environment, and has no migrations.

## G1 progress (2026-11-16 to 2026-11-17)

| Step | Result |
|---|---|
| 1. Baseline preservation | Done. 15 files extracted verbatim, all hashes verified (`docs/baseline/v4.6-F3/`). Pre-G1 snapshot taken (`docs/baseline/pre-g1-snapshot/`). |
| 2. Governance documents | Done. Docs 18, 19, 20 created. |
| 3. Authority and status headers | Done. `CLAUDE.md` (79 rule IDs) and doc 12 rewritten; status headers on `CLAUDE.md` and docs 00–20 (all PROPOSED). |
| 4. DCR application | Done. 98 of 99 DCRs APPLIED; DCR-20 BLOCKED by OD-02/OD-04. DCR-01 is APPLIED: its FR-PREF labels were completed in the correction pass, and the A2 B.1 ID renaming is not adopted (owner decision DR-2026-11-17-C1; doc 20 §6 note 1). |
| 5. Cross-document checks | Done. Superseded terms appear only in explicit retirement notes. |
| 6. Register traceability | Done. Contradictions C-1…C-78 marked aligned. |
| 7. OD and TR labelling | Done. OD-01 RESOLVED; OD-02…OD-10 OPEN; TR-05 and TR-14 APPROVED; all other TRs PROPOSED. |
| 8. Verification and report | Done (G1 Final Reconciliation Audit, 2026-11-17). |
| 9. Correction pass | Done (DR-2026-11-17-C; doc 20 §8). |
| 10. Owner acceptance | Done. G1 accepted and final document statuses assigned by the project owner (DR-2026-11-17-A; doc 20 §5). G1 exit checklist complete (doc 10 §0.5). |

## G2 repository governance (2026-11-17)

Authorized by the project owner on 2026-11-17 (G2 only; G3–G5 not authorized). Approved G2 scope: doc 10 §0.1.

### Inventory before G2

| Area | Found |
|---|---|
| Git | Not a repository; no history, no remote |
| Python environment | Stale root `.venv` (pip only; created for another path); no `backend/.venv` |
| Dependencies | `backend/requirements/{base,local,production}.txt` with compatible-release ranges; no lockfile |
| Quality tooling | `backend/pyproject.toml` (Ruff: line length 100, py312, rules E/F/I/B/UP; pytest-django with test settings) |
| Tests | 3 unit tests in `backend/accounts/tests/`; test settings use in-memory SQLite (KI-4) |
| CI/CD | `.github/workflows/.gitkeep` only |
| Docker / Compose | None |
| Frontend / mobile / infrastructure / scripts | Empty placeholders (`.gitkeep`) |
| README | Outdated ("Matrimonial Platform"; instructed `makemigrations`/`migrate`) |
| `.gitignore` | Basic Python/editor rules; `.env` ignored |
| Environment files | Root `.env` (owner-managed; not read); `backend/.env.example` (names and placeholders) |
| Claude Code instructions | `CLAUDE.md` + doc 12 (accepted in G1) |

### G2 changes

| Item | Result | Basis |
|---|---|---|
| `git init -b main` | Done; no commit, no remote, no Git config changed | doc 10 §0.1; doc 07 §8 |
| `.gitignore` | Extended (nested `.env*` except `.env.example`, keys, Node/Expo/build output, local DBs, local tool settings) | doc 10 §0.1; doc 07 §11, §14; doc 16 §8 |
| Virtual environment | Stale root `.venv` removed; `backend/.venv` created; `requirements/local.txt` installed; `pip check` clean | doc 10 §0.1; CC-R21 |
| CI | `.github/workflows/ci.yml`: install, `pip check`, Ruff lint and format, pytest collection; Python 3.12/3.13; read-only permissions; no secrets, no deploy | CC-R11, CC-R60; doc 08 §11; doc 09 §13 |
| PR template | `.github/pull_request_template.md` | doc 07 §10 |
| README | Rewritten as entry point | DR-2026-11-16-P3; doc 07 §12 |

### Classification of G2 choices

| Choice | Classification | Source |
|---|---|---|
| Monorepo; backend / frontend / mobile / infrastructure separation | Already approved | ADR-009; doc 07 §1 |
| Domain-oriented Django apps, services/selectors, thin views | Already approved (applied from G3) | CC-R15, CC-R16; doc 07 §3–4 |
| `/api/v1/`, OpenAPI with drf-spectacular | Already approved (applied from G3) | CC-R08, CC-R51; ADR-010 |
| `common/` shared code; `common/events` outbox location | `common/`: existing requirement (doc 07 §1). `common/events`: TR-11, PROPOSED | doc 07; doc 19 |
| Native local development with a `backend/` virtual environment | Existing project requirement | CC-R21; doc 10 §0.1 |
| Ruff; pytest + pytest-django | Already approved | CC-R08, CC-R60 |
| Test directory conventions (`apps/<domain>/tests/`) | Existing requirement (applied from G3) | doc 07 §3 |
| Reproducible dependency pinning | Approved method: pip-tools (DR-2026-11-17-G2D-4); implemented | doc 07 §13 |
| Branch model | Approved (DR-2026-11-17-G2D-3) | doc 07 §8 |
| Conventional Commits | Existing project guidance ("preferably") | doc 07 §9 |
| PR standards | Existing project requirement | doc 07 §10 |
| Branch protection, remote repository | Deferred (DR-2026-11-17-G2D-6) | Owner decision |
| CI quality checks (lint, dependency validation) | Approved tooling; implemented | CC-R11, CC-R60; doc 08 §11 |
| CI tests on PostgreSQL 16/18 | **Approved** (TR-13, DR-2026-11-17-G2D-2); implemented | doc 10 §0.1; doc 19 |
| Build / deploy separation | Approved principle; deployment out of G2 scope | doc 09 §12; CC-R22 |

### G2 owner decisions (recorded: DR-2026-11-17-G2D)

| ID | Decision | Outcome |
|---|---|---|
| D1 | Local baseline commit | APPROVED with conditions; **waiting for the owner's Git author identity** (the authorization contained placeholders) |
| D2 | TR-13 | **APPROVED.** PostgreSQL CI jobs added; SQLite test override removed |
| D3 | Branch model | APPROVED: `main` plus short-lived `feature/`, `fix/` and `hotfix/` branches; no `develop` |
| D4 | Dependency locking | APPROVED: pip-tools with hashed lockfiles |
| D5 | Ruff failures (KI-11) | DEFERRED to G3 |
| D6 | Remote and branch protection | DEFERRED |
| D7 | LICENSE | DEFERRED (KI-15) |

### G2 finalization changes

| Item | Result |
|---|---|
| `backend/requirements/{base,local,production}.in` | Created; existing version ranges kept; `pip-tools` added to `local.in` |
| `backend/requirements/{base,local,production}.txt` | Regenerated as hashed lockfiles (`pip-compile --generate-hashes`, Python 3.13). Pins equal the versions already installed; nothing upgraded |
| `backend/requirements/README.md` | Install and update procedure |
| `backend/config/settings/test.py` | SQLite override removed; tests use PostgreSQL through `DATABASE_URL` (TR-13) |
| `.github/workflows/ci.yml` | Python 3.13; quality job with hash-checked install, `pip check`, lockfile consistency check and Ruff; test job on PostgreSQL 16 and 18 |
| Docs | TR-13 APPROVED (doc 19, decision register, docs 08, 12, 13 and 20); D3 and D4 recorded in doc 07 §8 and §13; README updated |

**Assumption (CC-R67):** the supported and locked Python version is **3.13**. Hash-checked lockfiles are specific to one Python version: on Python < 3.13, `psycopg` and `referencing` need `typing-extensions`, which isn't locked. Earlier material said "3.12+".

### G2 exit checklist

| # | Criterion | Status |
|---|---|---|
| 1 | Repository inventory documented | Done |
| 2 | Approved repository structure established | Done (G2 scope) |
| 3 | Git governance established | Done except the baseline commit, which waits for the author identity (D1) |
| 4 | Development standards documented | Done |
| 5 | Local development setup documented | Done |
| 6 | Dependency-management conventions established | Done (pip-tools) |
| 7 | Testing and quality standards documented | Done |
| 8 | README consistent with the authoritative instructions | Done |
| 9 | CI/CD governance documented and validated within scope | Done locally. Not run on GitHub (D6). Ruff fails (KI-11, G3); tests fail at setup until G4 (KI-14) |
| 10 | Claude Code instructions consistent | Done |
| 11 | G2 deliverables validated | Done (local) |
| 12 | Project owner accepts G2 | **Pending** |

**doc 10 §0.1 G2 exit criterion "CI runs on the baseline":** not yet met. Exact blockers:
1. the baseline commit, which needs the author identity (D1)
2. a GitHub remote and push, which are deferred (D6)

Even once CI runs, it will report the known failures KI-11 (G3) and KI-14 (G4). The criterion says "runs", not "passes".
