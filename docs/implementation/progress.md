# Progress

**Last updated:** 2026-11-18 (G2 CI criterion accepted, DR-2026-11-18-G2C)

## Governance status

| Item | Status |
|---|---|
| Documentation baseline (v4–v4.6-F3) | APPROVED (see `docs/decisions/new_architecture_decisions.md`, DR-2026-11-16) |
| G1 Documentation reconciliation | **COMPLETED. ACCEPTED by the project owner** (DR-2026-11-17-A, 2026-11-17). Final document statuses assigned (doc 20 §5). |
| G2 Repository governance | **ACCEPTED** by the project owner with carried-forward items (DR-2026-11-17-G2A). Baseline commit `38f491dea79fb9bb10fd2010b1c2cb8a68d545f9`. Exit criterion "CI runs on the baseline" (carried forward under DR-2026-11-17-G2X): **satisfied by owner acceptance** (DR-2026-11-18-G2C, 2026-11-18) on the integrated run `44294474904` on commit `c5fc346` (success, 6/6 jobs). The baseline commit `38f491d` itself did not run independently. |
| G3 Backend foundation | **ACCEPTED** by the project owner on 2026-11-18, with an accepted exception and a carried-forward item (DR-2026-11-18-G3A). Exit criterion "tests green on PostgreSQL" is **not fully met**: the PostgreSQL foundation tests pass, but the 3 KI-14 User-model database tests are **OPEN** and must pass as part of G4. The G3 changes were committed and pushed by the owner as `c5fc346` (DR-2026-11-18-GH). |
| G4 First migration | NOT STARTED. **NOT AUTHORIZED.** The G2 precondition "CI runs on the baseline" is met (DR-2026-11-18-G2C), but G4 needs its own owner authorization. KI-14 is OPEN and part of G4. Remote `origin` and the push of `c5fc346` were performed by the owner (DR-2026-11-18-GH). Claude Code performs no commit, push or remote operation without explicit authorization. |
| G5 Features | NOT STARTED. NOT AUTHORIZED. |
| Current delivery scope | **CI/CD implementation and validation** (DR-2026-11-18-CI, 2026-11-18). AWS deployment and production infrastructure are **deferred** and out of current scope. CD execution stays disabled until a target and an authorization exist. This doesn't authorize a remote, a push, a commit, G4 or a deployment. |

## Implementation status

No implementation work has been authorized or started. Doc 18 lists 126 requirements: 124 NOT_STARTED and 2 BLOCKED (FR-ACC-009 by OD-02a/b, FR-PRO-005 by OD-04a). Nothing is PLANNED or beyond.

The `backend/` scaffold predates the baseline. G3 rebuilt it into the backend foundation, which has been **executed and verified**: system checks, `check --deploy`, WSGI/ASGI loading, and the test suite on Python 3.12 and 3.13. The PostgreSQL foundation tests pass on PostgreSQL 16 and 18. It has no migrations, so the 3 KI-14 User-model database tests stay deferred to G4. GitHub Actions ran for the first time on the owner-pushed commit `c5fc346` (run `44294474904`, success, 6/6 jobs; DR-2026-11-18-GH). The owner accepted this run as satisfying the G2 prerequisite "CI runs on the baseline" (DR-2026-11-18-G2C). The baseline commit `38f491d` itself did not run independently.

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
| CI | `.github/workflows/ci.yml`: install, `pip check`, Ruff lint and format, pytest collection (G2 state; superseded by the G3 correction: Python 3.12 and 3.13, DR-2026-11-17-G3C-2) | CC-R11, CC-R60; doc 08 §11; doc 09 §13 |
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
| D1 | Local baseline commit | APPROVED; **done**: commit `38f491dea79fb9bb10fd2010b1c2cb8a68d545f9`, 113 files, author Syed Arslan Asghar |
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
| `backend/requirements/{base,local,production}.txt` | Regenerated as hashed lockfiles (`pip-compile --generate-hashes`, Python 3.13). Pins equal the versions already installed; nothing upgraded (G2 state; recompiled with Python 3.12 in the G3 correction, with no version or hash changed, DR-2026-11-17-G3C-2) |
| `backend/requirements/README.md` | Install and update procedure |
| `backend/config/settings/test.py` | SQLite override removed; tests use PostgreSQL through `DATABASE_URL` (TR-13) |
| `.github/workflows/ci.yml` | Python 3.13; quality job with hash-checked install, `pip check`, lockfile consistency check and Ruff; test job on PostgreSQL 16 and 18 (G2 state; G3 correction: Python 3.12 and 3.13, DR-2026-11-17-G3C-2) |
| Docs | TR-13 APPROVED (doc 19, decision register, docs 08, 12, 13 and 20); D3 and D4 recorded in doc 07 §8 and §13; README updated |

