"""Write the daily signed Stream R checkpoint into Stream M (REGISTRY_CHECKPOINT)."""

from django.core.management.base import BaseCommand

from apps.platform_ops.services.maintenance import write_checkpoint


class Command(BaseCommand):
    help = "Write the Stream R checkpoint (idempotent per day and head)."

    def handle(self, *args, **options):
        op = write_checkpoint()
        self.stdout.write(f"Checkpoint {op.status}.")
