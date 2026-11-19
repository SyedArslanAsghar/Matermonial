"""Apply the code catalogue (``apps.admin_access.catalogue``) to the database. Idempotent.

Entries missing from the catalogue are retired (``is_active = False``), never deleted, so
assignment history stays intact; role-permission links follow the catalogue exactly. One audit
row records the counts of every run that changed something.
"""

from django.db import transaction

from common.db.locking import LockLevel, lock_plan

from .. import catalogue as spec
from ..models import AdminPermission, AdminRole, AdminRolePermission, AdminUserRole
from .roles import Actor, _lock_target, audit, refresh_staff_projection, revoke_admin_sessions


def _upsert(model, code: str, values: dict) -> bool:
    obj, created = model.objects.get_or_create(code=code, defaults=values)
    if created:
        return True
    changed = {k: v for k, v in values.items() if getattr(obj, k) != v}
    if changed:
        for key, value in changed.items():
            setattr(obj, key, value)
        obj.save()
    return bool(changed)


def sync_catalogue(actor: Actor) -> int:
    counts = {"permissions": 0, "roles": 0, "links_added": 0, "links_removed": 0, "retired": 0}
    with transaction.atomic():
        for p in spec.PERMISSIONS:
            values = {
                "name": p.name,
                "description": p.description,
                "is_sensitive": p.is_sensitive,
                "is_active": True,
            }
            counts["permissions"] += _upsert(AdminPermission, p.code, values)
        counts["retired"] += (
            AdminPermission.objects.exclude(code__in=[p.code for p in spec.PERMISSIONS])
            .filter(is_active=True)
            .update(is_active=False)
        )

        for r in spec.ROLES:
            values = {"name": r.name, "description": r.description, "is_active": True}
            counts["roles"] += _upsert(AdminRole, r.code, values)
            role = AdminRole.objects.get(code=r.code)
            wanted = set(
                AdminPermission.objects.filter(code__in=r.permissions).values_list("pk", flat=True)
            )
            have = set(
                AdminRolePermission.objects.filter(role=role).values_list(
                    "permission_id", flat=True
                )
            )
            for pk in wanted - have:
                AdminRolePermission.objects.create(role=role, permission_id=pk)
            counts["links_added"] += len(wanted - have)
            counts["links_removed"] += AdminRolePermission.objects.filter(
                role=role, permission_id__in=have - wanted
            ).delete()[0]
        retired_roles = AdminRole.objects.exclude(code__in=[r.code for r in spec.ROLES]).filter(
            is_active=True
        )
        retired_ids = list(retired_roles.values_list("pk", flat=True))
        counts["retired"] += retired_roles.update(is_active=False)

        # Holders of a retired role may have lost all access: recompute their projection.
        holders = AdminUserRole.objects.filter(role_id__in=retired_ids, revoked_at__isnull=True)
        for user_id in sorted(set(holders.values_list("user_id", flat=True))):
            with lock_plan("admin_access.catalogue", [LockLevel.ACCOUNT]):
                user = _lock_target(user_id)
                if not refresh_staff_projection(user.pk):
                    revoke_admin_sessions(user, actor)

        total = sum(counts.values())
        if total:
            audit(
                actor,
                "admin.catalogue_sync",
                "SUCCESS",
                target_id=None,
                resource="admin_access.admin_role",
                **counts,
            )
    return total
