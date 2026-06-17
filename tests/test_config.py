from __future__ import annotations

import pytest

from triage.config import Settings


def test_settings_load_from_env() -> None:
    settings = Settings()
    assert settings.anthropic_model == "claude-haiku-4-5"
    assert settings.anthropic_max_tokens == 1024
    assert settings.anthropic_api_key.get_secret_value() == "sk-ant-test"
    assert settings.telegram_enabled is False


def test_blank_telegram_values_coerce_to_none() -> None:
    settings = Settings()
    assert settings.telegram_bot_token is None
    assert settings.telegram_chat_id is None


def test_telegram_enabled_when_both_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    settings = Settings()
    assert settings.telegram_enabled is True
    assert settings.telegram_chat_id == 42
