# Конфиг: только то, что нужно для бота и двух механик (сканер + рейтинг чата)
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    bot_token: str = Field(..., alias="BOT_TOKEN")
    database_url: str = Field(default="sqlite+aiosqlite:///data/bot.db", alias="DATABASE_URL")
    debug: bool = Field(default=False, alias="DEBUG")

    min_participants_for_scan: int = Field(default=3, alias="MIN_PARTICIPANTS_FOR_SCAN")
    growth_message_cooldown_hours: float = Field(default=3.0, alias="GROWTH_MESSAGE_COOLDOWN_HOURS")

    @field_validator("bot_token", mode="before")
    @classmethod
    def strip_token(cls, v):
        if isinstance(v, str):
            return "".join(v.split())
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


settings = Settings()
