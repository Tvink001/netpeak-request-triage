from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import anthropic
import httpx

from triage.config import Settings
from triage.extract import RequestExtractor
from triage.models import Category, InputRequest, Priority

_VALID_JSON = (
    '{"category": "автоматизація", "target_department": "Marketing", '
    '"priority": "medium", "short_summary": "summary", '
    '"requested_actions": ["a"], "needs_clarification": false, '
    '"language": "uk", "confidence": "high", "secondary_category": null, '
    '"is_actionable": true}'
)


def _request(text: str = "автоматизувати щотижневий звіт") -> InputRequest:
    return InputRequest(id="REQ-001", channel="Slack", timestamp="2026-06-08 09:14", raw_text=text)


def _usage(inp: int = 100, out: int = 20) -> SimpleNamespace:
    return SimpleNamespace(input_tokens=inp, output_tokens=out)


def _response(stop_reason: str, text: str | None) -> SimpleNamespace:
    content = [SimpleNamespace(type="text", text=text)] if text is not None else []
    return SimpleNamespace(stop_reason=stop_reason, content=content, usage=_usage())


def _extractor(create: Any) -> RequestExtractor:
    extractor = RequestExtractor(Settings())
    extractor._client = SimpleNamespace(messages=SimpleNamespace(create=create))
    return extractor


def test_happy_path_parses_and_sends_expected_args() -> None:
    create = MagicMock(return_value=_response("end_turn", _VALID_JSON))
    extractor = _extractor(create)

    result = extractor.extract(_request())

    assert result.category is Category.AUTOMATION
    assert result.priority is Priority.MEDIUM
    assert result.target_department == "Marketing"
    assert result.id == "REQ-001"
    assert result.error is None
    assert (extractor.input_tokens, extractor.output_tokens, extractor.api_calls) == (100, 20, 1)

    kwargs = create.call_args.kwargs
    assert kwargs["model"] == "claude-haiku-4-5"
    assert kwargs["temperature"] == 0.0
    assert kwargs["max_tokens"] == 1024
    assert kwargs["output_config"]["format"]["type"] == "json_schema"


def test_refusal_falls_soft() -> None:
    result = _extractor(MagicMock(return_value=_response("refusal", None))).extract(_request())
    assert result.category is Category.UNPROCESSED
    assert result.needs_clarification is True
    assert "stop_reason=refusal" in (result.error or "")


def test_max_tokens_truncation_falls_soft() -> None:
    create = MagicMock(return_value=_response("max_tokens", '{"category": "автомат'))
    result = _extractor(create).extract(_request())
    assert result.category is Category.UNPROCESSED
    assert "stop_reason=max_tokens" in (result.error or "")


def test_invalid_json_on_end_turn_falls_soft() -> None:
    create = MagicMock(return_value=_response("end_turn", '{"category": "автомат'))
    result = _extractor(create).extract(_request())
    assert result.category is Category.UNPROCESSED
    assert "json_decode_error" in (result.error or "")


def test_non_object_json_falls_soft() -> None:
    create = MagicMock(return_value=_response("end_turn", '["not", "an", "object"]'))
    result = _extractor(create).extract(_request())
    assert result.category is Category.UNPROCESSED
    assert "not_an_object" in (result.error or "")


def test_api_error_falls_soft() -> None:
    error = anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.anthropic.com"))
    result = _extractor(MagicMock(side_effect=error)).extract(_request())
    assert result.category is Category.UNPROCESSED
    assert "api_error" in (result.error or "")
