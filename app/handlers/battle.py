from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import random

from app.models import Battle, BattleVote, ChatMember, User, MusicProfile
from app.keyboards import get_battle_keyboard

router = Router()

BATTLE_DURATION_HOURS = 2


async def create_random_battle(bot, session: AsyncSession, chat_id: int) -> Battle | None:
    """Создание случайного баттла в чате"""
    result = await session.execute(
        select(ChatMember)
        .where(
            ChatMember.chat_id == chat_id,
            ChatMember.has_completed_test == True
        )
    )
    members = result.scalars().all()
    
    if len(members) < 2:
        return None
    
    selected = random.sample(members, 2)
    user1_id = selected[0].user_id
    user2_id = selected[1].user_id
    
    user1 = await session.get(User, user1_id)
    user2 = await session.get(User, user2_id)
    
    battle = Battle(
        chat_id=chat_id,
        user1_id=user1_id,
        user2_id=user2_id,
        ends_at=datetime.utcnow() + timedelta(hours=BATTLE_DURATION_HOURS),
    )
    session.add(battle)
    await session.commit()
    await session.refresh(battle)
    
    text = (
        f"⚔️ <b>МУЗЫКАЛЬНЫЙ БАТТЛ</b>\n\n"
        f"🅰️ <b>{user1.display_name}</b>\n"
        f"vs\n"
        f"🅱️ <b>{user2.display_name}</b>\n\n"
        f"Чей вкус круче? Голосуйте!\n\n"
        f"⏱ Голосование закроется через {BATTLE_DURATION_HOURS} часа"
    )
    
    message = await bot.send_message(
        chat_id,
        text,
        reply_markup=get_battle_keyboard(battle.id, user1_id, user2_id),
        parse_mode="HTML"
    )
    
    battle.message_id = message.message_id
    await session.commit()
    
    return battle


@router.callback_query(F.data.startswith("vote:"))
async def vote_in_battle(callback: CallbackQuery, session: AsyncSession):
    """Голосование в баттле"""
    parts = callback.data.split(":")
    battle_id = int(parts[1])
    voted_for_id = int(parts[2])
    voter_id = callback.from_user.id
    
    battle = await session.get(Battle, battle_id)
    
    if not battle:
        await callback.answer("Баттл не найден", show_alert=True)
        return
    
    if not battle.is_active:
        await callback.answer("Баттл уже завершён", show_alert=True)
        return
    
    if voter_id in (battle.user1_id, battle.user2_id):
        await callback.answer("Нельзя голосовать за себя!", show_alert=True)
        return
    
    result = await session.execute(
        select(BattleVote).where(
            BattleVote.battle_id == battle_id,
            BattleVote.voter_id == voter_id
        )
    )
    existing_vote = result.scalar_one_or_none()
    
    if existing_vote:
        if existing_vote.voted_for_id == voted_for_id:
            await callback.answer("Ты уже голосовал!", show_alert=True)
            return
        
        if existing_vote.voted_for_id == battle.user1_id:
            battle.votes_user1 -= 1
        else:
            battle.votes_user2 -= 1
        
        existing_vote.voted_for_id = voted_for_id
    else:
        vote = BattleVote(
            battle_id=battle_id,
            voter_id=voter_id,
            voted_for_id=voted_for_id,
        )
        session.add(vote)
    
    if voted_for_id == battle.user1_id:
        battle.votes_user1 += 1
    else:
        battle.votes_user2 += 1
    
    await session.commit()
    
    user1 = await session.get(User, battle.user1_id)
    user2 = await session.get(User, battle.user2_id)
    
    text = (
        f"⚔️ <b>МУЗЫКАЛЬНЫЙ БАТТЛ</b>\n\n"
        f"🅰️ <b>{user1.display_name}</b> — {battle.votes_user1} голосов\n"
        f"vs\n"
        f"🅱️ <b>{user2.display_name}</b> — {battle.votes_user2} голосов\n\n"
        f"Чей вкус круче? Голосуйте!\n"
        f"Всего голосов: {battle.total_votes}"
    )
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_battle_keyboard(battle.id, battle.user1_id, battle.user2_id),
            parse_mode="HTML"
        )
    except:
        pass
    
    await callback.answer("✅ Голос принят!")


async def end_battle(bot, session: AsyncSession, battle_id: int):
    """Завершение баттла"""
    battle = await session.get(Battle, battle_id)
    
    if not battle or not battle.is_active:
        return
    
    battle.status = "completed"
    
    user1 = await session.get(User, battle.user1_id)
    user2 = await session.get(User, battle.user2_id)
    
    if battle.votes_user1 > battle.votes_user2:
        winner = user1
        battle.winner_id = battle.user1_id
        result_text = f"🏆 Победитель: <b>{user1.display_name}</b>!"
    elif battle.votes_user2 > battle.votes_user1:
        winner = user2
        battle.winner_id = battle.user2_id
        result_text = f"🏆 Победитель: <b>{user2.display_name}</b>!"
    else:
        result_text = "🤝 Ничья! Оба вкуса одинаково круты."
    
    await session.commit()
    
    text = (
        f"⚔️ <b>БАТТЛ ЗАВЕРШЁН</b>\n\n"
        f"🅰️ {user1.display_name} — {battle.votes_user1}\n"
        f"🅱️ {user2.display_name} — {battle.votes_user2}\n\n"
        f"{result_text}"
    )
    
    await bot.send_message(
        battle.chat_id,
        text,
        parse_mode="HTML"
    )
