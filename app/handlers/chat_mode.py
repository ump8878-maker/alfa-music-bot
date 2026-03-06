from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import User, Chat, ChatMember, MusicProfile, Match
from app.keyboards import get_chat_map_keyboard
from app.keyboards.inline import InlineKeyboardBuilder
from app.services.matching import calculate_chat_matches
from app.services.chat_map import generate_chat_map_text

router = Router()

MIN_PARTICIPANTS = 3


@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def bot_added_to_chat(event: ChatMemberUpdated, session: AsyncSession):
    """Бот добавлен в чат"""
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
        )
        session.add(chat)
    else:
        chat.is_active = True
        chat.title = event.chat.title
    
    result = await session.execute(
        select(ChatMember).where(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == user_id
        )
    )
    member = result.scalar_one_or_none()
    
    if not member:
        member = ChatMember(
            chat_id=chat_id,
            user_id=user_id,
        )
        session.add(member)
    
    profile_result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id == user_id)
    )
    has_profile = profile_result.scalar_one_or_none() is not None
    member.has_completed_test = has_profile
    
    await session.commit()
    
    bot_info = await event.bot.get_me()
    
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🎵 Пройти тест",
        url=f"https://t.me/{bot_info.username}?start=from_chat_{chat_id}"
    )
    
    completed = 1 if has_profile else 0
    remaining = MIN_PARTICIPANTS - completed
    
    await event.answer(
        f"🎵 <b>Привет! Я покажу, кто с кем тут совпадает по музыке.</b>\n\n"
        f"Пройдите тест (60 сек) — и увидите:\n"
        f"• Карту вкусов чата\n"
        f"• Лучшие совпадения\n"
        f"• Кто тут меломан, а кто попсовик\n\n"
        f"{'✅ ' + event.from_user.first_name + ' уже прошёл тест!\n' if has_profile else ''}"
        f"📊 Участников: {completed}/{MIN_PARTICIPANTS}\n"
        f"{'Ещё ' + str(remaining) + ' человек — и открою карту вкусов!' if remaining > 0 else ''}",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
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
    username: str
):
    """Уведомление чата о новом участнике"""
    result = await session.execute(
        select(func.count(ChatMember.user_id)).where(
            ChatMember.chat_id == chat_id,
            ChatMember.has_completed_test == True
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
            f"{int(completed_count/MIN_PARTICIPANTS*100)}%\n\n"
            f"Ещё {remaining} {'человек' if remaining > 1 else 'человека'} — и открою карту вкусов!",
            parse_mode="HTML"
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
