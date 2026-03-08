from aiogram.fsm.state import State, StatesGroup


class QuizStates(StatesGroup):
    selecting_genres = State()
    selecting_artists = State()
    entering_custom_artist = State()
    selecting_when_listen = State()
    selecting_guilty = State()
    selecting_mood = State()  # legacy, kept for old sessions
