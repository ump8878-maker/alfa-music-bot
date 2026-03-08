# Конфиг: BOT_TOKEN, DATABASE_URL и опции. Работает без pydantic_settings.
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _env(key: str, default: str = "") -> str:
    v = os.environ.get(key, default)
    return (v or "").strip()


def _env_bool(key: str, default: bool = False) -> bool:
    val = _env(key)
    if not val:
        return default
    return val.lower() in ("1", "true", "yes")


def _env_int(key: str, default: int = 0) -> int:
    try:
        return int(_env(key) or default)
    except ValueError:
        return default


def _env_float(key: str, default: float = 0.0) -> float:
    try:
        return float(_env(key) or default)
    except ValueError:
        return default


class Settings:
    """Конфиг из переменных окружения (без зависимости от pydantic_settings)."""

    @property
    def bot_token(self) -> str:
        raw = _env("BOT_TOKEN")
        return "".join(raw.split())  # убрать пробелы

    @property
    def database_url(self) -> str:
        return _env("DATABASE_URL") or "sqlite+aiosqlite:///data/bot.db"

    @property
    def debug(self) -> bool:
        return _env_bool("DEBUG", False)

    @property
    def min_participants_for_scan(self) -> int:
        return _env_int("MIN_PARTICIPANTS_FOR_SCAN", 3)

    @property
    def growth_message_cooldown_hours(self) -> float:
        return _env_float("GROWTH_MESSAGE_COOLDOWN_HOURS", 3.0)


settings = Settings()
