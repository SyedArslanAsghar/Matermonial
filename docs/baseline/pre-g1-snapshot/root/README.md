# Matrimonial Platform — Backend Foundation

Django + Django REST Framework + PostgreSQL foundation.

## Requirements
- Python 3.12+
- PostgreSQL 15+
- WSL Ubuntu or another supported Linux environment

Docker is intentionally not required for local development.

## 1. Create and activate a virtual environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements/local.txt
```

## 2. Configure environment

```bash
cp .env.example .env
```

Update `DATABASE_URL` and `SECRET_KEY` in `.env`. Create a PostgreSQL database and role matching those settings.

Example PostgreSQL setup (run in `psql` as a PostgreSQL administrator):

```sql
CREATE USER matrimonial_app WITH PASSWORD 'replace-this-password';
CREATE DATABASE matrimonial_db OWNER matrimonial_app;
```

## 3. Create migrations and migrate

The custom User model is configured as `accounts.User` from the beginning.

```bash
python manage.py makemigrations accounts
python manage.py migrate
python manage.py createsuperuser
```

## 4. Run checks and tests

```bash
python manage.py check
pytest
ruff check .
ruff format --check .
```

## 5. Run the development server

```bash
python manage.py runserver
```

Endpoints:
- Admin: http://127.0.0.1:8000/admin/
- API root: http://127.0.0.1:8000/api/v1/
- OpenAPI schema: http://127.0.0.1:8000/api/schema/
- Swagger UI: http://127.0.0.1:8000/api/docs/

## Important implementation notes
- Phone numbers are stored in normalized E.164 format. This foundation validates the format but does not yet implement OTP delivery or phone ownership verification.
- Authentication currently uses Django's standard session/admin authentication foundation. JWT/API authentication will be implemented in the authentication milestone after the account model is verified.
- Do not use the development `SECRET_KEY` in staging or production.
- Production settings require `DJANGO_ALLOWED_HOSTS`, secure cookies, HTTPS, and a production-grade database connection.
- Never commit `.env`, credentials, real user data, or uploaded private documents.
