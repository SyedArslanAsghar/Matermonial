"""Verify the compliance registry and the local maintenance log chains (read-only)."""

from django.core.management.base import BaseCommand

from apps.platform_ops.services.maintenance import verify_local_chain, verify_registry


class Command(BaseCommand):
    help = "Verify Stream R and Stream M chains locally and in the registry."

    def handle(self, *args, **options):
        for stream in ("R", "M"):
            local, remote = verify_local_chain(stream), verify_registry(stream)
            self.stdout.write(
                f"Stream {stream}: local {local} entries, registry {remote} entries OK"
            )
