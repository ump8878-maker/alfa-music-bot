# Квиз: 4 вопроса — жанры, артисты, когда слушаешь, настроение
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import MusicProfile, User, ChatMember, QuizResult
from app.states import TasteTestStates
from app.keyboards import (
    get_genres_keyboard,
    get_artists_keyboard,
    get_mood_keyboard,
    get_when_listen_keyboard,
    get_profile_keyboard,
    get_chat_invite_keyboard,
    get_chat_test_keyboard,
)
from app.keyboards.data import GENRES, POPULAR_ARTISTS, POPULAR_ARTISTS_RU
from app.services.profile_card import (
    generate_profile_text,
    generate_individual_analytics_block,
)
from app.services.matching import calculate_rarity_score, recalculate_user_matches
from app.rating import (
    compute_user_taste_score,
    get_chat_member_ranking,
    get_user_rank_in_chat,
)
from app.chat_rating import calculate_chat_rating
from app.utils.humor import get_top_comment
import random

router = Router()


def _get_genre_display_name(genre_id: str) -> str:
    for g in GENRES:
        if g["id"] == genre_id:
            return f"{g['emoji']} {g['name']}"
    return genre_id


@router.callback_query(TasteTestStates.selecting_genres, F.data.startswith("genre:"))
async def select_genre(callback: CallbackQuery, state: FSMContext):
    genre_id = callback.data.split(":")[1]
    data = await state.get_data()
    selected = set(data.get("selected_genres") or [])
    if genre_id in selected:
        selected.discard(genre_id)
    elif len(selected) < 4:
        selected.add(genre_id)
    else:
        await callback.answer("Максимум 4 жанра!", show_alert=True)
        return
    await state.update_data(selected_genres=list(selected))
    await callback.message.edit_reply_markup(reply_markup=get_genres_keyboard(selected))
    await callback.answer()


