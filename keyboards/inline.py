from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Set

from .data import GENRES, MOODS, WHEN_LISTEN, GUILTY_GENRES, get_shuffled_artists


def get_start_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎵 Начать тест", callback_data="start_test")
    return builder.as_markup()


def get_genre_keyboard(selected: Set[str] = None) -> InlineKeyboardMarkup:
    selected = selected or set()
    builder = InlineKeyboardBuilder()
    for genre in GENRES:
        is_selected = genre["id"] in selected
        text = f"✅ {genre['emoji']} {genre['name']}" if is_selected else f"{genre['emoji']} {genre['name']}"
        builder.button(text=text, callback_data=f"genre:{genre['id']}")
    builder.row(InlineKeyboardButton(text="✏️ Предложить свой вариант", callback_data="genre:other"))
    builder.adjust(3)
    if selected:
        builder.row(
            InlineKeyboardButton(
                text=f"Далее → ({len(selected)} выбрано)",
                callback_data="genres_done",
            )
        )
    return builder.as_markup()


def get_artist_keyboard(genres: List[str], selected: Set[str] = None) -> InlineKeyboardMarkup:
    selected = selected or set()
    artists = get_shuffled_artists(genres, count=16)
    builder = InlineKeyboardBuilder()
    for artist in artists:
        is_selected = artist in selected
        text = f"✅ {artist}" if is_selected else artist
        builder.button(text=text, callback_data=f"artist:{artist}")
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="✏️ Предложить свой вариант", callback_data="artist:custom")
    )
    if selected:
        builder.row(
            InlineKeyboardButton(
                text=f"Готово ({len(selected)} артистов)",
                callback_data="artists_done",
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(text="Пропустить →", callback_data="artists_skip")
        )
    return builder.as_markup()


def get_when_listen_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for w in WHEN_LISTEN:
        builder.button(
            text=f"{w['emoji']} {w['name']}",
            callback_data=f"when:{w['id']}",
        )
    builder.adjust(2)
    return builder.as_markup()


def get_mood_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for mood in MOODS:
        builder.button(
            text=f"{mood['emoji']} {mood['name']}",
            callback_data=f"mood:{mood['id']}",
        )
    builder.row(InlineKeyboardButton(text="✏️ Предложить свой вариант", callback_data="mood:other"))
    builder.adjust(1)
    return builder.as_markup()


def get_guilty_keyboard(selected: set = None) -> InlineKeyboardMarkup:
    """Клавиатура «зашкварные жанры» — мультивыбор как в шаге жанров."""
    selected = selected or set()
    builder = InlineKeyboardBuilder()
    for g in GUILTY_GENRES:
        is_sel = g["id"] in selected
        text = f"✅ {g['emoji']} {g['name']}" if is_sel else f"{g['emoji']} {g['name']}"
        builder.button(text=text, callback_data=f"guilty:{g['id']}")
    builder.adjust(3)
    if selected:
        builder.row(
            InlineKeyboardButton(
                text=f"Готово ({len(selected)} выбрано)",
                callback_data="guilty_done",
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(text="Пропустить →", callback_data="guilty_done")
        )
    return builder.as_markup()


def get_chat_test_keyboard(bot_username: str, chat_id: int = 0) -> InlineKeyboardMarkup:
    start_param = f"from_chat_{chat_id}" if chat_id else "from_chat"
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🎵 Пройти тест",
        url=f"https://t.me/{bot_username}?start={start_param}",
    )
    return builder.as_markup()


def get_chat_menu_keyboard(bot_username: str, chat_id: int) -> InlineKeyboardMarkup:
    """Меню чата: пройти тест."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🎵 Пройти тест",
        url=f"https://t.me/{bot_username}?start=from_chat_{chat_id}",
    )
    builder.adjust(1)
    return builder.as_markup()


def get_profile_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """Профиль: пройти заново, добавить в чат."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Пройти заново", callback_data="start_test")
    builder.button(
        text="👥 Добавить в чат",
        url=f"https://t.me/{bot_username}?startgroup=test",
    )
    builder.adjust(1)
    return builder.as_markup()


def get_finish_quiz_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """В конце теста: кнопка «Добавить в чат с друзьями» — по нажатию открывается выбор чата."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="👥 Добавить в чат с друзьями",
        url=f"https://t.me/{bot_username}?startgroup=share",
    )
    return builder.as_markup()
