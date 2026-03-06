from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    bot_token: str
    database_url: str = "sqlite+aiosqlite:///data/bot.db"
    admin_ids: List[int] = []
    debug: bool = True
    
    # Taste test settings
    min_genres: int = 1
    max_genres: int = 3
    min_artists: int = 1
    max_artists: int = 10
    
    # Chat settings
    min_participants_for_map: int = 3
    
    # Matching settings
    genre_weight: float = 0.30
    artist_weight: float = 0.30
    era_weight: float = 0.10
    mood_weight: float = 0.15
    rarity_weight: float = 0.15
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