**Superseded (2026-11-17, DR-2026-11-17-G3C-2):** the project supports **Python 3.12 and 3.13** (`requires-python = ">=3.12,<3.14"`). The lockfiles are compiled with Python 3.12, so `typing-extensions` (needed by `psycopg` and `referencing` on Python < 3.13) is locked, and the same hashed lockfiles install on both versions. *Original G2 text, kept for history:* "Assumption (CC-R67): the supported and locked Python version is 3.13. Hash-checked lockfiles are specific to one Python version: on Python < 3.13, `psycopg` and `referencing` need `typing-extensions`, which isn't locked. Earlier material said '3.12+'."

### G2 exit checklist

| # | Criterion | Status |
|---|---|---|
| 1 | Repository inventory documented | Done |
| 2 | Approved repository structure established | Done (G2 scope) |
| 3 | Git governance established | Done (baseline commit `38f491dea79fb9bb10fd2010b1c2cb8a68d545f9`) |
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
1. ~~the baseline commit~~: done, `38f491dea79fb9bb10fd2010b1c2cb8a68d545f9`
2. a GitHub remote and push, which are deferred (D6). This is the **only** remaining blocker

Even once CI runs, it will report the known failures KI-11 (G3) and KI-14 (G4). The criterion says "runs", not "passes".

## G3 backend foundation (2026-11-17)

Authorized by DR-2026-11-17-G3 and entered under exception DR-2026-11-17-G2X. Approvals recorded before G3: TR-12; TR-09/TR-22; the `apps/` layout; the dependency list (Celery and Redis only).

| Milestone | Result |
|---|---|
| G3.1 Assessment | The scaffold's User model already matched doc 03 §2.1/§22, with a UUID primary key |
| G3.2 Settings | `base`, `local`, `test`, new `staging`, `production`. Environment variables; fail-closed validation (`common/config.py`); secure cookie and header defaults |
| G3.3 Custom User | Moved to `apps/accounts` with the app label kept as `accounts`. `created_by` / `updated_by` changed to `PROTECT` (doc 12 F4, TR-09). No field added, **no migration** |
| G3.4 PostgreSQL and API | PostgreSQL 16/18 connectivity verified. DRF foundation, `/api/v1/` routing, error envelope (doc 02 §8), pagination (doc 04 §16), liveness and readiness endpoints, OpenAPI where enabled |
| G3.5 Shared infrastructure | `common/`: request IDs, JSON logging, SMS and push provider mocks (disabled by default), Django email backends and storage settings |
| G3.6 Authentication | Session authentication with CSRF for the same-origin web client (TR-12). Mobile tokens, `__Host-` cookies, lifetimes (TR-01), ActorContext (TR-02) and admin MFA (TR-07) **not implemented**: PROPOSED, due G4 or later |
| G3.7 Celery and Redis | Celery app, `BaseTask` conventions (bounded retries, acks_late, failure logging without arguments). A worker was verified against Redis |
| G3.8 Quality and tests | Ruff clean (KI-11 resolved); lockfiles regenerated with Celery/Redis only; 56 tests pass. 3 database tests not run (KI-14, G4) |
| G3.9 Documentation | README, doc 16 §11, `.env.example`, known issues and decision records |

Lock foundations (TR-09/TR-22): `common/db/locking.py` (LockLevel order, `lock_plan` tracker, FOR UPDATE / FOR SHARE / pair advisory helpers), `common/db/retry.py` (`@retry_on_contention`), `common/db/fk_inventory.py` with its review test, and the no-raw-SQL-in-services lint test. These are not used in any business workflow.

