"""
结构化日志 + RequestID 中间件
使用 structlog，每条日志自动包含 request_id、方法、路径等上下文字段
"""

from __future__ import annotations

import logging
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings


def configure_logging() -> None:
    """
    应用启动时调用一次，配置 structlog 全局渲染链。
    开发环境：彩色控制台输出
    生产环境：JSON 格式输出（便于 ELK / CloudWatch 解析）
    """
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_development:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.LOG_LEVEL)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 同步标准库 logging 到 structlog
    logging.basicConfig(
        format="%(message)s",
        level=logging.getLevelName(settings.LOG_LEVEL),
    )


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """获取带名称的结构化日志器"""
    return structlog.get_logger(name)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    为每个请求注入唯一 request_id，并绑定到 structlog context。
    所有后续日志自动携带 request_id，便于追踪全链路。
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 优先使用客户端传入的 X-Request-ID，否则自动生成
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # 清理上一个请求的 contextvars（避免串扰）
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=str(request.url.path),
        )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    """记录每次 HTTP 请求的访问日志"""

    _logger = get_logger("access")

    async def dispatch(self, request: Request, call_next) -> Response:
        import time
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        self._logger.info(
            "http_request",
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else None,
        )
        return response
