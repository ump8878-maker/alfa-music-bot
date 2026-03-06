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
    """Обработка команды /start"""
    user_id = message.from_user.id
    
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
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"🎧 <b>Йо, {message.from_user.first_name}!</b>\n\n"
            "Я — <b>Альфа</b>, бот который знает о музыке всё.\n\n"
            "🎵 Пройди короткий тест и узнай:\n"
            "├ Какой ты меломан на самом деле\n"
            "├ Кто слушает то же самое\n"
            "└ Насколько уникален твой вкус\n\n"
            "⏱ <i>Займёт меньше минуты</i>",
            reply_markup=get_start_keyboard(),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "start_test")
async def start_test(callback: CallbackQuery, state: FSMContext):
    """Начало теста"""
    from app.keyboards import get_genres_keyboard
    
    await state.set_state(TasteTestStates.selecting_genres)
    await state.update_data(selected_genres=set())
    
    await callback.message.edit_text(
        "🎵 <b>Шаг 1/5: Жанры</b>\n\n"
        "Какую музыку слушаешь чаще всего?\n"
        "Выбери до 3 жанров.",
        reply_markup=get_genres_keyboard(),
        parse_mode="HTML"
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
    """Показать профиль пользователя"""
    from aiogram.types import BufferedInputFile
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from app.services.card_generator import generate_profile_card
    
    user_id = message.from_user.id
    bot_info = await message.bot.get_me()
    
    result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    
    if profile:
        username = message.from_user.username
        
        try:
            card_buffer = generate_profile_card(profile, username)
            card_file = BufferedInputFile(card_buffer.read(), filename="profile.png")
            
            builder = InlineKeyboardBuilder()
            builder.button(text="📤 Поделиться", switch_inline_query="")
            builder.button(text="👥 Добавить в чат", url=f"https://t.me/{bot_info.username}?startgroup=true")
            builder.button(text="🔄 Пройти заново", callback_data="restart_test")
            builder.button(text="📊 Мои совпадения", callback_data="show_matches")
            builder.adjust(2, 2)
            
            await message.answer_photo(
                photo=card_file,
                caption="🎵 <b>Твой музыкальный профиль</b>",
                reply_markup=builder.as_markup(),
                parse_mode="HTML"
            )
        except Exception as e:
            profile_text = generate_profile_text(profile)
            await message.answer(
                f"📊 <b>Твой музыкальный профиль</b>\n\n{profile_text}",
                reply_markup=get_profile_keyboard(),
                parse_mode="HTML"
            )
    else:
        await message.answer(
            "У тебя пока нет профиля. Пройди тест!",
            reply_markup=get_start_keyboard()
        )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Справка по боту"""
    await message.answer(
        "🎵 <b>Альфа — бот музыкальных вкусов</b>\n\n"
        "<b>Команды:</b>\n"
        "/start — начать или перезапустить\n"
        "/profile — посмотреть свой профиль\n"
        "/matches — посмотреть совпадения\n"
        "/help — эта справка\n\n"
        "<b>В групповых чатах:</b>\n"
        "Добавь бота в чат, и когда 3+ человек "
        "пройдут тест — откроется карта вкусов чата!\n\n"
        "<b>Что умеет бот:</b>\n"
        "• Показывает музыкальные совпадения\n"
        "• Проводит баттлы вкусов\n"
        "• Запускает угадайки\n"
        "• Рекомендует события",
        parse_mode="HTML"
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


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession):
    """Статистика бота (только для админа)"""
    from config import settings
    
    # Проверяем что это владелец бота (первый пользователь или из admin_ids)
    user_id = message.from_user.id
    
    # Получаем статистику
    users_count = await session.scalar(select(func.count(User.id)))
    profiles_count = await session.scalar(select(func.count(MusicProfile.user_id)))
    chats_count = await session.scalar(select(func.count(Chat.id)).where(Chat.is_active == True))
    matches_count = await session.scalar(select(func.count(Match.id)))
    
    # Пользователи за последние 24 часа
    from datetime import datetime, timedelta
    day_ago = datetime.utcnow() - timedelta(days=1)
    new_users_24h = await session.scalar(
        select(func.count(User.id)).where(User.created_at >= day_ago)
    )
    
    # Активные за 24 часа
    active_24h = await session.scalar(
        select(func.count(User.id)).where(User.last_active_at >= day_ago)
    )
    
    # Конверсия в профиль
    conversion = (profiles_count / users_count * 100) if users_count > 0 else 0
    
    # Среднее участников на чат
    chat_members_count = await session.scalar(select(func.count(ChatMember.user_id)))
    avg_per_chat = (chat_members_count / chats_count) if chats_count > 0 else 0
    
    await message.answer(
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 <b>Пользователи:</b>\n"
        f"• Всего: {users_count}\n"
        f"• Новых за 24ч: {new_users_24h}\n"
        f"• Активных за 24ч: {active_24h}\n\n"
        f"🎧 <b>Профили:</b>\n"
        f"• Прошли тест: {profiles_count}\n"
        f"• Конверсия: {conversion:.1f}%\n\n"
        f"💬 <b>Чаты:</b>\n"
        f"• Активных чатов: {chats_count}\n"
        f"• Участников в чатах: {chat_members_count}\n"
        f"• Среднее на чат: {avg_per_chat:.1f}\n\n"
        f"🔥 <b>Совпадения:</b>\n"
        f"• Всего матчей: {matches_count}",
        parse_mode="HTML"
    )
