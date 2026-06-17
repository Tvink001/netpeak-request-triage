"""Write ``output.json`` and render the aggregate ``report.md``."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from triage.models import Category, ExtractedRequest, Language, Priority
from triage.pipeline import RunResult

_PRIORITY_ORDER = (Priority.HIGH, Priority.MEDIUM, Priority.LOW)
_UNROUTED = "(unrouted)"


def count_by(
    results: list[ExtractedRequest], key: Callable[[ExtractedRequest], str]
) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for result in results:
        counts[key(result)] += 1
    return counts


def write_outputs(result: RunResult, output_dir: str | Path) -> tuple[Path, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "output.json"
    report_path = out / "report.md"

    records = [r.model_dump(mode="json") for r in result.results]
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(render_report(result), encoding="utf-8")
    return json_path, report_path


def render_report(result: RunResult) -> str:
    results = result.results
    stats = result.stats
    lines: list[str] = [
        "# Request triage report",
        "",
        f"Model `{stats.model}` · {stats.total} requests · "
        f"{stats.fallbacks} fail-soft fallback(s).",
        "",
        f"Tokens: {stats.input_tokens:,} in / {stats.output_tokens:,} out across "
        f"{stats.api_calls} call(s) - estimated **${stats.estimated_cost_usd:.4f}**.",
        "",
    ]

    cat_counts = count_by(results, lambda r: r.category.value)
    lines += _table(
        "By category",
        ("category", "count"),
        [(c.value, cat_counts[c.value]) for c in Category if cat_counts.get(c.value)],
    )

    pri_counts = count_by(results, lambda r: r.priority.value)
    lines += _table(
        "By priority",
        ("priority", "count"),
        [(p.value, pri_counts.get(p.value, 0)) for p in _PRIORITY_ORDER],
    )

    dep_counts = count_by(results, lambda r: r.target_department or _UNROUTED)
    dep_rows = sorted(dep_counts.items(), key=lambda kv: (kv[0] == _UNROUTED, kv[0].lower()))
    lines += _table("By department", ("department", "count"), dep_rows)

    lang_counts = count_by(results, lambda r: r.language.value)
    lines += _table(
        "By language",
        ("language", "count"),
        [(lang.value, lang_counts[lang.value]) for lang in Language if lang_counts.get(lang.value)],
    )

    flagged = [r for r in results if r.needs_clarification]
    lines += _record_table(
        f"Needs clarification ({len(flagged)})",
        ("id", "channel", "summary"),
        [(r.id, r.channel, _md(r.short_summary)) for r in flagged],
    )

    inert = [r for r in results if not r.is_actionable]
    lines += _record_table(
        f"Not actionable ({len(inert)})",
        ("id", "category", "summary"),
        [(r.id, r.category.value, _md(r.short_summary)) for r in inert],
    )

    lines += _related_section(_related_clusters(results))
    return "\n".join(lines) + "\n"


def _related_clusters(
    results: list[ExtractedRequest],
) -> list[tuple[str, list[ExtractedRequest]]]:
    """Group actionable requests by target department; clusters of >1 are worth a
    human glance for overlap/duplication (e.g. the two Google-Ads report asks)."""
    groups: dict[str, list[ExtractedRequest]] = defaultdict(list)
    for r in results:
        if r.target_department and r.category not in (Category.UNPROCESSED, Category.OUT_OF_SCOPE):
            groups[r.target_department].append(r)
    clusters = [(dep, members) for dep, members in groups.items() if len(members) > 1]
    return sorted(clusters, key=lambda c: (-len(c[1]), c[0].lower()))


def _related_section(clusters: list[tuple[str, list[ExtractedRequest]]]) -> list[str]:
    lines = ["## Potential related requests", ""]
    if not clusters:
        return lines + ["_No same-department clusters._", ""]
    lines.append("_Requests aimed at the same department - scan for overlap/duplication._")
    lines.append("")
    for dep, members in clusters:
        ids = ", ".join(m.id for m in members)
        lines.append(f"- **{dep}** ({len(members)}): {ids}")
    return lines + [""]


def _table(title: str, header: tuple[str, str], rows: list[tuple[str, int]]) -> list[str]:
    out = [f"## {title}", "", f"| {header[0]} | {header[1]} |", "| --- | --- |"]
    out += [f"| {label} | {count} |" for label, count in rows]
    return out + [""]


def _record_table(
    title: str, header: tuple[str, str, str], rows: list[tuple[str, str, str]]
) -> list[str]:
    out = [f"## {title}", ""]
    if not rows:
        return out + ["_None._", ""]
    out += [f"| {header[0]} | {header[1]} | {header[2]} |", "| --- | --- | --- |"]
    out += [f"| {a} | {b} | {c} |" for a, b, c in rows]
    return out + [""]


def _md(text: str) -> str:
    """Make a value safe for a single markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ").strip()
