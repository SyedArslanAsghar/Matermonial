# Owner-approved employment-status options (KI-37; owner instruction of 2026-11-20, §2).
#
# Data only: no schema change. Options stay admin-managed (label, order, activation editable and
# audited in the Django Admin); codes are permanent. The 0004 proposal NOT_EMPLOYED is not part
# of the approved list and stays inactive (rows are never deleted). "Prefer not to say" is not an
# employment status. No Urdu labels were approved, so label_ur is left for administrators.

from django.db import migrations

APPROVED = [
    ("EMPLOYED", "Employed"),
    ("SELF_EMPLOYED", "Self-employed"),
    ("BUSINESS_OWNER", "Business owner"),
    ("UNEMPLOYED", "Unemployed"),
    ("STUDENT", "Student"),
    ("RETIRED", "Retired"),
    ("HOMEMAKER", "Homemaker"),
    ("OTHER", "Other"),
]


def activate(apps, schema_editor):
    Option = apps.get_model("profiles", "VocabularyOption")
    for order, (code, label) in enumerate(APPROVED):
        Option.objects.update_or_create(
            vocabulary="employment_status",
            code=code,
            defaults={"label_en": label, "sort_order": order * 10, "is_active": True},
        )


def deactivate(apps, schema_editor):
    # Reverse: deactivate only (the guard trigger forbids deleting options).
    Option = apps.get_model("profiles", "VocabularyOption")
    Option.objects.filter(
        vocabulary="employment_status", code__in=[code for code, _ in APPROVED]
    ).update(is_active=False)


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0005_approved_vocabularies_and_privacy_choices"),
    ]

    operations = [migrations.RunPython(activate, deactivate)]
