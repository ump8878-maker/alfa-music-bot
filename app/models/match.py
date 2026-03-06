from sqlalchemy import BigInteger, Float, DateTime, ForeignKey, func, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime

from .database import Base

if TYPE_CHECKING:
    from .user import User
    from .chat import Chat


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("user1_id", "user2_id", "chat_id", name="unique_match"),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user1_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id")
    )
    user2_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id")
    )
    chat_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("chats.id"),
        nullable=True
    )
    match_score: Mapped[float] = mapped_column(Float)
    common_genres: Mapped[List[str]] = mapped_column(JSON, default=list)
    common_artists: Mapped[List[str]] = mapped_column(JSON, default=list)
    genre_score: Mapped[float] = mapped_column(Float, default=0)
    artist_score: Mapped[float] = mapped_column(Float, default=0)
    mood_score: Mapped[float] = mapped_column(Float, default=0)
    era_score: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    user1: Mapped["User"] = relationship("User", foreign_keys=[user1_id])
    user2: Mapped["User"] = relationship("User", foreign_keys=[user2_id])
    chat: Mapped[Optional["Chat"]] = relationship("Chat")
    
    @property
    def score_percent(self) -> int:
        return int(self.match_score * 100)
    
    def get_match_description(self) -> str:
        """Генерирует описание совпадения"""
        parts = []
        
        if self.common_genres:
            genres_str = ", ".join(self.common_genres[:3])
            parts.append(f"🎸 Оба любите: {genres_str}")
        
        if self.common_artists:
            artists_str = ", ".join(self.common_artists[:3])
            parts.append(f"🎤 Общие артисты: {artists_str}")
        
        return "\n".join(parts) if parts else "🎵 Похожий музыкальный вкус"
