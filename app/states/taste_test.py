from aiogram.fsm.state import State, StatesGroup


class TasteTestStates(StatesGroup):
    """Состояния для прохождения музыкального теста"""
    
    selecting_genres = State()
    selecting_artists = State()
    selecting_mood = State()
    selecting_era = State()
    selecting_language = State()
    confirming = State()
