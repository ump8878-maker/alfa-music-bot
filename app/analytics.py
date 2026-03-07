# Аналитика: пользователи, чаты, квизы, популярные жанры
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import User, Chat, ChatMember, MusicProfile, QuizResult


async def get_analytics_overview(session: AsyncSession) -> Dict[str, Any]:
    """
    Сводка для админки: сколько пользователей, чатов, прошло квиз, средний рейтинг.
    """
    users_total = await session.scalar(select(func.count(User.id)))
    profiles_total = await session.scalar(select(func.count(MusicProfile.user_id)))
    chats_active = await session.scalar(
        select(func.count(Chat.id)).where(Chat.is_active == True)
    )
    quiz_results_total = await session.scalar(select(func.count(QuizResult.id)))

    avg_rating = await session.scalar(
        select(func.avg(Chat.rating)).where(Chat.is_active == True, Chat.rating > 0)
    )
    avg_rating = round(float(avg_rating or 0), 1)

    day_ago = datetime.utcnow() - timedelta(days=1)
    new_users_24h = await session.scalar(
        select(func.count(User.id)).where(User.created_at >= day_ago)
    )
    new_quizzes_24h = await session.scalar(
        select(func.count(QuizResult.id)).where(QuizResult.created_at >= day_ago)
    )

    return {
        "users_total": users_total or 0,
        "profiles_total": profiles_total or 0,
        "chats_active": chats_active or 0,
        "quiz_results_total": quiz_results_total or 0,
        "avg_music_rating": avg_rating,
        "new_users_24h": new_users_24h or 0,
        "new_quizzes_24h": new_quizzes_24h or 0,
    }


async def get_popular_genres(session: AsyncSession, limit: int = 10) -> List[Tuple[str, int]]:
    """Популярные жанры по всем профилям (название, количество упоминаний)."""
    from sqlalchemy import text

    # SQLAlchemy не умеет агрегировать JSON легко без raw — считаем в Python
    result = await session.execute(select(MusicProfile.genres))
    rows = result.fetchall()
    counts = {}
    for (genres,) in rows:
        if not genres:
            continue
        for g in genres:
            name = (g.get("name") or "").strip().lower() or "другое"
            counts[name] = counts.get(name, 0) + 1
    sorted_genres = sorted(counts.items(), key=lambda x: -x[1])
    return sorted_genres[:limit]


def format_analytics_message(data: Dict[str, Any], popular_genres: List[Tuple[str, int]]) -> str:
    """Форматирует сообщение со статистикой для команды /stats или админов."""
    lines = [
        "📊 <b>Аналитика бота</b>",
        "",
        "👥 <b>Пользователи:</b>",
        f"  • Всего: {data['users_total']}",
        f"  • Новых за 24ч: {data['new_users_24h']}",
        "",
        "🎧 <b>Профили / квиз:</b>",
        f"  • Прошли тест: {data['profiles_total']}",
        f"  • Всего прохождений квиза: {data['quiz_results_total']}",
        f"  • Новых тестов за 24ч: {data['new_quizzes_24h']}",
        "",
        "💬 <b>Чаты:</b>",
        f"  • Активных чатов: {data['chats_active']}",
        "",
        "📈 <b>Рейтинг:</b>",
        f"  • Средний музыкальный рейтинг чатов: {data['avg_music_rating']}",
    ]
    if popular_genres:
        lines.append("")
        lines.append("🔥 <b>Популярные жанры:</b>")
        for name, count in popular_genres[:7]:
            lines.append(f"  • {name}: {count}")
    return "\n".join(lines)
