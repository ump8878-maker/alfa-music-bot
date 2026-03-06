from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Chat, ChatMember, Match, User, MusicProfile
from app.keyboards.data import CHAT_ROLES


async def generate_chat_map_text(session: AsyncSession, chat_id: int) -> str:
    """Генерирует текст карты вкусов чата"""
    
    members_result = await session.execute(
        select(ChatMember)
        .where(
            ChatMember.chat_id == chat_id,
            ChatMember.has_completed_test == True
        )
    )
    members = members_result.scalars().all()
    
    user_ids = [m.user_id for m in members]
    
    users_result = await session.execute(
        select(User).where(User.id.in_(user_ids))
    )
    users = {u.id: u for u in users_result.scalars().all()}
    
    profiles_result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id.in_(user_ids))
    )
    profiles = {p.user_id: p for p in profiles_result.scalars().all()}
    
    matches_result = await session.execute(
        select(Match)
        .where(Match.chat_id == chat_id)
        .order_by(Match.match_score.desc())
    )
    matches = matches_result.scalars().all()
    
    lines = [f"👥 <b>Участников:</b> {len(members)}"]
    lines.append("")
    
    if matches:
        best_match = matches[0]
        user1 = users.get(best_match.user1_id)
        user2 = users.get(best_match.user2_id)
        
        if user1 and user2:
            lines.append(
                f"🔥 <b>Лучшее совпадение:</b>\n"
                f"   {user1.display_name} и {user2.display_name} — "
                f"{best_match.score_percent}%"
            )
            
            if best_match.common_genres:
                common = ", ".join(best_match.common_genres[:2])
                lines.append(f"   <i>Оба любят: {common}</i>")
            
            lines.append("")
    
    roles = await assign_chat_roles(profiles, users)
    
    if roles.get("rare"):
        user = roles["rare"]
        lines.append(f"🦄 <b>Редкий зверь:</b> {user.display_name}")
    
    if roles.get("mainstream"):
        user = roles["mainstream"]
        lines.append(f"📻 <b>Попсовик чата:</b> {user.display_name}")
    
    if roles.get("rock"):
        user = roles["rock"]
        lines.append(f"🎸 <b>Рок-душа:</b> {user.display_name}")
    
    if roles.get("melancholic"):
        user = roles["melancholic"]
        lines.append(f"🌙 <b>Меланхолик:</b> {user.display_name}")
    
    if roles.get("party"):
        user = roles["party"]
        lines.append(f"🪩 <b>Тусовщик:</b> {user.display_name}")
    
    return "\n".join(lines)


async def assign_chat_roles(
    profiles: dict,
    users: dict
) -> dict:
    """Назначает роли участникам чата на основе их профилей"""
    
    roles = {}
    
    rare_user = None
    rare_score = 0
    mainstream_user = None
    mainstream_score = 1
    
    for user_id, profile in profiles.items():
        if profile.rarity_score > rare_score:
            rare_score = profile.rarity_score
            rare_user = users.get(user_id)
        
        if profile.rarity_score < mainstream_score:
            mainstream_score = profile.rarity_score
            mainstream_user = users.get(user_id)
    
    if rare_user and rare_score > 0.6:
        roles["rare"] = rare_user
    
    if mainstream_user and mainstream_score < 0.4:
        roles["mainstream"] = mainstream_user
    
    for user_id, profile in profiles.items():
        genre_names = [g.get("name", "").lower() for g in profile.genres]
        
        if "rock" in genre_names or "metal" in genre_names:
            if "rock" not in roles:
                roles["rock"] = users.get(user_id)
        
        if profile.mood == "melancholic":
            if "melancholic" not in roles:
                roles["melancholic"] = users.get(user_id)
        
        if "electronic" in genre_names or profile.mood == "energetic":
            if "party" not in roles:
                roles["party"] = users.get(user_id)
    
    return roles
