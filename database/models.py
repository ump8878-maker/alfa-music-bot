from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    BigInteger,
    String,
    Boolean,
    DateTime,
    Float,
    Integer,
    Index,
    ForeignKey,
    func,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    is_bot_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    score: Mapped[float] = mapped_column(Float, default=0.0)

    music_profile: Mapped[Optional["MusicProfile"]] = relationship(
        "MusicProfile", back_populates="user", uselist=False
    )
    chat_memberships: Mapped[list["ChatMember"]] = relationship(
        "ChatMember", back_populates="user"
    )

    @property
    def display_name(self) -> str:
        if self.first_name:
            return self.first_name
        if self.username:
            return f"@{self.username}"
        return f"User {self.id}"

    @property
    def mention(self) -> str:
        if self.username:
            return f"@{self.username}"
        return f'<a href="tg://user?id={self.id}">{self.display_name}</a>'


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    type: Mapped[str] = mapped_column(String(50))
    member_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    owner_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    owner_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    added_by_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )

    members: Mapped[list["ChatMember"]] = relationship(
        "ChatMember", back_populates="chat"
    )
    added_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[added_by_user_id]
    )
    owner: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[owner_id]
    )
    stats: Mapped[Optional["ChatStats"]] = relationship(
        "ChatStats", back_populates="chat", uselist=False
    )


class ChatMember(Base):
    __tablename__ = "chat_members"
    __table_args__ = (
        Index("ix_chat_members_completed", "chat_id", "has_completed_test"),
    )

    chat_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chats.id"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), primary_key=True
    )
    has_completed_test: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    chat: Mapped["Chat"] = relationship("Chat", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="chat_memberships")


class ChatStats(Base):
    __tablename__ = "chat_stats"

    chat_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("chats.id"), primary_key=True
    )
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    profile_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    top_genres: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    top_artists: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    participants_count: Mapped[int] = mapped_column(Integer, default=0)
    last_scan_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_growth_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    chat: Mapped["Chat"] = relationship("Chat", back_populates="stats")


class MusicProfile(Base):
    __tablename__ = "music_profiles"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), primary_key=True
    )
    genres: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    artists: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    mood: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    era: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    language_pref: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    listening_time: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rarity_score: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="music_profile")

    @property
    def genre_names(self) -> List[str]:
        return [g.get("name", "") for g in (self.genres or [])]

    @property
    def artist_names(self) -> List[str]:
        return [a.get("name", "") for a in (self.artists or [])]

    @property
    def profile_type(self) -> str:
        genre_names = [g.get("name", "").lower() for g in (self.genres or [])]
        if self.rarity_score > 0.8:
            return "🦄 Андерграунд-гуру"
        if self.rarity_score > 0.65:
            return "💎 Охотник за редкостями"
        if self.rarity_score < 0.2:
            return "📻 Чартовый маньяк"
        if self.rarity_score < 0.35:
            return "🎯 Хитмейкер"
        if "hiphop" in genre_names:
            return "🎤 Хип-хоп душа"
        if "rock" in genre_names or "metal" in genre_names:
            return "⚡ Рок-н-ролльщик"
        if "indie" in genre_names:
            return "🎧 Инди-кид"
        if "electronic" in genre_names:
            return "🎛 Электронщик"
        if "jazz" in genre_names or "soul" in genre_names:
            return "🎷 Джазовая душа"
        if self.mood == "melancholic":
            return "🌙 Меланхолик"
        if self.mood == "energetic":
            return "☀️ Энерджайзер"
        if self.mood == "calm":
            return "🌊 Чиллер"
        if len(self.genres or []) >= 3:
            return "🎭 Музыкальный хамелеон"
        return "🎧 Меломан"


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
