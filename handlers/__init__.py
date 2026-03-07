from aiogram import Router

from . import start, quiz, chat


def setup_routers() -> Router:
    root = Router()
    root.include_router(start.router, name="start")
    root.include_router(quiz.router, name="quiz")
    root.include_router(chat.router, name="chat")
    return root
