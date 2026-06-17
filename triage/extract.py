"""Call Claude Haiku 4.5 to extract the triage schema, with fail-soft validation."""

from __future__ import annotations

import json
import logging

import anthropic
from anthropic.types import Message, MessageParam
from anthropic.types.output_config_param import OutputConfigParam
from pydantic import ValidationError

from triage.config import Settings
from triage.models import ExtractedRequest, InputRequest
from triage.prompts import SYSTEM_PROMPT, user_message
from triage.schema import EXTRACTION_SCHEMA

logger = logging.getLogger(__name__)


class RequestExtractor:
    """Thin wrapper over Anthropic Messages with structured output + fail-soft.

    ``extract`` never raises on a single request: any API, parse, or validation
    failure becomes an :meth:`ExtractedRequest.fallback` record, so the batch
    always completes and every input row appears in the output.
    """

    def __init__(self, settings: Settings) -> None:
        self._client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key.get_secret_value(),
            max_retries=4,
        )
        self._model = settings.anthropic_model
        self._max_tokens = settings.anthropic_max_tokens
        # Cumulative usage across the run (read by the pipeline for the cost line).
        self.input_tokens = 0
        self.output_tokens = 0
        self.api_calls = 0

    def extract(self, request: InputRequest) -> ExtractedRequest:
        messages: list[MessageParam] = [{"role": "user", "content": user_message(request)}]
        config: OutputConfigParam = {"format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA}}
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=0.0,
                system=SYSTEM_PROMPT,
                messages=messages,
                output_config=config,
            )
        except anthropic.APIError as exc:
            return self._fail(request, f"api_error: {type(exc).__name__}: {exc}")
        except Exception as exc:  # never let one row abort the batch
            return self._fail(request, f"unexpected_error: {type(exc).__name__}: {exc}")

        self._record_usage(response)
        return self._parse(request, response)

    def _parse(self, request: InputRequest, response: Message) -> ExtractedRequest:
        # Structured outputs can still return HTTP 200 with non-conforming output:
        # stop_reason "refusal" -> empty content; "max_tokens" -> truncated JSON.
        if response.stop_reason != "end_turn":
            return self._fail(request, f"stop_reason={response.stop_reason}")
        if not response.content:
            return self._fail(request, "empty_content")
        text = getattr(response.content[0], "text", None)
        if not text:
            return self._fail(request, "no_text_block")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            return self._fail(request, f"json_decode_error: {exc}")
        if not isinstance(data, dict):
            return self._fail(request, f"not_an_object: {type(data).__name__}")
        try:
            return ExtractedRequest.model_validate(
                {**data, "id": request.id, "channel": request.channel}
            )
        except ValidationError as exc:
            return self._fail(request, f"validation_error: {exc.error_count()} error(s)")

    def _record_usage(self, response: Message) -> None:
        self.input_tokens += response.usage.input_tokens
        self.output_tokens += response.usage.output_tokens
        self.api_calls += 1

    def _fail(self, request: InputRequest, reason: str) -> ExtractedRequest:
        logger.warning("Fallback for %s: %s", request.id, reason)
        return ExtractedRequest.fallback(id=request.id, channel=request.channel, error=reason)
