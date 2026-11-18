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
    # TR-01 lock order (doc 06 §22.1 amendment): login, refresh, logout and revocation take
    # the account's User FOR SHARE first, and refresh locks AuthSession before AuthToken.
    "accounts.AuthSession.user": "P",
    "accounts.AuthToken.session": "P",
    # TR-23: a data key is created in the same transaction as its pseudonym, and key
    # destruction runs inside the deletion step that already locks the subject.
    "accounts.SubjectDataKey.pseudonym": "P",
    # The idempotent operation runs inside a service that has already locked the account
    # (doc 12 §5: account level 2 precedes inserts).
    "idempotency.IdempotencyRecord.account": "P",
    # Maintenance lock domain (doc 09 §19.2): the operation row is locked first; the approver
    # is a staff actor (class B2, bounded wait).
    "platform_ops.MaintenanceApproval.operation": "P",
    "platform_ops.MaintenanceApproval.approver": "B2",
    # OTP verify locks the account (level 2) before the verification row; send runs with no
    # other business locks.
    "verification.PhoneVerification.user": "P",
}


def project_foreign_keys() -> list[str]:
    """Every concrete FK/OneToOne declared by models in project apps (``apps.*``, ``common.*``)."""
    found = []
    for model in apps.get_models():
        if not model._meta.app_config.name.startswith(("apps.", "common.")):
            continue
        for field in model._meta.get_fields():
            if field.concrete and (field.many_to_one or field.one_to_one):
                found.append(f"{model._meta.app_label}.{model.__name__}.{field.name}")
    return sorted(found)


def unclassified_foreign_keys() -> list[str]:
    return [fk for fk in project_foreign_keys() if fk not in FK_LOCK_CLASSES]
