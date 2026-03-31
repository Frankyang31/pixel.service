"""
作品广场路由
GET  /api/v1/gallery           公开作品列表（无需登录）
GET  /api/v1/gallery/:id       作品详情
POST /api/v1/gallery/:id/like  点赞/取消点赞
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.config import settings
from app.core.auth.dependencies import get_current_user_optional
from app.db.database import get_db
from app.models.task import Asset, AssetLike
from app.models.user import User
from app.schemas.common import PaginatedResponse

router = APIRouter(tags=["作品广场"])


class GalleryItemResponse(BaseModel):
    id: str
    job_id: str
    cdn_url: str
    thumb_url: str
    width: Optional[int] = None
    height: Optional[int] = None
    likes_count: int
    tool_slug: str
    created_at: str
    is_liked: bool = False  # 当前用户是否已点赞


@router.get("", response_model=PaginatedResponse[GalleryItemResponse])
async def list_gallery(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """公开作品广场（无需登录，登录后显示点赞状态）"""
    base_q = select(Asset).where(Asset.is_public == True)  # noqa: E712
    total = await db.scalar(select(func.count()).select_from(base_q.subquery())) or 0

    assets = (await db.scalars(
        base_q.order_by(Asset.created_at.desc())
               .offset((page - 1) * page_size)
               .limit(page_size)
    )).all()

    # 批量查点赞状态
    liked_ids: set[str] = set()
    if current_user and assets:
        asset_ids = [a.id for a in assets]
        likes = (await db.scalars(
            select(AssetLike.asset_id).where(
                and_(
                    AssetLike.asset_id.in_(asset_ids),
                    AssetLike.user_id == current_user.id,
                )
            )
        )).all()
        liked_ids = set(likes)

    items = [
        GalleryItemResponse(
            id=a.id,
            job_id=a.job_id,
            cdn_url=f"{settings.R2_PUBLIC_DOMAIN}/{a.storage_key}",
            thumb_url=f"{settings.R2_PUBLIC_DOMAIN}/{a.thumb_key}" if a.thumb_key else f"{settings.R2_PUBLIC_DOMAIN}/{a.storage_key}",
            width=a.width,
            height=a.height,
            likes_count=a.likes_count,
            tool_slug="",  # 关联查询 job.tool_slug，此处简化
            created_at=a.created_at.isoformat(),
            is_liked=a.id in liked_ids,
        )
        for a in assets
    ]
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.post("/{asset_id}/like", status_code=204)
async def toggle_like(
    asset_id: str,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """点赞/取消点赞（幂等操作）"""
    if current_user is None:
        from app.utils.exceptions import AuthError
        raise AuthError("请先登录再点赞")

    existing = await db.scalar(
        select(AssetLike).where(
            and_(AssetLike.asset_id == asset_id, AssetLike.user_id == current_user.id)
        )
    )

    asset = await db.get(Asset, asset_id)
    if asset is None:
        from app.utils.exceptions import NotFoundError
        raise NotFoundError("作品不存在")

    if existing:
        # 取消点赞
        await db.execute(
            delete(AssetLike).where(
                and_(AssetLike.asset_id == asset_id, AssetLike.user_id == current_user.id)
            )
        )
        asset.likes_count = max(0, asset.likes_count - 1)
    else:
        # 点赞
        db.add(AssetLike(asset_id=asset_id, user_id=current_user.id))
        asset.likes_count += 1

    await db.commit()
