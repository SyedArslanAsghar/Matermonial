# Matermonial — Repository Structure and Development Standards

**Version:** 1.0 (G1 revision 2026-11-16)  
**Date:** 11 November 2026  
**Document status:** APPROVED (project owner, 2026-11-17, DR-2026-11-17-G3C-4; record in doc 20 §5). Previously APPROVED_WITH_OPEN_ITEMS (DR-2026-11-17-A); its open items (TR-09, TR-22) have all been approved.  
**Applied corrections:** DCR-10, DCR-18, DCR-42 (doc 20)

## 1. Repository strategy

Use a monorepo so the backend, web frontend, mobile applications, documentation, scripts, and CI/CD workflows remain coordinated.

Recommended repository:

```text
matermonial/
│
├── backend/
│   ├── config/
│   ├── apps/
│   ├── common/
│   ├── tests/
│   ├── requirements/
│   ├── manage.py
│   ├── pyproject.toml
│   └── .env.example
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── lib/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── stores/
│   │   ├── styles/
│   │   ├── types/
│   │   └── utils/
│   ├── package.json
│   ├── tsconfig.json
│   └── .env.example
│
├── mobile/
│   ├── app/
│   ├── assets/
│   ├── src/
│   │   ├── components/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── navigation/
│   │   ├── services/
│   │   ├── stores/
│   │   ├── theme/
│   │   ├── types/
│   │   └── utils/
│   ├── app.json
│   ├── package.json
│   └── .env.example
│
├── docs/
│   ├── handover/
│   │   ├── 00_MASTER_HANDOVER_INDEX.md
│   │   ├── 01_COMPLETE_SRS.md
│   │   ├── 02_SYSTEM_ARCHITECTURE.md
│   │   ├── 03_DATABASE_DESIGN.md
│   │   ├── 04_API_AND_INTEGRATIONS.md
│   │   ├── 05_BUSINESS_RULES_AND_WORKFLOWS.md
│   │   ├── 06_SECURITY_PRIVACY_AUTHORIZATION.md
│   │   ├── 07_REPOSITORY_AND_DEVELOPMENT_STANDARDS.md
│   │   ├── 08_TESTING_AND_QA.md
│   │   ├── 09_AWS_DEPLOYMENT_AND_CICD.md
│   │   ├── 10_IMPLEMENTATION_ROADMAP.md
│   │   ├── 11_ARCHITECTURE_DECISIONS.md
│   │   ├── 12_CLAUDE_CODE_INSTRUCTIONS.md
│   │   ├── 13_ASSUMPTIONS_RISKS_TRACEABILITY.md
│   │   ├── 14_FAMILY_MANAGER_PERMISSION_MATRIX.md
│   │   ├── 15_STATE_MACHINES.md
│   │   ├── 16_ENVIRONMENT_CONFIGURATION.md
│   │   ├── 17_GLOSSARY.md
│   │   ├── 18_REQUIREMENTS_TRACEABILITY_MATRIX.md
│   │   ├── 19_OPEN_DECISION_REGISTER.md
│   │   └── 20_DOCUMENTATION_CORRECTION_REGISTER.md
│   ├── baseline/
│   │   ├── v4.6-F3/            # approved specification baseline (read-only)
│   │   └── pre-g1-snapshot/    # rollback copy until Git history exists (G2)
│   ├── decisions/              # decision records and new ADRs (ADR-025 onwards)
│   └── implementation/         # progress.md, completed_features.md, pending_features.md, known_issues.md
│
├── scripts/
│   ├── development/
│   ├── deployment/
│   └── maintenance/
│
├── infrastructure/
│   ├── docker/
│   ├── nginx/
│   └── aws/
│
├── .github/
│   └── workflows/
│
├── CLAUDE.md
├── .gitignore
├── README.md
└── LICENSE
```

This is the target structure, not a requirement to create every empty directory immediately.

**Approved layout (owner decision DR-2026-11-17-G3-3, 2026-11-17):** domain applications under `backend/apps/`, shared infrastructure under `backend/common/`; the existing `accounts` app moves to `backend/apps/accounts` (its app label stays `accounts`).

## 2. Backend Django settings

Use:

