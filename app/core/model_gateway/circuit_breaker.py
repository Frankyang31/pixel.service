"""
三态熔断器实现
状态存储在 Redis，多 Worker 共享
closed（正常）→ open（熔断）→ half_open（探测）→ closed
"""

from __future__ import annotations

import asyncio

from redis.asyncio import Redis

from app.core.monitoring.logging import get_logger
from app.utils.exceptions import CircuitOpenError, RetryableModelError

logger = get_logger(__name__)


class CircuitBreaker:
    FAILURE_THRESHOLD = 5    # 60s 内失败 5 次则熔断
    FAILURE_WINDOW    = 60   # 失败计数窗口（秒）
    OPEN_DURATION     = 300  # 熔断持续时间（秒），5 分钟后进入 half_open
    HALF_OPEN_PROBE   = 1    # 半开状态允许通过的请求数（探针）

    def __init__(self, provider: str, redis: Redis):
        self.provider = provider
        self.redis = redis
        self._failure_key  = f"circuit:{provider}:failures"
        self._state_key    = f"circuit:{provider}:state"
        self._halfopen_key = f"circuit:{provider}:halfopen_count"

    async def get_state(self) -> str:
        state = await self.redis.get(self._state_key)
        if state is None:
            return "closed"
        return state if isinstance(state, str) else state.decode()

    async def call(self, func, *args, **kwargs):
        """
        通过熔断器调用函数。
        - closed：正常调用
        - open：直接抛 CircuitOpenError
        - half_open：允许有限数量的探针请求通过
        """
        state = await self.get_state()

        if state == "open":
            raise CircuitOpenError(self.provider)

        if state == "half_open":
            probe_count = await self.redis.incr(self._halfopen_key)
            if probe_count > self.HALF_OPEN_PROBE:
                raise CircuitOpenError(self.provider)

        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) \
                else func(*args, **kwargs)
            # 成功：重置所有计数器
            await self.redis.delete(self._failure_key, self._state_key, self._halfopen_key)
            return result

        except (RetryableModelError, asyncio.TimeoutError, ConnectionError) as e:
            failures = await self.redis.incr(self._failure_key)
            await self.redis.expire(self._failure_key, self.FAILURE_WINDOW)

            if int(failures) >= self.FAILURE_THRESHOLD:
                await self.redis.set(self._state_key, "open", ex=self.OPEN_DURATION)
                logger.warning(
                    "circuit_breaker_opened",
                    provider=self.provider,
                    failures=failures
                )

            raise

    async def force_close(self) -> None:
        """手动关闭熔断器（运维操作）"""
        await self.redis.delete(self._failure_key, self._state_key, self._halfopen_key)
        logger.info("circuit_breaker_force_closed", provider=self.provider)
