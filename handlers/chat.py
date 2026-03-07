# Чат: добавление бота, /chat_scan, /chat_rating, /top_chats, growth
import logging
from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated
from aiogram.enums import ChatType
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER, Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from database.models import User, Chat, ChatMember, MusicProfile
from keyboards import get_chat_test_keyboard, get_chat_menu_keyboard
from services.chat_analytics import (
    calculate_chat_profile,
    generate_chat_comment,
)
from services.rating_helpers import get_chat_member_ranking
from services.chat_rating import (
    calculate_chat_rating,
    get_chat_rank,
    get_global_chat_ranking,
    get_needed_participants_for_next_rank,
    can_send_growth_message,
    mark_growth_message_sent,
)

logger = logging.getLogger(__name__)

router = Router()
MIN_PARTICIPANTS = getattr(settings, "min_participants_for_scan", 3)


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
        "Узнай свой вкус — пройди тест 👇"
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
    if needed.needed_count > 0:
        text = (
            f"🔥 Ваш чат <b>#{needed.current_position}</b> из {needed.total_chats}.\n\n"
            f"{comment}\n\n"
            f"До следующего места — ещё {needed.needed_count} участников."
        )
        if needed.next_competitor_title:
            text += f"\nОбгоните: {needed.next_competitor_title}"
    else:
        text = (
            f"🔥 Ваш чат <b>#{needed.current_position}</b> в рейтинге.\n\n"
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


@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def bot_added_to_chat(
    event: ChatMemberUpdated, session: AsyncSession
) -> None:
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
    chat_type = getattr(event.chat.type, "value", event.chat.type) or "group"
    if not chat:
        chat = Chat(
            id=chat_id,
            title=event.chat.title,
            type=chat_type,
            added_by_user_id=user_id,
            owner_id=user_id,
            owner_username=event.from_user.username,
        )
        session.add(chat)
    else:
        chat.is_active = True
        chat.title = event.chat.title
        if not chat.owner_id:
            chat.owner_id = user_id
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
    member.has_completed_test = profile_result.scalar_one_or_none() is not None
    await session.commit()

    bot_info = await event.bot.get_me()
    completed = 1 if member.has_completed_test else 0
    remaining = max(0, MIN_PARTICIPANTS - completed)
    text = (
        "🎧 <b>Музыкальный тест чата</b>\n\n"
        "Узнай вкус чата и своё место в рейтинге.\n\n"
        f"📊 Участников с тестом: {completed}"
    )
    if remaining > 0:
        text += f"\nЕщё {remaining} человек — открою скан чата."
    try:
        await event.bot.send_message(
            event.chat.id,
            text,
            reply_markup=get_chat_menu_keyboard(bot_info.username, chat_id),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.exception("Приветствие в чат %s: %s", chat_id, e)


@router.my_chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def bot_removed_from_chat(
    event: ChatMemberUpdated, session: AsyncSession
) -> None:
    chat = await session.get(Chat, event.chat.id)
    if chat:
        chat.is_active = False
        await session.commit()


@router.message(Command("chat_scan"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_chat_scan(message: Message, session: AsyncSession) -> None:
    chat_id = message.chat.id
    profile = await calculate_chat_profile(session, chat_id)
    if not profile:
        bot_info = await message.bot.get_me()
        await message.answer(
            f"Пока мало данных: нужно минимум {MIN_PARTICIPANTS} участников с пройденным тестом.\n\n"
            "Пройди тест — и попроси друзей 👇",
            reply_markup=get_chat_test_keyboard(bot_info.username, chat_id),
            parse_mode="HTML",
        )
        return

    comment = generate_chat_comment(profile)
    # Шкала редкости: 0% = чарты, 100% = редкий вкус
    r = getattr(profile, "avg_rarity", 0.5) or 0.5
    rare_pct = int(r * 100)
    bar_len = 10
    filled = int(rare_pct / 100 * bar_len)
    scale_bar = "█" * filled + "░" * (bar_len - filled)
    rarity_label = "редкий вкус" if rare_pct >= 50 else "ближе к чартам"

    lines = [
        "🎧 <b>Музыкальный скан чата</b>\n",
        f"<b>{profile.profile_name}</b>\n",
        f"Вайб: {profile.vibe_text}\n",
        f"Средний вкус: <b>{profile.overall_score}/100</b>\n",
        "<i>Рейтинг вкуса: полнота квиза + разнообразие выбора + небольшой бонус за редкий вкус. Без предвзятости к жанрам.</i>\n",
        f"<b>Редкость:</b> {scale_bar} {rare_pct}% ({rarity_label})\n",
        "<i>Шкала: слева — популярные чарты (Яндекс.Музыка, Beatport, DJ Mag), справа — более редкий вкус.</i>\n",
    ]
    rare_c = getattr(profile, "rare_count", 0)
    main_c = getattr(profile, "mainstream_count", 0)
    if rare_c + main_c > 0:
        lines.append(
            f"<b>По редкости:</b> {main_c} чел. — ближе к чартам, {rare_c} чел. — более редкий вкус.\n"
        )
    # Топ участников по баллу вкуса — итоговая оценка участников чата
    ranking = await get_chat_member_ranking(session, chat_id)
    if ranking:
        lines.append("\n<b>Топ по вкусу в чате:</b>")
        for i, (user, _, score) in enumerate(ranking[:5], 1):
            name = user.display_name or user.mention or f"Участник {i}"
            if len(name) > 25:
                name = name[:22] + "…"
            lines.append(f"  {i}. {name} — <b>{score}</b>/100")
    if profile.genre_stats:
        lines.append("\n<b>Жанры:</b>")
        for name, pct in profile.genre_stats[:8]:
            lines.append(f"  {name}: {pct}%")
    if profile.top_artists:
        lines.append("\n<b>Топ артистов:</b> " + ", ".join(profile.top_artists[:8]))
    lines.append(f"\n\n{comment}")
    text = "\n".join(lines)
    await message.answer(text, parse_mode="HTML")


@router.message(Command("chat_rating"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_chat_rating(message: Message, session: AsyncSession) -> None:
    chat_id = message.chat.id
    await calculate_chat_rating(session, chat_id)
    chat = await session.get(Chat, chat_id)
    if not chat or chat.rating <= 0:
        await message.answer(
            "Пока нет рейтинга: пройди тест и позови друзей.",
            parse_mode="HTML",
        )
        return
    rank = await get_chat_rank(session, chat_id)
    needed = await get_needed_participants_for_next_rank(session, chat_id)
    text = (
        f"📊 <b>Рейтинг чата</b>\n\n"
        f"Балл: <b>{chat.rating}/100</b>\n"
    )
    if rank:
        pos, total = rank
        text += f"Место: <b>#{pos}</b> из {total}\n"
    if needed and needed.needed_count > 0:
        text += f"\nДобрать {needed.needed_count} участников — подниметесь выше."
        if needed.next_competitor_title:
            text += f"\nБлижайший сосед: {needed.next_competitor_title}"
    await message.answer(text, parse_mode="HTML")


@router.message(Command("top_chats"))
async def cmd_top_chats(message: Message, session: AsyncSession) -> None:
    ranking = await get_global_chat_ranking(session, limit=15)
    if not ranking:
        await message.answer("Пока нет чатов в рейтинге. Добавь бота в группу и пройди тест.")
        return
    lines = ["🏆 <b>Топ чатов по музыкальному вкусу</b>\n"]
    for i, (c, rating) in enumerate(ranking, 1):
        title = (c.title or f"Чат #{i}").replace("<", "").replace(">", "")
        lines.append(f"{i}. {title} — {rating}/100")
    await message.answer("\n".join(lines), parse_mode="HTML")
