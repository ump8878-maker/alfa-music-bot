# Модель результата квиза для аналитики и истории
from sqlalchemy import BigInteger, Float, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime

from .database import Base

if TYPE_CHECKING:
    from .user import User
    from .chat import Chat


class QuizResult(Base):
    __tablename__ = "quiz_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    chat_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("chats.id"), nullable=True
    )
    answers: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship("User")
    chat: Mapped[Optional["Chat"]] = relationship("Chat")
