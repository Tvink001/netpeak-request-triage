"""Score a produced ``output.json`` against a small hand-labeled golden set.

Runs offline against an existing ``output.json`` (no extra API calls). Ambiguous
rows are labeled with an accept-set rather than a single value, so a defensible
disagreement does not count as wrong. Usage::

    python -m triage <csv>              # produce output/output.json
    python -m triage.evaluation         # score it against test-data/golden.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from triage.console import force_utf8_stdio

DEFAULT_OUTPUT = "output/output.json"
DEFAULT_GOLDEN = "test-data/golden.jsonl"

# Fields whose label is an accept-set (correct if the value is any member).
_SET_FIELDS = ("category", "priority")
# Fields whose label is a single value (correct on exact match).
_EXACT_FIELDS = ("is_actionable",)


@dataclass
class FieldScore:
    name: str
    correct: int
    total: int

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


@dataclass
class EvalReport:
    scores: list[FieldScore]
    misses: list[str]
    scored_rows: int


def load_golden(path: str | Path) -> list[dict[str, Any]]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def score(records_by_id: dict[str, dict[str, Any]], golden: list[dict[str, Any]]) -> EvalReport:
    tally: dict[str, list[int]] = {name: [0, 0] for name in (*_SET_FIELDS, *_EXACT_FIELDS)}
    misses: list[str] = []
    scored = 0
    for label in golden:
        record = records_by_id.get(label["id"])
        if record is None:
            continue
        scored += 1
        for name in _SET_FIELDS:
            if name in label:
                tally[name][1] += 1
                actual = record.get(name)
                if actual in label[name]:
                    tally[name][0] += 1
                else:
                    misses.append(f"{label['id']} {name}={actual!r} not in {label[name]}")
        for name in _EXACT_FIELDS:
            if name in label:
                tally[name][1] += 1
                actual = record.get(name)
                if actual == label[name]:
                    tally[name][0] += 1
                else:
                    misses.append(f"{label['id']} {name}={actual!r} expected {label[name]!r}")
    scores = [FieldScore(name, correct, total) for name, (correct, total) in tally.items()]
    return EvalReport(scores=scores, misses=misses, scored_rows=scored)


def render(report: EvalReport) -> str:
    lines = [f"Scored {report.scored_rows} labeled rows.", ""]
    for field_score in report.scores:
        if field_score.total:
            lines.append(
                f"  {field_score.name:16} "
                f"{field_score.correct}/{field_score.total} = {field_score.accuracy:.0%}"
            )
    if report.misses:
        lines += ["", "Misses:"]
        lines += [f"  - {miss}" for miss in report.misses]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog="triage.evaluation", description="Score output.json against a golden set."
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help=f"default: {DEFAULT_OUTPUT}")
    parser.add_argument("--golden", default=DEFAULT_GOLDEN, help=f"default: {DEFAULT_GOLDEN}")
    args = parser.parse_args(argv)

    output_path = Path(args.output)
    if not output_path.exists():
        print(
            f"error: {output_path} not found — run `python -m triage <csv>` first.",
            file=sys.stderr,
        )
        return 2

    records = json.loads(output_path.read_text(encoding="utf-8"))
    records_by_id = {r["id"]: r for r in records}
    report = score(records_by_id, load_golden(args.golden))
    print(render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
