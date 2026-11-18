"""Drop a past audit_log partition, keeping held events (PARTITION_DROP; TR-23 / TR-24)."""

from datetime import datetime

from django.core.management.base import BaseCommand

from apps.platform_ops.services.maintenance import drop_audit_partition


class Command(BaseCommand):
    help = "Drop a past audit_log partition through the maintenance protocol."

    def add_arguments(self, parser):
        parser.add_argument("partition")
        parser.add_argument("--retain-until", type=datetime.fromisoformat, default=None)

    def handle(self, *args, partition, retain_until, **options):
        moved = drop_audit_partition(partition, retain_until)
        self.stdout.write(f"Dropped {partition}; {moved} held event(s) kept.")