### G3 exit (doc 10 §0.1: "Lint and tests green on PostgreSQL. No migration files.")

Final verification: 2026-11-18. Python 3.12.16 and 3.13.18 × PostgreSQL 16.16 and 18.7, in throwaway containers.

| Part | Status |
|---|---|
| Lint green | **Met.** Ruff lint and format pass on Python 3.12 and 3.13 (45 files) |
| Tests green on PostgreSQL | **Not fully met.** (a) **Foundation tests: green.** All 77 tests that don't need Django's test database pass in all four Python × PostgreSQL combinations; these include the 9 automated PostgreSQL foundation tests (DR-2026-11-17-G3C-3). (b) **The 3 User-model database tests: not green.** They are not run successfully and are not counted as passing: their setup fails with `ValueError: Dependency on app with no migrations: accounts` because there is no first migration (KI-14). Resolving that is G4 work. **Owner decision (DR-2026-11-18-G3A):** G3 accepted with this criterion not fully met (accepted exception). (b) is carried forward to G4 as an OPEN item (KI-14) |
| No migration files | **Met.** No migration file exists, and a test enforces this. No migration was applied; no `django_migrations` table or application table exists in any test database |

## G3 controlled correction (2026-11-17, DR-2026-11-17-G3C)

| Item | Result |
|---|---|
| D-1 Celery broker | Staging and production require `CELERY_BROKER_URL` or `REDIS_URL` (`common/config.py`). Errors name variables, never values. Local development unchanged. 10 new tests |
| D-2 Python 3.12 + 3.13 | `requires-python = ">=3.12,<3.14"`; Ruff target `py312`; lockfiles compiled with Python 3.12 (no version or hash changed; `typing-extensions` now locked via `psycopg` and `referencing`). Hash-checked development and production installs verified on 3.12.16 and 3.13.18. CI matrix covers both |
| G-3 PostgreSQL tests | `tests/test_postgres_foundation.py`, 9 tests: readiness, advisory locks, `lock_timeout`, contention retry. Disposable database only (`MATERMONIAL_TEST_POSTGRES_URL`; port 5432 and local sockets refused). No migration, no table |
| Document statuses | `CLAUDE.md`, doc 07, doc 08 → APPROVED (DR-2026-11-17-G3C-4; doc 20 §5) |

Test totals: 80 collected. 77 pass on PostgreSQL 16.16 and 18.7, under Python 3.12 and 3.13. The 3 User-model database tests were not run (G4, KI-14).

## G3 finalization and integrity verification (2026-11-18)

Fresh results. Python ran in throwaway `python:3.12-slim` / `python:3.13-slim` containers and PostgreSQL in throwaway `postgres:16` / `postgres:18` containers on host port 55432. The source was mounted read-only. The owner's PostgreSQL server (port 5432) and `.env` were not used.

| Check | Python 3.12.16 | Python 3.13.18 |
|---|---|---|
| Development lockfile, hash-checked install + `pip check` | Pass | Pass |
| Production lockfile, hash-checked install + `pip check` | Pass | Pass |
| Lockfile consistency (pip-compile from the committed lockfiles) | Pass | Not applicable: lockfiles are compiled on 3.12, and CI checks on 3.12 only. On 3.13 only `# via` comments differ |
| Ruff lint / format | Pass / Pass | Pass / Pass |

| Tests (each Python × PostgreSQL 16.16 and 18.7) | Result |
|---|---|
| Collected | 80 |
| Foundation step (`pytest -m "not django_db"`) | 77 passed, 0 failed, 0 skipped |
| PostgreSQL foundation tests (`-m postgres`, part of the 77) | 9 passed |
| User-model database tests (`-m django_db`) | 3 errors at setup (KI-14): **not passing, deferred to G4** |

After each PostgreSQL run: 0 application tables, no `django_migrations` table, 0 advisory locks, and no remaining client sessions or open transactions. The database step's setup created only an empty `test_matermonial_ci` database inside the throwaway container. The containers were then removed.

