# 🎵 Alfa Music Bot

Telegram бот для знакомств по музыкальным вкусам с вирусными механиками.

## Возможности

- 🎧 **Музыкальный тест** — определи свой музыкальный профиль
- 🎭 **25+ архетипов** — от "Рэп-голова" до "Андерграунд-гуру"
- 🤝 **Мэтчинг** — находи людей с похожим вкусом
- 👥 **Групповой режим** — добавь бота в чат друзей
- 📊 **Карта вкусов** — визуализация музыкальных предпочтений группы
- 🏆 **Баттлы вкусов** — соревнуйся с друзьями

## Стек

- Python 3.11+
- aiogram 3.x
- SQLAlchemy 2.0 (async)
- SQLite / PostgreSQL
- Pillow (генерация карточек)

## Установка

```bash
# Клонирование
git clone https://github.com/YOUR_USERNAME/alfa-music-bot.git
cd alfa-music-bot

# Виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows

# Зависимости
pip install -r requirements.txt

# Конфигурация
cp .env.example .env
# Отредактируй .env и добавь BOT_TOKEN
```

## Запуск

```bash
python run.py
```

## Деплой на Railway

1. Создай проект на [Railway](https://railway.app)
2. Подключи GitHub репозиторий
3. Добавь переменную окружения `BOT_TOKEN`
4. Deploy!

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен бота от @BotFather |
| `DATABASE_URL` | URL базы данных (опционально) |
| `DEBUG` | Режим отладки (true/false) |

## Структура проекта

```
alfa-music-bot/
├── app/
│   ├── handlers/      # Обработчики команд
│   ├── keyboards/     # Клавиатуры
│   ├── models/        # Модели БД
│   ├── services/      # Бизнес-логика
│   ├── states/        # FSM состояния
│   └── bot.py         # Инициализация бота
├── config/
│   └── settings.py    # Конфигурация
├── run.py             # Точка входа
└── requirements.txt
```

## Лицензия

MIT
