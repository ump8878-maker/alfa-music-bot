from aiogram.fsm.state import State, StatesGroup


class TasteTestStates(StatesGroup):
    """Состояния для прохождения музыкального теста (4 вопроса)."""
    selecting_genres = State()
    selecting_artists = State()
    selecting_when_listen = State()
    selecting_mood = State()