```text
backend/config/settings/
├── __init__.py
├── base.py
├── local.py
├── test.py
├── staging.py
└── production.py
```

`base.py` contains shared configuration.

Environment-specific files override only what is necessary.

Do not duplicate the entire settings configuration across environments.

## 3. Django application structure

Recommended pattern:

```text
apps/<domain>/
├── apps.py
├── models/
├── api/
│   ├── serializers/
│   ├── views/
│   ├── permissions.py
│   └── urls.py
├── services/
├── selectors/
├── tasks.py
├── admin.py
├── constants.py
├── exceptions.py
├── tests/
└── migrations/
```

Use simple structures where appropriate. Do not create unnecessary abstractions for small modules.

## 4. Backend coding standards

- Follow PEP 8.
- Use Ruff for linting and formatting.
- Use meaningful names.
- Add type hints to service interfaces and complex functions.
- Keep views thin.
- Keep serializers focused on input/output validation.
- Keep business logic in services.
- Keep read queries in selectors.
- Avoid circular imports.
- Avoid large model methods containing cross-module workflows.
- Avoid using signals for critical business operations.
- Use transactions explicitly.
- Use `select_for_update()` for relevant concurrency-sensitive operations, following the global lock-order policy and the per-service lock plans in doc 12 §5 (G1, DCR-42) [TR-09, TR-22].
- Use database constraints in addition to Python validation.
- Never swallow exceptions silently.
- Use structured logging.
- Do not expose internal exceptions to API clients.
- Avoid unnecessary generic frameworks and abstractions.

## 5. Frontend standards

Use React, Vite, and TypeScript.

Requirements:

- Enable TypeScript strict mode.
- Use ESLint and Prettier.
- Organize screens and components by feature.
- Use a centralized API client.
- Centralize authentication state.
- Define API response types.
- Avoid `any` unless justified.
- Keep server state separate from UI state.
- Validate forms on the client for usability and on the backend for security.
- Implement loading, empty, error, and success states.
- Support responsive layouts.
- Support English and Urdu.
- Support RTL direction for Urdu.
- Never treat hidden UI elements as security controls.

## 6. Mobile standards

Use React Native and Expo.

Requirements:

- Use typed API services.
- Store sensitive credentials in secure platform storage.
- Support access-token expiry and session renewal.
- Register and revoke push devices.
- Support deep links only with server-side authorization.
- Provide loading/error/offline states.
- Avoid duplicating backend business rules in mobile code.
- Keep localization and RTL behavior consistent with web.
- Do not hardcode API URLs or secrets.

## 7. Naming conventions

### Python

- Modules and functions: `snake_case`.
- Classes: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- Boolean fields: meaningful `is_`, `has_`, `can_`, or `allow_` prefixes.

### Database

Use clear singular model names and consistent field names.

Prefer explicit fields such as:

- `created_at`
- `updated_at`
- `is_active`
- `expires_at`
- `revoked_at`

### API

Use plural resource names and consistent nested paths.

### Frontend

- Components: `PascalCase`.
- Hooks: `useSomething`.
- Utility functions: `camelCase`.
- Feature folders: consistent naming.

## 8. Git workflow

Recommended branches:

- `main`: production-ready code.
- `develop`: integration branch if the team uses it.
- `feature/<short-name>`: new features.
- `fix/<short-name>`: bug fixes.
- `hotfix/<short-name>`: urgent production fixes.

For a small team, a simpler branch model is acceptable, but production changes must still be reviewed.

**Adopted branch model (owner decision DR-2026-11-17-G2D-3, 2026-11-17):** `main` is the primary branch. Work happens on short-lived `feature/<short-name>`, `fix/<short-name>` and `hotfix/<short-name>` branches. No permanent `develop` branch is used.

## 9. Commit conventions

Use clear commit messages, preferably Conventional Commits:

```text
feat(accounts): implement phone registration
feat(profiles): add profile completion service
fix(requests): prevent duplicate active requests
test(credits): cover concurrent credit deductions
docs(api): update request endpoint specification
refactor(matching): extract profile eligibility selector
```

Do not use vague messages such as `update`, `changes`, or `final`.

## 10. Pull request standards

Every pull request should include:

