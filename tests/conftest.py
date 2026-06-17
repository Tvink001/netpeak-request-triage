"""Shared fixtures: a hermetic environment so Settings() constructs in tests."""

from __future__ import annotations

import pytest

# Set every relevant var explicitly (including empty Telegram values) so the
# tests are independent of any real .env on the developer's machine.
_TEST_ENV = {
    "ANTHROPIC_API_KEY": "sk-ant-test",
    "ANTHROPIC_MODEL": "claude-haiku-4-5",
    "ANTHROPIC_MAX_TOKENS": "1024",
    "TELEGRAM_BOT_TOKEN": "",
    "TELEGRAM_CHAT_ID": "",
    "LOG_LEVEL": "INFO",
}


@pytest.fixture(autouse=True)
def _test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _TEST_ENV.items():
        monkeypatch.setenv(key, value)
    from triage.config import get_settings

    get_settings.cache_clear()
