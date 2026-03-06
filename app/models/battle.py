from sqlalchemy import BigInteger, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime

from .database import Base

if TYPE_CHECKING:
    from .user import User
    from .chat import Chat


class Battle(Base):
    __tablename__ = "battles"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chats.id")
    )
    user1_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id")
    )
    user2_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id")
    )
    status: Mapped[str] = mapped_column(String(20), default="active")
    votes_user1: Mapped[int] = mapped_column(Integer, default=0)
    votes_user2: Mapped[int] = mapped_column(Integer, default=0)
    winner_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    chat: Mapped["Chat"] = relationship("Chat")
    user1: Mapped["User"] = relationship("User", foreign_keys=[user1_id])
    user2: Mapped["User"] = relationship("User", foreign_keys=[user2_id])
    votes: Mapped[list["BattleVote"]] = relationship("BattleVote", back_populates="battle")
    
    @property
    def total_votes(self) -> int:
        return self.votes_user1 + self.votes_user2
    
    @property
    def is_active(self) -> bool:
        return self.status == "active"
    
    def get_winner(self) -> Optional["User"]:
        if self.votes_user1 > self.votes_user2:
            return self.user1
        elif self.votes_user2 > self.votes_user1:
            return self.user2
        return None


class BattleVote(Base):
    __tablename__ = "battle_votes"
    
    battle_id: Mapped[int] = mapped_column(
        ForeignKey("battles.id"),
        primary_key=True
    )
    voter_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        primary_key=True
    )
    voted_for_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    battle: Mapped["Battle"] = relationship("Battle", back_populates="votes")
    voter: Mapped["User"] = relationship("User", foreign_keys=[voter_id])
    voted_for: Mapped["User"] = relationship("User", foreign_keys=[voted_for_id])
