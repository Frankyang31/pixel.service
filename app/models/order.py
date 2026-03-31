"""
订单和工具配置 ORM 模型
对应 membership_orders 和 tools 表
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Index, Integer, SmallInteger,
    Numeric, String, Text, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class MembershipOrder(Base):
    __tablename__ = "membership_orders"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True,
        server_default=func.uuid_generate_v4()
    )
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # 套餐信息
    plan_id: Mapped[str] = mapped_column(String(50), nullable=False)
    plan_name: Mapped[str] = mapped_column(String(100), nullable=False)
    credits_granted: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    membership_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    membership_days: Mapped[int] = mapped_column(Integer, nullable=False)

    # 金额
    currency: Mapped[str] = mapped_column(String(10), nullable=False)  # CNY | USD
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # 支付
    payment_provider: Mapped[str] = mapped_column(String(20), nullable=False)  # wechat | stripe
    payment_order_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payment_intent_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 状态：pending | paid | refunded | expired | cancelled
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User")  # type: ignore[name-defined]

    __table_args__ = (
        Index("idx_orders_user", "user_id", "created_at"),
        Index("idx_orders_payment_id", "payment_order_id",
              postgresql_where="payment_order_id IS NOT NULL"),
        UniqueConstraint("payment_intent_id", name="idx_orders_stripe_intent"),
    )

    def __repr__(self) -> str:
        return f"<MembershipOrder id={self.id} plan={self.plan_id} status={self.status}>"


class Tool(Base):
    """
    工具配置表。MVP 阶段数据从 init.sql 插入，运营可通过管理后台修改。
    """
    __tablename__ = "tools"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True,
        server_default=func.uuid_generate_v4()
    )
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    # 多语言名称
    name_zh: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    description_zh: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 积分定价
    credits_min: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    credits_max: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # 模型配置（JSON，灵活配置不同会员等级对应的模型）
    model_config_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, name="model_config"
    )

    # 支持的参数
    supported_aspect_ratios: Mapped[list] = mapped_column(
        ARRAY(String), nullable=False,
        default=lambda: ["1:1", "2:3", "3:4", "9:16"]
    )
    supported_style_presets: Mapped[list] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    supports_reference_image: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supports_negative_prompt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # 状态与排序
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    # SEO
    seo_title_zh: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    seo_title_en: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    seo_desc_zh: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    seo_desc_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Tool slug={self.slug} name={self.name_zh}>"
