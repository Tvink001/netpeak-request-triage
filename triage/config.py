"""Runtime configuration, loaded from the environment / ``.env``."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration. Secrets are ``SecretStr`` so they never log."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Anthropic — required.
    anthropic_api_key: SecretStr
    anthropic_model: str = "claude-haiku-4-5"
    anthropic_max_tokens: int = Field(default=1024, ge=1, le=4096)

    # Telegram digest — optional (only used with --telegram).
    telegram_bot_token: SecretStr | None = None
    telegram_chat_id: int | None = None

    log_level: str = "INFO"

    @field_validator("telegram_bot_token", "telegram_chat_id", mode="before")
    @classmethod
    def _empty_to_none(cls, value: object) -> object:
        """Treat a blank env value (as in .env.example) as unset."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def telegram_enabled(self) -> bool:
        return self.telegram_bot_token is not None and self.telegram_chat_id is not None


@lru_cache
def get_settings() -> Settings:
    """Process-wide cached settings. Constructed lazily so ``--help`` and the
    unit tests do not require a real API key in the environment."""
    return Settings()
