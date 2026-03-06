from sqlalchemy import BigInteger, String, Float, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, TYPE_CHECKING, List, Dict, Any
from datetime import datetime

from .database import Base

if TYPE_CHECKING:
    from .user import User


class MusicProfile(Base):
    __tablename__ = "music_profiles"
    
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        primary_key=True
    )
    genres: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list
    )
    artists: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        default=list
    )
    mood: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    era: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    language_pref: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rarity_score: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    user: Mapped["User"] = relationship("User", back_populates="music_profile")
    
    @property
    def genre_names(self) -> List[str]:
        return [g.get("name", "") for g in self.genres]
    
    @property
    def artist_names(self) -> List[str]:
        return [a.get("name", "") for a in self.artists]
    
    @property
    def profile_type(self) -> str:
        """Определяет тип музыкального профиля для отображения"""
        genre_names = [g.get("name", "").lower() for g in self.genres]
        
        # По редкости
        if self.rarity_score > 0.8:
            return "🦄 Андерграунд-гуру"
        elif self.rarity_score > 0.65:
            return "💎 Охотник за редкостями"
        elif self.rarity_score < 0.2:
            return "📻 Чартовый маньяк"
        elif self.rarity_score < 0.35:
            return "🎯 Хитмейкер"
        
        # По жанрам
        if "hiphop" in genre_names:
            if self.mood == "aggressive":
                return "🔥 Рэп-голова"
            elif self.mood == "melancholic":
                return "💔 Эмо-рэпер"
            return "🎤 Хип-хоп душа"
        
        if "rock" in genre_names or "metal" in genre_names:
            if self.era == "oldschool":
                return "🎸 Олдскул рокер"
            elif "metal" in genre_names:
                return "🤘 Металхэд"
            return "⚡ Рок-н-ролльщик"
        
        if "indie" in genre_names:
            if self.mood == "melancholic":
                return "🌙 Инди-меланхолик"
            return "🎧 Инди-кид"
        
        if "electronic" in genre_names:
            if self.mood == "energetic":
                return "🪩 Рейвер"
            elif self.mood == "calm":
                return "🌌 Эмбиент-душа"
            return "🎛 Электронщик"
        
        if "jazz" in genre_names or "soul" in genre_names:
            return "🎷 Джазовая душа"
        
        if "classical" in genre_names:
            return "🎻 Классик"
        
        if "rnb" in genre_names:
            return "💜 R&B вайбы"
        
        # По настроению
        if self.mood == "melancholic":
            if self.era == "2020s":
                return "🖤 Сэдбой/Сэдгёрл"
            return "🌙 Меланхолик"
        elif self.mood == "energetic":
            if self.era == "2020s":
                return "✨ Вайбовый"
            return "☀️ Энерджайзер"
        elif self.mood == "calm":
            return "🌊 Чиллер"
        elif self.mood == "aggressive":
            return "⚡ Качатель"
        
        # По эпохе
        if self.era == "oldschool":
            return "📼 Олдскульщик"
        elif self.era == "2020s":
            return "🔮 Трендсеттер"
        
        # Fallback - по количеству жанров
        if len(self.genres) >= 3:
            return "🎭 Музыкальный хамелеон"
        
        return "🎧 Меломан"
    
    @property
    def profile_description(self) -> str:
        """Краткое описание профиля"""
        descriptions = {
            "🦄 Андерграунд-гуру": "Слушаешь то, что другие ещё не открыли",
            "💎 Охотник за редкостями": "Находишь жемчужины раньше всех",
            "📻 Чартовый маньяк": "Знаешь все хиты наизусть",
            "🎯 Хитмейкер": "Твой плейлист — это чарты",
            "🔥 Рэп-голова": "Флоу в крови, биты в сердце",
            "💔 Эмо-рэпер": "Грустный рэп — это искусство",
            "🎤 Хип-хоп душа": "От олдскула до нового звука",
            "🎸 Олдскул рокер": "Классика никогда не умрёт",
            "🤘 Металхэд": "Громче, тяжелее, мощнее",
            "⚡ Рок-н-ролльщик": "Гитары и драйв — твоя стихия",
            "🌙 Инди-меланхолик": "Красота в грусти",
            "🎧 Инди-кид": "Альтернатива мейнстриму",
            "🪩 Рейвер": "Танцуй, пока не рассвело",
            "🌌 Эмбиент-душа": "Музыка как медитация",
            "🎛 Электронщик": "Синтезаторы — твой язык",
            "🎷 Джазовая душа": "Импровизация и свинг",
            "🎻 Классик": "Вечные произведения",
            "💜 R&B вайбы": "Smooth и soulful",
            "🖤 Сэдбой/Сэдгёрл": "Грустить красиво — это талант",
            "🌙 Меланхолик": "Глубина в каждой ноте",
            "☀️ Энерджайзер": "Позитив и движение",
            "✨ Вайбовый": "Только свежие вайбы",
            "🌊 Чиллер": "Расслабься и наслаждайся",
            "⚡ Качатель": "Музыка должна качать",
            "📼 Олдскульщик": "Ностальгия — лучший жанр",
            "🔮 Трендсеттер": "Всегда на острие",
            "🎭 Музыкальный хамелеон": "Нет границ, есть музыка",
            "🎧 Меломан": "Музыка — это жизнь",
        }
        return descriptions.get(self.profile_type, "Уникальный музыкальный вкус")
