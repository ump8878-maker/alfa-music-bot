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
)
from app.utils.humor import get_chat_position_comment, get_top_comment, get_growth_comment
from app.services.chat_analytics import (
    calculate_chat_profile,
    generate_chat_comment,
)
from app.chat_rating import (
    calculate_chat_rating,
    get_chat_rank,
    get_needed_participants_for_next_rank,
    can_send_growth_message,
    mark_growth_message_sent,
)
from config import settings

router = Router()

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
    # Мотивирующее сообщение о росте рейтинга (с cooldown)
    await try_send_growth_message(bot, session, chat_id)


async def try_send_growth_message(bot, session: AsyncSession, chat_id: int) -> None:
    """
    Отправляет мотивирующее сообщение в чат (рейтинг, добор участников),
    не чаще чем раз в growth_message_cooldown_hours.
    """
    if not await can_send_growth_message(session, chat_id):
        return
    needed = await get_needed_participants_for_next_rank(session, chat_id)
    if not needed or needed.total_chats == 0:
        return
    bot_info = await bot.get_me()
    if needed.needed_count > 0:
        text = (
            f"🔥 Ваш чат сейчас <b>#{needed.current_position}</b> в рейтинге.\n\n"
            f"До следующего места не хватает {needed.needed_count} участников."
        )
        if needed.next_competitor_title:
            text += f"\n\nЕщё {needed.needed_count} человек — и обгоните <b>{needed.next_competitor_title}</b>."
    else:
        text = f"🔥 Ваш чат сейчас <b>#{needed.current_position}</b> в рейтинге.\n\nПусть тест пройдут новые участники — подниметесь выше."
    try:
        await bot.send_message(
            chat_id,
            text,
            reply_markup=get_chat_test_keyboard(bot_info.username, chat_id),
            parse_mode="HTML",
        )
        await mark_growth_message_sent(session, chat_id)
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
            owner_username=event.from_user.username,
        )
        session.add(chat)
    else:
        chat.is_active = True
        chat.title = event.chat.title
        if not getattr(chat, "owner_id", None):
            chat.owner_id = user_id
        if hasattr(chat, "owner_username"):
            chat.owner_username = event.from_user.username or chat.owner_username

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


def _chat_only(message: Message) -> bool:
    """Команда только для групп/супергрупп."""
    return message.chat.type in ("group", "supergroup")


@router.message(Command("chat_scan"))
async def cmd_chat_scan(message: Message, session: AsyncSession):
    """Музыкальный сканер чата: профиль, жанры, артисты, вайб. Только в группах."""
    if not _chat_only(message):
        await message.answer(
            "Музыкальный сканер доступен только в групповых чатах. "
            "Добавьте бота в чат и вызовите /chat_scan там."
        )
        return

    chat_id = message.chat.id
    bot_info = await message.bot.get_me()
    min_participants = getattr(
        settings, "min_participants_for_scan", 3
    )

    profile = await calculate_chat_profile(session, chat_id)
    if not profile:
        await message.answer(
            "Недостаточно данных для музыкального сканирования чата.\n"
            "Пусть тест пройдут ещё участники.",
            reply_markup=get_chat_test_keyboard(bot_info.username, chat_id),
        )
        return

    comment = generate_chat_comment(profile)
    lines = [
        "🎧 <b>Музыкальный сканер чата</b>",
        "",
        "<b>Профиль чата:</b>",
        profile.profile_name,
        "",
        "<b>Жанры чата:</b>",
    ]
    for name, pct in profile.genre_stats[:8]:
        lines.append(f"{pct}% {name}")
    if profile.top_artists:
        lines.append("")
        lines.append("<b>Любимые артисты:</b>")
        lines.append(", ".join(profile.top_artists[:8]))
    lines.append("")
    lines.append("<b>Общий вайб:</b>")
    lines.append(profile.vibe_text)
    lines.append("")
    lines.append(f"<i>Комментарий бота: {comment}</i>")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("chat_rating"))
async def cmd_chat_rating(message: Message, session: AsyncSession):
    """Рейтинг чата: название, позиция, рейтинг, добор участников, комментарий."""
    if not _chat_only(message):
        await message.answer(
            "Эта команда работает только в групповых чатах. "
            "Добавьте бота в чат и напишите /chat_rating там."
        )
        return

    chat_id = message.chat.id
    chat = await session.get(Chat, chat_id)
    if not chat:
        await message.answer("Чат не найден. Сначала добавьте бота в чат.")
        return

    ranking = await get_chat_member_ranking(session, chat_id)
    if not ranking:
        await message.answer(
            "Пока никто не прошёл тест в этом чате. Пройдите тест — и появится рейтинг!",
            reply_markup=get_chat_test_keyboard((await message.bot.get_me()).username, chat_id),
        )
        return

    await calculate_chat_rating(session, chat_id)
    rank = await get_chat_rank(session, chat_id)
    needed = await get_needed_participants_for_next_rank(session, chat_id)
    participants_count = len(ranking)
    title = (chat.title or "Чат")[:50]
    rating_val = chat.rating or 0

    lines = [
        "🏆 <b>Рейтинг чата</b>",
        "",
        f"<b>Название:</b> {title}",
    ]
    if rank:
        pos, total = rank
        lines.append(f"<b>Позиция:</b> #{pos} из {total}")
    lines.append(f"<b>Рейтинг:</b> {rating_val:.0f} / 100")
    lines.append(f"<b>Прошли тест:</b> {participants_count} участников")
    lines.append("")
    if needed and needed.needed_count > 0:
        lines.append("Чтобы подняться выше, нужно чтобы тест прошли ещё "
                     f"{needed.needed_count} человек.")
        if needed.next_competitor_title:
            lines.append(f"Ближайший сосед: {needed.next_competitor_title}")
    else:
        lines.append("Чтобы подняться выше — пусть тест пройдут новые участники.")
    lines.append("")
    lines.append(f"<i>Комментарий: {get_growth_comment()}</i>")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("top_chats"))
async def cmd_top_chats(message: Message, session: AsyncSession):
    """Глобальный топ музыкальных чатов (топ-10)."""
    from app.rating import get_global_chat_ranking
    ranking = await get_global_chat_ranking(session, limit=10)
    if not ranking:
        await message.answer(
            "Пока нет чатов в рейтинге. Добавьте бота в чат и пройдите тест!"
        )
        return
    lines = ["🌍 <b>Топ музыкальных чатов</b>", ""]
    for i, (c, score) in enumerate(ranking, 1):
        title = (c.title or f"Чат {c.id}")[:40]
        owner = ""
        if getattr(c, "owner_username", None):
            owner = f"\n   владелец: @{c.owner_username}"
        elif c.added_by and c.added_by.username:
            owner = f"\n   владелец: @{c.added_by.username}"
        lines.append(f"{i}. {title} — {score:.0f}{owner}")
    await message.answer("\n".join(lines), parse_mode="HTML")
