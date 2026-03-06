from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.models import Match, MusicProfile
from app.keyboards import get_match_keyboard, get_paywall_keyboard
from app.models.payment import Products

router = Router()

FREE_MATCHES_LIMIT = 1


@router.message(Command("matches"))
async def cmd_matches(message: Message, session: AsyncSession):
    """Показать совпадения пользователя"""
    user_id = message.from_user.id
    
    result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        await message.answer(
            "Сначала пройди тест, чтобы увидеть совпадения!\n"
            "Напиши /start"
        )
        return
    
    matches_result = await session.execute(
        select(Match)
        .where(
            or_(
                Match.user1_id == user_id,
                Match.user2_id == user_id
            )
        )
        .order_by(Match.match_score.desc())
        .limit(10)
    )
    matches = matches_result.scalars().all()
    
    if not matches:
        await message.answer(
            "Совпадений пока нет 😔\n\n"
            "Добавь бота в чат друзей — там точно найдутся!"
        )
        return
    
    first_match = matches[0]
    other_user_id = (
        first_match.user2_id 
        if first_match.user1_id == user_id 
        else first_match.user1_id
    )
    other_user = (
        first_match.user2 
        if first_match.user1_id == user_id 
        else first_match.user1
    )
    
    text = (
        f"🎯 <b>Твоё лучшее совпадение!</b>\n\n"
        f"<b>{other_user.display_name}</b>\n"
        f"Совпадение: <b>{first_match.score_percent}%</b>\n\n"
        f"{first_match.get_match_description()}"
    )
    
    await message.answer(
        text,
        reply_markup=get_match_keyboard(first_match.id, other_user_id),
        parse_mode="HTML"
    )
    
    if len(matches) > FREE_MATCHES_LIMIT:
        hidden_count = len(matches) - FREE_MATCHES_LIMIT
        await message.answer(
            f"🔒 <b>Ещё {hidden_count} совпадений скрыто</b>\n\n"
            f"У тебя есть сильные матчи, но они пока закрыты.",
            reply_markup=get_paywall_keyboard(Products.UNLOCK_MATCHES["id"]),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "show_matches")
async def show_matches_callback(callback: CallbackQuery, session: AsyncSession):
    """Показать совпадения через callback"""
    user_id = callback.from_user.id
    
    matches_result = await session.execute(
        select(Match)
        .where(
            or_(
                Match.user1_id == user_id,
                Match.user2_id == user_id
            )
        )
        .order_by(Match.match_score.desc())
        .limit(10)
    )
    matches = matches_result.scalars().all()
    
    if not matches:
        await callback.answer(
            "Совпадений пока нет. Добавь бота в чат друзей!",
            show_alert=True
        )
        return
    
    first_match = matches[0]
    other_user_id = (
        first_match.user2_id 
        if first_match.user1_id == user_id 
        else first_match.user1_id
    )
    other_user = (
        first_match.user2 
        if first_match.user1_id == user_id 
        else first_match.user1
    )
    
    text = (
        f"🎯 <b>Твоё лучшее совпадение!</b>\n\n"
        f"<b>{other_user.display_name}</b>\n"
        f"Совпадение: <b>{first_match.score_percent}%</b>\n\n"
        f"{first_match.get_match_description()}"
    )
    
    await callback.message.answer(
        text,
        reply_markup=get_match_keyboard(first_match.id, other_user_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "more_matches")
async def more_matches(callback: CallbackQuery, session: AsyncSession):
    """Показать больше совпадений (с paywall)"""
    await callback.message.answer(
        "🔒 <b>Открой все совпадения</b>\n\n"
        "Увидишь всех, кто совпадает с тобой по музыке.",
        reply_markup=get_paywall_keyboard(Products.UNLOCK_MATCHES["id"]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("share_match:"))
async def share_match(callback: CallbackQuery, session: AsyncSession):
    """Поделиться совпадением"""
    match_id = int(callback.data.split(":")[1])
    
    match = await session.get(Match, match_id)
    if not match:
        await callback.answer("Совпадение не найдено", show_alert=True)
        return
    
    bot_info = await callback.bot.get_me()
    
    share_text = (
        f"🎵 Мы совпали на {match.score_percent}% по музыкальному вкусу!\n\n"
        f"Проверь свои совпадения: @{bot_info.username}"
    )
    
    await callback.answer()
    await callback.message.answer(
        f"📤 <b>Поделись с друзьями:</b>\n\n{share_text}",
        parse_mode="HTML"
    )
