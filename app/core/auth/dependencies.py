"""
FastAPI 认证依赖注入
提供 get_current_user 和 require_membership 两个 Depends 工厂
"""

from __future__ import annotations

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.jwt import decode_access_token
from app.db.database import get_db
from app.models.user import User
from app.utils.exceptions import AuthError, MembershipRequiredError, NotFoundError

http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(http_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    验证 Bearer Token，返回当前用户对象。
    Token 无效或过期时抛 AuthError/TokenExpiredError（HTTP 401）。
    """
    if credentials is None:
        raise AuthError("请求需要登录，请提供访问令牌")

    payload = decode_access_token(credentials.credentials)
    user_id: str = payload["sub"]

    user = await db.get(User, user_id)
    if not user:
        raise NotFoundError("用户不存在")
    if not user.is_active:
        raise AuthError("账号已被禁用，请联系客服")

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Security(http_bearer),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    可选认证：Token 存在则验证并返回用户，不存在则返回 None（公开接口使用）。
    """
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials=credentials, db=db)
    except Exception:
        return None


def require_membership(min_level: int = 1):
    """
    工厂函数，生成会员等级守卫 Depends。

    用法示例:
        @router.post("/pro-feature")
        async def pro_feature(
            current_user: User = Depends(require_membership(min_level=2))
        ):
            ...
    """
    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.membership_level < min_level:
            raise MembershipRequiredError(min_level)
        return user
    return _check
