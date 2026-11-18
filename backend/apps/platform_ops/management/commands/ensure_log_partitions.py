"""Create missing current/future log partitions through the maintenance protocol (TR-24)."""

from django.core.management.base import BaseCommand

from apps.platform_ops.services.maintenance import ensure_log_partitions


class Command(BaseCommand):
    help = "Create missing log partitions (PARTITION_CREATE operations)."

    def handle(self, *args, **options):
        created = ensure_log_partitions()
        self.stdout.write(f"Created {len(created)} partition(s): {', '.join(created) or '-'}")
