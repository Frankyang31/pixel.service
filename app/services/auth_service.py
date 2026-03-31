"""
认证服务
处理注册/登录/OAuth/Token 刷新等全链路
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth.jwt import create_access_token, create_refresh_token, hash_token
from app.core.monitoring.logging import get_logger
from app.core.monitoring.metrics import user_registrations_total
from app.models.user import RefreshToken, User
from app.models.points import PointsAccount
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.points_service import earn_credits
from app.utils.exceptions import (
    AuthError, ConflictError, NotFoundError, TokenExpiredError
)
from decimal import Decimal

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


async def _create_tokens(user: User, db: AsyncSession, ip: str | None = None) -> TokenResponse:
    """内部：生成双 Token 并写入数据库"""
    access_token = create_access_token(user.id, user.membership_level)
    token_plain, token_hash = create_refresh_token(user.id)

    expires_at = datetime.now(tz=timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        ip_address=ip,
        expires_at=expires_at,
    ))
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=token_plain,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    )


async def register_with_email(
    db: AsyncSession,
    request: RegisterRequest,
    ip: str | None = None,
) -> TokenResponse:
    """邮箱注册"""
    # 检查邮箱唯一性
    existing = await db.scalar(select(User).where(User.email == request.email))
    if existing:
        raise ConflictError("该邮箱已注册，请直接登录")

    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        nickname=request.nickname or "用户",
        locale=request.locale or "zh-CN",
    )
    db.add(user)
    await db.flush()

    # 创建积分账户 + 注册赠送积分
    db.add(PointsAccount(user_id=user.id))
    await db.flush()

    await earn_credits(
        db=db,
        user_id=user.id,
        amount=Decimal(str(settings.SIGNUP_BONUS_CREDITS)),
        source="SIGNUP_BONUS",
        transaction_id=f"SIGNUP:{user.id}",
        remark="新用户注册赠送",
    )

    user_registrations_total.labels(method="email").inc()
    logger.info("user_registered", user_id=user.id, method="email")

    return await _create_tokens(user, db, ip)


async def login_with_email(
    db: AsyncSession,
    request: LoginRequest,
    ip: str | None = None,
) -> TokenResponse:
    """邮箱密码登录"""
    user = await db.scalar(select(User).where(User.email == request.email))
    if not user or not user.password_hash:
        raise AuthError("邮箱或密码错误")
    if not verify_password(request.password, user.password_hash):
        raise AuthError("邮箱或密码错误")
    if not user.is_active:
        raise AuthError("账号已被禁用")

    user.last_login_at = datetime.now(tz=timezone.utc)
    user.last_login_ip = ip

    logger.info("user_login", user_id=user.id, method="email")
    return await _create_tokens(user, db, ip)


async def login_or_register_with_wechat(
    db: AsyncSession,
    openid: str,
    unionid: str | None,
    nickname: str,
    avatar_url: str | None,
    ip: str | None = None,
) -> TokenResponse:
    """微信 OAuth 登录/注册（一体化）"""
    user = await db.scalar(
        select(User).where(User.oauth_wechat_openid == openid)
    )

    if user is None:
        # 新用户，自动注册
        user = User(
            oauth_wechat_openid=openid,
            oauth_wechat_unionid=unionid,
            nickname=nickname,
            avatar_url=avatar_url,
            locale="zh-CN",
        )
        db.add(user)
        await db.flush()
        db.add(PointsAccount(user_id=user.id))
        await db.flush()
        await earn_credits(
            db=db,
            user_id=user.id,
            amount=Decimal(str(settings.SIGNUP_BONUS_CREDITS)),
            source="SIGNUP_BONUS",
            transaction_id=f"SIGNUP:{user.id}",
        )
        user_registrations_total.labels(method="wechat").inc()
        logger.info("user_registered", user_id=user.id, method="wechat")
    else:
        # 老用户，更新头像昵称
        user.nickname = nickname
        if avatar_url:
            user.avatar_url = avatar_url
        user.last_login_at = datetime.now(tz=timezone.utc)

    return await _create_tokens(user, db, ip)


async def login_or_register_with_google(
    db: AsyncSession,
    google_sub: str,
    email: str | None,
    nickname: str,
    avatar_url: str | None,
    ip: str | None = None,
) -> TokenResponse:
    """Google OAuth 登录/注册（一体化）"""
    user = await db.scalar(
        select(User).where(User.oauth_google_sub == google_sub)
    )

    if user is None:
        user = User(
            oauth_google_sub=google_sub,
            email=email,
            is_email_verified=True,
            nickname=nickname,
            avatar_url=avatar_url,
            locale="en",
        )
        db.add(user)
        await db.flush()
        db.add(PointsAccount(user_id=user.id))
        await db.flush()
        await earn_credits(
            db=db,
            user_id=user.id,
            amount=Decimal(str(settings.SIGNUP_BONUS_CREDITS)),
            source="SIGNUP_BONUS",
            transaction_id=f"SIGNUP:{user.id}",
        )
        user_registrations_total.labels(method="google").inc()
        logger.info("user_registered", user_id=user.id, method="google")
    else:
        user.last_login_at = datetime.now(tz=timezone.utc)

    return await _create_tokens(user, db, ip)


async def refresh_access_token(
    db: AsyncSession,
    refresh_token: str,
    ip: str | None = None,
) -> TokenResponse:
    """用 Refresh Token 换新 Access Token"""
    token_hash = hash_token(refresh_token)

    rt = await db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,  # noqa: E712
        )
    )
    if rt is None:
        raise AuthError("无效的刷新令牌，请重新登录")

    if rt.expires_at < datetime.now(tz=timezone.utc):
        raise TokenExpiredError("刷新令牌已过期，请重新登录")

    user = await db.get(User, rt.user_id)
    if not user or not user.is_active:
        raise AuthError("用户不存在或已被禁用")

    # 吊销旧 Refresh Token（单设备策略：可选），发新 Access Token
    access_token = create_access_token(user.id, user.membership_level)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,  # 复用，不轮换（可按需改为轮换）
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    )


async def logout(
    db: AsyncSession,
    refresh_token: str,
) -> None:
    """登出：吊销 Refresh Token"""
    token_hash = hash_token(refresh_token)
    rt = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if rt:
        rt.is_revoked = True
        await db.commit()
