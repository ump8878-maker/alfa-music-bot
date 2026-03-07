# Рейтинг чатов: формула без предвзятости к жанрам
# Учитываются: активность, полнота квиза, согласованность, разнообразие, вовлечённость
from dataclasses import dataclass
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import Chat, ChatMember, MusicProfile, ChatStats
from app.rating import (
    get_chat_member_ranking,
    get_chat_genre_stats,
    profile_completeness,
)


@dataclass
class NeededForNextRank:
    """Результат get_needed_participants_for_next_rank."""
    current_position: int
    total_chats: int
    needed_count: int
    next_competitor_title: Optional[str] = None


# Веса компонент рейтинга чата (сумма = 100)
WEIGHT_ACTIVITY = 25      # количество прошедших квиз
WEIGHT_COMPLETENESS = 25  # полнота прохождения квиза
WEIGHT_CONSISTENCY = 25   # согласованность вкусов в чате
WEIGHT_DIVERSITY = 15     # разнообразие жанров (без штрафа за поп/рок и т.д.)
WEIGHT_ENGAGEMENT = 10    # вовлечённость (доля прошедших квиз при известном размере чата)


async def calculate_chat_rating(session: AsyncSession, chat_id: int) -> float:
    """
    Рейтинг чата 0–100 без иерархии жанров.
    Учитывает только:
    - активность (число прошедших квиз),
    - полноту данных (заполненность полей квиза),
    - согласованность (средний match между участниками),
    - разнообразие (число уникальных жанров, все жанры равны),
    - вовлечённость (доля прошедших квиз, если известен размер чата).
    """
    members_result = await session.execute(
        select(ChatMember.user_id).where(
            ChatMember.chat_id == chat_id,
            ChatMember.has_completed_test == True,
        )
    )
    user_ids = [r[0] for r in members_result.fetchall()]
    if not user_ids:
        return 0.0

    profiles_result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id.in_(user_ids))
    )
    profiles = list(profiles_result.scalars().all())
    if not profiles:
        return 0.0

    participants_count = len(profiles)
    chat = await session.get(Chat, chat_id)

    # 1. Активность: до 25 баллов (норма: 20 человек = макс)
    activity = min(participants_count, 20) / 20.0 * WEIGHT_ACTIVITY

    # 2. Полнота: средняя полнота профилей (все поля квиза равноправны)
    avg_completeness = sum(profile_completeness(p) for p in profiles) / len(profiles)
    completeness = avg_completeness * WEIGHT_COMPLETENESS

    # 3. Согласованность: средний match между парами (без предвзятости — просто похожесть вкусов)
    from app.services.matching import calculate_match_score
    # Ограничиваем выборку для больших чатов (макс 12 профилей → 66 пар)
    sample = profiles if len(profiles) <= 12 else profiles[:12]
    consistency_sum = 0.0
    pair_count = 0
    for i in range(len(sample)):
        for j in range(i + 1, len(sample)):
            score, _ = calculate_match_score(sample[i], sample[j])
            consistency_sum += score
            pair_count += 1
    avg_consistency = consistency_sum / pair_count if pair_count else 0.5
    consistency = avg_consistency * WEIGHT_CONSISTENCY

    # 4. Разнообразие: число уникальных жанров в чате (без штрафа за любые жанры)
    genre_stats = await get_chat_genre_stats(session, chat_id)
    unique_genres = len(genre_stats)
    diversity_norm = min(unique_genres / 8.0, 1.0)  # 8+ жанров = макс
    diversity = diversity_norm * WEIGHT_DIVERSITY

    # 5. Вовлечённость: доля прошедших квиз (если есть member_count)
    engagement = 0.0
    if chat and getattr(chat, "member_count", None) and chat.member_count > 0:
        ratio = participants_count / chat.member_count
        engagement = min(ratio, 1.0) * WEIGHT_ENGAGEMENT
    else:
        # Нет данных о размере чата — даём средний балл, чтобы не наказывать
        engagement = (WEIGHT_ENGAGEMENT / 2)

    rating = activity + completeness + consistency + diversity + engagement
    rating = min(100.0, max(0.0, round(rating, 1)))

    # Сохраняем в Chat и ChatStats
    if chat:
        chat.rating = round(rating, 1)

    stats = await session.get(ChatStats, chat_id)
    if not stats:
        stats = ChatStats(chat_id=chat_id)
        session.add(stats)
    stats.rating = round(rating, 1)
    stats.participants_count = participants_count
    stats.top_genres = [{"name": g[0], "pct": g[1]} for g in genre_stats[:10]]
    if not stats.top_artists:
        ranking = await get_chat_member_ranking(session, chat_id)
        if ranking:
            _, p, _ = ranking[0]
            stats.top_artists = [a.get("name", "") for a in (p.artists or [])[:5]]
    await session.commit()
    return round(rating, 1)


