"""
图像生成 Celery 任务
处理所有图像工具：character-art, environment-art, sprite-sheet,
                  texture-generator, ai-retouch
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone

from celery import Task
from celery.utils.log import get_task_logger

from app.core.task_queue.celery_app import celery_app

logger = get_task_logger(__name__)

# 每个工具的实际积分消耗（Worker 完成后写入）
TOOL_ACTUAL_COST = {
    "character-art":    4,
    "environment-art":  5,
    "sprite-sheet":     2,
    "texture-generator": 4,
    "ai-retouch":       2,
    "motion-preview":   20,
}


@celery_app.task(
    name="tasks.image.generate",
    bind=True,
    max_retries=5,
    autoretry_for=(Exception,),
    retry_backoff=True,         # 指数退避：1s, 2s, 4s, 8s, 16s
    retry_backoff_max=120,      # 最大等待 2 分钟
    retry_jitter=True,          # 随机抖动
)
def generate_image(self: Task, job_id: str) -> dict:
    """
    图像生成 Worker 任务
    执行顺序：取任务 → 更新状态 → 调用模型 → 压缩上传 → 写 asset → 确认积分
    """
    # 延迟导入，避免循环依赖（Worker 进程独立，不共享 FastAPI 上下文）
    from app.db.database import AsyncSessionLocal
    from app.core.cache.redis_client import get_redis_client
    from app.core.model_gateway.factory import get_adapter
    from app.core.model_gateway.base import GenerateRequest
    from app.core.model_gateway.router import parse_dimensions
    from app.core.storage.r2_client import upload_file
    from app.core.storage.image_processor import process_image
    from app.models.task import GenerationJob, Asset
    from app.services.points_service import confirm_freeze, refund_for_failed_job
    from app.utils.exceptions import NonRetryableModelError
    import asyncio

    redis = get_redis_client()

    async def _run():
        async with AsyncSessionLocal() as db:
            job = await db.get(GenerationJob, job_id)
            if not job or job.status == "cancelled":
                logger.info(f"Job {job_id} cancelled or not found, skipping")
                return {"status": "skipped"}

            try:
                # 1. 更新状态：processing
                job.status = "processing"
                job.processing_started_at = datetime.now(tz=timezone.utc)
                await db.commit()

                # 2. 写进度到 Redis
                await redis.set(f"job:progress:{job_id}", "10", ex=3600)
                await redis.set(f"job:status:{job_id}", "processing", ex=3600)

                # 3. 获取适配器，调用模型
                adapter = get_adapter(job.model_provider, job.model_name)
                width, height = parse_dimensions(job.aspect_ratio)

                req = GenerateRequest(
                    prompt=job.prompt,
                    negative_prompt=job.negative_prompt,
                    width=width,
                    height=height,
                    style_preset=job.style_preset,
                    reference_url=job.reference_image_url,
                )
                result = adapter.generate_sync(req)

                await redis.set(f"job:progress:{job_id}", "70", ex=3600)

                # 4. 下载 → 压缩为 WebP → 生成缩略图
                webp_path, thumb_path, img_width, img_height, file_size = \
                    await process_image(result.image_url, job_id)

                await redis.set(f"job:progress:{job_id}", "90", ex=3600)

                # 5. 上传到 R2
                storage_key = f"images/{job.user_id}/{job_id}.webp"
                thumb_key   = f"thumbs/{job.user_id}/{job_id}.webp"
                await upload_file(webp_path, storage_key, content_type="image/webp")
                await upload_file(thumb_path, thumb_key,   content_type="image/webp")

                # 6. 写 assets 表
                async with db.begin():
                    asset = Asset(
                        job_id=job_id,
                        user_id=job.user_id,
                        storage_key=storage_key,
                        thumb_key=thumb_key,
                        width=img_width,
                        height=img_height,
                        file_size=file_size,
                    )
                    db.add(asset)

                    # 7. 确认积分扣费
                    from decimal import Decimal
                    actual_cost = Decimal(str(TOOL_ACTUAL_COST.get(job.tool_slug, job.credits_frozen or 0)))
                    await confirm_freeze(db=db, user_id=job.user_id, job_id=job_id, actual_amount=actual_cost)

                    # 8. 更新任务完成
                    job.status = "done"
                    job.credits_charged = actual_cost
                    job.completed_at = datetime.now(tz=timezone.utc)
                    job.progress = 100

                # 9. 清除进度缓存
                await redis.delete(f"job:progress:{job_id}", f"job:status:{job_id}")

                # 10. 清理临时文件
                for path in [webp_path, thumb_path]:
                    if path and os.path.exists(path):
                        os.unlink(path)

                logger.info(f"Job {job_id} completed successfully")
                return {"status": "done", "asset_key": storage_key}

            except NonRetryableModelError as e:
                # 不可重试：直接标记失败，退还积分
                logger.error(f"Job {job_id} non-retryable error: {e}")
                async with db.begin():
                    job.status = "failed"
                    job.error_message = str(e)
                    await refund_for_failed_job(db=db, user_id=job.user_id, job_id=job_id)
                raise  # Celery 不重试

            except Exception as e:
                # 可重试错误：更新错误信息，等待 Celery 重试
                logger.warning(f"Job {job_id} retryable error (attempt {self.request.retries}): {e}")
                job.error_message = str(e)
                await db.commit()

                # max_retries 耗尽后的最终失败
                if self.request.retries >= self.max_retries:
                    async with db.begin():
                        job.status = "failed"
                        await refund_for_failed_job(db=db, user_id=job.user_id, job_id=job_id)
                raise

    import asyncio
    return asyncio.run(_run())
