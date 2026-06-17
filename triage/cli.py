"""Command-line entry point: ``triage`` / ``python -m triage``."""

from __future__ import annotations

import argparse
import logging
import sys

import truststore
from pydantic import ValidationError

from triage.config import get_settings
from triage.console import force_utf8_stdio
from triage.inbox import read_requests
from triage.pipeline import run
from triage.report import write_outputs
from triage.telegram import send_digest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="triage",
        description="Classify a free-form request inbox CSV into a strict, validated schema.",
    )
    parser.add_argument("csv", help="Path to the input requests CSV.")
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory for output.json + report.md (default: output).",
    )
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N rows.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read and summarize the CSV without calling the LLM (no API key needed).",
    )
    parser.add_argument(
        "--telegram", action="store_true", help="Send a digest to Telegram after the run."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    force_utf8_stdio()
    # Trust the OS certificate store so HTTPS works behind corporate
    # TLS-inspecting proxies (and behaves normally everywhere else).
    truststore.inject_into_ssl()
    args = build_parser().parse_args(argv)

    try:
        if args.dry_run:
            return _dry_run(args.csv, args.limit)

        try:
            settings = get_settings()
        except ValidationError as exc:
            print(
                f"error: configuration invalid - is ANTHROPIC_API_KEY set in .env?\n{exc}",
                file=sys.stderr,
            )
            return 2

        logging.basicConfig(
            level=settings.log_level.upper(), format="%(levelname)s %(name)s: %(message)s"
        )
        # httpx logs the full request URL at INFO; the Telegram URL embeds the
        # bot token, so keep httpx quiet to avoid leaking it into logs.
        logging.getLogger("httpx").setLevel(logging.WARNING)
        result = run(settings, args.csv, limit=args.limit)
        json_path, report_path = write_outputs(result, args.output_dir)
        stats = result.stats
        print(
            f"Done: {stats.total} requests, {stats.fallbacks} fallback(s), "
            f"{stats.input_tokens + stats.output_tokens:,} tokens "
            f"(~${stats.estimated_cost_usd:.4f}).\n"
            f"Wrote {json_path} and {report_path}."
        )
        if args.telegram:
            send_digest(settings, result)
        return 0
    except FileNotFoundError:
        print(f"error: input CSV not found: {args.csv}", file=sys.stderr)
        return 2


def _dry_run(csv_path: str, limit: int | None) -> int:
    logging.basicConfig(level="INFO", format="%(message)s")
    requests = read_requests(csv_path)
    shown = requests[:limit] if limit else requests
    print(f"{len(requests)} request(s) in {csv_path}; would process {len(shown)} (no API calls).")
    for request in shown[:10]:
        preview = request.raw_text[:70].replace("\n", " ")
        print(f"  {request.id} [{request.channel}] {preview}")
    return 0
