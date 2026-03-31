"""
User ORM 模型
对应 users 和 refresh_tokens 表
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Index, Integer, SmallInteger,
    String, Text, func
)
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True,
        server_default=func.uuid_generate_v4()
    )

    # 登录凭证（三选一或多选）
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # OAuth
    oauth_wechat_openid: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True)
    oauth_wechat_unionid: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    oauth_google_sub: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True)

    # 基本信息
    nickname: Mapped[str] = mapped_column(String(100), nullable=False, default="用户")
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="zh-CN")

    # 会员状态（冗余字段，快速读取权益）
    membership_level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    membership_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # 安全
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[Optional[str]] = mapped_column(INET, nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # 关联
    points_account: Mapped[Optional["PointsAccount"]] = relationship(  # type: ignore[name-defined]
        "PointsAccount", back_populates="user", uselist=False
    )
    generation_jobs: Mapped[list["GenerationJob"]] = relationship(  # type: ignore[name-defined]
        "GenerationJob", back_populates="user"
    )
    assets: Mapped[list["Asset"]] = relationship(  # type: ignore[name-defined]
        "Asset", back_populates="user"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user"
    )

    __table_args__ = (
        Index("idx_users_email", "email", postgresql_where="email IS NOT NULL"),
        Index("idx_users_phone", "phone", postgresql_where="phone IS NOT NULL"),
        Index("idx_users_wechat_openid", "oauth_wechat_openid",
              postgresql_where="oauth_wechat_openid IS NOT NULL"),
        Index("idx_users_google_sub", "oauth_google_sub",
              postgresql_where="oauth_google_sub IS NOT NULL"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True,
        server_default=func.uuid_generate_v4()
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    device_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("idx_refresh_tokens_user", "user_id"),
        Index("idx_refresh_tokens_active", "user_id",
              postgresql_where="is_revoked = false"),
    )
