from aiogram import Router

from .start import router as start_router
from .taste_test import router as taste_test_router
from .chat_mode import router as chat_mode_router
from .matches import router as matches_router
from .battle import router as battle_router
from .payments import router as payments_router
from .inline import router as inline_router


def setup_routers() -> Router:
    """Настройка и объединение всех роутеров"""
    router = Router()
    
    router.include_router(start_router)
    router.include_router(taste_test_router)
    router.include_router(chat_mode_router)
    router.include_router(matches_router)
    router.include_router(battle_router)
    router.include_router(payments_router)
    router.include_router(inline_router)
    
    return router


__all__ = ["setup_routers"]
