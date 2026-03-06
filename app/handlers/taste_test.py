from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import MusicProfile
from app.states import TasteTestStates
from app.keyboards import (
    get_genres_keyboard,
    get_artists_keyboard,
    get_mood_keyboard,
    get_era_keyboard,
    get_language_keyboard,
    get_profile_keyboard,
    get_chat_invite_keyboard,
)
from app.services.profile_card import generate_profile_text
from app.services.matching import calculate_rarity_score, recalculate_user_matches

router = Router()


@router.callback_query(TasteTestStates.selecting_genres, F.data.startswith("genre:"))
async def select_genre(callback: CallbackQuery, state: FSMContext):
    """Выбор жанра"""
    genre_id = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_genres", set())
    
    if genre_id in selected:
        selected.discard(genre_id)
    elif len(selected) < 3:
        selected.add(genre_id)
    else:
        await callback.answer("Максимум 3 жанра!", show_alert=True)
        return
    
    await state.update_data(selected_genres=selected)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_genres_keyboard(selected)
    )
    await callback.answer()


@router.callback_query(TasteTestStates.selecting_genres, F.data == "genres_done")
async def genres_done(callback: CallbackQuery, state: FSMContext):
    """Завершение выбора жанров"""
    import random
    from app.keyboards.data import POPULAR_ARTISTS, POPULAR_ARTISTS_RU, GENRES
    
    data = await state.get_data()
    selected = data.get("selected_genres", set())
    
    if not selected:
        await callback.answer("Выбери хотя бы один жанр!", show_alert=True)
        return
    
    genres_list = list(selected)
    
    # Генерируем артистов для каждого жанра заранее
    cached_artists_by_genre = {}
    for genre in genres_list:
        artists = []
        if genre in POPULAR_ARTISTS:
            artists = POPULAR_ARTISTS[genre].copy()
        ru_artists = [a for a in POPULAR_ARTISTS_RU if a not in artists]
        random.shuffle(ru_artists)
        artists.extend(ru_artists[:4])
        random.shuffle(artists)
        cached_artists_by_genre[genre] = artists[:12]
    
    await state.set_state(TasteTestStates.selecting_artists)
    await state.update_data(
        selected_artists=set(), 
        current_genre_idx=0,
        genres_list=genres_list,
        cached_artists_by_genre=cached_artists_by_genre
    )
    
    # Получаем название первого жанра
    first_genre = genres_list[0]
    genre_name = first_genre
    for g in GENRES:
        if g["id"] == first_genre:
            genre_name = f"{g['emoji']} {g['name']}"
            break
    
    total = len(genres_list)
    await callback.message.edit_text(
        f"🎤 <b>Шаг 2/5: Артисты</b>\n\n"
        f"<b>{genre_name}</b> (1/{total})\n"
        f"Выбери артистов из этого жанра:",
        reply_markup=get_artists_keyboard(
            genres_list, 
            current_genre_idx=0,
            cached_artists_by_genre=cached_artists_by_genre
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(TasteTestStates.selecting_artists, F.data.startswith("artist:"))
async def select_artist(callback: CallbackQuery, state: FSMContext):
    """Выбор артиста"""
    artist_name = callback.data.split(":", 1)[1]
    data = await state.get_data()
    selected = data.get("selected_artists", set())
    genres_list = data.get("genres_list", [])
    current_genre_idx = data.get("current_genre_idx", 0)
    cached_artists_by_genre = data.get("cached_artists_by_genre", {})
    
    if artist_name in selected:
        selected.discard(artist_name)
    elif len(selected) < 15:
        selected.add(artist_name)
    else:
        await callback.answer("Максимум 15 артистов!", show_alert=True)
        return
    
    await state.update_data(selected_artists=selected)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_artists_keyboard(
            genres_list, 
            selected, 
            current_genre_idx,
            cached_artists_by_genre
        )
    )
    await callback.answer()


@router.callback_query(TasteTestStates.selecting_artists, F.data.startswith("artists_genre:"))
async def switch_genre(callback: CallbackQuery, state: FSMContext):
    """Переключение между жанрами"""
    from app.keyboards.data import GENRES
    
    new_idx = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected = data.get("selected_artists", set())
    genres_list = data.get("genres_list", [])
    cached_artists_by_genre = data.get("cached_artists_by_genre", {})
    
    await state.update_data(current_genre_idx=new_idx)
    
    # Получаем название текущего жанра
    current_genre = genres_list[new_idx]
    genre_name = current_genre
    for g in GENRES:
        if g["id"] == current_genre:
            genre_name = f"{g['emoji']} {g['name']}"
            break
    
    total = len(genres_list)
    await callback.message.edit_text(
        f"🎤 <b>Шаг 2/5: Артисты</b>\n\n"
        f"<b>{genre_name}</b> ({new_idx + 1}/{total})\n"
        f"Выбери артистов из этого жанра:",
        reply_markup=get_artists_keyboard(
            genres_list, 
            selected, 
            new_idx,
            cached_artists_by_genre
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(TasteTestStates.selecting_artists, F.data.in_({"artists_done", "artists_skip"}))
async def artists_done(callback: CallbackQuery, state: FSMContext):
    """Завершение выбора артистов"""
    await state.set_state(TasteTestStates.selecting_mood)
    
    await callback.message.edit_text(
        "🌙 <b>Шаг 3/5: Настроение</b>\n\n"
        "Какую музыку выбираешь чаще?",
        reply_markup=get_mood_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(TasteTestStates.selecting_mood, F.data.startswith("mood:"))
async def select_mood(callback: CallbackQuery, state: FSMContext):
    """Выбор настроения"""
    mood = callback.data.split(":")[1]
    await state.update_data(mood=mood)
    await state.set_state(TasteTestStates.selecting_era)
    
    await callback.message.edit_text(
        "📼 <b>Шаг 4/5: Эпоха</b>\n\n"
        "Музыка какого времени тебе ближе?",
        reply_markup=get_era_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(TasteTestStates.selecting_era, F.data.startswith("era:"))
async def select_era(callback: CallbackQuery, state: FSMContext):
    """Выбор эпохи"""
    era = callback.data.split(":")[1]
    await state.update_data(era=era)
    await state.set_state(TasteTestStates.selecting_language)
    
    await callback.message.edit_text(
        "🌍 <b>Шаг 5/5: Язык</b>\n\n"
        "На каком языке чаще слушаешь?",
        reply_markup=get_language_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(TasteTestStates.selecting_language, F.data.startswith("language:"))
async def select_language(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Выбор языка и завершение теста"""
    from aiogram.types import BufferedInputFile
    from app.services.card_generator import generate_profile_card
    
    language = callback.data.split(":")[1]
    data = await state.get_data()
    user_id = callback.from_user.id
    
    genres = [{"name": g, "weight": 1.0} for g in data.get("selected_genres", [])]
    artists = [{"name": a} for a in data.get("selected_artists", [])]
    mood = data.get("mood")
    era = data.get("era")
    
    rarity = calculate_rarity_score(genres, artists)
    
    result = await session.execute(
        select(MusicProfile).where(MusicProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    
    if profile:
        profile.genres = genres
        profile.artists = artists
        profile.mood = mood
        profile.era = era
        profile.language_pref = language
        profile.rarity_score = rarity
    else:
        profile = MusicProfile(
            user_id=user_id,
            genres=genres,
            artists=artists,
            mood=mood,
            era=era,
            language_pref=language,
            rarity_score=rarity,
        )
        session.add(profile)
    
    await session.commit()
    await session.refresh(profile)
    
    await recalculate_user_matches(session, user_id)
    
    await state.clear()
    
    bot_info = await callback.bot.get_me()
    username = callback.from_user.username
    
    try:
        card_buffer = generate_profile_card(profile, username)
        card_file = BufferedInputFile(card_buffer.read(), filename="profile.png")
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="📤 Поделиться", switch_inline_query="")
        builder.button(text="👥 Добавить в чат", url=f"https://t.me/{bot_info.username}?startgroup=true")
        builder.button(text="🔄 Пройти заново", callback_data="restart_test")
        builder.adjust(2, 1)
        
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=card_file,
            caption=(
                f"✨ <b>Твой музыкальный профиль готов!</b>\n\n"
                f"Нажми «Поделиться» чтобы отправить друзьям 👇"
            ),
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    except Exception as e:
        profile_text = generate_profile_text(profile)
        await callback.message.edit_text(
            f"✨ <b>Твой музыкальный профиль готов!</b>\n\n"
            f"{profile_text}\n\n"
            f"💡 <i>Добавь меня в чат друзей — покажу, кто с кем совпадает!</i>",
            reply_markup=get_chat_invite_keyboard(bot_info.username),
            parse_mode="HTML"
        )
    
    await callback.answer("🎉 Профиль создан!")
