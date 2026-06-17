from __future__ import annotations

from pathlib import Path

import pytest

from triage import cli
from triage.models import (
    Category,
    Confidence,
    ExtractedRequest,
    InputRequest,
    Language,
    Priority,
)


class _FakeExtractor:
    def __init__(self, settings: object) -> None:
        self.input_tokens = 1
        self.output_tokens = 1
        self.api_calls = 0

    def extract(self, request: InputRequest) -> ExtractedRequest:
        self.api_calls += 1
        return ExtractedRequest(
            id=request.id,
            channel=request.channel,
            category=Category.QUESTION_CONSULTATION,
            target_department=None,
            priority=Priority.LOW,
            short_summary="питання",
            requested_actions=[],
            needs_clarification=True,
            language=Language.UK,
            confidence=Confidence.LOW,
            secondary_category=None,
            is_actionable=False,
        )


def _csv(tmp_path: Path) -> Path:
    path = tmp_path / "in.csv"
    path.write_text(
        "id,channel,timestamp,raw_text\nREQ-001,Slack,2026-06-08 09:14,треба бот\n",
        encoding="utf-8",
    )
    return path


def test_dry_run_returns_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([str(_csv(tmp_path)), "--dry-run"]) == 0
    assert "would process 1" in capsys.readouterr().out


def test_missing_file_returns_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["does-not-exist.csv", "--dry-run"]) == 2


def test_full_run_writes_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("triage.pipeline.RequestExtractor", _FakeExtractor)
    out_dir = tmp_path / "out"
    assert cli.main([str(_csv(tmp_path)), "--output-dir", str(out_dir)]) == 0
    assert (out_dir / "output.json").exists()
    assert (out_dir / "report.md").exists()
    assert "Done:" in capsys.readouterr().out
