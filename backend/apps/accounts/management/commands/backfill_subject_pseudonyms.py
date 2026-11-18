"""Create missing account pseudonyms and data keys (TR-23; doc 03 §22.2: "Staff accounts are
backfilled once at G4"). Idempotent: accounts that already have a pseudonym are skipped."""

from django.core.management.base import BaseCommand

from apps.accounts.models import SubjectPseudonym, User
from apps.accounts.services.pseudonyms import create_subject


class Command(BaseCommand):
    help = "Create the pseudonym and data key for every account that lacks one."

    def handle(self, *args, **options):
        linked = SubjectPseudonym.objects.filter(subject_type="ACCOUNT").values("subject_id")
        missing = User.objects.exclude(id__in=linked).values_list("id", flat=True)
        created = 0
        for user_id in missing.iterator():
            create_subject("ACCOUNT", user_id)
            created += 1
        self.stdout.write(f"Backfilled {created} account pseudonym(s).")
