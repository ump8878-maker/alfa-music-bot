# Справочник: чат, кнопки, пуш в чат и рейтинг

Где искать функции и оформление, связанные с чатом, квизом из чата и рейтингом.

---

## 1. Переход «из чата в личку» и обратный пуш

| Что | Файл | Функция/место |
|-----|------|----------------|
| Ссылка «Пройти тест» с `from_chat_{chat_id}` | `app/keyboards/inline.py` | `get_chat_test_keyboard(bot_username, chat_id)` (стр. ~172) |
| Сохранение `from_chat_id` при `/start` из чата | `app/handlers/start.py` | `cmd_start` — парсит `?start=from_chat_123`, кладёт в FSM (стр. ~19–30) |
| Подсказка «пришёл из чата» в ЛС | `app/handlers/start.py` | `cmd_start` — строка `intro += "📌 Ты пришёл из чата..."` (~65) |
| Сохранение `from_chat_id` при нажатии «Начать тест» | `app/handlers/start.py` | `start_test` (callback `start_test`) — стр. ~77–84 |
| Откуда берётся `chat_id` в конце квиза | `app/handlers/taste_test.py` | `select_mood_and_finish` — `chat_id = data.get("from_chat_id")` (~182) |
| Публикация результата в чат | `app/handlers/chat_mode.py` | `post_quiz_result_to_chat(...)` (стр. ~52) — вызывается из `taste_test.py` (~312–321) |
| Отметка «прошёл тест» и создание ChatMember | `app/handlers/chat_mode.py` | `ensure_chat_member_completed(session, chat_id, user_id)` (стр. ~36) |

---

## 2. Что видит пользователь в личке после квиза (если пришёл из чата)

Всё формируется в **`app/handlers/taste_test.py`** в обработчике **`select_mood_and_finish`** (около строк 172–323):

- **Профиль и аналитика** — `generate_individual_analytics_block(profile)` (~247).
- **Совпадения с участниками чата** — цикл по `get_chat_member_ranking`, `calculate_match_score`, строки ~253–266.
- **Место в рейтинге чата** — `get_user_rank_in_chat`, комментарий `get_top_comment(my_rank)` (~268–270).
- **Рейтинг чата (позиция в глобальном топе и добор)** — `get_chat_rank`, `get_needed_participants_for_next_rank` (~272–282).
- **Кнопки в ЛС** — «Поделиться», «Добавить в чат», «Пройти заново» — собираются в том же обработчике (~288–284).

---

## 3. Кнопки (клавиатуры) чата

| Кнопки | Файл | Функция |
|--------|------|---------|
| Одна кнопка «Пройти тест» (ссылка в ЛС) | `app/keyboards/inline.py` | `get_chat_test_keyboard(bot_username, chat_id)` (~172) |
| То же для «первого сообщения» | `app/keyboards/inline.py` | `get_chat_start_keyboard(bot_username, chat_id)` (~301) — внутри вызывает `get_chat_test_keyboard` |
| Меню чата: Пройти тест, Сканер, Рейтинг, Топ | `app/keyboards/inline.py` | `get_chat_menu_keyboard(bot_username, chat_id)` (~306) |
| После карты вкусов: совпадения, баттл, угадайка | `app/keyboards/inline.py` | `get_chat_map_keyboard(chat_id)` (~322) |

Экспорт клавиатур: **`app/keyboards/__init__.py`** (get_chat_test_keyboard, get_chat_start_keyboard, get_chat_menu_keyboard, get_chat_map_keyboard).

---

## 4. Где показывается меню чата (4 кнопки)

В **`app/handlers/chat_mode.py`** меню везде через **`get_chat_menu_keyboard(bot_info.username, chat_id)`**:

