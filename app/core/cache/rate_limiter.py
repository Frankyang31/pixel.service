"""
限流器 — 滑动窗口实现
基于 Redis，支持 IP 限流和用户级限流
"""

from __future__ import annotations

import time

from redis.asyncio import Redis

from app.utils.exceptions import RateLimitError


async def check_rate_limit(
    redis: Redis,
    key: str,
    limit: int,
    window_seconds: int,
) -> None:
    """
    滑动窗口限流（基于 sorted set）。
    如果超过限制，抛出 RateLimitError。

    Args:
        redis: Redis 客户端
        key:   限流 key，如 ratelimit:gen:{user_id}
        limit: 窗口内最大请求数
        window_seconds: 窗口大小（秒）
    """
    now = time.time()
    window_start = now - window_seconds
    full_key = f"ratelimit:{key}"

    pipe = redis.pipeline()
    # 删除窗口外的记录
    pipe.zremrangebyscore(full_key, 0, window_start)
    # 添加当前请求
    pipe.zadd(full_key, {str(now): now})
    # 获取窗口内请求数
    pipe.zcard(full_key)
    # 设置 key 过期（避免内存泄露）
    pipe.expire(full_key, window_seconds * 2)

    results = await pipe.execute()
    current_count = results[2]

    if current_count > limit:
        raise RateLimitError(
            f"请求过于频繁，{window_seconds}秒内最多允许{limit}次请求"
        )


async def check_rate_limit_simple(
    redis: Redis,
    key: str,
    limit: int,
    window_seconds: int,
) -> None:
    """
    简单计数器限流（基于 incr + expire，性能更高但精度略低）
    适用于高频低精度场景，如验证码发送
    """
    full_key = f"ratelimit:{key}"
    count = await redis.incr(full_key)
    if count == 1:
        await redis.expire(full_key, window_seconds)
    if count > limit:
        ttl = await redis.ttl(full_key)
        raise RateLimitError(
            f"操作过于频繁，请 {ttl} 秒后再试"
        )
