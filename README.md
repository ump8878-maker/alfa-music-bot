# 🎵 Alfa Music Bot

Социальный Telegram-бот для определения музыкального профиля, рейтингов и распространения через чаты.

## Возможности

- 🎧 **Короткий квиз (4 вопроса)** — жанры, артисты, когда слушаешь, настроение (+ «свой вариант»)
- 🎭 **Музыкальный архетип** — тип профиля и индивидуальная аналитика
- 🤝 **Совпадения** — процент совпадения с участниками чата
- 🏆 **Рейтинг участников чата** — топ по «вкусу» с шуточными комментариями
- 🌍 **Глобальный рейтинг чатов** — топ чатов по среднему вкусу
- 📊 **Рейтинг чата** — жанры в процентах, позиция (#N из M)
- 🔥 **Вирусные механики** — публикация результата в чат, сообщения «странный вкус»
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
├── rating.py           # Рейтинги: пользователь, чат, глобальный топ, жанры чата
├── analytics.py        # Аналитика: сводка, популярные жанры
├── handlers/           # Обработчики
│   ├── start.py        # /start, /profile, /help, /stats, /global_rating
│   ├── taste_test.py   # Квиз (4 шага), сохранение, публикация в чат
│   ├── chat_mode.py    # Добавление в чат, /chat_rating, карта вкусов
│   ├── matches.py      # Совпадения
│   ├── battle.py       # Баттлы
│   ├── payments.py     # Платежи
│   └── inline.py       # Inline-режим
├── keyboards/          # Клавиатуры и данные (жанры, артисты, настроения)
├── models/             # БД: User, Chat, ChatMember, MusicProfile, Match, QuizResult
├── services/           # matching, profile_card, chat_map, card_generator
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

## Команды

| Команда | Описание |
|--------|----------|
| `/start` | Старт, переход из чата (from_chat_123) |
| `/profile` | Профиль: архетип, совпадения, место в рейтинге |
| `/matches` | Совпадения по вкусу |
| `/chat_rating` | В чате: топ участников, жанры, позиция чата |
| `/global_rating` | Глобальный рейтинг музыкальных чатов |
| `/stats` | Аналитика (пользователи, квизы, жанры) |
| `/help` | Справка |

## База данных

- **users** — user_id, username, score (вкус 0–100)
- **chats** — chat_id, title, rating, owner_id
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
