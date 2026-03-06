from sqlalchemy import BigInteger, String, Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime

from .database import Base

if TYPE_CHECKING:
    from .user import User


class Chat(Base):
    __tablename__ = "chats"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    type: Mapped[str] = mapped_column(String(50))
    member_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    map_unlocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    added_by_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=True
    )
    
    members: Mapped[list["ChatMember"]] = relationship(
        "ChatMember",
        back_populates="chat"
    )
    added_by: Mapped[Optional["User"]] = relationship("User")
    
    @property
    def tested_members_count(self) -> int:
        return sum(1 for m in self.members if m.has_completed_test)


class ChatMember(Base):
    __tablename__ = "chat_members"
    
    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chats.id"),
        primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        primary_key=True
    )
    has_completed_test: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    chat: Mapped["Chat"] = relationship("Chat", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="chat_memberships")
