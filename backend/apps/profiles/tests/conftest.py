"""Profile test fixtures. Production seeds every proposal INACTIVE; tests activate the neutral
proposals so the sections can be exercised. Sensitive vocabularies stay empty unless a test
configures stand-in codes. Owner-activated lists (``reference.OWNER_ACTIVATED``) keep exactly the
state the migrations give them, so tests exercise the production values (KI-37)."""

import pytest

from apps.profiles import reference
from apps.profiles.models import VocabularyOption


def activate(vocabulary: str, *codes: str) -> None:
    for order, code in enumerate(codes):
        VocabularyOption.objects.update_or_create(
            vocabulary=vocabulary,
            code=code,
            defaults={"label_en": code.title(), "sort_order": order, "is_active": True},
        )


@pytest.fixture(autouse=True)
def neutral_vocabularies(db):
    for vocabulary, codes in reference.PROPOSED.items():
        if not reference.VOCABULARIES[vocabulary] and vocabulary not in reference.OWNER_ACTIVATED:
            activate(vocabulary, *codes)
