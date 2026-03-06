from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from typing import Optional
import os

from app.models import MusicProfile


CARD_WIDTH = 800
CARD_HEIGHT = 500

BG_COLOR = (26, 26, 46)
ACCENT_COLOR = (138, 43, 226)
TEXT_COLOR = (255, 255, 255)
SECONDARY_COLOR = (180, 180, 200)
HIGHLIGHT_COLOR = (255, 107, 107)


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Получает шрифт (или fallback)"""
    try:
        if bold:
            return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except:
        return ImageFont.load_default()


def get_mood_emoji(mood: str) -> str:
    """Возвращает эмодзи для настроения"""
    moods = {
        "melancholic": "🌙",
        "energetic": "☀️",
        "calm": "🌊",
        "aggressive": "🔥",
    }
    return moods.get(mood, "🎵")


def get_profile_type_color(profile: MusicProfile) -> tuple:
    """Цвет акцента по типу профиля"""
    profile_type = profile.profile_type
    
    # По ключевым словам в типе
    if "Андерграунд" in profile_type or "Редкост" in profile_type:
        return (148, 0, 211)  # Фиолетовый
    elif "Чартов" in profile_type or "Хитмейкер" in profile_type:
        return (255, 165, 0)  # Оранжевый
    elif "Рэп" in profile_type or "Хип-хоп" in profile_type:
        return (255, 87, 51)  # Красно-оранжевый
    elif "Рок" in profile_type or "Метал" in profile_type:
        return (220, 20, 60)  # Красный
    elif "Инди" in profile_type:
        return (255, 182, 193)  # Розовый
    elif "Электрон" in profile_type or "Рейвер" in profile_type:
        return (0, 255, 255)  # Циан
    elif "Джаз" in profile_type or "R&B" in profile_type:
        return (218, 165, 32)  # Золотой
    elif "Меланхол" in profile_type or "Сэдбой" in profile_type:
        return (100, 149, 237)  # Голубой
    elif "Энерджайзер" in profile_type or "Вайбовый" in profile_type:
        return (255, 215, 0)  # Жёлтый
    elif "Чилл" in profile_type or "Эмбиент" in profile_type:
        return (64, 224, 208)  # Бирюзовый
    elif "Олдскул" in profile_type:
        return (139, 69, 19)  # Коричневый
    elif "Трендсеттер" in profile_type:
        return (255, 0, 255)  # Маджента
    elif "Хамелеон" in profile_type:
        return (50, 205, 50)  # Зелёный
    
    return ACCENT_COLOR


def draw_rounded_rect(draw, xy, radius, fill):
    """Рисует прямоугольник со скруглёнными углами"""
    x1, y1, x2, y2 = xy
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    draw.ellipse([x1, y1, x1 + 2*radius, y1 + 2*radius], fill=fill)
    draw.ellipse([x2 - 2*radius, y1, x2, y1 + 2*radius], fill=fill)
    draw.ellipse([x1, y2 - 2*radius, x1 + 2*radius, y2], fill=fill)
    draw.ellipse([x2 - 2*radius, y2 - 2*radius, x2, y2], fill=fill)


def generate_profile_card(profile: MusicProfile, username: str = None) -> BytesIO:
    """Генерирует красивую карточку профиля"""
    
    img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    accent = get_profile_type_color(profile)
    
    for i in range(150):
        alpha = int(255 * (1 - i / 150) * 0.3)
        color = (accent[0], accent[1], accent[2])
        draw.ellipse([
            CARD_WIDTH - 200 - i,
            -100 - i,
            CARD_WIDTH + i,
            100 + i
        ], fill=(*color, ))
    
    draw_rounded_rect(draw, [30, 30, CARD_WIDTH - 30, CARD_HEIGHT - 30], 20, (35, 35, 60))
    
    title_font = get_font(28, bold=True)
    type_font = get_font(36, bold=True)
    label_font = get_font(18)
    value_font = get_font(22, bold=True)
    small_font = get_font(16)
    
    draw.text((60, 50), "🎵 МУЗЫКАЛЬНЫЙ ПРОФИЛЬ", font=title_font, fill=SECONDARY_COLOR)
    
    if username:
        draw.text((60, 90), f"@{username}", font=value_font, fill=TEXT_COLOR)
        y_offset = 140
    else:
        y_offset = 100
    
    profile_type = profile.profile_type
    draw.text((60, y_offset), profile_type, font=type_font, fill=accent)
    y_offset += 42
    
    # Описание профиля
    description = profile.profile_description
    draw.text((60, y_offset), description, font=small_font, fill=SECONDARY_COLOR)
    y_offset += 30
    
    if profile.genres:
        genre_names = [g.get("name", "").upper() for g in profile.genres[:3]]
        genres_text = " • ".join(genre_names)
        draw.text((60, y_offset), "ЖАНРЫ", font=label_font, fill=SECONDARY_COLOR)
        draw.text((60, y_offset + 25), genres_text, font=value_font, fill=TEXT_COLOR)
        y_offset += 70
    
    if profile.artists:
        artist_names = [a.get("name", "") for a in profile.artists[:4]]
        artists_text = ", ".join(artist_names)
        if len(artists_text) > 40:
            artists_text = artists_text[:37] + "..."
        draw.text((60, y_offset), "АРТИСТЫ", font=label_font, fill=SECONDARY_COLOR)
        draw.text((60, y_offset + 25), artists_text, font=value_font, fill=TEXT_COLOR)
        y_offset += 70
    
    if profile.mood:
        mood_names = {
            "melancholic": "Меланхоличная",
            "energetic": "Энергичная",
            "calm": "Спокойная", 
            "aggressive": "Драйвовая",
        }
        mood_text = f"{get_mood_emoji(profile.mood)} {mood_names.get(profile.mood, profile.mood)}"
        draw.text((60, y_offset), "НАСТРОЕНИЕ", font=label_font, fill=SECONDARY_COLOR)
        draw.text((60, y_offset + 25), mood_text, font=value_font, fill=TEXT_COLOR)
    
    rarity_x = CARD_WIDTH - 200
    rarity_y = 150
    
    rarity_percent = int(profile.rarity_score * 100)
    
    draw.text((rarity_x, rarity_y), "РЕДКОСТЬ", font=label_font, fill=SECONDARY_COLOR)
    
    bar_width = 120
    bar_height = 12
    bar_x = rarity_x
    bar_y = rarity_y + 30
    
    draw_rounded_rect(draw, [bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], 6, (60, 60, 80))
    
    fill_width = int(bar_width * profile.rarity_score)
    if fill_width > 0:
        draw_rounded_rect(draw, [bar_x, bar_y, bar_x + fill_width, bar_y + bar_height], 6, accent)
    
    draw.text((rarity_x, bar_y + 20), f"{rarity_percent}%", font=value_font, fill=TEXT_COLOR)
    
    if rarity_percent > 70:
        rarity_label = "Редкий зверь"
    elif rarity_percent < 30:
        rarity_label = "В тренде"
    else:
        rarity_label = "Уникальный"
    
    draw.text((rarity_x, bar_y + 50), rarity_label, font=small_font, fill=SECONDARY_COLOR)
    
    draw.text((60, CARD_HEIGHT - 60), "t.me/alfamusicpeople_bot", font=small_font, fill=SECONDARY_COLOR)
    
    buffer = BytesIO()
    img.save(buffer, format='PNG', quality=95)
    buffer.seek(0)
    
    return buffer


def generate_match_card(
    user1_name: str,
    user2_name: str,
    match_score: int,
    common_genres: list,
    common_artists: list
) -> BytesIO:
    """Генерирует карточку совпадения"""
    
    img = Image.new('RGB', (CARD_WIDTH, 400), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    draw_rounded_rect(draw, [30, 30, CARD_WIDTH - 30, 370], 20, (35, 35, 60))
    
    title_font = get_font(24, bold=True)
    big_font = get_font(48, bold=True)
    name_font = get_font(28, bold=True)
    value_font = get_font(20)
    small_font = get_font(16)
    
    draw.text((60, 50), "🎵 МУЗЫКАЛЬНОЕ СОВПАДЕНИЕ", font=title_font, fill=SECONDARY_COLOR)
    
    center_x = CARD_WIDTH // 2
    draw.text((center_x - 100, 100), user1_name, font=name_font, fill=TEXT_COLOR, anchor="rm")
    draw.text((center_x - 30, 95), "❤️", font=big_font, fill=HIGHLIGHT_COLOR)
    draw.text((center_x + 100, 100), user2_name, font=name_font, fill=TEXT_COLOR, anchor="lm")
    
    score_color = HIGHLIGHT_COLOR if match_score > 80 else ACCENT_COLOR
    draw.text((center_x, 170), f"{match_score}%", font=big_font, fill=score_color, anchor="mm")
    draw.text((center_x, 210), "совпадение", font=value_font, fill=SECONDARY_COLOR, anchor="mm")
    
    y = 260
    if common_genres:
        genres_text = "🎸 " + ", ".join(common_genres[:3])
        draw.text((60, y), genres_text, font=value_font, fill=TEXT_COLOR)
        y += 35
    
    if common_artists:
        artists_text = "🎤 " + ", ".join(common_artists[:3])
        draw.text((60, y), artists_text, font=value_font, fill=TEXT_COLOR)
    
    draw.text((60, 340), "t.me/alfamusicpeople_bot", font=small_font, fill=SECONDARY_COLOR)
    
    buffer = BytesIO()
    img.save(buffer, format='PNG', quality=95)
    buffer.seek(0)
    
    return buffer
