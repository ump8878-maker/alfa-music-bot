from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import User, MusicProfile, Chat, ChatMember, Match
from app.keyboards import get_start_keyboard, get_profile_keyboard, get_chat_invite_keyboard
from app.states import TasteTestStates
from app.services.profile_card import generate_profile_text

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext):
    """Обработка команды /start (в т.ч. from_chat_123 из группового чата)."""
    user_id = message.from_user.id
    # Deep link из чата: ?start=from_chat_123 — сохраняем chat_id для публикации результата
    from_chat_id = None
    if message.text and " " in message.text:
        args = message.text.split(maxsplit=1)
        if len(args) > 1 and args[1].startswith("from_chat_"):
            try:
                from_chat_id = int(args[1].replace("from_chat_", "").strip())
            except ValueError:
                pass
    if from_chat_id:
        await state.update_data(from_chat_id=from_chat_id)

    user = await session.get(User, user_id)
    if not user:
        user = User(
            id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            language_code=message.from_user.language_code,
        )
        session.add(user)
        await session.commit()

    result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if profile:
        profile_text = generate_profile_text(profile)
        await message.answer(
            f"👋 С возвращением, {message.from_user.first_name}!\n\n{profile_text}",
            reply_markup=get_profile_keyboard(),
            parse_mode="HTML",
        )
    else:
        intro = (
            f"🎧 <b>Йо, {message.from_user.first_name}!</b>\n\n"
            "Я — <b>Альфа</b>, бот, который знает о музыке всё.\n\n"
            "🎵 Пройди короткий тест (4 вопроса) и узнай:\n"
            "├ свой музыкальный архетип\n"
            "├ совпадения с друзьями и чатами\n"
            "└ место в рейтинге\n\n"
            "⏱ <i>Займёт меньше минуты</i>"
        )
        if from_chat_id:
            intro += "\n\n📌 Ты пришёл из чата — после теста твой результат покажу там!"
        await message.answer(
            intro,
            reply_markup=get_start_keyboard(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "start_test")
async def start_test(callback: CallbackQuery, state: FSMContext):
    """Начало теста (4 шага). Сохраняем from_chat_id из state, если есть."""
    from app.keyboards import get_genres_keyboard
    data = await state.get_data()
    await state.set_state(TasteTestStates.selecting_genres)
    await state.update_data(selected_genres=set())
    # Не затираем from_chat_id
    if data.get("from_chat_id"):
        await state.update_data(from_chat_id=data["from_chat_id"])
    await callback.message.edit_text(
        "🎵 <b>Шаг 1/4: Жанры</b>\n\n"
        "Какую музыку слушаешь чаще всего?\n"
        "Выбери до 4 жанров (или «Свой вариант»).",
        reply_markup=get_genres_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "restart_test")
async def restart_test(callback: CallbackQuery, state: FSMContext):
    """Перезапуск теста"""
    await start_test(callback, state)


@router.callback_query(F.data == "about_bot")
async def about_bot(callback: CallbackQuery):
    """Информация о боте"""
    await callback.message.edit_text(
        "🎧 <b>Альфа — бот для поиска музыкальных совпадений</b>\n\n"
        "🔹 <b>Как это работает?</b>\n"
        "Ты отвечаешь на несколько вопросов о музыке, "
        "а я составляю твой уникальный профиль и нахожу людей "
        "с похожим вкусом.\n\n"
        "🔹 <b>Что можно делать?</b>\n"
        "• Узнать свой музыкальный архетип\n"
        "• Найти людей с похожим вкусом\n"
        "• Добавить бота в чат друзей\n"
        "• Увидеть карту вкусов группы\n"
        "• Устроить баттл вкусов\n\n"
        "🔹 <b>Это бесплатно?</b>\n"
        "Да, полностью бесплатно!",
        reply_markup=get_start_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(Command("profile"))
async def cmd_profile(message: Message, session: AsyncSession):
    """Показать профиль: архетип, совпадения, место в рейтинге."""
    from aiogram.types import BufferedInputFile
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from app.services.card_generator import generate_profile_card
    from app.services.matching import calculate_match_score
    from app.rating import get_chat_member_ranking, get_user_rank_in_chat
    from app.models import ChatMember

    user_id = message.from_user.id
    bot_info = await message.bot.get_me()

    result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        await message.answer(
            "У тебя пока нет профиля. Пройди тест!",
            reply_markup=get_start_keyboard(),
        )
        return

    username = message.from_user.username
    caption = "🎵 <b>Твой музыкальный профиль</b>\n\n"
    caption += f"<b>Тип:</b> {profile.profile_type}\n\n"

    # Совпадения (топ из любого чата)
    memberships = await session.execute(
        select(ChatMember.chat_id).where(ChatMember.user_id == user_id)
    )
    chat_ids = [r[0] for r in memberships.fetchall()]
    seen = set()
    match_lines = []
    for cid in chat_ids[:3]:
        ranking = await get_chat_member_ranking(session, cid)
        for u, p, _ in ranking:
            if u.id == user_id or u.id in seen:
                continue
            seen.add(u.id)
            sc, _ = calculate_match_score(profile, p)
            match_lines.append(f"{u.display_name} — {int(sc * 100)}%")
            if len(match_lines) >= 5:
                break
        if len(match_lines) >= 5:
            break
    if match_lines:
        caption += "<b>Совпадения:</b>\n" + "\n".join(match_lines) + "\n\n"
    rank_line = ""
    for cid in chat_ids[:1]:
        r = await get_user_rank_in_chat(session, user_id, cid)
        if r:
            rank_line = f"<b>Место в рейтинге чата:</b> {r}"
            break
    if rank_line:
        caption += rank_line + "\n\n"

    try:
        card_buffer = generate_profile_card(profile, username)
        card_file = BufferedInputFile(card_buffer.read(), filename="profile.png")
        builder = InlineKeyboardBuilder()
        builder.button(text="📤 Поделиться", switch_inline_query="")
        builder.button(
            text="👥 Добавить в чат",
            url=f"https://t.me/{bot_info.username}?startgroup=true",
        )
        builder.button(text="🔄 Пройти заново", callback_data="restart_test")
        builder.button(text="📊 Мои совпадения", callback_data="show_matches")
        builder.adjust(2, 2)
        await message.answer_photo(
            photo=card_file,
            caption=caption,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
    except Exception:
        profile_text = generate_profile_text(profile)
        if match_lines:
            profile_text += "\n\n<b>Совпадения:</b>\n" + "\n".join(match_lines)
        if rank_line:
            profile_text += "\n\n" + rank_line
        await message.answer(
            f"📊 <b>Твой музыкальный профиль</b>\n\n{profile_text}",
            reply_markup=get_profile_keyboard(),
            parse_mode="HTML",
        )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Справка по боту"""
    await message.answer(
        "🎵 <b>Альфа — бот музыкальных вкусов</b>\n\n"
        "<b>Команды:</b>\n"
        "/start — начать или перезапустить\n"
        "/profile — архетип, совпадения, место в рейтинге\n"
        "/matches — посмотреть совпадения\n"
        "/global_rating — глобальный рейтинг чатов\n"
        "/help — эта справка\n\n"
        "<b>В групповых чатах:</b>\n"
        "/chat_rating — рейтинг чата, топ участников, жанры\n\n"
        "Добавь бота в чат → пройдите тест → рейтинг и совпадения!",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "share_profile")
async def share_profile(callback: CallbackQuery, session: AsyncSession):
    """Поделиться профилем"""
    from aiogram.types import BufferedInputFile
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from app.services.card_generator import generate_profile_card
    
    user_id = callback.from_user.id
    bot_info = await callback.bot.get_me()
    
    result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        await callback.answer("Сначала пройди тест!", show_alert=True)
        return
    
    username = callback.from_user.username
    
    try:
        card_buffer = generate_profile_card(profile, username)
        card_file = BufferedInputFile(card_buffer.read(), filename="profile.png")
        
        builder = InlineKeyboardBuilder()
        builder.button(text="📤 Переслать друзьям", switch_inline_query="")
        builder.adjust(1)
        
        await callback.message.answer_photo(
            photo=card_file,
            caption=(
                f"🎵 <b>Мой музыкальный профиль</b>\n\n"
                f"Нажми кнопку ниже чтобы отправить друзьям 👇"
            ),
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        profile_text = generate_profile_text(profile)
        
        builder = InlineKeyboardBuilder()
        builder.button(text="📤 Переслать друзьям", switch_inline_query="")
        builder.adjust(1)
        
        await callback.message.answer(
            f"🎵 <b>Мой музыкальный профиль</b>\n\n"
            f"{profile_text}\n\n"
            f"Узнай свой вкус → @{bot_info.username}",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data == "add_to_chat")
async def add_to_chat(callback: CallbackQuery):
    """Добавить бота в чат"""
    bot_info = await callback.bot.get_me()
    
    await callback.message.answer(
        "👥 <b>Добавь бота в чат друзей!</b>\n\n"
        "Там ты сможешь:\n"
        "• Увидеть совпадения бесплатно\n"
        "• Запустить баттлы и угадайки\n"
        "• Узнать карту вкусов компании\n\n"
        "Нажми кнопку ниже 👇",
        reply_markup=get_chat_invite_keyboard(bot_info.username),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(Command("global_rating"))
async def cmd_global_rating(message: Message, session: AsyncSession):
    """Глобальный рейтинг музыкальных чатов."""
    from app.rating import get_global_chat_ranking

    ranking = await get_global_chat_ranking(session, limit=15)
    if not ranking:
        await message.answer(
            "Пока нет чатов в рейтинге. Добавьте бота в чат и пройдите тест!"
        )
        return
    lines = ["🌍 <b>Глобальный рейтинг музыкальных чатов</b>\n"]
    for i, (chat, score) in enumerate(ranking, 1):
        title = (chat.title or f"Чат {chat.id}")[:40]
        owner_str = ""
        if getattr(chat, "owner", None) and chat.owner:
            owner_str = f"\n   владелец: {chat.owner.mention}"
        elif getattr(chat, "added_by", None) and chat.added_by:
            owner_str = f"\n   владелец: {chat.added_by.mention}"
        lines.append(f"{i}. {title} — {score:.0f}{owner_str}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession):
    """Аналитика бота: пользователи, квизы, чаты, популярные жанры."""
    from app.analytics import get_analytics_overview, get_popular_genres, format_analytics_message

    data = await get_analytics_overview(session)
    popular_genres = await get_popular_genres(session, limit=7)
    text = format_analytics_message(data, popular_genres)
    await message.answer(text, parse_mode="HTML")
