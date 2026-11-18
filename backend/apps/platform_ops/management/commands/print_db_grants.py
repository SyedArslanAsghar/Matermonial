"""Print the application-role GRANT statements (D-11; read-only, applies nothing)."""

from django.core.management.base import BaseCommand

from common.db.grants import application_grants


class Command(BaseCommand):
    help = "Print the privilege statements for the application database role."

    def add_arguments(self, parser):
        parser.add_argument("app_role")

    def handle(self, *args, app_role, **options):
        for statement in application_grants(app_role):
            self.stdout.write(statement + ";")
