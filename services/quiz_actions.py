"""Действия после завершения квиза: обновление чат-мембера, пост в чат, growth-сообщение."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User, ChatMember, MusicProfile
from keyboards import get_chat_menu_keyboard
from services.chat_rating import (
    calculate_chat_rating,
    can_send_growth_message,
    mark_growth_message_sent,
    get_chat_level_name,
    get_needed_participants_for_next_rank,
)

logger = logging.getLogger(__name__)


async def ensure_chat_member_completed(
    session: AsyncSession, chat_id: int, user_id: int
) -> None:
    result = await session.execute(
        select(ChatMember).where(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        member = ChatMember(chat_id=chat_id, user_id=user_id)
        session.add(member)
    member.has_completed_test = True


async def post_quiz_result_to_chat(
    bot,
    session: AsyncSession,
    chat_id: int,
    user_id: int,
    profile: MusicProfile,
) -> None:
    user = await session.get(User, user_id)
    name = user.display_name if user else "Участник"
    bot_info = await bot.get_me()
    text = (
        f"🎧 <b>{name}</b> прошёл музыкальный тест\n\n"
        f"<b>Профиль:</b> {profile.profile_type}\n\n"
        "Пройди тест и увидишь результаты чата.\n"
        "Большая часть участников уже прошла — результаты тебя удивят 👇"
    )
    await bot.send_message(
        chat_id,
        text,
        reply_markup=get_chat_menu_keyboard(bot_info.username, chat_id),
        parse_mode="HTML",
    )


async def try_send_growth_message(
    bot, session: AsyncSession, chat_id: int
) -> None:
    if not await can_send_growth_message(session, chat_id):
        return
    needed = await get_needed_participants_for_next_rank(session, chat_id)
    if not needed or needed.total_chats == 0:
        return
    bot_info = await bot.get_me()
    from utils.humor import get_growth_comment
    comment = get_growth_comment()
    level_name = get_chat_level_name(needed.current_position)
    if needed.needed_count > 0:
        text = (
            f"🔥 Ваш чат <b>#{needed.current_position}</b> из {needed.total_chats} — уровень «{level_name}».\n\n"
            f"{comment}\n\n"
            f"До следующего места — ещё {needed.needed_count} участников."
        )
        if needed.next_competitor_title:
            text += f"\nОбгоните: {needed.next_competitor_title}"
    else:
        text = (
            f"🔥 Ваш чат <b>#{needed.current_position}</b> в рейтинге — уровень «{level_name}».\n\n"
            f"{comment}"
        )
    try:
        await bot.send_message(
            chat_id,
            text,
            reply_markup=get_chat_menu_keyboard(bot_info.username, chat_id),
            parse_mode="HTML",
        )
        await mark_growth_message_sent(session, chat_id)
    except Exception as e:
        logger.debug("Growth message not sent: %s", e)
