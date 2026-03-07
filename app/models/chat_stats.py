# Агрегированная статистика чата: рейтинг, профиль, защита от спама
from sqlalchemy import BigInteger, Float, String, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime

from .database import Base

if TYPE_CHECKING:
    from .chat import Chat


class ChatStats(Base):
    """Кэш рейтинга и профиля чата + время последнего мотивирующего сообщения (антиспам)."""
    __tablename__ = "chat_stats"

    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chats.id"),
        primary_key=True,
    )
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    profile_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    top_genres: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)  # [{"name": "techno", "pct": 30}, ...]
    top_artists: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    participants_count: Mapped[int] = mapped_column(default=0)
    last_scan_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_growth_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    chat: Mapped["Chat"] = relationship("Chat", back_populates="stats")
