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
from services.rating_helpers import (
    get_chat_member_ranking,
    find_rarest_user,
    find_closest_in_ranking,
    calc_rarity_percentile,
)
from services.chat_rating import (
    calculate_chat_rating,
    get_chat_rank,
    get_chat_level_name,
    get_global_chat_ranking,
    get_needed_participants_for_next_rank,
)
from utils.humor import get_scan_trigger_question

logger = logging.getLogger(__name__)

router = Router()
MIN_PARTICIPANTS = getattr(settings, "min_participants_for_scan", 3)


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

    # Топ участников по баллу — нужен для прогресса и персональных строк
    ranking = await get_chat_member_ranking(session, chat_id)
    participants = len(ranking)
    full_map_count = 10
    progress_pct = min(100, int(100 * participants / full_map_count))
    remaining = max(0, full_map_count - participants)
    progress_line = f"Чат на <b>{progress_pct}%</b> к полной карте"
    if remaining > 0:
        progress_line += f" (ещё {remaining} чел. — расширенная статистика)"
    progress_line += ".\n"

    lines = [
        "🎧 <b>Музыкальный скан чата</b>\n",
        f"<b>{profile.profile_name}</b>\n",
        f"Вайб: {profile.vibe_text}\n",
        progress_line,
        f"Средний вкус: <b>{profile.overall_score}/100</b>\n",
        "<i>Балл вкуса: полнота квиза (30) + разнообразие жанров и артистов (50) + редкость (15) + бонус за вайб (5). Чем полнее и разнообразнее — тем выше.</i>\n",
        f"<b>Редкость:</b> {scale_bar} {rare_pct}% ({rarity_label})\n",
        "<i>Шкала: слева — популярные чарты (Яндекс.Музыка, Beatport, DJ Mag), справа — более редкий вкус.</i>\n",
    ]
    rare_c = getattr(profile, "rare_count", 0)
    main_c = getattr(profile, "mainstream_count", 0)
    if rare_c + main_c > 0:
        lines.append(
            f"<b>По редкости:</b> {main_c} чел. — ближе к чартам, {rare_c} чел. — более редкий вкус.\n"
        )
    # Титулы: лучший по баллу и самый редкий вкус
    rarest = find_rarest_user(ranking)
    if ranking:
        lines.append("\n<b>🏆 Титулы в чате:</b>")
        first_user, _, first_score = ranking[0]
        first_name = first_user.display_name or first_user.mention or "Участник"
        if len(first_name) > 20:
            first_name = first_name[:17] + "…"
        lines.append(f"  🥇 <b>Лучший балл:</b> {first_name} — {first_score}/100")
        if rarest:
            rarest_user, rarest_profile, rarest_r = rarest
            rarest_name = rarest_user.display_name or rarest_user.mention or "Участник"
            if len(rarest_name) > 20:
                rarest_name = rarest_name[:17] + "…"
            # Показать только если самый редкий — не тот же, что первый (или всё равно показать)
            lines.append(f"  🏅 <b>Самый редкий вкус:</b> {rarest_name} ({int(rarest_r * 100)}%)")
        lines.append("\n<b>Рейтинг участников:</b>")
        medal = ["🥇", "🥈", "🥉"]
        for i, (user, prof, score) in enumerate(ranking[:10], 1):
            name = user.display_name or user.mention or f"Участник {i}"
            if len(name) > 22:
                name = name[:19] + "…"
            badge = medal[i - 1] if i <= 3 else f"{i}."
            is_rarest = rarest and rarest[0].id == user.id
            rare_tag = " 🏅" if is_rarest else ""
            lines.append(f"  {badge} {name} — <b>{score}</b>/100{rare_tag}")
    if profile.genre_stats:
        lines.append("\n<b>Жанры:</b>")
        for name, pct in profile.genre_stats[:8]:
            lines.append(f"  {name}: {pct}%")
    if profile.top_artists:
        lines.append("\n<b>Топ артистов:</b> " + ", ".join(profile.top_artists[:8]))
    if profile.top_guilty:
        from keyboards.data import GENRES as ALL_GENRES
        guilty_display = {g["id"]: g["name"] for g in ALL_GENRES}
        guilty_name = guilty_display.get(profile.top_guilty, profile.top_guilty)
        lines.append(f"\n🤮 <b>Самый зашкварный жанр чата:</b> {guilty_name}")
    # Персонально для того, кто запросил скан
    requestor_id = message.from_user.id if message.from_user else None
    if requestor_id and participants >= 2:
        closest = find_closest_in_ranking(ranking, requestor_id)
        if closest:
            other_user, sim = closest
            name = other_user.display_name or other_user.mention or "участник"
            if len(name) > 20:
                name = name[:17] + "…"
            lines.append(f"\n<b>Ты ближе всего по вкусу к</b> {name} — {int(sim)}% совпадение.")
        rarity_pct = calc_rarity_percentile(ranking, requestor_id)
        if rarity_pct is not None:
            lines.append(f"<b>Твой вкус</b> в топ-{rarity_pct}% по редкости в этом чате.")
    lines.append(f"\n\n{comment}")
    lines.append(f"\n💬 {get_scan_trigger_question()}")
    text = "\n".join(lines)
    await message.answer(text, parse_mode="HTML")


@router.message(Command("chat_top"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_chat_top(message: Message, session: AsyncSession) -> None:
    """Рейтинг участников чата по баллу вкуса + титулы (редкий, лучший)."""
    chat_id = message.chat.id
    ranking = await get_chat_member_ranking(session, chat_id)
    if len(ranking) < 2:
        bot_info = await message.bot.get_me()
        await message.answer(
            "Нужно минимум 2 участников с пройденным тестом. Пройди тест и позови друзей 👇",
            reply_markup=get_chat_test_keyboard(bot_info.username, chat_id),
            parse_mode="HTML",
        )
        return
    rarest = find_rarest_user(ranking)
    lines = ["🏆 <b>Рейтинг участников чата</b>\n"]
    first_user, _, first_score = ranking[0]
    first_name = first_user.display_name or first_user.mention or "Участник"
    if len(first_name) > 20:
        first_name = first_name[:17] + "…"
    lines.append(f"🥇 <b>Лучший балл:</b> {first_name} — {first_score}/100")
    if rarest:
        ru, rp, rr = rarest
        rn = ru.display_name or ru.mention or "Участник"
        if len(rn) > 20:
            rn = rn[:17] + "…"
        lines.append(f"🏅 <b>Самый редкий вкус:</b> {rn} ({int(rr * 100)}%)\n")
    medal = ["🥇", "🥈", "🥉"]
    for i, (user, prof, score) in enumerate(ranking[:15], 1):
        name = user.display_name or user.mention or f"Участник {i}"
        if len(name) > 22:
            name = name[:19] + "…"
        badge = medal[i - 1] if i <= 3 else f"{i}."
        is_rarest = rarest and rarest[0].id == user.id
        rare_tag = " 🏅" if is_rarest else ""
        lines.append(f"  {badge} {name} — <b>{score}</b>/100{rare_tag}")
    await message.answer("\n".join(lines), parse_mode="HTML")


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
    level_name = get_chat_level_name(rank[0]) if rank else "Участник"
    text = (
        f"📊 <b>Рейтинг чата</b>\n\n"
        f"Балл: <b>{chat.rating}/100</b>\n"
    )
    if rank:
        pos, total = rank
        text += f"Место: <b>#{pos}</b> из {total}\n"
        text += f"Уровень чата: <b>«{level_name}»</b>\n"
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
