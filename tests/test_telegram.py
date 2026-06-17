from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from triage.config import Settings
from triage.models import Category, Confidence, ExtractedRequest, Language, Priority
from triage.pipeline import RunResult, RunStats
from triage.telegram import build_digest, send_digest


def _result() -> RunResult:
    rec = ExtractedRequest(
        id="REQ-001",
        channel="Slack",
        category=Category.AUTOMATION,
        target_department="Marketing",
        priority=Priority.HIGH,
        short_summary="s",
        requested_actions=[],
        needs_clarification=True,
        language=Language.UK,
        confidence=Confidence.HIGH,
        secondary_category=None,
        is_actionable=True,
    )
    stats = RunStats(
        model="claude-haiku-4-5",
        total=1,
        fallbacks=0,
        api_calls=1,
        input_tokens=100,
        output_tokens=20,
        estimated_cost_usd=0.0002,
    )
    return RunResult(stats=stats, results=[rec])


def test_build_digest_contains_counts_and_fits_limit() -> None:
    text = build_digest(_result())
    assert "<b>Request triage</b>" in text
    assert "автоматизація" in text
    assert "Needs clarification: 1" in text
    assert len(text) <= 4096


def test_send_digest_skips_when_not_configured() -> None:
    assert send_digest(Settings(), _result()) is False


def test_send_digest_posts_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    captured: dict[str, Any] = {}

    def fake_post(url: str, json: dict[str, Any], timeout: float) -> MagicMock:
        captured["url"] = url
        captured["json"] = json
        return MagicMock(raise_for_status=lambda: None)

    monkeypatch.setattr("triage.telegram.httpx.post", fake_post)

    assert send_digest(Settings(), _result()) is True
    assert "/bot123:abc/sendMessage" in captured["url"]
    assert captured["json"]["chat_id"] == 42
    assert captured["json"]["parse_mode"] == "HTML"


def test_send_digest_swallows_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")

    def fake_post(url: str, json: dict[str, Any], timeout: float) -> httpx.Response:
        return httpx.Response(
            400,
            json={"ok": False, "description": "Bad Request: chat not found"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("triage.telegram.httpx.post", fake_post)

    # A 400 is swallowed (returns False), never raised.
    assert send_digest(Settings(), _result()) is False