CI workflow: the YAML parses, with no duplicate keys; matrices are Python 3.12/3.13 × PostgreSQL 16/18; PostgreSQL is published only on host port 55432. No workflow change was needed. The workflow has not run on GitHub (KI-12, D6).

## G3 owner acceptance and CI pre-G4 preparation (2026-11-18, DR-2026-11-18-G3A)

**G3 ACCEPTED** by the project owner, with an accepted exception: "tests green on PostgreSQL" is not fully met. KI-14 is carried forward to G4 as OPEN. G4, GitHub remote and push: NOT AUTHORIZED.

CI test job before this change:
1. `pytest -m "not django_db"`. The PostgreSQL tests would silently skip if `MATERMONIAL_TEST_POSTGRES_URL` were missing.
2. `pytest -m django_db`, which always failed with 3 KI-14 setup errors, so every test job was red.

CI test job after this change:
1. A guard fails the job if `MATERMONIAL_TEST_POSTGRES_URL` is missing or empty.
2. A check that exactly the 3 known KI-14 node IDs are marked deferred.
3. `pytest -m postgres`.
4. `pytest -m "not postgres"`. The 3 KI-14 tests carry `deferred_g4_ki14` and are reported as `SKIPPED … DEFERRED to G4 (KI-14 …)`, never as passed.

Any other failure, error or collection error fails the job, and there is no `continue-on-error`. If the initial `accounts` migration exists, the run stops with an error until the marker is removed (`backend/conftest.py`).

Local verification: the workflow's own `run:` steps, parsed from `ci.yml`, were run in `bash -eo pipefail` in throwaway containers (Python 3.12.16 and 3.13.18 × PostgreSQL 16.16 and 18.7). The changes do not affect the quality job; it was re-run and passed on both Python versions (on 3.13 the lockfile check differs only in `# via` comments; CI runs that check on 3.12 only).

| Scenario | Result |
|---|---|
| Unmodified tree (all 4 combinations) | Job succeeds: 9 PostgreSQL passed; 68 passed, 3 skipped (DEFERRED) |
| `MATERMONIAL_TEST_POSTGRES_URL` empty / unset | Job fails at the guard |
| Unrelated failing test | Job fails (1 failed) |
| Non-deferred `django_db` test (unrelated database error) | Job fails (1 error) |
| Collection error | Job fails |
| A 4th test marked deferred | Job fails at the deferred-set check |
| Failing PostgreSQL foundation test | Job fails (1 failed, 8 passed) |

Not run on GitHub: no remote exists, and none is authorized.

## Owner-performed GitHub actions and first CI run (2026-11-18, DR-2026-11-18-GH)

The project owner manually:
- made commit `c5fc346` ("added first commit", on top of the baseline `38f491d`; 69 files);
- added the remote `origin` (`https://github.com/SyedArslanAsghar/Matermonial.git`, **public**);
- pushed `main`.

A content check of `c5fc346` found no `.env`, caches, virtual environment, keys or migrations.

GitHub Actions evidence, from a read-only review through the public API:

| Item | Result |
|---|---|
| Run | `44294474904`, workflow "CI", event `push`, branch `main`, commit `c5fc346` |
| Conclusion | **success**: 6/6 jobs, every step succeeded (the lockfile check is skipped on 3.13 by design) |
| Jobs | Backend quality (Python 3.12, 3.13); Backend tests (Python 3.12, 3.13 × PostgreSQL 16, 18) |
| KI-14 | Each test job carries the notice "3 tests DEFERRED to G4 (KI-14) … not run and not passed" |
| Warnings | Node.js 20 deprecation for `actions/checkout@v4` and `actions/setup-python@v5` (KI-19); `ubuntu-latest` label migration notice |
| Not reviewed | Job logs and per-test counts on GitHub (they need authentication) |
| Baseline commit `38f491d` | No workflow run exists for it |

G2 criterion "CI runs on the baseline": **OPEN**, pending the owner's decision on whether the `c5fc346` run satisfies it.

*Outcome (same day):* accepted by the owner as satisfying the criterion (Option A, DR-2026-11-18-G2C). `38f491d` did not run independently. The governance records are submitted on the branch `docs/ci-governance-acceptance` as a pull request to `main`, not merged (D2).

