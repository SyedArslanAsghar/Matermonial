# Matermonial

A privacy-conscious matrimonial platform: a Django REST API backend, a React web app and a React Native (Expo) mobile app in one monorepo.

> **Authoritative documentation.** This README is only an entry point. The project rules are in [`CLAUDE.md`](CLAUDE.md), and the specification is in [`docs/handover/`](docs/handover/) (start with [doc 00](docs/handover/00_MASTER_HANDOVER_INDEX.md)). If this README and those documents ever differ, they win.

## Project status

Work proceeds through owner-authorized gates (doc 10 §0): G1 documentation → G2 repository governance → G3 backend foundation → **G4 first migration and backend kernel** → G5 features (G4 and G5 authorized, DR-2026-11-18-G4). Current status: [`docs/implementation/progress.md`](docs/implementation/progress.md).

G5 Phases 2 and 3 are implemented and tested on `feature/g5-phase2-auth`, pending owner review. Phase 3 covers the own profile and its sections, partner preferences, and photos through the TR-10 pipeline, which needs `MALWARE_SCANNER=mock` locally. Phase 2 covers registration, phone OTP, login, logout, web sessions, mobile tokens, password reset, rate limits, AdminRole authorization and Django Admin MFA. The backend foundation (G3) and the G4 kernel are in place: the final `User` model and migrations, sessions and tokens, pseudonyms and envelope encryption, partitioned security-event and audit logs, the transactional outbox, idempotency records and the TR-24 maintenance protocol with a local compliance registry. Status and open items: [`progress.md`](docs/implementation/progress.md) and [`known_issues.md`](docs/implementation/known_issues.md).

## Repository structure

