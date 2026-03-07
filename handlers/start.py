from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.enums import ChatType
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User, MusicProfile
from keyboards import get_start_keyboard, get_profile_keyboard
from states import QuizStates
from services.rating_helpers import compute_user_taste_score
from utils.taste_phrase import generate_taste_phrase

router = Router()
BOT_VERSION = "v2 · скан и рейтинг чатов"


@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def cmd_start_private(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    command: CommandObject | None = None,
):
    """Старт только в личке: полное меню и тест."""
    user_id = message.from_user.id
    args = (command.args or "").strip() if command else ""

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

    from_chat_id = None
    if args.startswith("from_chat_"):
        try:
            from_chat_id = int(args.replace("from_chat_", "").strip())
        except ValueError:
            pass
    await state.update_data(from_chat_id=from_chat_id)

    text = (
        "Привет! 👋\n\n"
        "Я помогу узнать твой музыкальный вкус за 4 шага — жанры, артисты, когда слушаешь, настроение. "
        "Получишь свой архетип и балл 0–100.\n\n"
        "🎯 <b>Что ещё умею:</b>\n"
        "• Твой профиль и вкус — /profile\n"
        "• Топ чатов по рейтингу — /top_chats\n"
        "• Добавь меня в группу — там /chat_scan (скан вкусов чата) и /chat_rating (рейтинг чата). "
        "После теста увидишь своё место в рейтинге чата 🏆\n\n"
        "Жми кнопку ниже — начнём с теста 🎵"
    )
    await message.answer(
        text,
        reply_markup=get_start_keyboard(),
        parse_mode="HTML",
    )


@router.message(CommandStart(), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_start_group(message: Message, session: AsyncSession):
    """В группе: короткая подсказка, тест — в личку."""
    bot_info = await message.bot.get_me()
    text = (
        "👋 В группе я умею: <b>/chat_scan</b> (скан вкусов), <b>/chat_rating</b> (рейтинг чата).\n"
        "Тест и профиль — только в личке. Напиши мне в личные сообщения 👇"
    )
    from keyboards.inline import get_chat_test_keyboard
    await message.answer(
        text,
        reply_markup=get_chat_test_keyboard(bot_info.username, message.chat.id),
        parse_mode="HTML",
    )


@router.message(Command("profile"), F.chat.type == ChatType.PRIVATE)
async def cmd_profile(message: Message, session: AsyncSession):
    """Профиль только в личке: архетип, вкус, кнопки."""
    user_id = message.from_user.id
    result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    bot_info = await message.bot.get_me()

    if not profile:
        text = (
            "Профиля пока нет. Пройди тест — жанры, артисты, когда слушаешь, настроение.\n\n"
            "После теста увидишь архетип, вкус 0–100 и место в рейтинге чата (если проходил из группы)."
        )
        await message.answer(
            text,
            reply_markup=get_start_keyboard(),
            parse_mode="HTML",
        )
        return

    taste = compute_user_taste_score(profile)
    taste_phrase = generate_taste_phrase(profile)
    text = (
        f"🎧 <b>Твой профиль</b>\n\n"
        f"<b>Архетип:</b> {profile.profile_type}\n"
        f"<b>Вкус:</b> {taste}/100\n"
        f"<b>Твой вайб:</b> {taste_phrase}\n\n"
        "Пройти заново или добавить бота в чат — кнопки ниже."
    )
    await message.answer(
        text,
        reply_markup=get_profile_keyboard(bot_info.username),
        parse_mode="HTML",
    )


@router.message(Command("help"), F.chat.type == ChatType.PRIVATE)
async def cmd_help(message: Message, session: AsyncSession):
    """Справка только в личке."""
    text = (
        "📋 <b>Команды</b>\n\n"
        "🎧 <b>Тест:</b> /start → «Начать тест» — 4 шага, потом профиль и вкус.\n\n"
        "📊 <b>Рейтинги:</b>\n"
        "  /profile — твой архетип и вкус (0–100)\n"
        "  /top_chats — глобальный топ чатов по вкусу\n"
        "  В группе: /chat_rating — рейтинг и место этого чата\n\n"
        "👥 <b>Чаты и аналитика:</b>\n"
        "  Добавь бота в группу → /chat_scan (жанры, артисты, вайб чата)\n"
        "  /chat_rating — балл чата и сколько добрать до роста\n\n"
        "🏆 <b>Соревнования:</b>\n"
        "  После теста в группе — твоё место в рейтинге чата.\n"
        "  /top_chats — соревнование чатов между собой."
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("profile"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_profile_group(message: Message):
    """В группе: подсказка писать в личку."""
    from keyboards.inline import get_chat_test_keyboard
    bot_info = await message.bot.get_me()
    await message.answer(
        "Профиль и тест — только в личке. Открой бота в личке 👇",
        reply_markup=get_chat_test_keyboard(bot_info.username, message.chat.id),
        parse_mode="HTML",
    )


@router.message(Command("help"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_help_group(message: Message):
    """В группе: подсказка про команды здесь и в личке."""
    await message.answer(
        "Здесь: <b>/chat_scan</b> — скан вкусов чата, <b>/chat_rating</b> — рейтинг чата.\n"
        "В личке: /start, /profile, /top_chats, /help.",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "start_test")
async def start_test(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
):
    from .quiz import ask_genres

    data = await state.get_data()
    from_chat_id = data.get("from_chat_id")
    await state.update_data(from_chat_id=from_chat_id)
    await state.set_state(QuizStates.selecting_genres)
    await state.update_data(selected_genres=[])

    await ask_genres(callback.message, state, edit=True)
    await callback.answer()
