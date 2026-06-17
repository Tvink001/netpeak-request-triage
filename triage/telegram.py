"""Send a compact run digest to Telegram via the Bot API (best-effort)."""

from __future__ import annotations

import html
import logging

import httpx

from triage.config import Settings
from triage.models import Category, Priority
from triage.pipeline import RunResult
from triage.report import count_by

logger = logging.getLogger(__name__)

_TELEGRAM_MAX_CHARS = 4096
_SEND_TIMEOUT_SECONDS = 15.0


def build_digest(result: RunResult) -> str:
    """Compose the HTML digest message (kept well under the 4096-char limit)."""
    stats = result.stats
    cats = count_by(result.results, lambda r: r.category.value)
    pris = count_by(result.results, lambda r: r.priority.value)
    flagged = sum(1 for r in result.results if r.needs_clarification)

    lines = [
        "<b>Request triage</b>",
        f"{stats.total} requests · {stats.fallbacks} fallback(s) · "
        f"~${stats.estimated_cost_usd:.4f}",
        "",
        "<b>By category</b>",
    ]
    lines += [f"• {html.escape(c.value)}: {cats[c.value]}" for c in Category if cats.get(c.value)]
    lines += ["", "<b>By priority</b>"]
    lines += [
        f"• {p.value}: {pris.get(p.value, 0)}"
        for p in (Priority.HIGH, Priority.MEDIUM, Priority.LOW)
    ]
    lines += ["", f"Needs clarification: {flagged}"]
    return "\n".join(lines)


def send_digest(settings: Settings, result: RunResult) -> bool:
    """Post the digest; never raise. Returns True iff it was delivered."""
    if not settings.telegram_enabled or settings.telegram_bot_token is None:
        logger.info("Telegram not configured; skipping digest.")
        return False

    text = build_digest(result)[:_TELEGRAM_MAX_CHARS]
    token = settings.telegram_bot_token.get_secret_value()
    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": settings.telegram_chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=_SEND_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except Exception as exc:  # the digest is a nicety; never abort the run
        logger.warning("Telegram digest failed: %s", exc)
        return False
    logger.info("Telegram digest sent to chat %s.", settings.telegram_chat_id)
    return True
