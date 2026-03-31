"""
生成任务路由
POST /api/v1/generation/jobs         提交任务
GET  /api/v1/generation/jobs         查询任务列表
GET  /api/v1/generation/jobs/:id     查询单任务状态
POST /api/v1/generation/jobs/:id/cancel  取消任务
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.cache.rate_limiter import check_rate_limit
from app.core.cache.redis_client import get_redis
from app.db.database import get_db
from app.models.task import GenerationJob
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.generation import CreateJobRequest, JobResponse
from app.services import generation_service

router = APIRouter(tags=["生成任务"])


@router.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(
    body: CreateJobRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """
    提交 AI 生成任务。
    限流规则：L0(free)=3次/min，L1(basic)=10次/min，L2+(pro)=30次/min
    """
    # 按会员等级限流
    limits = {0: 3, 1: 10, 2: 30, 3: 60}
    limit = limits.get(current_user.membership_level, 3)
    await check_rate_limit(redis, f"gen:{current_user.id}", limit, window_seconds=60)

    return await generation_service.submit_job(
        db=db,
        redis=redis,
        user_id=current_user.id,
        membership_level=current_user.membership_level,
        request=body,
    )


@router.get("/jobs", response_model=PaginatedResponse[JobResponse])
async def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    status: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询当前用户的任务列表"""
    q = select(GenerationJob).where(GenerationJob.user_id == current_user.id)
    if status:
        q = q.where(GenerationJob.status == status)
    q = q.order_by(GenerationJob.created_at.desc())

    total = await db.scalar(
        select(func.count()).select_from(
            select(GenerationJob).where(GenerationJob.user_id == current_user.id).subquery()
        )
    ) or 0

    jobs = (await db.scalars(q.offset((page - 1) * page_size).limit(page_size))).all()
    items = [JobResponse.from_orm(j) for j in jobs]

    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """查询单个任务状态（前端轮询使用）"""
    return await generation_service.get_job(
        db=db, redis=redis, user_id=current_user.id, job_id=job_id
    )


@router.post("/jobs/{job_id}/cancel", status_code=204)
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取消等待中的任务"""
    await generation_service.cancel_job(db=db, user_id=current_user.id, job_id=job_id)
