# 🎵 Alfa Music Bot

Социальный Telegram-бот для определения музыкального профиля, рейтингов и распространения через чаты.

## Возможности

- 🎧 **Короткий квиз (4 вопроса)** — жанры, артисты, когда слушаешь, настроение (+ «свой вариант»)
- 🎭 **Музыкальный архетип** — тип профиля и индивидуальная аналитика
- 🤝 **Совпадения** — процент совпадения с участниками чата
- 🏆 **Рейтинг участников чата** — топ по «вкусу» с шуточными комментариями
- 🌍 **Глобальный рейтинг чатов** — топ чатов по среднему вкусу
- 📊 **Рейтинг чата** — позиция, рейтинг, сколько добрать до роста
- 🎧 **Музыкальный сканер чата** (`/chat_scan`) — профиль чата, жанры, артисты, вайб
- 🌍 **Топ чатов** (`/top_chats`) — глобальный топ-10 музыкальных чатов
- 🔥 **Рост через рейтинг** — мотивирующие сообщения после квиза (с защитой от спама)
- ⚔️ **Баттлы вкусов** — голосование в чате
- 📈 **Аналитика** — пользователи, квизы, популярные жанры

## Стек

- Python 3.11+
- aiogram 3.x
- SQLAlchemy 2.0 (async)
- SQLite / PostgreSQL (aiosqlite)
- Pillow (карточки профиля)

## Структура проекта

```
app/
├── bot.py              # Точка входа бота, FSM, middleware
├── quiz.py             # Логика квиза (построение профиля из ответов)
├── rating.py           # Рейтинги: пользователь, чат, жанры чата
├── chat_rating.py      # Рейтинг чатов: формула, позиция, добор участников, антиспам
├── analytics.py        # Аналитика: сводка, популярные жанры
├── handlers/           # Обработчики
│   ├── start.py        # /start, /profile, /help, /stats, /global_rating, /top_chats
│   ├── taste_test.py   # Квиз (4 шага), сохранение, публикация в чат
│   ├── chat_mode.py    # /chat_scan, /chat_rating, /top_chats, карта вкусов, рост
│   ├── matches.py      # Совпадения
│   ├── battle.py       # Баттлы
│   ├── payments.py     # Платежи
│   └── inline.py       # Inline-режим
├── keyboards/          # Клавиатуры и данные (жанры, артисты, настроения)
├── models/             # БД: User, Chat, ChatMember, ChatStats, MusicProfile, Match, QuizResult
├── services/           # matching, profile_card, chat_map, chat_analytics, card_generator
├── states/             # FSM: TasteTestStates
└── utils/              # middleware, humor (шуточные комментарии)
config/
├── settings.py
run.py
requirements.txt
```

## Установка и запуск

```bash
python -m venv venv
source venv/bin/activate   # или venv\Scripts\activate на Windows
pip install -r requirements.txt
cp .env.example .env      # задать BOT_TOKEN
python run.py
```

## База данных и миграции

- **Первый запуск или чистая установка**  
  Бот при старте вызывает `init_db()` и создаёт все таблицы (SQLAlchemy `create_all`). Папка `data/` создаётся автоматически, в ней лежит `bot.db`.

- **Обновление после изменений в моделях (новые таблицы/поля)**  
  Вариант 1 — пересоздать БД (подходит для разработки):
  ```bash
  rm -f data/bot.db
  python run.py
  ```
  Вариант 2 — применить миграции Alembic (сохраняет данные):
  ```bash
  alembic upgrade head
  ```
  Миграции лежат в `alembic/versions/`. Текущая добавляет таблицу `quiz_results` и поля `chats.rating`, `chats.owner_id`, `users.score`, `music_profiles.listening_time`.

## Команды

| Команда | Описание |
|--------|----------|
| `/start` | Старт, переход из чата (from_chat_123) |
| `/profile` | Профиль: архетип, совпадения, место в рейтинге |
| `/matches` | Совпадения по вкусу |
| `/chat_scan` | В чате: музыкальный сканер (профиль, жанры, артисты, вайб) |
| `/chat_rating` | В чате: рейтинг, позиция, сколько добрать до роста |
| `/top_chats` | Топ-10 музыкальных чатов |
| `/global_rating` | Глобальный рейтинг музыкальных чатов |
| `/stats` | Аналитика (пользователи, квизы, жанры) |
| `/help` | Справка |

## База данных

- **users** — user_id, username, score (вкус 0–100)
- **chats** — chat_id, title, rating, owner_id, owner_username, updated_at
- **chat_stats** — chat_id, rating, profile_name, top_genres, top_artists, participants_count, last_scan_at, last_growth_message_at
- **music_profiles** — жанры, артисты, mood, listening_time, rarity_score
- **quiz_results** — user_id, chat_id, answers, score
- **matches** — совпадения между пользователями (в чате и глобально)

## Деплой (Railway)

1. Создать проект на [Railway](https://railway.app)
2. Подключить репозиторий
3. Добавить переменную `BOT_TOKEN`
4. При необходимости задать `DATABASE_URL` (PostgreSQL)

## Лицензия

MIT