- Purpose.
- Scope.
- Related requirements.
- Database migration impact.
- API changes.
- Authorization impact.
- Security/privacy impact.
- Tests added or updated.
- Manual verification steps.
- Screenshots where relevant.
- Known limitations.

A reviewer must check for secrets, unsafe permissions, missing tests, migration risks, and business-rule regressions.

## 11. Environment variables

Provide `.env.example` files containing names and safe placeholders only.

Never commit actual secrets.

Example backend configuration categories:

```text
DJANGO_SECRET_KEY=
DJANGO_DEBUG=
DJANGO_ALLOWED_HOSTS=
DATABASE_URL=
REDIS_URL=
CELERY_BROKER_URL=
EMAIL_PROVIDER=
SMS_PROVIDER=
PAYMENT_PROVIDER=
STORAGE_BACKEND=
AWS_REGION=
AWS_STORAGE_BUCKET=
JAZZCASH_MERCHANT_ID=
JAZZCASH_PASSWORD=
JAZZCASH_INTEGRITY_SALT=
```

Do not assume all providers are enabled in every environment.

## 12. Local development

Docker is not mandatory locally.

The README must document:

1. Supported Python version.
2. Virtual environment setup.
3. Dependency installation.
4. Local PostgreSQL configuration.
5. Database migration.
6. Superuser creation.
7. Local media storage.
8. Mock email/SMS/payment configuration.
9. Optional Redis/Celery setup.
10. Backend startup.
11. Frontend startup.
12. Mobile startup.
13. Running tests.
14. Generating API documentation.

## 13. Backend dependencies

Keep dependencies controlled and documented.

Separate runtime and development/test dependencies where practical.

Pin compatible versions using a reproducible dependency-management approach.

Avoid unnecessary dependencies.

**Adopted method (owner decision DR-2026-11-17-G2D-4, 2026-11-17):** pip-tools. Inputs are `backend/requirements/*.in`; hashed lockfiles (`*.txt`) are generated with `pip-compile --generate-hashes`. Runtime and development/production dependencies stay separate. The procedure is in `backend/requirements/README.md`.

## 14. Frontend and mobile dependencies

Use lockfiles and reproducible installation commands.

Do not commit `node_modules`, build outputs, or generated secrets.

## 15. Migration standards

- Commit migrations with the code change.
- Test migrations from an empty database.
- Test upgrade paths for important schema changes.
- Avoid destructive migrations without a data migration plan.
- Use data migrations for required transformations.
- Never edit an already-applied production migration casually.
- Document rollback limitations.
- Use appropriate database constraints.

## 16. API standards

- All public API endpoints use `/api/v1/`.
- Every endpoint has OpenAPI documentation.
- Use standard HTTP status codes.
- Use consistent error response structure.
- Use pagination for collections.
- Validate filters and sorting.
- Enforce authorization at the backend.
- Avoid leaking private fields.
- Maintain backward compatibility within an API version where practical.

## 17. Logging standards

Use structured logs.

Include:

- Request/correlation ID.
- Actor ID where safe.
- Module.
- Operation.
- Result.
- Error classification.
- Timestamp.

Redact secrets and sensitive personal information.

Do not log passwords, OTPs, tokens, private document contents, or full payment credentials.

## 18. Definition of Done

A feature is complete only when:

- Requirements are mapped.
- Models and migrations are complete.
- Business rules are implemented.
- Authorization is enforced.
- API behavior is documented.
- Errors are standardized.
- Audit/history requirements are met.
- Tests pass.
- Linting passes.
- No sensitive data is leaked.
- Documentation is updated.
- Code review is completed.

## 19. Development rules for Claude Code

Claude Code must:

1. Inspect existing code before editing.
2. Respect the repository's established conventions.
3. Avoid replacing existing working functionality without justification.
4. Implement only the agreed stage.
5. Explain migration impact.
6. Add tests for every business operation.
7. Run relevant tests after changes.
8. Report commands and results accurately.
9. Never claim tests passed without running them.
10. Never invent credentials or production configuration.
11. Ask before destructive operations.
12. Update documentation as implementation changes.

## 20. Local development versus deployment

Local development uses a native environment.

Production deployment on AWS EC2 uses Docker and Docker Compose.

Do not make local developers depend on production container infrastructure unless they explicitly choose to use it.