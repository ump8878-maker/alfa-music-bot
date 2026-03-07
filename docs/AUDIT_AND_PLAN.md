# Аудит и план переписывания бота

## 1. Краткий аудит текущего проекта

### Архитектура
- **Структура:** Всё под `app/` (handlers, models, services, keyboards, states, utils), конфиг в `config/`, точка входа `run.py` → `app.bot.main`.
- **Проблемы:** Много разрозненных фич (battle, prediction, payments, matches, referrals, inline), дублирование логики рейтинга между `app.rating` и `app.chat_rating`, зависимости размазаны по модулям.

### Handlers
- **start, taste_test, chat_mode, matches, battle, payments, inline, profiles** — избыточно для задачи «сканер + рейтинг чата». Квиз и чат-механики перемешаны с платёжками и баттлами.
- **Состояние квиза:** FSM в `states/taste_test.py`, хранится в MemoryStorage — ок для одного инстанса.

### Database layer
- **Модели:** User, Chat, ChatMember, MusicProfile, QuizResult, ChatStats — нужны. Match, Battle, Payment, Referral, Prediction — не нужны для двух механик.
- **Сессия:** AsyncSession через middleware, `app.models.database` — нормально, но импорты завязаны на `app.models`.

### Асинхронность
- Везде async/await, SQLAlchemy async — ок.

### Дублирование
- Рейтинг: часть в `rating.py`, часть в `chat_rating.py`, часть в `analytics`. Логика сканера в `chat_analytics` и в handlers.

### Масштабирование
- MemoryStorage FSM не подходит для нескольких воркеров (нужен Redis). Для одного воркера — приемлемо.
- Нет явного разделения «слой БД / сервисы / хендлеры».

### Итог аудита
Архитектуру стоит упростить: оставить только квиз + сканер чата + рейтинг чата + рост с cooldown. Убрать battle, payments, matches, referrals, inline, profiles. Структуру сделать плоской: `config`, `database`, `handlers`, `services`, `keyboards`, `utils`, `main.py`.

---

## 2. План изменений

1. **Новая структура (корень репозитория):**
   - `main.py` — точка входа, Bot, Dispatcher, polling.
   - `config/settings.py` — BOT_TOKEN, DATABASE_URL, DEBUG, MIN_PARTICIPANTS_FOR_SCAN, GROWTH_MESSAGE_COOLDOWN_HOURS.
   - `database/` — Base, engine, async_session, init_db; модели User, Chat, ChatMember, ChatStats, MusicProfile, QuizResult.
   - `handlers/` — start, quiz (FSM), chat (chat_scan, chat_rating, top_chats, welcome, growth).
   - `services/chat_analytics.py` — collect_chat_music_stats, calculate_chat_profile, generate_chat_comment.
   - `services/chat_rating.py` — calculate_chat_rating, get_global_chat_ranking, get_chat_rank, get_needed_participants_for_next_rank, can_send_growth_message, mark_growth_message_sent + хелперы (profile_completeness, get_chat_genre_stats, get_chat_member_ranking).
   - `keyboards/` — data (GENRES, MOODS, WHEN_LISTEN, артисты), inline (старт, квиз, кнопка «Пройти тест»).
   - `utils/` — middleware (DB session).

2. **Удалить:** `app/` (после переноса кода в новую структуру), лишние миграции (оставить одну актуальную под новую схему или создать новую).

3. **Тон бота:** короткие сообщения, живой/ироничный стиль, без токсичности и спама. Growth-сообщения только с cooldown из config.

4. **Не реализовывать:** детектор странного вкуса, токсичные сценарии, раздражающий спам.

---

## 3. Реализация

См. код в корне и в папках `config`, `database`, `handlers`, `services`, `keyboards`, `utils`, `main.py`, `run.py`.
