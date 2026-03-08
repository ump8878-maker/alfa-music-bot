# Квиз: жанры → артисты → когда слушаешь → зашкварные жанры
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User, ChatMember, MusicProfile, QuizResult
from keyboards import (
    get_genre_keyboard,
    get_artist_keyboard,
    get_when_listen_keyboard,
    get_guilty_keyboard,
    get_finish_quiz_keyboard,
)
from keyboards.data import GENRES
from states import QuizStates
from services.rating_helpers import (
    compute_user_taste_score,
    compute_rarity_score,
    get_chat_member_ranking,
    get_user_rank_in_chat,
    get_taste_score_breakdown,
    get_taste_explanation,
    get_competitor_above,
)
from services.chat_rating import (
    calculate_chat_rating,
    get_chat_rank,
    get_needed_participants_for_next_rank,
)
from utils.humor import get_top_comment
from utils.taste_phrase import generate_taste_phrase

router = Router()


async def ask_genres(message: Message, state: FSMContext, edit: bool = False):
    data = await state.get_data()
    selected = set(data.get("selected_genres") or [])
    text = "🎸 <b>Шаг 1/4: Жанры</b>\n\nВыбери до 4 жанров, затем «Далее»."
    kb = get_genre_keyboard(selected)
    if edit and message:
        await message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(QuizStates.selecting_genres, F.data.startswith("genre:"))
async def select_genre(callback: CallbackQuery, state: FSMContext):
    genre_id = callback.data.split(":")[1]
    data = await state.get_data()
    selected = set(data.get("selected_genres") or [])
    if genre_id in selected:
        selected.discard(genre_id)
    elif len(selected) < 4:
        selected.add(genre_id)
    else:
        await callback.answer("Максимум 4 жанра", show_alert=True)
        return
    await state.update_data(selected_genres=list(selected))
    await callback.message.edit_reply_markup(reply_markup=get_genre_keyboard(selected))
    await callback.answer()


