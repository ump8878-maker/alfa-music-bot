from typing import List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.models import MusicProfile, Match, ChatMember
from config import settings


POPULAR_ARTISTS_SET = {
    "Билли Айлиш", "The Weeknd", "Дуа Липа", "Тейлор Свифт",
    "Дрейк", "Эд Ширан", "Coldplay", "Imagine Dragons",
    "Эминем", "Ариана Гранде", "Бруно Марс"
}


def calculate_match_score(
    profile1: MusicProfile,
    profile2: MusicProfile
) -> Tuple[float, Dict[str, Any]]:
    """
    Рассчитывает совпадение между двумя профилями.
    Возвращает (score, details)
    """
    g1 = set(g.get("name", "") for g in profile1.genres)
    g2 = set(g.get("name", "") for g in profile2.genres)
    
    if g1 and g2:
        genre_intersection = g1 & g2
        genre_union = g1 | g2
        genre_score = len(genre_intersection) / len(genre_union)
    else:
        genre_intersection = set()
        genre_score = 0
    
    a1 = set(a.get("name", "") for a in profile1.artists)
    a2 = set(a.get("name", "") for a in profile2.artists)
    
    if a1 or a2:
        artist_intersection = a1 & a2
        artist_score = len(artist_intersection) / max(len(a1), len(a2), 1)
    else:
        artist_intersection = set()
        artist_score = 0
    
    eras = ["oldschool", "2000s", "2010s", "2020s"]
    era1_idx = eras.index(profile1.era) if profile1.era in eras else 2
    era2_idx = eras.index(profile2.era) if profile2.era in eras else 2
    era_diff = abs(era1_idx - era2_idx)
    era_score = 1 - (era_diff / 3)
    
    mood_score = 1.0 if profile1.mood == profile2.mood else 0.3
    
    rarity_diff = abs(profile1.rarity_score - profile2.rarity_score)
    rarity_score = 1 - rarity_diff
    
    total_score = (
        genre_score * settings.genre_weight +
        artist_score * settings.artist_weight +
        era_score * settings.era_weight +
        mood_score * settings.mood_weight +
        rarity_score * settings.rarity_weight
    )
    
    details = {
        "genre_score": genre_score,
        "artist_score": artist_score,
        "era_score": era_score,
        "mood_score": mood_score,
        "common_genres": list(genre_intersection),
        "common_artists": list(artist_intersection),
    }
    
    return round(total_score, 3), details


def calculate_rarity_score(
    genres: List[Dict[str, Any]],
    artists: List[Dict[str, Any]]
) -> float:
    """
    Рассчитывает редкость музыкального вкуса.
    0 = максимально мейнстрим, 1 = максимально редкий
    """
    mainstream_genres = {"pop", "hiphop", "rock"}
    genre_names = [g.get("name", "").lower() for g in genres]
    
    mainstream_genre_count = sum(1 for g in genre_names if g in mainstream_genres)
    genre_rarity = 1 - (mainstream_genre_count / max(len(genres), 1))
    
    artist_names = [a.get("name", "") for a in artists]
    popular_count = sum(1 for a in artist_names if a in POPULAR_ARTISTS_SET)
    artist_rarity = 1 - (popular_count / max(len(artists), 1))
    
    diversity_bonus = min(len(genres) / 3, 1) * 0.1
    
    rarity = (genre_rarity * 0.4 + artist_rarity * 0.5 + diversity_bonus)
    
    return round(min(max(rarity, 0), 1), 2)


async def recalculate_user_matches(
    session: AsyncSession,
    user_id: int
) -> List[Match]:
    """
    Пересчитывает совпадения для пользователя со всеми другими пользователями
    в тех же чатах.
    """
    user_profile_result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id == user_id)
    )
    user_profile = user_profile_result.scalar_one_or_none()
    
    if not user_profile:
        return []
    
    memberships_result = await session.execute(
        select(ChatMember.chat_id).where(ChatMember.user_id == user_id)
    )
    chat_ids = [row[0] for row in memberships_result.fetchall()]
    
    if not chat_ids:
        return []
    
    other_members_result = await session.execute(
        select(ChatMember.user_id)
        .where(
            ChatMember.chat_id.in_(chat_ids),
            ChatMember.user_id != user_id,
            ChatMember.has_completed_test == True
        )
        .distinct()
    )
    other_user_ids = [row[0] for row in other_members_result.fetchall()]
    
    if not other_user_ids:
        return []
    
    profiles_result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id.in_(other_user_ids))
    )
    other_profiles = profiles_result.scalars().all()
    
    new_matches = []
    
    for other_profile in other_profiles:
        score, details = calculate_match_score(user_profile, other_profile)
        
        user1_id = min(user_id, other_profile.user_id)
        user2_id = max(user_id, other_profile.user_id)
        
        existing_result = await session.execute(
            select(Match).where(
                Match.user1_id == user1_id,
                Match.user2_id == user2_id,
                Match.chat_id == None
            )
        )
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            existing.match_score = score
            existing.common_genres = details["common_genres"]
            existing.common_artists = details["common_artists"]
            existing.genre_score = details["genre_score"]
            existing.artist_score = details["artist_score"]
            existing.mood_score = details["mood_score"]
            existing.era_score = details["era_score"]
            new_matches.append(existing)
        else:
            match = Match(
                user1_id=user1_id,
                user2_id=user2_id,
                match_score=score,
                common_genres=details["common_genres"],
                common_artists=details["common_artists"],
                genre_score=details["genre_score"],
                artist_score=details["artist_score"],
                mood_score=details["mood_score"],
                era_score=details["era_score"],
            )
            session.add(match)
            new_matches.append(match)
    
    await session.commit()
    return new_matches


async def calculate_chat_matches(
    session: AsyncSession,
    chat_id: int
) -> List[Match]:
    """
    Рассчитывает все совпадения внутри чата.
    """
    members_result = await session.execute(
        select(ChatMember.user_id).where(
            ChatMember.chat_id == chat_id,
            ChatMember.has_completed_test == True
        )
    )
    user_ids = [row[0] for row in members_result.fetchall()]
    
    if len(user_ids) < 2:
        return []
    
    profiles_result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id.in_(user_ids))
    )
    profiles = {p.user_id: p for p in profiles_result.scalars().all()}
    
    new_matches = []
    
    for i, user1_id in enumerate(user_ids):
        for user2_id in user_ids[i+1:]:
            if user1_id not in profiles or user2_id not in profiles:
                continue
            
            score, details = calculate_match_score(
                profiles[user1_id],
                profiles[user2_id]
            )
            
            u1, u2 = min(user1_id, user2_id), max(user1_id, user2_id)
            
            existing_result = await session.execute(
                select(Match).where(
                    Match.user1_id == u1,
                    Match.user2_id == u2,
                    Match.chat_id == chat_id
                )
            )
            existing = existing_result.scalar_one_or_none()
            
            if existing:
                existing.match_score = score
                existing.common_genres = details["common_genres"]
                existing.common_artists = details["common_artists"]
            else:
                match = Match(
                    user1_id=u1,
                    user2_id=u2,
                    chat_id=chat_id,
                    match_score=score,
                    common_genres=details["common_genres"],
                    common_artists=details["common_artists"],
                    genre_score=details["genre_score"],
                    artist_score=details["artist_score"],
                    mood_score=details["mood_score"],
                    era_score=details["era_score"],
                )
                session.add(match)
                new_matches.append(match)
    
    await session.commit()
    return new_matches
