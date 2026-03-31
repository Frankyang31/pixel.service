"""
健康检查路由
GET /health        快速检查（负载均衡心跳用）
GET /health/deep   深度检查（DB + Redis 连通性）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache.redis_client import get_redis
from app.db.database import get_db

router = APIRouter(tags=["健康检查"])


@router.get("/health")
async def health():
    """快速健康检查（不查数据库，负载均衡 ping 用）"""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
    }


@router.get("/health/deep")
async def deep_health(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """深度健康检查（验证 DB + Redis 连通性）"""
    checks = {}

    # PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Redis
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
    }
