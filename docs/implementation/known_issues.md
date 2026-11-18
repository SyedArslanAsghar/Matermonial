# Known Issues

**Last updated:** 2026-11-18 (G3 finalization)

Issues in the existing repository scaffold, found during the specification assessment. None has been fixed; fixes belong to the gate shown.

| # | Issue | Gate |
|---|---|---|
| KI-1 | **Resolved in G3:** the backend has now been executed and verified: system checks, `check --deploy`, WSGI/ASGI loading, 56 tests, and PostgreSQL 16/18 connectivity. The 3 database tests wait for KI-14. | — |
| KI-2 | **Resolved in G2:** local Git repository on `main` with the single baseline commit `38f491dea79fb9bb10fd2010b1c2cb8a68d545f9` (2026-11-17; author Syed Arslan Asghar; DR-2026-11-17-G2D-1). No remote and no push (D6 deferred). | — |
| KI-3 | **Resolved in G2:** the stale root `.venv` (pip only) was removed and the environment recreated in `backend/.venv` with `requirements/local.txt` (doc 10 §0.1). | — |
| KI-4 | **Resolved in G2:** `test.py` no longer overrides the database with SQLite; tests use PostgreSQL through `DATABASE_URL` (TR-13 approved, DR-2026-11-17-G2D-2). | — |
| KI-5 | **Resolved in G3:** `CSRF_COOKIE_HTTPONLY = False` so the same-origin client (TR-12) can read the CSRF token; the session cookie stays HttpOnly. `__Host-` cookie names remain TR-01 (G4). | — |
| KI-6 | **Resolved in G3:** the unenforced global throttle rates were removed. Rate limits are added per sensitive endpoint with their features (CC-R49; doc 06). | — |
| KI-7 | **Resolved in G3:** the OpenAPI schema and docs are served only when `API_DOCS_ENABLED` (local and test by default; off in staging and production). | — |
| KI-8 | **Resolved in G3:** the WSGI, ASGI and Celery entry points default to production settings, which fail closed. `manage.py` stays local. | — |
| KI-9 | `accounts/migrations/` contains no migrations; the `User` model isn't final (G4). | G4 |
| KI-10 | **Resolved in G2:** root `README.md` rewritten as an entry point to the authoritative documentation (DR-2026-11-16-P3). | — |
| KI-11 | **Resolved in G3:** Ruff lint and format pass on the whole backend (import order fixed; the settings star imports are marked `noqa: F403`; `accounts/admin.py` and `manage.py` reformatted). | — |
| KI-12 | **Open; partly resolved (2026-11-18).** *Resolved:* the Python-compatibility part. The workflow tests Python 3.12 and 3.13 (DR-2026-11-17-G3C-2), and on 2026-11-18 its commands were re-run locally in throwaway containers (Python 3.12.16 and 3.13.18; PostgreSQL 16.16 and 18.7). Results: hash-checked development and production installs, `pip check`, the lockfile consistency check (3.12), Ruff lint and format, and the foundation step (77 passed, including the 9 PostgreSQL foundation tests). The workflow file parses as YAML with no duplicate keys, and PostgreSQL is published only on host port 55432. *Still open:* (1) CI has never run on GitHub; there is no remote (D6). **The G2 exit criterion "CI runs on the baseline" stays OPEN and must be met before G4** (DR-2026-11-17-G2X). (2) ~~The "Database tests" step fails until G4 (3 errors, KI-14), so every `backend-tests` job reports failure even though the foundation step passes.~~ **Resolved in the workflow (2026-11-18, DR-2026-11-18-G3A):**
- a guard now fails the job if `MATERMONIAL_TEST_POSTGRES_URL` is missing;
- exactly the 3 KI-14 tests are reported as skipped, DEFERRED to G4, never as passed;
- any other failure, database error or collection error still fails the job.

This was verified locally only (`progress.md`). *History:* G2 validated Python 3.13 only; the 3.12 + 3.13 matrix came with the G3 correction. | Before G4 |
| KI-13 | **Resolved in G2:** pip-tools hashed lockfiles (DR-2026-11-17-G2D-4); procedure in `backend/requirements/README.md`. | — |
| KI-14 | Anything that builds Django's migration graph fails with `ValueError: Dependency on app with no migrations: accounts`: the built-in admin and auth migrations depend on the custom `accounts.User`, which has no migration. Affected: the 3 database tests (pytest-django's automatic test-database setup) and `manage.py runserver` (its migration pre-check). Not affected: system checks, `check --deploy`, WSGI/ASGI, Celery, and the 56 tests that don't need the database. Fix: the first migration, **G4**. In G3 the database tests were deliberately not run, because their setup would run `migrate`. **OPEN; carried forward to G4 by the owner's G3 acceptance (DR-2026-11-18-G3A-2).** The 3 tests must pass as part of G4:
- `apps/accounts/tests/test_user_model.py::test_create_user_stores_e164_phone_and_hashed_password`
- `apps/accounts/tests/test_user_model.py::test_create_user_without_password_gets_unusable_password`
- `apps/accounts/tests/test_user_model.py::test_invalid_phone_format_is_rejected`

Until then they carry `@pytest.mark.deferred_g4_ki14` and are reported as skipped (DEFERRED), never as passed. When the migration is added, remove the marker; the test run stops with an error until it is removed. | G4 |
| KI-15 | No `LICENSE` file. The owner chooses a licence before public distribution or when otherwise required (DR-2026-11-17-G2D-7). | Owner decision |
| KI-16 | `apps/accounts/admin.py` still shows Django `groups` and `user_permissions`. TR-07 (single admin-authorization source, admin MFA with `django-otp`) replaces this at G4. | G4 (TR-07) |
| KI-17 | Only local private file storage exists. A production object-storage backend needs a separately approved dependency (DR-2026-11-17-G3-4), and deployed settings refuse any other `STORAGE_BACKEND`. | Owner decision |
| KI-18 | No payment-provider interface yet. Its contract depends on JazzCash decisions (doc 13 OD-001/003); it is added in G5 Phase 13. | G5 Phase 13 |