- При добавлении бота в чат — `bot_added_to_chat` (~187–199).
- Под сообщением «N прошёл тест» — `post_quiz_result_to_chat` (~80–84).
- Под мотивирующим сообщением о рейтинге — `try_send_growth_message` (~111–115).
- Ответы на кнопки «Сканер» / «Рейтинг» / «Топ чатов» — `cb_chat_menu_scan`, `cb_chat_menu_rating`, `cb_chat_menu_top` (~382–441).
- Ответы команд `/chat_scan` и `/chat_rating` при ошибке (мало участников и т.п.) — ~462, ~510.

---

## 5. Обработчики кнопок меню чата

В **`app/handlers/chat_mode.py`**:

| Кнопка | callback_data | Обработчик |
|--------|----------------|------------|
| Сканер чата | `chat_menu:scan:{chat_id}` | `cb_chat_menu_scan` (~382) |
| Рейтинг чата | `chat_menu:rating:{chat_id}` | `cb_chat_menu_rating` (~399) |
| Топ чатов | `chat_menu:top` | `cb_chat_menu_top` (~417) |

Вспомогательные функции текста (чтобы не дублировать логику команд):

- `_send_chat_scan_result(bot, chat_id, session, reply_markup)` (~314).
- `_send_chat_rating_result(bot, chat_id, session, reply_markup)` (~348).

---

## 6. Команды чата (то же по смыслу, что и кнопки)

В **`app/handlers/chat_mode.py`**:

- **`/chat_scan`** — `cmd_chat_scan` (~445): сканер чата (профиль, жанры, артисты, вайб).
- **`/chat_rating`** — `cmd_chat_rating` (~496): рейтинг чата (позиция, балл, добор участников).
- **`/top_chats`** — `cmd_top_chats` (~538): глобальный топ-10 чатов.

---

## 7. Рейтинг чата (логика, не UI)

- **`app/chat_rating.py`** — `calculate_chat_rating`, `get_chat_rank`, `get_needed_participants_for_next_rank`, рост рейтинга, cooldown мотивирующих сообщений.
- **`app/rating.py`** — рейтинг пользователя (вкус), `get_chat_position`, `get_global_chat_ranking`, `get_chat_member_ranking`, `get_user_rank_in_chat`.

---

## 8. Текст сообщения «N прошёл тест» в чате

Формируется в **`app/handlers/chat_mode.py`** в **`post_quiz_result_to_chat`** (стр. ~52):

- Имя пользователя, «прошёл музыкальный тест».
- Профиль (архетип), совпадение с чатом (%).
- Призыв пройти тест.
- При наличии: «Ваш чат сейчас #N из M», «пусть тест пройдут ещё K человек».
- Под сообщением — `get_chat_menu_keyboard` (Пройти тест, Сканер, Рейтинг, Топ чатов).

---

## 9. Краткий поток «нажал в чате → прошёл в личке → пуш в чат»

1. В чате: сообщение с кнопкой «Пройти тест» (меню или при добавлении бота) — ссылка `t.me/BOT?start=from_chat_{chat_id}`.
2. Пользователь переходит в ЛС, вызывается `cmd_start` в **start.py** → в state сохраняется `from_chat_id`.
3. Пользователь нажимает «Начать тест» → **start.py** `start_test` сохраняет `from_chat_id` в state.
4. Прохождение квиза в **taste_test.py** (шаги жанры → артисты → когда слушаешь → настроение).
5. В **taste_test.py** `select_mood_and_finish`: берётся `chat_id = data.get("from_chat_id")`, сохраняется профиль, пересчитываются совпадения и рейтинг чата, вызывается `ensure_chat_member_completed` и **`post_quiz_result_to_chat`**.
6. В ЛС пользователь видит карточку + совпадения с участниками + место в чате + рейтинг чата (#N из M, добор).
7. В чат уходит сообщение от бота из `post_quiz_result_to_chat` с текстом и меню из `get_chat_menu_keyboard`.

Если что-то из этого не находится — ищи по имени функции или по строке из этой таблицы (файл + примерное место).
