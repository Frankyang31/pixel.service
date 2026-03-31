"""
JWT 工具模块
负责 Access Token 和 Refresh Token 的生成与验证
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, ExpiredSignatureError, jwt

from app.config import settings
from app.utils.exceptions import AuthError, TokenExpiredError


def create_access_token(user_id: str, membership_level: int) -> str:
    """
    生成 Access Token（短效，2 小时）
    Payload 中携带 membership_level，避免每次请求都查数据库
    """
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": user_id,
        "ml": membership_level,     # membership_level 缩写，减小 token 体积
        "type": "access",
        "iat": now,
        "exp": now + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    验证并解码 Access Token，返回 payload。
    过期抛 TokenExpiredError，其他无效情况抛 AuthError。
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise AuthError("无效的 token 类型")
        return payload
    except ExpiredSignatureError:
        raise TokenExpiredError()
    except JWTError:
        raise AuthError("无效的访问凭证")


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """
    生成 Refresh Token（长效，30 天）
    返回 (token_plain, token_hash)
    - token_plain：返回给客户端，存 HttpOnly Cookie
    - token_hash：SHA-256 哈希，存数据库（防数据库泄露）
    """
    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash


def hash_token(token: str) -> str:
    """对 token 做 SHA-256 哈希（用于数据库查询比对）"""
    return hashlib.sha256(token.encode()).hexdigest()
