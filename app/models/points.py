"""
积分相关 ORM 模型
对应 points_accounts 和 points_transactions 表
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    CheckConstraint, DateTime, Index, Integer,
    Numeric, String, Text, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class PointsAccount(Base):
    __tablename__ = "points_accounts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True,
        server_default=func.uuid_generate_v4()
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), unique=True, nullable=False
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    frozen_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    total_earned: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    total_spent: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="points_account")  # type: ignore[name-defined]
    transactions: Mapped[list["PointsTransaction"]] = relationship(
        "PointsTransaction", back_populates="account",
        foreign_keys="PointsTransaction.user_id",
        primaryjoin="PointsAccount.user_id == PointsTransaction.user_id",
    )

    __table_args__ = (
        CheckConstraint("balance >= 0", name="chk_points_balance_non_negative"),
        CheckConstraint("frozen_balance >= 0", name="chk_points_frozen_non_negative"),
    )


class PointsTransaction(Base):
    __tablename__ = "points_transactions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True,
        server_default=func.uuid_generate_v4()
    )
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # 幂等键（业务唯一键）
    transaction_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)

    # 变动信息
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    # EARN | SPEND | FREEZE | UNFREEZE | REFUND
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    balance_before: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # 来源
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    # SIGNUP_BONUS | SIGN_IN | MEMBERSHIP | API_CALL | ACTIVITY | REFUND
    reference_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # job | order | activity
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    account: Mapped["PointsAccount"] = relationship(
        "PointsAccount",
        foreign_keys=[user_id],
        primaryjoin="PointsTransaction.user_id == PointsAccount.user_id",
        back_populates="transactions",
    )

    __table_args__ = (
        UniqueConstraint("transaction_id", name="uq_points_transaction_id"),
        Index("idx_points_tx_user_time", "user_id", "created_at"),
        Index("idx_points_tx_ref", "reference_id",
              postgresql_where="reference_id IS NOT NULL"),
    )
