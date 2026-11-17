# Known Issues

**Last updated:** 2026-11-17 (G2)

Issues in the existing repository scaffold, found during the specification assessment. None has been fixed; fixes belong to the gate shown.

| # | Issue | Gate |
|---|---|---|
| KI-1 | The existing `backend/` code has never been executed or tested in this environment (risk R-1). | G2/G3 |
| KI-2 | Local Git repository initialized on `main` in G2. The single local baseline commit is approved (DR-2026-11-17-G2D-1) but **waiting for the owner's author identity**. Until it exists, `docs/baseline/pre-g1-snapshot/` remains the rollback copy. | G2 |
| KI-3 | **Resolved in G2:** the stale root `.venv` (pip only) was removed and the environment recreated in `backend/.venv` with `requirements/local.txt` (doc 10 §0.1). | — |
| KI-4 | **Resolved in G2:** `test.py` no longer overrides the database with SQLite; tests use PostgreSQL through `DATABASE_URL` (TR-13 approved, DR-2026-11-17-G2D-2). | — |
| KI-5 | `CSRF_COOKIE_HTTPONLY = True` in `base.py` conflicts with the proposed readable `__Host-mat_csrf` cookie (TR-01). | G3 |
| KI-6 | Throttle rates are configured without throttle classes. | G3 |
| KI-7 | The OpenAPI schema and docs endpoints are public in every environment. | G3 |
| KI-8 | `wsgi.py`, `asgi.py` and `manage.py` default to local settings. | G3 |
| KI-9 | `accounts/migrations/` contains no migrations; the `User` model isn't final (G4). | G4 |
| KI-10 | **Resolved in G2:** root `README.md` rewritten as an entry point to the authoritative documentation (DR-2026-11-16-P3). | — |
| KI-11 | The pre-baseline scaffold fails Ruff: 9 lint findings (4 import-order I001; F403/F405 from `from .base import *` in settings) and 2 files that need reformatting (`accounts/admin.py`, `manage.py`). The CI quality job fails on Ruff until fixed. **Deferred to G3** (owner decision DR-2026-11-17-G2D-5). | G3 |
| KI-12 | CI (`.github/workflows/ci.yml`) is validated locally only: YAML parse, every quality step, lockfile consistency, and Django connectivity to PostgreSQL 16 and 18 in containers matching the CI services. It has **not run on GitHub**: no remote or push is authorized (DR-2026-11-17-G2D-6). | Owner decision (remote) |
| KI-13 | **Resolved in G2:** pip-tools hashed lockfiles (DR-2026-11-17-G2D-4); procedure in `backend/requirements/README.md`. | — |
| KI-14 | The existing scaffold tests can't run on any database: `ValueError: Dependency on app with no migrations: accounts`. Django's admin and auth migrations depend on the custom `accounts.User`, which has no migration. Reproduced on PostgreSQL 16 and 18. The fix is the first migration, which belongs to **G4** (doc 10 §0.1). Until then the CI test job fails at test-database setup. | G4 |
| KI-15 | No `LICENSE` file. The owner chooses a licence before public distribution or when otherwise required (DR-2026-11-17-G2D-7). | Owner decision |
