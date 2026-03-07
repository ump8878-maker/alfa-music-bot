from aiogram import Router

from . import start, quiz, chat


def setup_routers() -> Router:
    root = Router()
    root.include_router(start.router)
    root.include_router(quiz.router)
    root.include_router(chat.router)
    return root
