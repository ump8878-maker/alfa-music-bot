from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User, MusicProfile
from keyboards import get_start_keyboard, get_profile_keyboard
from states import QuizStates
from services.rating_helpers import compute_user_taste_score

router = Router()


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    command: CommandObject | None = None,
):
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
        "🎧 <b>Музыкальный тест</b>\n\n"
        "Четыре шага — жанры, артисты, когда слушаешь, настроение.\n\n"
        "📊 <b>Рейтинги:</b> свой вкус — /profile, топ чатов — /top_chats.\n"
        "👥 <b>В группе</b> (добавь бота): скан чата — /chat_scan, рейтинг чата — /chat_rating.\n"
        "🏆 Соревнование: место в рейтинге чата после теста, топ чатов — /top_chats."
    )
    await message.answer(
        text,
        reply_markup=get_start_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message, session: AsyncSession):
    """Профиль: архетип, вкус, кнопки «Пройти заново» и «Добавить в чат»."""
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
    text = (
        f"🎧 <b>Твой профиль</b>\n\n"
        f"<b>Архетип:</b> {profile.profile_type}\n"
        f"<b>Вкус:</b> {taste}/100\n\n"
        "Пройти заново или добавить бота в чат — кнопки ниже."
    )
    await message.answer(
        text,
        reply_markup=get_profile_keyboard(bot_info.username),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message, session: AsyncSession):
    """Справка: рейтинги, чаты, аналитика, соревнования."""
    bot_info = await message.bot.get_me()
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
