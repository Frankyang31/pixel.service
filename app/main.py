"""
FastAPI 应用主入口
中间件注册 → 路由挂载 → 全局异常处理 → 生命周期钩子
"""

from __future__ import annotations

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import auth, generation, account, gallery, health, webhooks
from app.config import settings
from app.core.cache.redis_client import close_redis, init_redis
from app.core.monitoring.logging import (
    AccessLogMiddleware,
    RequestIDMiddleware,
    configure_logging,
    get_logger,
)
from app.utils.exceptions import AppError

# ── Sentry 初始化（仅生产环境）────────────────────────────
if settings.SENTRY_DSN and settings.is_production:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV,
        traces_sample_rate=0.1,   # 10% 的请求采样
    )

# ── 日志配置 ─────────────────────────────────────────────
configure_logging()
logger = get_logger(__name__)


# ── FastAPI 应用 ─────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="PixelMind 游戏资产 AI 生成平台后端 API",
    docs_url="/docs" if settings.is_development else None,      # 生产禁用 Swagger UI
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
)


# ── 中间件（从外到内执行）────────────────────────────────
# 1. 请求 ID 注入（最外层）
app.add_middleware(RequestIDMiddleware)

# 2. 结构化访问日志
app.add_middleware(AccessLogMiddleware)

# 3. CORS（必须在 Auth 之前，OPTIONS 预检需要通过）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. 响应压缩
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ── 全局异常处理器 ────────────────────────────────────────

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning("app_error", code=exc.error_code, message=exc.message,
                   path=str(request.url.path))
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.error_code, "message": exc.message, "detail": None}
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "code": "VALIDATION_ERROR",
            "message": "请求参数校验失败",
            "detail": exc.errors(),
        }
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", path=str(request.url.path), exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "服务器内部错误", "detail": None}
    )


# ── 生命周期钩子 ─────────────────────────────────────────

@app.on_event("startup")
async def on_startup() -> None:
    await init_redis()
    logger.info("app_started", env=settings.APP_ENV, version=settings.APP_VERSION)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await close_redis()
    logger.info("app_stopped")


# ── 路由挂载 ─────────────────────────────────────────────
app.include_router(auth.router,       prefix="/api/v1/auth")
app.include_router(generation.router, prefix="/api/v1/generation")
app.include_router(account.router,    prefix="/api/v1/account")
app.include_router(gallery.router,    prefix="/api/v1/gallery")
app.include_router(health.router)
app.include_router(webhooks.router,   prefix="/webhooks")
