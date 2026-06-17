from __future__ import annotations

from triage.models import (
    MODEL_CATEGORIES,
    Category,
    Confidence,
    ExtractedRequest,
    Priority,
)


def test_model_categories_excludes_sentinel() -> None:
    assert Category.UNPROCESSED not in MODEL_CATEGORIES
    assert len(MODEL_CATEGORIES) == 6


def test_fallback_is_valid_and_flagged() -> None:
    rec = ExtractedRequest.fallback(id="REQ-001", channel="Slack", error="boom")
    assert rec.id == "REQ-001"
    assert rec.channel == "Slack"
    assert rec.category is Category.UNPROCESSED
    assert rec.priority is Priority.LOW
    assert rec.confidence is Confidence.LOW
    assert rec.needs_clarification is True
    assert rec.is_actionable is False
    assert rec.error == "boom"
    assert "boom" in rec.short_summary
    # The fallback record must itself be valid - no fallback-of-the-fallback.
    ExtractedRequest.model_validate(rec.model_dump())
