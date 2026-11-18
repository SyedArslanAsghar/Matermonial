"""Repository rules enforced as tests.

- Migrations are in sync with the models (G4 decision D-7; replaces the G3 "no migration files"
  guard). The check writes nothing.
- Lint rule (doc 12 §5.6, TR-22): no raw(), extra() or cursor.execute in service modules.
- FK review rule (doc 12 §5.5, TR-22): every project FK has an implicit-lock class.
- Project apps live in apps/ (DR-2026-11-17-G3-3).
"""

import ast
from io import StringIO
from pathlib import Path

import pytest
from django.apps import apps
from django.core.management import call_command

from common.db.fk_inventory import (
    FK_LOCK_CLASSES,
    LOCK_CLASSES,
    project_foreign_keys,
    unclassified_foreign_keys,
)

BACKEND = Path(__file__).resolve().parent.parent
FORBIDDEN_IN_SERVICES = {"raw", "extra", "execute", "cursor"}


def forbidden_calls(source: str) -> list[str]:
    """Names of forbidden raw-SQL calls in a service module's source."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in FORBIDDEN_IN_SERVICES:
                found.append(f"{node.func.attr} (line {node.lineno})")
    return found


@pytest.mark.django_db
def test_migrations_are_in_sync_with_models():
    out = StringIO()
    try:
        call_command("makemigrations", "--check", "--dry-run", stdout=out, stderr=out)
    except SystemExit as exc:  # --check exits non-zero when a migration is missing
        raise AssertionError(f"Models and migrations differ:\n{out.getvalue()}") from exc


def test_lint_rule_detects_raw_sql():
    sample = "def f(qs, connection):\n    qs.raw('x')\n    connection.cursor().execute('y')\n"
    assert {name.split()[0] for name in forbidden_calls(sample)} == {"raw", "cursor", "execute"}


def test_service_modules_contain_no_raw_sql():
    offenders = {}
    for path in (BACKEND / "apps").glob("*/services/**/*.py"):
        calls = forbidden_calls(path.read_text(encoding="utf-8"))
        if calls:
            offenders[str(path.relative_to(BACKEND))] = calls
    assert offenders == {}, "Use common.db.locking helpers instead of raw SQL in services"


def test_every_project_foreign_key_has_a_lock_class():
    assert unclassified_foreign_keys() == []
    assert set(FK_LOCK_CLASSES.values()) <= LOCK_CLASSES
    assert set(FK_LOCK_CLASSES) <= set(project_foreign_keys()), "stale inventory entries"


def test_project_apps_live_under_apps_package():
    def is_project_app(config) -> bool:
        path = Path(config.path)
        return path.is_relative_to(BACKEND) and path.relative_to(BACKEND).parts[0] != ".venv"

    project = [c for c in apps.get_app_configs() if is_project_app(c)]
    assert {c.name for c in project} == {"apps.accounts"}
    assert apps.get_app_config("accounts").name == "apps.accounts"


def project_models():
    """Concrete models declared in project apps (apps.* and common.*), excluding M2M links."""
    return [
        m for m in apps.get_models() if m._meta.app_config.name.startswith(("apps.", "common."))
    ]


def test_project_models_use_uuid_primary_keys():
    """CC-R32: UUID primary keys for domain entities (G4 decision package)."""
    offenders = [
        f"{m._meta.label}.{m._meta.pk.name}: {m._meta.pk.get_internal_type()}"
        for m in project_models()
        if m._meta.pk.get_internal_type() != "UUIDField"
    ]
    assert offenders == []