async def get_chat_rank(
    session: AsyncSession, chat_id: int
) -> Optional[Tuple[int, int]]:
    """Позиция чата в глобальном рейтинге: (позиция, всего_чатов)."""
    from app.rating import get_chat_position
    return await get_chat_position(session, chat_id)


async def get_needed_participants_for_next_rank(
    session: AsyncSession, chat_id: int
) -> Optional[NeededForNextRank]:
    """
    Сколько участников нужно добрать, чтобы подняться в рейтинге.
    Возвращает текущую позицию, сколько людей нужно, и название ближайшего чата-конкурента.
    """
    rank = await get_chat_rank(session, chat_id)
    if not rank:
        return None
    current_position, total_chats = rank
    chat = await session.get(Chat, chat_id)
    if not chat or chat.rating <= 0:
        return None

    # Чаты с рейтингом выше текущего (мы их обгоняем, если наберём участников)
    # Упрощение: считаем, что 1 новый участник с средним score даёт +примерно 1-2 к рейтингу.
    # Чтобы обойти чат выше, нужно поднять rating. Сосед сверху — чат с ближайшим большим рейтингом.
    result_above = await session.execute(
        select(Chat)
        .where(Chat.is_active == True, Chat.rating > chat.rating)
        .order_by(Chat.rating.asc())
        .limit(1)
    )
    next_competitor = result_above.scalar_one_or_none()
    next_title = (next_competitor.title or f"Чат #{current_position - 1}") if next_competitor else None

    # Грубая оценка: каждый новый участник добавляет к рейтингу (avg ~50 * 0.6 / n + 2) баллов
    # Упрощаем: нужно 1-3 человека чтобы "подняться" (следующая позиция)
    participants_count = await session.scalar(
        select(func.count(ChatMember.user_id)).where(
            ChatMember.chat_id == chat_id,
            ChatMember.has_completed_test == True,
        )
    )
    participants_count = participants_count or 0
    # Для обгона следующего чата сверху нужен примерно 1-2 новых участника (условно)
    needed_count = 1 if current_position > 1 else 0
    if current_position > 1 and next_competitor:
        diff = next_competitor.rating - chat.rating
        if diff > 5:
            needed_count = 2
        elif diff > 10:
            needed_count = 3

    return NeededForNextRank(
        current_position=current_position,
        total_chats=total_chats,
        needed_count=needed_count,
        next_competitor_title=next_title,
    )


async def get_global_chat_ranking(
    session: AsyncSession, limit: int = 20
) -> List[Tuple[Chat, float]]:
    """Глобальный рейтинг чатов (делегируем в rating.py для единого места)."""
    from app.rating import get_global_chat_ranking as _get_global
    return await _get_global(session, limit)


async def can_send_growth_message(
    session: AsyncSession, chat_id: int
) -> bool:
    """Проверка: прошло ли достаточно времени с последнего мотивирующего сообщения."""
    from config import settings
    from datetime import datetime, timezone
    stats = await session.get(ChatStats, chat_id)
    if not stats or not stats.last_growth_message_at:
        return True
    since = stats.last_growth_message_at
    now = datetime.now(timezone.utc)
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    elapsed = (now - since).total_seconds() / 3600
    return elapsed >= settings.growth_message_cooldown_hours


async def mark_growth_message_sent(
    session: AsyncSession, chat_id: int
) -> None:
    """Обновляет last_growth_message_at после отправки мотивирующего сообщения."""
    stats = await session.get(ChatStats, chat_id)
    if not stats:
        stats = ChatStats(chat_id=chat_id)
        session.add(stats)
    from datetime import datetime, timezone
    stats.last_growth_message_at = datetime.now(timezone.utc)
    await session.commit()
