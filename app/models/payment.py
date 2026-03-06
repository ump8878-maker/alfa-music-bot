from sqlalchemy import BigInteger, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime

from .database import Base

if TYPE_CHECKING:
    from .user import User


class Payment(Base):
    __tablename__ = "payments"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id")
    )
    amount: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(10), default="XTR")
    product: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    telegram_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    user: Mapped["User"] = relationship("User")


class UserUnlock(Base):
    __tablename__ = "user_unlocks"
    
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        primary_key=True
    )
    unlock_type: Mapped[str] = mapped_column(String(100), primary_key=True)
    chat_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("chats.id"),
        nullable=True
    )
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    user: Mapped["User"] = relationship("User")


# Типы unlock
class UnlockType:
    ALL_MATCHES = "all_matches"
    WHO_CHOSE_ME = "who_chose_me"
    FULL_INSIGHTS = "full_insights"
    PREMIUM_WEEK = "premium_week"
    PREMIUM_MONTH = "premium_month"


# Продукты и цены (в Telegram Stars)
class Products:
    UNLOCK_MATCHES = {
        "id": "unlock_matches",
        "title": "Открыть все совпадения",
        "price": 50,
    }
    WHO_CHOSE_ME = {
        "id": "who_chose_me",
        "title": "Кто угадал твой вкус",
        "price": 30,
    }
    FULL_INSIGHTS = {
        "id": "full_insights",
        "title": "Полная аналитика вкуса",
        "price": 75,
    }
    PREMIUM_WEEK = {
        "id": "premium_week",
        "title": "Premium на неделю",
        "price": 100,
    }
