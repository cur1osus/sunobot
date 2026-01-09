from datetime import datetime

from sqlalchemy import BigInteger, String, func
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.enum import UserRole

from .base import Base


class UserModel(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(100))
    credits: Mapped[int] = mapped_column(default=2)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.USER.value)

    referrer_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    balance: Mapped[int] = mapped_column(default=0, nullable=False)
    # TODO: another table for calculate referral_paid, payout_amount

    registration_datetime: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
    )
    last_active: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
