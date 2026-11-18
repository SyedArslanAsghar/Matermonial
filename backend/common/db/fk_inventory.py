"""Implicit foreign-key lock inventory (doc 12 §5.5; TR-22, approved).

Rule: every foreign key in a project app must be assigned an implicit-lock class at design
review. An unclassified foreign key fails the test suite (tests/test_architecture_rules.py).

Classes (doc 12 §5.5, inventory from baseline v4.5 §6.1):
- P  prior-locked: the transaction already holds FOR SHARE or stronger on the referenced row
- S  soft reference: no database FK, no implicit lock
- B1 counterparty profile in a protective action (bounded wait)
- B2 staff actor User (bounded wait)
- N  the transaction holds no other locks when the FK check runs
"""

from django.apps import apps

LOCK_CLASSES = frozenset({"P", "S", "B1", "B2", "N"})

# "<app_label>.<Model>.<field>": class
FK_LOCK_CLASSES: dict[str, str] = {
    # doc 12 §5.5 class B2: created_by/updated_by where the actor is staff, including the
    # User.updated_by self-FK.
    "accounts.User.created_by": "B2",
    "accounts.User.updated_by": "B2",
}


def project_foreign_keys() -> list[str]:
    """Every concrete FK/OneToOne declared by models in project apps (``apps.*``)."""
    found = []
    for model in apps.get_models():
        if not model._meta.app_config.name.startswith("apps."):
            continue
        for field in model._meta.get_fields():
            if field.concrete and (field.many_to_one or field.one_to_one):
                found.append(f"{model._meta.app_label}.{model.__name__}.{field.name}")
    return sorted(found)


def unclassified_foreign_keys() -> list[str]:
    return [fk for fk in project_foreign_keys() if fk not in FK_LOCK_CLASSES]
