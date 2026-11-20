"""Operator commands for administrative access (TR-07). Shell access to the server is itself
privileged, so these run as the CLI operator (audit ``channel=cli``, actor SYSTEM).

    manage.py admin_access sync-catalogue
    manage.py admin_access assign-role --phone +92... --role system_admin [--expires-days N]
    manage.py admin_access revoke-role --phone +92... --role system_admin
    manage.py admin_access grant-superuser --phone +92... --reason INCIDENT_123
    manage.py admin_access revoke-superuser --phone +92... --reason INCIDENT_123
    manage.py admin_access issue-mfa-enrollment --phone +92...      (first enrollment only)
    manage.py admin_access emergency-mfa-recovery --phone +92... --emergency --reason CODE

No enrollment code is ever printed. First-enrollment codes (KI-39) and emergency-recovery codes
(ADR-033 Amendment 1, A1-4) go only by SMS to the account holder's verified phone. For emergency
recovery, the account holder and every superuser are also notified.
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
        sub.add_parser("issue-mfa-enrollment").add_argument("--phone", required=True)
        p = sub.add_parser("emergency-mfa-recovery")
        p.add_argument("--phone", required=True)
        p.add_argument(
            "--emergency", action="store_true", help="Required: confirms break-glass use"
        )
        p.add_argument("--reason", required=True, help="Code such as INCIDENT_2026_11_19")

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
                if not mfa.issue_enrollment(roles.CLI, user):
                    raise CommandError(
                        "SMS delivery failed: the enrollment code was revoked and not revealed. "
                        "Retry when SMS works."
                    )
                self.stdout.write("The enrollment code was sent by SMS to the account holder.")
            elif action == "emergency-mfa-recovery":
                if not opts["emergency"]:
                    raise CommandError("Emergency recovery needs --emergency (break-glass only).")
                if not re.fullmatch(REASON, opts["reason"]):
                    raise CommandError("--reason must be an upper-case code (A-Z, 0-9, _).")
                from apps.admin_access.services.recovery import emergency_recovery

                delivered = emergency_recovery(user, opts["reason"])
                self.stdout.write("Emergency recovery done: authenticator removed, sessions ended.")
                if not delivered:
                    raise CommandError(
                        "SMS delivery failed: the replacement code was revoked and not revealed. "
                        "Retry when SMS works."
                    )
                self.stdout.write("The replacement code was sent by SMS to the account holder.")
        except roles.AdminAccessError as exc:
            raise CommandError(str(exc) or exc.code) from None
        self.stdout.write("Done.")
