"""Operator commands for administrative access (TR-07). Shell access to the server is itself
privileged, so these run as the CLI operator (audit ``channel=cli``, actor SYSTEM).

    manage.py admin_access sync-catalogue
    manage.py admin_access assign-role --phone +92... --role system_admin [--expires-days N]
    manage.py admin_access revoke-role --phone +92... --role system_admin
    manage.py admin_access grant-superuser --phone +92... --reason INCIDENT_123
    manage.py admin_access revoke-superuser --phone +92... --reason INCIDENT_123
    manage.py admin_access issue-mfa-enrollment --phone +92...
    manage.py admin_access reset-mfa --phone +92...

Enrollment codes are printed once to this terminal and never logged.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.managers import normalize_phone_number
from apps.accounts.models import User
from apps.admin_access.services import catalogue, mfa, roles, superusers

REASON = r"^[A-Z0-9_]{3,40}$"


class Command(BaseCommand):
    help = "Manage administrative roles, break-glass superusers and admin MFA."

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="action", required=True)
        sub.add_parser("sync-catalogue")
        for name in ("assign-role", "revoke-role"):
            p = sub.add_parser(name)
            p.add_argument("--phone", required=True)
            p.add_argument("--role", required=True)
            if name == "assign-role":
                p.add_argument("--expires-days", type=int)
        for name in ("grant-superuser", "revoke-superuser"):
            p = sub.add_parser(name)
            p.add_argument("--phone", required=True)
            p.add_argument("--reason", required=True, help="Code such as INCIDENT_2026_11_19")
        for name in ("issue-mfa-enrollment", "reset-mfa"):
            sub.add_parser(name).add_argument("--phone", required=True)

    def _user(self, phone) -> User:
        try:
            return User.objects.get(phone_number=normalize_phone_number(phone))
        except Exception:
            raise CommandError("No such account.") from None

    def handle(self, *args, action, **opts):
        import re

        try:
            if action == "sync-catalogue":
                changes = catalogue.sync_catalogue(roles.CLI)
                self.stdout.write(f"Catalogue synchronised ({changes} change(s)).")
                return
            user = self._user(opts["phone"])
            if action == "assign-role":
                days = opts.get("expires_days")
                expires = timezone.now() + timedelta(days=days) if days else None
                roles.assign_role(roles.CLI, user, opts["role"], expires_at=expires)
            elif action == "revoke-role":
                roles.revoke_role(roles.CLI, user, opts["role"])
            elif action in ("grant-superuser", "revoke-superuser"):
                if not re.fullmatch(REASON, opts["reason"]):
                    raise CommandError("--reason must be an upper-case code (A-Z, 0-9, _).")
                operation = (
                    superusers.grant_superuser
                    if action == "grant-superuser"
                    else superusers.revoke_superuser
                )
                operation(roles.CLI, user, reason_code=opts["reason"])
            elif action == "issue-mfa-enrollment":
                self.stdout.write(
                    f"Enrollment code (single use): {mfa.issue_enrollment(roles.CLI, user)}"
                )
            elif action == "reset-mfa":
                code = mfa.reset_mfa(roles.CLI, user)
                self.stdout.write("MFA reset; admin sessions ended.")
                if code:
                    self.stdout.write(f"Enrollment code (single use): {code}")
        except roles.AdminAccessError as exc:
            raise CommandError(str(exc) or exc.code) from None
        self.stdout.write("Done.")
