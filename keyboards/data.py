"""Данные для квиза и клавиатур."""
import random

GENRES = [
    {"id": "pop", "name": "Поп", "emoji": "🎤"},
    {"id": "rock", "name": "Рок", "emoji": "🎸"},
    {"id": "hiphop", "name": "Хип-хоп", "emoji": "🎤"},
    {"id": "indie", "name": "Инди", "emoji": "🎧"},
    {"id": "electronic", "name": "Электроника", "emoji": "🎛"},
    {"id": "rnb", "name": "R&B", "emoji": "💜"},
    {"id": "metal", "name": "Метал", "emoji": "🤘"},
    {"id": "jazz", "name": "Джаз", "emoji": "🎷"},
    {"id": "classical", "name": "Классика", "emoji": "🎻"},
    {"id": "folk", "name": "Фолк", "emoji": "🪕"},
    {"id": "punk", "name": "Панк", "emoji": "🔥"},
    {"id": "soul", "name": "Соул", "emoji": "❤️"},
    {"id": "other", "name": "Другое", "emoji": "✏️"},
]

POPULAR_ARTISTS = {
    "pop": ["Zivert", "Тейлор Свифт", "The Weeknd", "Билли Айлиш", "Оливия Родриго"],
    "rock": ["Кино", "Би-2", "Arctic Monkeys", "Queen", "Nirvana"],
    "hiphop": ["Баста", "Oxxxymiron", "Дрейк", "Кендрик Ламар", "Travis Scott"],
    "indie": ["Монеточка", "Tame Impala", "Cigarettes After Sex", "The 1975", "Мукка"],
    "electronic": ["Fred again..", "Peggy Gou", "Charlotte de Witte", "Daft Punk", "Skrillex"],
    "rnb": ["Frank Ocean", "SZA", "The Weeknd", "Мари Краймбрери", "Jony"],
    "metal": ["Metallica", "Rammstein", "Ария", "Louna", "Slipknot"],
    "jazz": ["Miles Davis", "Norah Jones", "Robert Glasper", "Пелагея", "Snarky Puppy"],
    "classical": ["Бах", "Моцарт", "Ludovico Einaudi", "Max Richter", "Ólafur Arnalds"],
    "folk": ["Мельница", "Аквариум", "Bon Iver", "Mumford & Sons", "Hozier"],
    "punk": ["Король и Шут", "Green Day", "Порнофильмы", "Blink-182", "Ленинград"],
    "soul": ["Aretha Franklin", "Stevie Wonder", "Amy Winehouse", "Bruno Mars", "D'Angelo"],
}

# Множество «популярных» артистов (Яндекс.Музыка, чарты, Beatport, DJ Mag — условно)
def get_popular_artists_set():
    s = set()
    for lst in POPULAR_ARTISTS.values():
        s.update(a.strip() for a in lst if a)
    s.update(a.strip() for a in POPULAR_ARTISTS_RU if a)
    return s

# Дополнительные артисты для микса
POPULAR_ARTISTS_RU = [
    "MORGENSHTERN", "Баста", "ЛСП", "Скриптонит", "Монеточка", "Zivert",
    "Би-2", "Кино", "Сплин", "Земфира", "Порнофильмы", "ANNA ASTI",
    "Клава Кока", "Jony", "Cream Soda", "Little Big",
]


def get_shuffled_artists(genres: list, count: int = 16) -> list:
    artists = []
    for g in genres:
        if g in POPULAR_ARTISTS:
            artists.extend(POPULAR_ARTISTS[g])
    artists.extend(random.sample(POPULAR_ARTISTS_RU, min(8, len(POPULAR_ARTISTS_RU))))
    artists = list(dict.fromkeys(artists))
    random.shuffle(artists)
    return artists[:count]


MOODS = [
    {"id": "melancholic", "name": "Грустную / меланхоличную", "emoji": "🌙"},
    {"id": "energetic", "name": "Весёлую / энергичную", "emoji": "☀️"},
    {"id": "calm", "name": "Спокойную / фоновую", "emoji": "🌊"},
    {"id": "aggressive", "name": "Агрессивную / драйвовую", "emoji": "🔥"},
    {"id": "other", "name": "Свой вариант", "emoji": "✨"},
]

WHEN_LISTEN = [
    {"id": "morning", "name": "Утром", "emoji": "🌅"},
    {"id": "day", "name": "Днём", "emoji": "☀️"},
    {"id": "evening", "name": "Вечером", "emoji": "🌆"},
    {"id": "night", "name": "Ночью", "emoji": "🌙"},
    {"id": "anytime", "name": "В любое время", "emoji": "🕐"},
]