@router.callback_query(TasteTestStates.selecting_genres, F.data == "genres_done")
async def genres_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_genres") or []
    if not selected:
        await callback.answer("Выбери хотя бы один жанр!", show_alert=True)
        return
    genres_list = list(selected)
    cached_artists_by_genre = {}
    for genre in genres_list:
        artists = []
        if genre in POPULAR_ARTISTS:
            artists = POPULAR_ARTISTS[genre].copy()
        ru = [a for a in POPULAR_ARTISTS_RU if a not in artists]
        random.shuffle(ru)
        artists.extend(ru[:4])
        random.shuffle(artists)
        cached_artists_by_genre[genre] = artists[:12]
    await state.set_state(TasteTestStates.selecting_artists)
    await state.update_data(
        selected_artists=set(),
        current_genre_idx=0,
        genres_list=genres_list,
        cached_artists_by_genre=cached_artists_by_genre,
    )
    first_genre = genres_list[0]
    genre_name = _get_genre_display_name(first_genre)
    total = len(genres_list)
    await callback.message.edit_text(
        f"🎤 <b>Шаг 2/4: Артисты</b>\n\n"
        f"<b>{genre_name}</b> (1/{total})\nВыбери артистов или пропусти:",
        reply_markup=get_artists_keyboard(
            genres_list, set(), 0, cached_artists_by_genre
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(TasteTestStates.selecting_artists, F.data.startswith("artist:"))
async def select_artist(callback: CallbackQuery, state: FSMContext):
    artist_name = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected = set(data.get("selected_artists") or [])
    genres_list = data.get("genres_list", [])
    current_genre_idx = data.get("current_genre_idx", 0)
    cached = data.get("cached_artists_by_genre", {})
    if artist_name in selected:
        selected.discard(artist_name)
    elif len(selected) < 10:
        selected.add(artist_name)
    else:
        await callback.answer("Максимум 10 артистов!", show_alert=True)
        return
    await state.update_data(selected_artists=selected)
    await callback.message.edit_reply_markup(
        reply_markup=get_artists_keyboard(
            genres_list, selected, current_genre_idx, cached
        )
    )
    await callback.answer()


@router.callback_query(TasteTestStates.selecting_artists, F.data.startswith("artists_genre:"))
async def switch_genre(callback: CallbackQuery, state: FSMContext):
    new_idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected = data.get("selected_artists") or set()
    genres_list = data.get("genres_list", [])
    cached = data.get("cached_artists_by_genre", {})
    await state.update_data(current_genre_idx=new_idx)
    current_genre = genres_list[new_idx]
    genre_name = _get_genre_display_name(current_genre)
    total = len(genres_list)
    await callback.message.edit_text(
        f"🎤 <b>Шаг 2/4: Артисты</b>\n\n"
        f"<b>{genre_name}</b> ({new_idx + 1}/{total})\nВыбери артистов или пропусти:",
        reply_markup=get_artists_keyboard(
            genres_list, selected, new_idx, cached
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(TasteTestStates.selecting_artists, F.data.in_({"artists_done", "artists_skip"}))
async def artists_done(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TasteTestStates.selecting_when_listen)
    await callback.message.edit_text(
        "🕐 <b>Шаг 3/4: Когда слушаешь?</b>\n\n"
        "Когда вы чаще слушаете музыку?",
        reply_markup=get_when_listen_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(TasteTestStates.selecting_when_listen, F.data.startswith("when:"))
async def select_when_listen(callback: CallbackQuery, state: FSMContext):
    when_id = callback.data.split(":")[1]
    await state.update_data(listening_time=when_id)
    await state.set_state(TasteTestStates.selecting_mood)
    await callback.message.edit_text(
        "🌙 <b>Шаг 4/4: Музыкальное настроение</b>\n\n"
        "Какую музыку выбираешь чаще?",
        reply_markup=get_mood_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(TasteTestStates.selecting_mood, F.data.startswith("mood:"))
async def select_mood_and_finish(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    from aiogram.types import BufferedInputFile
    from app.services.card_generator import generate_profile_card

    mood_id = callback.data.split(":")[1]
    data = await state.get_data()
    user_id = callback.from_user.id
    chat_id = data.get("from_chat_id")  # откуда пришли в квиз (для публикации в чат)

    selected_genres = list(data.get("selected_genres") or [])
    selected_artists = list(data.get("selected_artists") or [])
    listening_time = data.get("listening_time") or "anytime"

    genres = [{"name": g, "weight": 1.0} for g in selected_genres]
    artists = [{"name": a} for a in selected_artists]
    rarity = calculate_rarity_score(genres, artists)

    result = await session.execute(select(MusicProfile).where(MusicProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if profile:
        profile.genres = genres
        profile.artists = artists
        profile.mood = mood_id
        profile.listening_time = listening_time
        profile.rarity_score = rarity
        profile.era = profile.era or "2010s"
        profile.language_pref = profile.language_pref or "both"
    else:
        profile = MusicProfile(
            user_id=user_id,
            genres=genres,
            artists=artists,
            mood=mood_id,
            listening_time=listening_time,
            rarity_score=rarity,
            era="2010s",
            language_pref="both",
        )
        session.add(profile)

    taste_score = compute_user_taste_score(profile)
    user = await session.get(User, user_id)
    if user:
        user.score = float(taste_score)

    quiz_result = QuizResult(
        user_id=user_id,
        chat_id=chat_id,
        answers={
            "genres": selected_genres,
            "artists": selected_artists,
            "listening_time": listening_time,
            "mood": mood_id,
        },
        score=float(taste_score),
    )
    session.add(quiz_result)

    await session.commit()
    await session.refresh(profile)

    await recalculate_user_matches(session, user_id)
    if chat_id:
        await calculate_chat_rating(session, chat_id)
        from app.handlers.chat_mode import ensure_chat_member_completed
        await ensure_chat_member_completed(session, chat_id, user_id)

    await state.clear()

    bot_info = await callback.bot.get_me()
    username = callback.from_user.username or callback.from_user.first_name or ""

    # Индивидуальная аналитика
    analytics_text = generate_individual_analytics_block(profile)

    # Совпадения с чатом (если есть чат)
    matches_lines = []
    avg_match_percent = 0
    if chat_id:
        from app.services.matching import calculate_match_score
        ranking = await get_chat_member_ranking(session, chat_id)
        my_rank = await get_user_rank_in_chat(session, user_id, chat_id)
        scores_for_avg = []
        for u, p, score in ranking:
            if u.id == user_id:
                continue
            match_score, _ = calculate_match_score(profile, p)
            pct = int(match_score * 100)
            matches_lines.append(f"{u.display_name} — {pct}%")
            scores_for_avg.append(match_score)
        if matches_lines:
            analytics_text += "\n\n<b>Совпадения:</b>\n" + "\n".join(matches_lines[:10])
        if scores_for_avg:
            avg_match_percent = int(sum(scores_for_avg) / len(scores_for_avg) * 100)
        if my_rank:
            comment = get_top_comment(my_rank)
            analytics_text += f"\n\n🏆 Ваше место в чате: <b>{my_rank}</b>. {comment.capitalize()}"

    try:
        card_buffer = generate_profile_card(profile, username)
        card_file = BufferedInputFile(card_buffer.read(), filename="profile.png")
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="📤 Поделиться", switch_inline_query="")
        builder.button(
            text="👥 Добавить в чат",
            url=f"https://t.me/{bot_info.username}?startgroup=true",
        )
        builder.button(text="🔄 Пройти заново", callback_data="restart_test")
        builder.adjust(2, 1)
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=card_file,
            caption=analytics_text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.edit_text(
            analytics_text + "\n\n💡 Добавь меня в чат — покажу рейтинг и совпадения!",
            reply_markup=get_chat_invite_keyboard(bot_info.username),
            parse_mode="HTML",
        )

    # Публикация в чат: «Юра прошел тест», профиль, совпадение, кнопка
    if chat_id:
        from app.handlers.chat_mode import post_quiz_result_to_chat
        await post_quiz_result_to_chat(
            callback.bot,
            session,
            chat_id,
            user_id=user_id,
            profile=profile,
            match_percent=avg_match_percent,
        )
    await callback.answer("🎉 Профиль создан!")
