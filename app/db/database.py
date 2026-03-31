"""
数据库连接模块
异步 SQLAlchemy engine + Session 工厂
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# ── 异步引擎 ─────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,          # 自动检测断开的连接
    pool_recycle=3600,           # 1 小时回收连接（防 MySQL 8h 超时，PG 同理）
    echo=settings.DEBUG,         # 开发模式下打印 SQL
)

# ── Session 工厂 ─────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,      # commit 后对象属性不过期（避免 lazy load 错误）
    autocommit=False,
    autoflush=False,
)


# ── ORM 基类 ─────────────────────────────────────────────
class Base(DeclarativeBase):
    """所有 ORM 模型的基类"""
    pass


# ── FastAPI Depends ──────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入：每次请求获取一个 Session，请求结束后自动关闭。
    在路由函数中使用：db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
