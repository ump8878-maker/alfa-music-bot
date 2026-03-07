from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER, Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import User, Chat, ChatMember, MusicProfile, Match
from app.keyboards import get_chat_map_keyboard, get_chat_test_keyboard
from app.keyboards.inline import InlineKeyboardBuilder
from app.services.matching import calculate_chat_matches
from app.services.chat_map import generate_chat_map_text
from app.rating import (
    get_chat_member_ranking,
    get_chat_genre_stats,
    get_chat_position,
    update_chat_rating,
)
from app.utils.humor import (
    get_chat_position_comment,
    get_top_comment,
    get_strange_taste_comment,
)

router = Router()
import random
import asyncio

MIN_PARTICIPANTS = 3


async def ensure_chat_member_completed(
    session: AsyncSession, chat_id: int, user_id: int
) -> None:
    """Отмечает участника чата как прошедшего тест."""
    result = await session.execute(
        select(ChatMember).where(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if member:
        member.has_completed_test = True
        await session.commit()


async def post_quiz_result_to_chat(
    bot,
    session: AsyncSession,
    chat_id: int,
    user_id: int,
    profile: MusicProfile,
    match_percent: int,
) -> None:
    """Публикует в чат: «Юра прошел музыкальный тест», профиль, совпадение, кнопка «Пройти тест»."""
    user = await session.get(User, user_id)
    name = user.display_name if user else "Участник"
    bot_info = await bot.get_me()
    text = (
        f"🎧 <b>{name}</b> прошёл музыкальный тест\n\n"
        f"<b>Профиль:</b> {profile.profile_type}\n"
        f"<b>Совпадение с чатом:</b> {match_percent}%\n\n"
        f"Узнай свой вкус и место в рейтинге — пройди тест 👇"
    )
    position = await get_chat_position(session, chat_id)
    completed = await session.scalar(
        select(func.count(ChatMember.user_id)).where(
            ChatMember.chat_id == chat_id,
            ChatMember.has_completed_test == True,
        )
    )
    remaining = max(0, MIN_PARTICIPANTS - (completed or 0))
    if position and remaining > 0:
        pos, total = position
        text += f"\n\n🔥 Ваш чат сейчас <b>#{pos}</b> из {total}. Чтобы подняться выше — пусть тест пройдут ещё {remaining} человек."
    await bot.send_message(
        chat_id,
        text,
        reply_markup=get_chat_test_keyboard(bot_info.username, chat_id),
        parse_mode="HTML",
    )
    # Вирусная механика: с вероятностью ~15% пишем «в чате обнаружен человек с очень странным вкусом»
    if random.random() < 0.15:
        asyncio.create_task(_send_strange_taste_later(bot, chat_id, bot_info.username))


async def _send_strange_taste_later(bot, chat_id: int, bot_username: str):
    await asyncio.sleep(3)
    comment = get_strange_taste_comment()
    from app.keyboards import get_chat_test_keyboard
    try:
        await bot.send_message(
            chat_id,
            f"🎧 {comment.capitalize()}.\n\nПройдите тест, чтобы понять, кто это 👇",
            reply_markup=get_chat_test_keyboard(bot_username, chat_id),
        )
    except Exception:
        pass


@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def bot_added_to_chat(event: ChatMemberUpdated, session: AsyncSession):
    """Бот добавлен в чат — приветствие «Музыкальный тест чата»."""
    chat_id = event.chat.id
    user_id = event.from_user.id

    user = await session.get(User, user_id)
    if not user:
        user = User(
            id=user_id,
            username=event.from_user.username,
            first_name=event.from_user.first_name,
        )
        session.add(user)

    chat = await session.get(Chat, chat_id)
    if not chat:
        chat = Chat(
            id=chat_id,
            title=event.chat.title,
            type=event.chat.type,
            added_by_user_id=user_id,
            owner_id=user_id,
        )
        session.add(chat)
    else:
        chat.is_active = True
        chat.title = event.chat.title
        if not getattr(chat, "owner_id", None):
            chat.owner_id = user_id

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

    profile_result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id == user_id)
    )
    has_profile = profile_result.scalar_one_or_none() is not None
    member.has_completed_test = has_profile

    await session.commit()

    bot_info = await event.bot.get_me()
    completed = 1 if has_profile else 0
    remaining = MIN_PARTICIPANTS - completed
    profile_line = (
        f"✅ {event.from_user.first_name} уже прошёл тест!\n" if has_profile else ""
    )
    remaining_line = (
        f"Ещё {remaining} человек — и открою карту вкусов!"
        if remaining > 0
        else ""
    )

    await event.answer(
        "🎧 <b>Музыкальный тест чата</b>\n\n"
        "Узнайте, у кого в чате лучший музыкальный вкус.\n\n"
        "Пройдите короткий тест (4 вопроса) — и получите:\n"
        "• свой музыкальный профиль\n"
        "• совпадения с участниками чата\n"
        "• место в рейтинге чата\n\n"
        f"{profile_line}"
        f"📊 Участников: {completed}/{MIN_PARTICIPANTS}\n"
        f"{remaining_line}",
        reply_markup=get_chat_test_keyboard(bot_info.username, chat_id),
        parse_mode="HTML",
    )