@router.callback_query(QuizStates.selecting_genres, F.data == "genres_done")
async def genres_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_genres") or []
    if not selected:
        await callback.answer("Выбери хотя бы один жанр", show_alert=True)
        return
    genres_list = list(selected)
    await state.set_state(QuizStates.selecting_artists)
    await state.update_data(
        selected_artists=[],
        genres_list=genres_list,
    )
    text = "🎤 <b>Шаг 2/4: Артисты</b>\n\nВыбери любимых артистов или пропусти."
    await callback.message.edit_text(
        text,
        reply_markup=get_artist_keyboard(genres_list, set()),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(QuizStates.selecting_artists, F.data == "artist:custom")
async def ask_custom_artist(callback: CallbackQuery, state: FSMContext):
    await state.set_state(QuizStates.entering_custom_artist)
    await callback.message.answer(
        "Напиши имя артиста или несколько через запятую — добавлю в выбор."
    )
    await callback.answer()


@router.message(QuizStates.entering_custom_artist, F.text)
async def add_custom_artist(message: Message, state: FSMContext):
    data = await state.get_data()
    selected = set(data.get("selected_artists") or [])
    genres_list = data.get("genres_list", [])
    parts = [p.strip() for p in (message.text or "").split(",") if p.strip()]
    for name in parts:
        if name and len(name) <= 100:
            selected.add(name)
    await state.update_data(selected_artists=list(selected))
    await state.set_state(QuizStates.selecting_artists)
    count = len(parts)
    await message.answer(
        f"Добавлено: {', '.join(parts[:5])}{'…' if count > 5 else ''}. Выбери ещё или нажми «Готово».",
        reply_markup=get_artist_keyboard(genres_list, selected),
    )


@router.callback_query(QuizStates.selecting_artists, F.data.startswith("artist:"))
async def select_artist(callback: CallbackQuery, state: FSMContext):
    artist_name = callback.data.split(":", 1)[1]
    if artist_name == "custom":
        return
    data = await state.get_data()
    selected = set(data.get("selected_artists") or [])
    genres_list = data.get("genres_list", [])
    if artist_name in selected:
        selected.discard(artist_name)
    else:
        selected.add(artist_name)
    await state.update_data(selected_artists=list(selected))
    await callback.message.edit_reply_markup(
        reply_markup=get_artist_keyboard(genres_list, selected)
    )
    await callback.answer()


@router.callback_query(QuizStates.selecting_artists, F.data == "artists_done")
async def artists_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected_artists") or []
    await state.set_state(QuizStates.selecting_when_listen)
    text = "🕐 <b>Шаг 3/4: Когда чаще слушаешь музыку?</b>"
    await callback.message.edit_text(
        text,
        reply_markup=get_when_listen_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(QuizStates.selecting_artists, F.data == "artists_skip")
async def artists_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(selected_artists=[])
    await state.set_state(QuizStates.selecting_when_listen)
    text = "🕐 <b>Шаг 3/4: Когда чаще слушаешь музыку?</b>"
    await callback.message.edit_text(
        text,
        reply_markup=get_when_listen_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(QuizStates.selecting_when_listen, F.data.startswith("when:"))
async def select_when(callback: CallbackQuery, state: FSMContext):
    when_id = callback.data.split(":")[1]
    await state.update_data(listening_time=when_id, selected_guilty=[])
    await state.set_state(QuizStates.selecting_guilty)
    text = (
        "🤮 <b>Шаг 4/4: Какие стили считаешь самыми зашкварными?</b>\n\n"
        "Выбери жанры, которые терпеть не можешь, или пропусти."
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_guilty_keyboard(set()),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(QuizStates.selecting_guilty, F.data.startswith("guilty:"))
async def select_guilty(callback: CallbackQuery, state: FSMContext):
    genre_id = callback.data.split(":")[1]
    data = await state.get_data()
    selected = set(data.get("selected_guilty") or [])
    if genre_id in selected:
        selected.discard(genre_id)
    elif len(selected) < 4:
        selected.add(genre_id)
    else:
        await callback.answer("Максимум 4 зашкварных жанра", show_alert=True)
        return
    await state.update_data(selected_guilty=list(selected))
    await callback.message.edit_reply_markup(reply_markup=get_guilty_keyboard(selected))
    await callback.answer()


# Fallback: пользователи, застрявшие в старом selecting_mood → перенаправляем на guilty
@router.callback_query(QuizStates.selecting_mood)
async def legacy_mood_redirect(callback: CallbackQuery, state: FSMContext):
    await state.update_data(selected_guilty=[])
    await state.set_state(QuizStates.selecting_guilty)
    text = (
        "🤮 <b>Шаг 4/4: Какие стили считаешь самыми зашкварными?</b>\n\n"
        "Выбери жанры, которые терпеть не можешь, или пропусти."
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_guilty_keyboard(set()),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(QuizStates.selecting_guilty, F.data == "guilty_done")
async def guilty_done_and_finish(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
):
    data = await state.get_data()
    user_id = callback.from_user.id
    chat_id = data.get("from_chat_id")
    selected_genres = list(data.get("selected_genres") or [])
    selected_artists = list(data.get("selected_artists") or [])
    listening_time = data.get("listening_time") or "anytime"
    guilty = list(data.get("selected_guilty") or [])

    genres = [{"name": g, "weight": 1.0} for g in selected_genres]
    artists = [{"name": a} for a in selected_artists]
    rarity = compute_rarity_score(selected_artists)

    result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile:
        profile.genres = genres
        profile.artists = artists
        profile.guilty_genres = guilty
        profile.listening_time = listening_time
        profile.rarity_score = rarity
    else:
        profile = MusicProfile(
            user_id=user_id,
            genres=genres,
            artists=artists,
            guilty_genres=guilty,
            listening_time=listening_time,
            rarity_score=rarity,
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
            "guilty_genres": guilty,
        },
        score=float(taste_score),
    )
    session.add(quiz_result)
    await session.flush()
    await session.refresh(profile)

    if chat_id:
        await calculate_chat_rating(session, chat_id)
        from services.quiz_actions import ensure_chat_member_completed, post_quiz_result_to_chat, try_send_growth_message
        await ensure_chat_member_completed(session, chat_id, user_id)
        await post_quiz_result_to_chat(
            callback.bot,
            session,
            chat_id,
            user_id=user_id,
            profile=profile,
        )
        await try_send_growth_message(callback.bot, session, chat_id)

    await state.clear()

    # Итог: архетип, разбивка балла, фраза о вкусе, шаринг
    breakdown = get_taste_score_breakdown(profile)
    taste_phrase = generate_taste_phrase(profile)
    bot_info = await callback.bot.get_me()
    share_link = f"https://t.me/{bot_info.username}"
    share_line = f"Архетип: {profile.profile_type}, вкус {taste_score}/100. Пройти тест: {share_link}"

    result_text = (
        f"🎉 <b>Готово!</b>\n\n"
        f"<b>Профиль:</b> {profile.profile_type}\n"
        f"<b>Вкус:</b> {breakdown.total}/100\n"
        f"<i>{breakdown.to_short_str()}</i>\n"
        f"<b>Твой вайб:</b> {taste_phrase}\n\n"
        f"📤 <i>Скопируй и поделись:</i>\n<code>{share_line}</code>\n"
    )
    if guilty:
        from keyboards.data import GENRES as ALL_GENRES
        guilty_map = {g["id"]: g["name"] for g in ALL_GENRES}
        guilty_names = [guilty_map.get(g, g) for g in guilty]
        result_text += f"\n🤮 <b>Зашквар:</b> {', '.join(guilty_names)}\n"
    if chat_id:
        my_rank = await get_user_rank_in_chat(session, user_id, chat_id)
        if my_rank:
            comment = get_top_comment(my_rank)
            result_text += f"\n🏆 <b>Место в чате: #{my_rank}</b>. {comment.capitalize()}"
        competitor = await get_competitor_above(session, chat_id, user_id)
        if competitor:
            rank_above, user_above, score_above = competitor
            need_pts = score_above - taste_score + 1
            name_above = user_above.display_name or user_above.mention or "соперник"
            if len(name_above) > 18:
                name_above = name_above[:15] + "…"
            result_text += f"\n🔥 <b>Обгони {name_above}</b> — ещё <b>{need_pts}</b> баллов до #{rank_above} места!"
        rank = await get_chat_rank(session, chat_id)
        needed = await get_needed_participants_for_next_rank(session, chat_id)
        if rank:
            pos, total = rank
            result_text += f"\n📊 Рейтинг чата: <b>#{pos}</b> из {total}"
        if needed and needed.needed_count > 0:
            result_text += f"\nЕщё {needed.needed_count} участников — чат поднимется выше."
            if needed.next_competitor_title:
                result_text += f" Ближайший чат: {needed.next_competitor_title}"

    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        result_text,
        reply_markup=get_finish_quiz_keyboard(bot_info.username),
        parse_mode="HTML",
    )
    await callback.answer("🎉 Профиль создан!")
