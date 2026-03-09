import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config import settings
from database import init_db
from handlers import setup_routers
from utils import DatabaseMiddleware


def _get_clean_token() -> str:
    raw = os.environ.get("BOT_TOKEN") or getattr(settings, "bot_token", "") or ""
    return "".join(str(raw).split())


logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    logger.info("Initializing database...")
    await init_db()
    await bot.set_my_commands([
        BotCommand(command="start", description="Старт и начало теста"),
        BotCommand(command="profile", description="Мой профиль и вкус"),
        BotCommand(command="top_chats", description="Топ чатов по рейтингу"),
        BotCommand(command="chat_scan", description="Скан вкусов чата"),
        BotCommand(command="chat_top", description="Рейтинг участников чата"),
        BotCommand(command="chat_rating", description="Рейтинг чата"),
        BotCommand(command="help", description="Рейтинги, чаты, аналитика"),
    ])
    bot_info = await bot.get_me()
    logger.info("Bot started: @%s (entry: main.py)", bot_info.username)


async def on_shutdown(bot: Bot) -> None:
    logger.info("Bot shutting down...")


async def main() -> None:
    token = _get_clean_token()
    if not token:
        raise ValueError("BOT_TOKEN не задан. Укажите переменную окружения BOT_TOKEN.")

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.update.middleware(DatabaseMiddleware())
    dp.include_router(setup_routers())
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Starting bot...")
    allowed = ["message", "callback_query", "my_chat_member"]
    await dp.start_polling(bot, allowed_updates=allowed)


if __name__ == "__main__":
    asyncio.run(main())
