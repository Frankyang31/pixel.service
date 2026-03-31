"""
Redis 连接池模块
提供异步 Redis 客户端，用于缓存、限流、分布式锁、任务进度等
"""

from __future__ import annotations

from redis.asyncio import Redis, ConnectionPool

from app.config import settings

# ── 连接池（全局单例）────────────────────────────────────
_pool: ConnectionPool | None = None
_redis: Redis | None = None


def get_redis_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True,      # 自动解码 bytes → str
        )
    return _pool


def get_redis_client() -> Redis:
    """获取 Redis 客户端单例（复用连接池）"""
    global _redis
    if _redis is None:
        _redis = Redis(connection_pool=get_redis_pool())
    return _redis


# ── FastAPI Depends ──────────────────────────────────────
async def get_redis() -> Redis:
    """
    FastAPI 依赖注入：获取 Redis 客户端。
    在路由函数中使用：redis: Redis = Depends(get_redis)
    """
    return get_redis_client()


# ── 应用生命周期钩子 ─────────────────────────────────────
async def init_redis() -> None:
    """应用启动时预热连接池"""
    redis = get_redis_client()
    await redis.ping()


async def close_redis() -> None:
    """应用关闭时释放连接池"""
    global _pool, _redis
    if _redis:
        await _redis.aclose()
        _redis = None
    if _pool:
        await _pool.aclose()
        _pool = None
