# Matermonial

A privacy-conscious matrimonial platform: a Django REST API backend, a React web app and a React Native (Expo) mobile app in one monorepo.

> **Authoritative documentation.** This README is only an entry point. The project rules are in [`CLAUDE.md`](CLAUDE.md), and the specification is in [`docs/handover/`](docs/handover/) (start with [doc 00](docs/handover/00_MASTER_HANDOVER_INDEX.md)). If this README and those documents ever differ, they win.

## Project status

Work proceeds through owner-authorized gates (doc 10 §0): G1 documentation → **G2 repository governance** → G3 backend foundation → G4 first migration → G5 features. Current status: [`docs/implementation/progress.md`](docs/implementation/progress.md).

There are no product features yet. The code under `backend/` is an early scaffold that predates the approved baseline; it is reworked in G3 (see [`known_issues.md`](docs/implementation/known_issues.md)). **Don't run migrations**: the first migration belongs to G4.

## Repository structure

```text
backend/          Django + DRF API (scaffold; reorganized into apps/ and common/ in G3)
frontend/         React + Vite + TypeScript web app (placeholder until G5 Phase 17)
mobile/           React Native + Expo app (placeholder until G5 Phase 18)
infrastructure/   Production deployment files (placeholder; AWS EC2 + Docker)
scripts/          Development, deployment and maintenance scripts (placeholder)
docs/handover/    Approved specification documents 00–20
docs/baseline/    Read-only approved baseline (v4.6-F3) and the pre-G1 snapshot
docs/decisions/   Decision records and ADR-025 onwards
docs/implementation/  Progress, pending and completed features, known issues
.github/          CI workflow and pull request template
```

The target layout is in doc 07 §1. Directories are created only when their gate needs them.

## Technology stack

Approved stack (`CLAUDE.md` §3): Python, Django, Django REST Framework, PostgreSQL, Celery, Redis, drf-spectacular, pytest + pytest-django, Ruff; React, Vite, TypeScript, Vitest, ESLint, Prettier; React Native + Expo; AWS EC2, Docker, Docker Compose, GitHub Actions; JazzCash.

## Local development (native, no Docker required)

Prerequisites: **Python 3.13** (the dependency lockfiles are compiled for it, and CI uses it), Git, and PostgreSQL 15 or later. Tests run on PostgreSQL (CI checks 16 and 18). Docker is **not** needed for local development (`CLAUDE.md` CC-R21).

### Backend environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements/local.txt
pip check
```

Dependencies are locked with **pip-tools**. The `*.in` files are the inputs; the `*.txt` files are hashed lockfiles generated with `pip-compile`. There are three sets:
- `base`: runtime dependencies
- `local`: runtime plus development and test tools
- `production`: runtime plus the production server

To add or update a dependency and regenerate the lockfiles, follow [`backend/requirements/README.md`](backend/requirements/README.md).

### Configuration and secrets

- Copy `backend/.env.example` to `backend/.env` and fill in local values. The example contains names and safe placeholders only.
- `.env` files are never committed (`.gitignore`). The root `.env` is owner-managed: don't read, copy or edit it.
- Configuration names and handling rules: doc 16. Never commit credentials, tokens, keys, real user data or private documents (doc 07 §11, doc 16 §8).

### Formatting, linting and tests

```bash
cd backend
ruff check .            # lint
ruff format --check .   # formatting check (use `ruff format .` to apply)
pytest                  # tests
```

- Ruff and pytest settings are in `backend/pyproject.toml`.
- Tests run on PostgreSQL (TR-13; `CLAUDE.md` CC-R58). Set `DATABASE_URL` in `backend/.env` to a local database role that may create databases; pytest-django creates and drops its own `test_…` database.
- Known limitations ([`known_issues.md`](docs/implementation/known_issues.md)):
  - the existing scaffold fails Ruff until G3 (KI-11)
  - its tests can't run until the first migration exists in G4 (KI-14)
- Testing standards: doc 08.

### Later setup steps

These are documented as their gates are delivered:
- PostgreSQL configuration and backend startup (G3)
- migrations and superuser creation (G4)
- local media and mock providers, optional Redis/Celery, and API docs (G3 onwards)
- frontend and mobile startup (G5)

## Git workflow and contributions

- Branch model (owner decision, doc 07 §8): `main` is the primary branch. Work on short-lived `feature/<short-name>`, `fix/<short-name>` and `hotfix/<short-name>` branches; there is no `develop` branch. Production changes are always reviewed.
- Commit messages follow Conventional Commits, for example `feat(accounts): …`, `fix(requests): …`, `docs(api): …` (doc 07 §9).
- Pull requests use [`.github/pull_request_template.md`](.github/pull_request_template.md) (doc 07 §10).
- No remote repository, push or branch protection is set up yet. Each needs separate owner authorization. A licence is still to be chosen by the owner.

## CI/CD

- [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push and pull request, on Python 3.13. It uses no repository secrets and doesn't deploy. It has two jobs:
  - **quality**: hash-checked install, `pip check`, a lockfile consistency check, and Ruff lint and format
  - **tests**: `pytest` on PostgreSQL 16 and 18 (TR-13)
- Both jobs are expected to fail until the known issues KI-11 (G3) and KI-14 (G4) are resolved.
- The full pipeline, including builds, migration and schema checks, staging and production, is described in docs 08 and 09. It is delivered in later gates.

## Docker's role

Docker and Docker Compose are for production on AWS EC2 and the deployment workflow only (`CLAUDE.md` CC-R22; doc 09). There are no production containers or cloud configuration yet.

## Working with Claude Code

Claude Code follows [`CLAUDE.md`](CLAUDE.md), the authoritative entry point, and its detailed companion [doc 12](docs/handover/12_CLAUDE_CODE_INSTRUCTIONS.md). It works only within the currently authorized gate.
