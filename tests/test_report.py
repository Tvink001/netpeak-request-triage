from __future__ import annotations

from typing import Any

from triage.models import Category, Confidence, ExtractedRequest, Language, Priority
from triage.pipeline import RunResult, RunStats
from triage.report import _related_clusters, count_by, render_report


def _rec(**overrides: Any) -> ExtractedRequest:
    base: dict[str, Any] = {
        "id": "X",
        "channel": "Slack",
        "category": Category.AUTOMATION,
        "target_department": "Marketing",
        "priority": Priority.MEDIUM,
        "short_summary": "s",
        "requested_actions": [],
        "needs_clarification": False,
        "language": Language.UK,
        "confidence": Confidence.HIGH,
        "secondary_category": None,
        "is_actionable": True,
    }
    base.update(overrides)
    return ExtractedRequest(**base)


def _result(results: list[ExtractedRequest]) -> RunResult:
    stats = RunStats(
        model="claude-haiku-4-5",
        total=len(results),
        fallbacks=sum(1 for r in results if r.error is not None),
        api_calls=len(results),
        input_tokens=100,
        output_tokens=20,
        estimated_cost_usd=0.0002,
    )
    return RunResult(stats=stats, results=results)


def test_count_by_buckets_null_department() -> None:
    recs = [
        _rec(target_department="Marketing"),
        _rec(target_department=None),
        _rec(target_department=None),
    ]
    counts = count_by(recs, lambda r: r.target_department or "(unrouted)")
    assert counts["Marketing"] == 1
    assert counts["(unrouted)"] == 2


def test_related_clusters_group_same_department() -> None:
    recs = [
        _rec(id="REQ-001", target_department="Marketing"),
        _rec(id="REQ-013", target_department="Marketing"),
        _rec(id="REQ-009", target_department="HR"),
    ]
    clusters = _related_clusters(recs)
    assert len(clusters) == 1
    department, members = clusters[0]
    assert department == "Marketing"
    assert {m.id for m in members} == {"REQ-001", "REQ-013"}


def test_render_report_has_expected_sections() -> None:
    md = render_report(_result([_rec(needs_clarification=True, is_actionable=False)]))
    assert "# Request triage report" in md
    assert "## By category" in md
    assert "## By priority" in md
    assert "## Needs clarification (1)" in md
    assert "## Not actionable (1)" in md
