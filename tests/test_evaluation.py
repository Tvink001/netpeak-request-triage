from __future__ import annotations

from typing import Any

from triage.evaluation import score


def test_accept_set_and_exact_scoring() -> None:
    records: dict[str, dict[str, Any]] = {
        "REQ-005": {
            "id": "REQ-005",
            "category": "звіт/аналітика",
            "priority": "high",
            "is_actionable": True,
        },
        # is_actionable is wrong here (thank-you should be False).
        "REQ-008": {
            "id": "REQ-008",
            "category": "поза скоупом",
            "priority": "low",
            "is_actionable": True,
        },
    }
    golden = [
        {
            "id": "REQ-005",
            "category": ["звіт/аналітика", "автоматизація"],
            "priority": ["high"],
            "is_actionable": True,
        },
        {"id": "REQ-008", "category": ["поза скоупом"], "is_actionable": False},
    ]

    report = score(records, golden)
    by_field = {s.name: s for s in report.scores}

    assert report.scored_rows == 2
    assert (by_field["category"].correct, by_field["category"].total) == (2, 2)
    assert (by_field["is_actionable"].correct, by_field["is_actionable"].total) == (1, 2)
    assert any("REQ-008" in miss for miss in report.misses)


def test_missing_record_is_skipped() -> None:
    golden = [{"id": "REQ-999", "category": ["автоматизація"]}]
    report = score({}, golden)
    assert report.scored_rows == 0
