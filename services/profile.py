"""Обновление профиля пользователя (настроение, время слушания и т.д.)."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import MusicProfile


async def update_mood(session: AsyncSession, user_id: int, mood: str) -> bool:
    """
    Обновляет поле mood в MusicProfile пользователя.
    Если профиля нет — создаёт с пустыми жанрами/артистами и указанным mood.
    Возвращает True, если запись обновлена/создана.
    """
    result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile:
        profile.mood = mood
    else:
        profile = MusicProfile(user_id=user_id, mood=mood)
        session.add(profile)
    await session.commit()
    return True
