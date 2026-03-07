from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List
import os


class Settings(BaseSettings):
    bot_token: str = Field(..., alias="BOT_TOKEN")
    database_url: str = Field(default="sqlite+aiosqlite:///data/bot.db", alias="DATABASE_URL")
    debug: bool = Field(default=False, alias="DEBUG")
    
    # Taste test settings
    min_genres: int = 1
    max_genres: int = 3
    min_artists: int = 1
    max_artists: int = 10
    
    # Chat settings
    min_participants_for_map: int = 3
    # Минимум участников для сканера чата
    min_participants_for_scan: int = Field(default=3, alias="MIN_PARTICIPANTS_FOR_SCAN")
    # Защита от спама: не чаще одного мотивирующего сообщения в N часов на чат
    growth_message_cooldown_hours: float = Field(default=3.0, alias="GROWTH_MESSAGE_COOLDOWN_HOURS")
    
    # Matching settings
    genre_weight: float = 0.30
    artist_weight: float = 0.30
    era_weight: float = 0.10
    mood_weight: float = 0.15
    rarity_weight: float = 0.15
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
