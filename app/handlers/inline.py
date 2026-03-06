from aiogram import Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib

from app.models import MusicProfile, User
from app.services.profile_card import generate_profile_text

router = Router()


@router.inline_query()
async def inline_query_handler(query: InlineQuery, session: AsyncSession):
    """Обработка inline-запросов"""
    user_id = query.from_user.id
    bot_info = await query.bot.get_me()
    
    results = []
    
    # Получаем профиль пользователя
    profile_result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()
    
    if profile:
        # 1. Поделиться своим профилем
        profile_text = generate_profile_text(profile)
        
        share_text = (
            f"🎵 <b>Мой музыкальный профиль</b>\n\n"
            f"{profile_text}\n\n"
            f"Узнай свой вкус → @{bot_info.username}"
        )
        
        results.append(
            InlineQueryResultArticle(
                id=hashlib.md5(f"profile_{user_id}".encode()).hexdigest(),
                title="🎧 Мой музыкальный профиль",
                description=f"{profile.profile_type} • Редкость: {int(profile.rarity_score * 100)}%",
                thumbnail_url="https://img.icons8.com/color/96/headphones.png",
                input_message_content=InputTextMessageContent(
                    message_text=share_text,
                    parse_mode="HTML"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🎵 Узнать свой вкус",
                        url=f"https://t.me/{bot_info.username}?start=inline"
                    )]
                ])
            )
        )
        
        # 2. Пригласить сравнить вкусы
        compare_text = (
            f"🎵 <b>Сравним музыкальные вкусы?</b>\n\n"
            f"Я прошёл тест — {profile.profile_type}\n"
            f"Пройди тоже и узнаем, насколько мы совпадаем!\n\n"
            f"→ @{bot_info.username}"
        )
        
        results.append(
            InlineQueryResultArticle(
                id=hashlib.md5(f"compare_{user_id}".encode()).hexdigest(),
                title="🔥 Сравнить вкусы",
                description="Пригласи друга пройти тест",
                thumbnail_url="https://img.icons8.com/color/96/compare.png",
                input_message_content=InputTextMessageContent(
                    message_text=compare_text,
                    parse_mode="HTML"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🎵 Пройти тест",
                        url=f"https://t.me/{bot_info.username}?start=compare_{user_id}"
                    )]
                ])
            )
        )
        
        # 3. Добавить бота в чат
        results.append(
            InlineQueryResultArticle(
                id=hashlib.md5(f"addchat_{user_id}".encode()).hexdigest(),
                title="👥 Добавить бота в чат",
                description="Открой карту вкусов своей компании",
                thumbnail_url="https://img.icons8.com/color/96/conference-call.png",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"🎵 <b>Давайте узнаем, кто с кем совпадает по музыке!</b>\n\n"
                        f"Добавьте @{bot_info.username} в чат,\n"
                        f"пройдите тест — и откроется карта вкусов!\n\n"
                        f"• Лучшие совпадения\n"
                        f"• Баттлы вкусов\n"
                        f"• Угадайки про друзей"
                    ),
                    parse_mode="HTML"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="➕ Добавить в чат",
                        url=f"https://t.me/{bot_info.username}?startgroup=true"
                    )]
                ])
            )
        )
    
    else:
        # Пользователь ещё не прошёл тест
        results.append(
            InlineQueryResultArticle(
                id=hashlib.md5(f"notest_{user_id}".encode()).hexdigest(),
                title="🎵 Пройди тест первым!",
                description="Узнай свой музыкальный вкус за 60 секунд",
                thumbnail_url="https://img.icons8.com/color/96/headphones.png",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"🎵 <b>Узнай свой музыкальный ДНК!</b>\n\n"
                        f"Пройди тест за 60 секунд и узнай:\n"
                        f"• С кем совпадаешь по вкусу\n"
                        f"• Насколько редкий твой вкус\n"
                        f"• Кто твой музыкальный близнец\n\n"
                        f"→ @{bot_info.username}"
                    ),
                    parse_mode="HTML"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🎵 Пройти тест",
                        url=f"https://t.me/{bot_info.username}?start=inline"
                    )]
                ])
            )
        )
    
    await query.answer(results, cache_time=60, is_personal=True)
