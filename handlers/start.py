from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from keyboards import get_start_keyboard
from states import QuizStates

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
        "Четыре шага — жанры, артисты, когда слушаешь, настроение.\n"
        "В группах увидишь скан чата и рейтинг."
    )
    await message.answer(
        text,
        reply_markup=get_start_keyboard(),
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
