from __future__ import annotations

from triage.models import (
    BOOKKEEPING_FIELDS,
    IDENTITY_FIELDS,
    MODEL_CATEGORIES,
    Category,
    Confidence,
    ExtractedRequest,
    Language,
    Priority,
)
from triage.schema import EXTRACTION_PROPERTIES, EXTRACTION_SCHEMA


def test_schema_covers_exactly_the_model_facing_fields() -> None:
    model_facing = {
        name
        for name in ExtractedRequest.model_fields
        if name not in IDENTITY_FIELDS + BOOKKEEPING_FIELDS
    }
    assert set(EXTRACTION_PROPERTIES) == model_facing
    assert EXTRACTION_SCHEMA["required"] == list(EXTRACTION_PROPERTIES)
    assert EXTRACTION_SCHEMA["additionalProperties"] is False


def test_schema_enums_match_python_enums() -> None:
    assert EXTRACTION_PROPERTIES["category"]["enum"] == [c.value for c in MODEL_CATEGORIES]
    assert EXTRACTION_PROPERTIES["priority"]["enum"] == [p.value for p in Priority]
    assert EXTRACTION_PROPERTIES["language"]["enum"] == [lang.value for lang in Language]
    assert EXTRACTION_PROPERTIES["confidence"]["enum"] == [c.value for c in Confidence]


def test_sentinel_category_is_never_offered_to_the_model() -> None:
    assert Category.UNPROCESSED.value not in EXTRACTION_PROPERTIES["category"]["enum"]
    assert Category.UNPROCESSED.value not in EXTRACTION_PROPERTIES["secondary_category"]["enum"]
