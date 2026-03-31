"""
生成任务相关 Schema
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Any

from pydantic import BaseModel, Field


class CreateJobRequest(BaseModel):
    tool_slug: str = Field(description="工具 slug，如 character-art")
    prompt: str = Field(min_length=5, max_length=2000)
    negative_prompt: Optional[str] = Field(default=None, max_length=500)
    aspect_ratio: str = Field(default="2:3", pattern="^(1:1|2:3|3:4|9:16|16:9|21:9)$")
    style_preset: Optional[str] = None
    reference_image_url: Optional[str] = None
    extra_params: Optional[dict[str, Any]] = None


class JobResponse(BaseModel):
    id: str
    tool_slug: str
    model_provider: str
    model_name: str
    prompt: str
    status: str
    progress: int
    credits_frozen: Optional[Decimal] = None
    credits_charged: Optional[Decimal] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
    completed_at: Optional[str] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, job) -> "JobResponse":
        return cls(
            id=str(job.id),
            tool_slug=job.tool_slug,
            model_provider=job.model_provider,
            model_name=job.model_name,
            prompt=job.prompt,
            status=job.status,
            progress=job.progress,
            credits_frozen=job.credits_frozen,
            credits_charged=job.credits_charged,
            error_message=job.error_message,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat(),
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
        )


class AssetResponse(BaseModel):
    id: str
    job_id: str
    storage_key: str
    thumb_key: Optional[str] = None
    cdn_url: str
    thumb_url: Optional[str] = None
    file_format: str
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    is_public: bool
    is_starred: bool
    likes_count: int
    created_at: str

    model_config = {"from_attributes": True}