@router.my_chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def bot_removed_from_chat(event: ChatMemberUpdated, session: AsyncSession):
    """Бот удалён из чата"""
    chat = await session.get(Chat, event.chat.id)
    if chat:
        chat.is_active = False
        await session.commit()


async def notify_chat_progress(
    bot,
    session: AsyncSession,
    chat_id: int,
    user_id: int,
    username: str,
):
    """Уведомление чата о новом участнике + соревновательное сообщение про рейтинг."""
    result = await session.execute(
        select(func.count(ChatMember.user_id)).where(
            ChatMember.chat_id == chat_id,
            ChatMember.has_completed_test == True,
        )
    )
    completed_count = result.scalar()
    remaining = MIN_PARTICIPANTS - completed_count

    if remaining > 0:
        await bot.send_message(
            chat_id,
            f"✅ @{username or 'Участник'} прошёл тест!\n\n"
            f"📊 Участников: {completed_count}/{MIN_PARTICIPANTS}\n"
            f"{'█' * completed_count}{'░' * remaining} "
            f"{int(completed_count / max(MIN_PARTICIPANTS, 1) * 100)}%\n\n"
            f"Ещё {remaining} {'человек' if remaining > 1 else 'человека'} — и открою карту вкусов!",
            parse_mode="HTML",
        )
    else:
        await reveal_chat_map(bot, session, chat_id)


async def reveal_chat_map(bot, session: AsyncSession, chat_id: int):
    """Открытие карты вкусов чата"""
    chat = await session.get(Chat, chat_id)
    if not chat or chat.map_unlocked:
        return
    
    await calculate_chat_matches(session, chat_id)
    
    chat.map_unlocked = True
    await session.commit()
    
    chat_map_text = await generate_chat_map_text(session, chat_id)
    
    await bot.send_message(
        chat_id,
        f"🗺 <b>КАРТА ВКУСОВ ГОТОВА!</b>\n\n{chat_map_text}",
        reply_markup=get_chat_map_keyboard(chat_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("chat_matches:"))
async def show_chat_matches(callback: CallbackQuery, session: AsyncSession):
    """Показать все совпадения в чате"""
    chat_id = int(callback.data.split(":")[1])
    
    result = await session.execute(
        select(Match)
        .where(Match.chat_id == chat_id)
        .order_by(Match.match_score.desc())
        .limit(10)
    )
    matches = result.scalars().all()
    
    if not matches:
        await callback.answer("Совпадений пока нет", show_alert=True)
        return
    
    text = "📊 <b>Все совпадения в чате:</b>\n\n"
    
    for i, match in enumerate(matches, 1):
        text += (
            f"{i}. {match.user1.display_name} & {match.user2.display_name}\n"
            f"   {match.score_percent}% совпадение\n"
        )
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("start_battle:"))
async def start_battle_from_chat(callback: CallbackQuery, session: AsyncSession):
    """Запуск баттла из меню чата"""
    from app.handlers.battle import create_random_battle
    
    chat_id = int(callback.data.split(":")[1])
    await create_random_battle(callback.bot, session, chat_id)
    await callback.answer("⚔️ Баттл запущен!")


@router.callback_query(F.data.startswith("start_prediction:"))
async def start_prediction_from_chat(callback: CallbackQuery, session: AsyncSession):
    """Запуск prediction из меню чата"""
    chat_id = int(callback.data.split(":")[1])
    await callback.answer("🔮 Функция в разработке", show_alert=True)


@router.message(Command("chat_rating"))
async def cmd_chat_rating(message: Message, session: AsyncSession):
    """Рейтинг чата: топ участников, жанры чата, позиция в глобальном рейтинге."""
    chat_id = message.chat.id
    if message.chat.type == "private":
        await message.answer(
            "Эта команда работает только в групповых чатах. Добавьте бота в чат и напишите /chat_rating там."
        )
        return

    ranking = await get_chat_member_ranking(session, chat_id)
    if not ranking:
        await message.answer(
            "Пока никто не прошёл тест в этом чате. Пройдите тест — и появится рейтинг!"
        )
        return

    await update_chat_rating(session, chat_id)
    genre_stats = await get_chat_genre_stats(session, chat_id)
    position = await get_chat_position(session, chat_id)
    comment = get_chat_position_comment()

    lines = ["🏆 <b>Музыкальный топ чата</b>\n"]
    for i, (u, p, score) in enumerate(ranking[:10], 1):
        comm = get_top_comment(i) if i <= 3 else ""
        lines.append(f"{i}. {u.display_name} — вкус {score} {comm}")
    lines.append("")

    if genre_stats:
        lines.append("🎸 <b>Жанры чата:</b>")
        for name, pct in genre_stats[:8]:
            lines.append(f"  {pct}% {name}")
        lines.append("")

    if position:
        pos, total = position
        lines.append(f"🌍 Ваш чат сейчас <b>#{pos}</b> из {total}")
        lines.append(f"<i>{comment}</i>")

    await message.answer("\n".join(lines), parse_mode="HTML")
