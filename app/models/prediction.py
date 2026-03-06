from sqlalchemy import BigInteger, String, Integer, Boolean, DateTime, ForeignKey, Text, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime

from .database import Base

if TYPE_CHECKING:
    from .user import User
    from .chat import Chat


class PredictionRound(Base):
    __tablename__ = "prediction_rounds"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chats.id")
    )
    question_type: Mapped[str] = mapped_column(String(50))
    question_text: Mapped[str] = mapped_column(Text)
    about_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id")
    )
    correct_answer: Mapped[str] = mapped_column(String(255))
    options: Mapped[List[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="active")
    message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    chat: Mapped["Chat"] = relationship("Chat")
    about_user: Mapped["User"] = relationship("User")
    answers: Mapped[list["PredictionAnswer"]] = relationship(
        "PredictionAnswer",
        back_populates="round"
    )
    
    @property
    def is_active(self) -> bool:
        return self.status == "active"
    
    @property
    def participants_count(self) -> int:
        return len(self.answers)
    
    @property
    def correct_answers_count(self) -> int:
        return sum(1 for a in self.answers if a.is_correct)


class PredictionAnswer(Base):
    __tablename__ = "prediction_answers"
    
    round_id: Mapped[int] = mapped_column(
        ForeignKey("prediction_rounds.id"),
        primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        primary_key=True
    )
    answer: Mapped[str] = mapped_column(String(255))
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    round: Mapped["PredictionRound"] = relationship(
        "PredictionRound",
        back_populates="answers"
    )
    user: Mapped["User"] = relationship("User")
