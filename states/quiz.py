from aiogram.fsm.state import State, StatesGroup


class QuizStates(StatesGroup):
    selecting_genres = State()
    selecting_artists = State()
    selecting_when_listen = State()
    selecting_mood = State()
