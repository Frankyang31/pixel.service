"""
Celery 应用配置
三队列隔离：image / video / system
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery("pixelmind")

celery_app.config_from_object({
    "broker_url":                  settings.CELERY_BROKER_URL,
    "result_backend":              settings.CELERY_RESULT_BACKEND,
    "task_serializer":             "json",
    "accept_content":              ["json"],
    "result_serializer":           "json",
    "timezone":                    "UTC",
    "enable_utc":                  True,

    # ── AI 任务关键配置 ──────────────────────────────────
    "worker_prefetch_multiplier":  1,    # 每次只取 1 个任务，AI 任务耗时长，避免饥饿
    "task_acks_late":              True, # 任务完成后才 ACK，Worker 崩溃可重试
    "task_reject_on_worker_lost":  True, # Worker 意外退出，任务重新入队
    "task_time_limit":             600,  # 硬限制：10 分钟超时强制杀死
    "task_soft_time_limit":        540,  # 软限制：9 分钟触发 SoftTimeLimitExceeded

    # ── 三队列路由 ────────────────────────────────────────
    "task_routes": {
        "tasks.image.*": {"queue": "image"},   # 图像生成
        "tasks.video.*": {"queue": "video"},   # 视频/动画
        "tasks.system.*": {"queue": "system"}, # 定时清理
    },
    "task_default_queue": "image",

    # ── 定时任务 ─────────────────────────────────────────
    "beat_schedule": {
        "cleanup-expired-jobs": {
            "task":     "tasks.system.cleanup_expired_jobs",
            "schedule": crontab(hour=3, minute=0),  # 每天凌晨 3 点
        },
        # 增长阶段启用（Redis 积分 → PG 同步）
        # "sync-points-to-db": {
        #     "task":     "tasks.system.sync_redis_points",
        #     "schedule": crontab(minute="*/5"),
        # },
    },

    # ── 任务模块自动发现 ──────────────────────────────────
    "include": [
        "app.core.task_queue.tasks.image_tasks",
        "app.core.task_queue.tasks.video_tasks",
        "app.core.task_queue.tasks.system_tasks",
    ],
})
