"""
公共 Pydantic Schema
分页、错误响应通用模型
"""

from __future__ import annotations

import math
from typing import Generic, Optional, TypeVar, Any

from pydantic import BaseModel, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """统一成功响应包装"""
    data: T
    meta: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """统一错误响应"""
    code: str
    message: str
    detail: Optional[Any] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: list[T]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")
    total_pages: int = Field(alias="totalPages")

    model_config = {"populate_by_name": True}

    @classmethod
    def create(
        cls,
        items: list,
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse":
        return cls(
            items=items,
            total=total,
            page=page,
            pageSize=page_size,
            totalPages=math.ceil(total / page_size) if page_size > 0 else 0,
        )


class PageParams(BaseModel):
    """分页查询参数"""
    page: int = Field(default=1, ge=1, description="页码（从 1 开始）")
    page_size: int = Field(default=20, ge=1, le=100, alias="pageSize", description="每页条数")

    model_config = {"populate_by_name": True}

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
