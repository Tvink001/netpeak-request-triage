"""Orchestrate the triage run: read CSV -> extract each row -> collect results."""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel

from triage.config import Settings
from triage.extract import RequestExtractor
from triage.inbox import read_requests
from triage.models import ExtractedRequest

logger = logging.getLogger(__name__)

# Claude Haiku 4.5 list price, USD per million tokens. Verify on the console;
# overridable here because pricing changes faster than this code.
HAIKU_INPUT_USD_PER_MTOK = 1.0
HAIKU_OUTPUT_USD_PER_MTOK = 5.0


class RunStats(BaseModel):
    model: str
    total: int
    fallbacks: int
    api_calls: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float


class RunResult(BaseModel):
    stats: RunStats
    results: list[ExtractedRequest]


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return round(
        input_tokens / 1_000_000 * HAIKU_INPUT_USD_PER_MTOK
        + output_tokens / 1_000_000 * HAIKU_OUTPUT_USD_PER_MTOK,
        4,
    )


def run(settings: Settings, csv_path: str | Path, *, limit: int | None = None) -> RunResult:
    """Read the inbox, classify every row, and collect the validated results."""
    requests = read_requests(csv_path)
    if limit is not None:
        requests = requests[:limit]

    extractor = RequestExtractor(settings)
    results: list[ExtractedRequest] = []
    for index, request in enumerate(requests, start=1):
        result = extractor.extract(request)
        results.append(result)
        logger.info(
            "(%d/%d) %s -> %s / %s",
            index,
            len(requests),
            request.id,
            result.category.value,
            result.priority.value,
        )

    stats = RunStats(
        model=settings.anthropic_model,
        total=len(results),
        fallbacks=sum(1 for r in results if r.error is not None),
        api_calls=extractor.api_calls,
        input_tokens=extractor.input_tokens,
        output_tokens=extractor.output_tokens,
        estimated_cost_usd=estimate_cost_usd(extractor.input_tokens, extractor.output_tokens),
    )
    return RunResult(stats=stats, results=results)
