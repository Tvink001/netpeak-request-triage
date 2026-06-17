from __future__ import annotations

import json
from pathlib import Path

import pytest

from triage.config import Settings
from triage.models import (
    Category,
    Confidence,
    ExtractedRequest,
    InputRequest,
    Language,
    Priority,
)
from triage.pipeline import run
from triage.report import write_outputs


class _FakeExtractor:
    """Stands in for RequestExtractor so the pipeline runs without the API."""

    def __init__(self, settings: object) -> None:
        self.input_tokens = 10
        self.output_tokens = 5
        self.api_calls = 0

    def extract(self, request: InputRequest) -> ExtractedRequest:
        self.api_calls += 1
        return ExtractedRequest(
            id=request.id,
            channel=request.channel,
            category=Category.AUTOMATION,
            target_department="Marketing",
            priority=Priority.MEDIUM,
            short_summary="підсумок запиту",
            requested_actions=["зробити"],
            needs_clarification=False,
            language=Language.UK,
            confidence=Confidence.HIGH,
            secondary_category=None,
            is_actionable=True,
        )


def _csv(tmp_path: Path) -> Path:
    path = tmp_path / "in.csv"
    path.write_text(
        "id,channel,timestamp,raw_text\n"
        "REQ-001,Slack,2026-06-08 09:14,Привіт автоматизувати звіт\n"
        "REQ-002,Telegram,2026-06-08 09:31,треба бот\n",
        encoding="utf-8",
    )
    return path


def test_run_and_write_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("triage.pipeline.RequestExtractor", _FakeExtractor)
    result = run(Settings(), _csv(tmp_path))
    assert result.stats.total == 2
    assert result.stats.fallbacks == 0

    json_path, report_path = write_outputs(result, tmp_path / "out")
    records = json.loads(json_path.read_text(encoding="utf-8"))
    assert [r["id"] for r in records] == ["REQ-001", "REQ-002"]
    # Cyrillic stored readably, not as \uXXXX escapes.
    assert records[0]["category"] == "автоматизація"
    assert "автоматизація" in report_path.read_text(encoding="utf-8")


def test_run_respects_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("triage.pipeline.RequestExtractor", _FakeExtractor)
    result = run(Settings(), _csv(tmp_path), limit=1)
    assert result.stats.total == 1