```text
backend/          Django + DRF API: config/ (settings, URLs, Celery), apps/ (domain apps), common/ (shared infrastructure), tests/
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

Prerequisites: **Python 3.12 or 3.13** (both supported and tested; `requires-python` in `backend/pyproject.toml`), Git, and PostgreSQL 15 or later. Tests run on PostgreSQL (CI checks 16 and 18). Docker is **not** needed for local development (`CLAUDE.md` CC-R21).

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
- Tests that need the database carry `@pytest.mark.django_db`; pytest-django builds the test database from the migrations. Concurrency tests use `django_db(transaction=True)` with one connection per thread (doc 12 §8). Nothing is deferred: KI-14 was resolved in G4.
- PostgreSQL foundation tests (`@pytest.mark.postgres`) cover readiness, advisory locks, `lock_timeout` and contention retry against a real server. They create no tables and run no migration. They only run when `MATERMONIAL_TEST_POSTGRES_URL` points to a **disposable** database, for example a throwaway container on a port other than 5432; otherwise they skip. They refuse port 5432 and local sockets, so they never touch a developer's own PostgreSQL server.
- Testing standards: doc 08.

### Settings and running the backend

| Settings module | Use |
|---|---|
| `config.settings.local` | Native development: `DEBUG` on, mock SMS and push, console email, API docs, Celery tasks run inline |
| `config.settings.test` | pytest, on PostgreSQL |
| `config.settings.staging`, `config.settings.production` | Deployed environments. They **fail closed**: they refuse to start with an insecure key, no allowed hosts, no `DATABASE_URL`, mock providers or a console email backend (doc 16 §7) |

- `manage.py` defaults to local settings. The WSGI, ASGI and Celery entry points default to production settings.
- Endpoints:
  - liveness: `GET /api/v1/health/`
  - readiness, which checks the database: `GET /api/v1/health/ready/`
  - OpenAPI schema and Swagger UI at `/api/schema/` and `/api/docs/`, only when `API_DOCS_ENABLED` (local by default)
- `python manage.py check --database default` validates the configuration and database connection.
- Set up a local database (never point at data you care about):

  ```bash
  python manage.py migrate                      # schema, functions, triggers, log partitions
  python manage.py createsuperuser              # break-glass admin (TR-07: at most two)
  python manage.py backfill_subject_pseudonyms  # only for accounts created outside the manager
  python manage.py runserver
  ```

- Local settings use **dev-only** encryption, HMAC and registry keys derived from a public label (`common/crypto/keys.py`). They protect nothing and staging/production refuse them (doc 16 §11). The local compliance registry writes to `backend/var/compliance_registry/` (git-ignored).
- Maintenance commands (TR-24 protocol, doc 09 §19): `ensure_log_partitions`, `drop_audit_partition`, `write_registry_checkpoint`; read-only: `verify_registry`, `print_db_grants <app_role>`.
- Celery and Redis are optional locally. To run a worker against a local Redis:

  ```bash
  DJANGO_SETTINGS_MODULE=config.settings.local CELERY_TASK_ALWAYS_EAGER=false celery -A config worker -l info
  ```

### Django Admin access (TR-07, ADR-033)

Admin access comes only from administrative roles, and every administrator, superusers included, signs in with a password **and** a TOTP code from an authenticator app. To set up a local administrator:

```bash
cd backend
python manage.py migrate
python manage.py admin_access sync-catalogue          # role definitions from apps/admin_access/catalogue.py
python manage.py createsuperuser                      # break-glass account (at most two exist)
# or a normal administrator:
python manage.py admin_access assign-role --phone +923001234567 --role system_admin
python manage.py admin_access issue-mfa-enrollment --phone +923001234567   # prints a single-use code
```

Then open `/admin/mfa/enroll/`, enter the password and the enrollment code, add the shown key to an authenticator app, and confirm with a code. Sign in at `/admin/login/`. The admin uses its own session cookie (30 min idle, 12 h absolute). If an authenticator is lost, another administrator uses the account action "Reset admin MFA", or the operator runs `python manage.py admin_access reset-mfa --phone ...`. Other subcommands: `revoke-role`, `grant-superuser`, `revoke-superuser` (with `--reason CODE`).

### Later setup steps

Frontend and mobile startup are documented as G5 delivers them.

## Git workflow and contributions

- Branch model (owner decision, doc 07 §8): `main` is the primary branch. Work on short-lived `feature/<short-name>`, `fix/<short-name>` and `hotfix/<short-name>` branches; there is no `develop` branch. Production changes are always reviewed.
- Commit messages follow Conventional Commits, for example `feat(accounts): …`, `fix(requests): …`, `docs(api): …` (doc 07 §9).
- Pull requests use [`.github/pull_request_template.md`](.github/pull_request_template.md) (doc 07 §10).
- Remote: `origin` on GitHub, set up and pushed by the owner (DR-2026-11-18-GH). Branch protection isn't set up yet. A licence is still to be chosen by the owner.

## CI/CD

- [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push and pull request, on Python 3.12 and 3.13. It uses no repository secrets and doesn't deploy. It has two jobs:
  - **quality**: hash-checked installs of the development and production lockfiles, `pip check`, a lockfile consistency check (on 3.12, the version the lockfiles are compiled with), and Ruff lint and format
  - **tests**, on each Python version × PostgreSQL 16 and 18 (TR-13), in this order:
    1. fail if `MATERMONIAL_TEST_POSTGRES_URL` is missing or empty, so the PostgreSQL tests can't silently skip
    2. check that exactly the 3 KI-14 tests are marked deferred
    3. run the PostgreSQL foundation tests
    4. run every other test; the 3 KI-14 tests are reported as skipped, DEFERRED to G4
- Any failure, error or collection error fails the job. There is no `continue-on-error`.
- **After G4 (owner action, KI-21):** step 2 checks for the 3 KI-14 tests marked deferred. G4 removed that marker because the tests now run and pass, so step 2 will fail until the workflow is updated: remove step 2 (and the KI-14 wording of step 4). CI/CD changes are made by the owner (DR-2026-11-18-G4).
- Before G4, all steps passed locally. On GitHub, the first run (commit `c5fc346`) succeeded on all 6 jobs. The owner accepted it as satisfying the G2 criterion "CI runs on the baseline" (DR-2026-11-18-G2C). The baseline commit `38f491d` itself did not run independently.
- The full pipeline, including builds, migration and schema checks, staging and production, is described in docs 08 and 09. It is delivered in later gates.

## Docker's role

Docker and Docker Compose are for production on AWS EC2 and the deployment workflow only (`CLAUDE.md` CC-R22; doc 09). There are no production containers or cloud configuration yet.

## Working with Claude Code

Claude Code follows [`CLAUDE.md`](CLAUDE.md), the authoritative entry point, and its detailed companion [doc 12](docs/handover/12_CLAUDE_CODE_INSTRUCTIONS.md). It works only within the currently authorized gate.
