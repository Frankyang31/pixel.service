"""
AI 生成任务和资产 ORM 模型
对应 generation_jobs、assets、asset_likes 表
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Index, Integer, SmallInteger,
    Numeric, String, Text, func
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True,
        server_default=func.uuid_generate_v4()
    )
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # 工具与参数
    tool_slug: Mapped[str] = mapped_column(String(50), nullable=False)
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    negative_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    aspect_ratio: Mapped[str] = mapped_column(String(10), nullable=False, default="2:3")
    style_preset: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # 状态机
    # submitted → queued → processing → done | failed | cancelled
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="submitted")
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    progress: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 积分
    credits_frozen: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    credits_charged: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    credits_refunded: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0")
    )

    # 时间
    queued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # 关联
    user: Mapped["User"] = relationship("User", back_populates="generation_jobs")  # type: ignore[name-defined]
    assets: Mapped[list["Asset"]] = relationship("Asset", back_populates="job")

    __table_args__ = (
        Index("idx_jobs_user_status", "user_id", "status"),
        Index("idx_jobs_user_created", "user_id", "created_at"),
        Index("idx_jobs_celery_id", "celery_task_id",
              postgresql_where="celery_task_id IS NOT NULL"),
        Index("idx_jobs_status_queued", "created_at",
              postgresql_where="status = 'queued'"),
    )

    def __repr__(self) -> str:
        return f"<GenerationJob id={self.id} tool={self.tool_slug} status={self.status}>"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True,
        server_default=func.uuid_generate_v4()
    )
    job_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # 文件信息
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    thumb_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_format: Mapped[str] = mapped_column(String(20), nullable=False, default="webp")
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 展示属性
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_starred: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    likes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # 关联
    job: Mapped["GenerationJob"] = relationship("GenerationJob", back_populates="assets")
    user: Mapped["User"] = relationship("User", back_populates="assets")  # type: ignore[name-defined]
    likes: Mapped[list["AssetLike"]] = relationship("AssetLike", back_populates="asset")

    __table_args__ = (
        Index("idx_assets_user", "user_id", "created_at"),
        Index("idx_assets_user_starred", "user_id",
              postgresql_where="is_starred = true"),
        Index("idx_assets_public", "created_at",
              postgresql_where="is_public = true"),
        Index("idx_assets_job", "job_id"),
    )

    def __repr__(self) -> str:
        return f"<Asset id={self.id} job_id={self.job_id}>"


class AssetLike(Base):
    __tablename__ = "asset_likes"

    asset_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    asset: Mapped["Asset"] = relationship("Asset", back_populates="likes")
