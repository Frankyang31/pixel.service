"""
生成任务服务
处理任务提交、状态查询、取消等业务逻辑
"""

from __future__ import annotations

from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_gateway.router import select_model
from app.core.task_queue.celery_app import celery_app
from app.models.task import GenerationJob
from app.models.order import Tool
from app.schemas.generation import CreateJobRequest, JobResponse
from app.services import points_service
from app.utils.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.core.monitoring.logging import get_logger
from app.core.monitoring.metrics import generation_jobs_total, credits_consumed_total

logger = get_logger(__name__)


async def submit_job(
    db: AsyncSession,
    redis: Redis,
    user_id: str,
    membership_level: int,
    request: CreateJobRequest,
) -> JobResponse:
    """
    提交 AI 生成任务
    完整链路：校验工具 → 选模型 → 预扣积分 → 写任务记录 → 入 Celery 队列
    整个过程在同一数据库事务内完成（积分扣减 + 任务写入原子性）
    """
    # 1. 查工具配置
    tool = await db.scalar(
        select(Tool).where(Tool.slug == request.tool_slug, Tool.is_active == True)
    )
    if tool is None:
        raise NotFoundError(f"工具 {request.tool_slug} 不存在")

    # 2. 校验参数
    if len(request.prompt) < 5:
        raise ValidationError("Prompt 太短，至少需要 5 个字符")
    if len(request.prompt) > 2000:
        raise ValidationError("Prompt 超过最大长度 2000 字符")
    if request.aspect_ratio not in tool.supported_aspect_ratios:
        raise ValidationError(f"不支持的宽高比 {request.aspect_ratio}")
    if request.reference_image_url and not tool.supports_reference_image:
        raise ValidationError(f"工具 {request.tool_slug} 不支持参考图")

    # 3. 选择模型（按工具 + 会员等级）
    model_config = select_model(request.tool_slug, membership_level)
    provider = model_config["provider"]
    model_name = model_config["model"]

    # 4. 计算预扣积分
    credits_to_freeze = Decimal(str(tool.credits_min))  # MVP 阶段按 min 预扣

    # 5. 创建任务记录（状态 submitted）
    job = GenerationJob(
        user_id=user_id,
        tool_slug=request.tool_slug,
        model_provider=provider,
        model_name=model_name,
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        aspect_ratio=request.aspect_ratio,
        style_preset=request.style_preset,
        reference_image_url=request.reference_image_url,
        extra_params=request.extra_params or {},
        status="submitted",
        credits_frozen=credits_to_freeze,
    )
    db.add(job)
    await db.flush()  # 获取 job.id（还未提交）

    # 6. 预扣积分（同一事务，原子性）
    await points_service.freeze_for_job(
        db=db,
        redis=redis,
        user_id=user_id,
        job_id=job.id,
        amount=credits_to_freeze,
    )

    # 7. 提交到 Celery（事务提交前先提交，避免任务跑了但 DB 没记录的情况）
    # 注：Celery 任务检查 job 状态，若事务回滚任务会安全退出
    celery_task = celery_app.send_task(
        "tasks.image.generate",
        kwargs={"job_id": job.id},
        queue="image",
    )
    job.celery_task_id = celery_task.id
    job.status = "queued"

    await db.commit()

    # 指标
    generation_jobs_total.labels(tool_slug=request.tool_slug, status="submitted").inc()
    credits_consumed_total.labels(tool_slug=request.tool_slug).inc(float(credits_to_freeze))

    logger.info(
        "job_submitted",
        user_id=user_id, job_id=job.id, tool=request.tool_slug,
        model=f"{provider}/{model_name}", credits=str(credits_to_freeze)
    )

    return JobResponse.from_orm(job)


async def get_job(
    db: AsyncSession,
    redis: Redis,
    user_id: str,
    job_id: str,
) -> JobResponse:
    """查询任务状态（优先读 Redis 进度，降低数据库压力）"""
    job = await db.get(GenerationJob, job_id)
    if job is None:
        raise NotFoundError("任务不存在")
    if job.user_id != user_id:
        raise PermissionDeniedError("无权访问此任务")

    # 从 Redis 读取实时进度（Worker 写入）
    redis_progress = await redis.get(f"job:progress:{job_id}")
    if redis_progress is not None:
        job.progress = int(redis_progress)

    return JobResponse.from_orm(job)


async def cancel_job(
    db: AsyncSession,
    user_id: str,
    job_id: str,
) -> None:
    """取消任务（只能取消 submitted/queued 状态的任务）"""
    job = await db.get(GenerationJob, job_id)
    if job is None:
        raise NotFoundError("任务不存在")
    if job.user_id != user_id:
        raise PermissionDeniedError("无权操作此任务")
    if job.status not in ("submitted", "queued"):
        raise ValidationError("只能取消等待中的任务")

    job.status = "cancelled"
    await db.commit()

    # 退还积分（异步处理）
    await points_service.refund_for_failed_job(db=db, user_id=user_id, job_id=job_id)
    await db.commit()

    logger.info("job_cancelled", user_id=user_id, job_id=job_id)
