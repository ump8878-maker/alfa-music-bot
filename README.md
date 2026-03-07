# 🎵 Музыкальный тест чата

Telegram-бот: квиз по вкусу, музыкальный скан чата и рейтинг чатов. Без токсичности и спама.

## Возможности

- **Квиз (4 шага)** — жанры, артисты, когда слушаешь, настроение
- **Музыкальный скан чата** (`/chat_scan`) — только в группах; профиль чата, жанры, артисты, вайб; при нехватке данных — кнопка «Пройти тест»
- **Рейтинг чата** (`/chat_rating`) — балл, место в рейтинге, сколько добрать до роста
- **Топ чатов** (`/top_chats`) — глобальный рейтинг чатов
- **Рост через рейтинг** — мотивирующие сообщения после прохождения квиза в чате (с cooldown из config)

## Стек

- Python 3.11+
- aiogram 3.x
- SQLAlchemy 2.0 (async)
- SQLite / PostgreSQL (через DATABASE_URL)

## Структура

```
config/          # settings (BOT_TOKEN, DATABASE_URL, MIN_PARTICIPANTS_FOR_SCAN, GROWTH_MESSAGE_COOLDOWN_HOURS)
database/       # Base, engine, async_session, init_db, модели (User, Chat, ChatMember, ChatStats, MusicProfile, QuizResult)
handlers/       # start, quiz (FSM), chat (chat_scan, chat_rating, top_chats, welcome, growth)
services/       # chat_analytics, chat_rating, rating_helpers
keyboards/      # data (GENRES, MOODS, WHEN_LISTEN), inline (старт, квиз, «Пройти тест»)
utils/          # middleware (DB), humor (комментарии)
states/         # QuizStates (FSM квиза)
main.py         # точка входа, Bot, Dispatcher, polling
run.py          # asyncio.run(main()) — для Railway
```

## Установка и запуск

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# В .env: BOT_TOKEN=..., DATABASE_URL=... (опционально, по умолчанию data/bot.db)
python run.py
```

## Команды

| Команда        | Описание |
|----------------|----------|
| `/start`       | Старт; из чата — start=from_chat_123 |
| `/chat_scan`   | В группе: музыкальный скан чата |
| `/chat_rating` | В группе: рейтинг и место в топе |
| `/top_chats`   | Глобальный топ чатов |

## База данных

При первом запуске вызывается `init_db()` — создаются таблицы в `data/` (если SQLite). Модели: **users**, **chats**, **chat_members**, **chat_stats**, **music_profiles**, **quiz_results**.

## Деплой (Railway)

1. Подключить репозиторий к Railway.
2. Переменные: `BOT_TOKEN` (обязательно), при необходимости `DATABASE_URL`.
3. Procfile: `worker: python run.py`.

Токен при деплое часто подставляется с пробелами — бот очищает его автоматически.
