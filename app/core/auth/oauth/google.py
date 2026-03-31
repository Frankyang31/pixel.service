"""
Google OAuth 2.0 封装
使用 Authorization Code Flow（PKCE 可选）
"""

from __future__ import annotations

import uuid

import httpx

from app.config import settings
from app.core.cache.redis_client import get_redis_client
from app.utils.exceptions import AuthError

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
STATE_TTL = 600


async def get_google_oauth_redirect_url() -> tuple[str, str]:
    """
    生成 Google OAuth 授权 URL，在 Redis 保存 state（防 CSRF）。
    返回 (auth_url, state)
    """
    state = str(uuid.uuid4())
    redis = get_redis_client()
    await redis.set(
        f"oauth:state:{state}",
        '{"provider": "google"}',
        ex=STATE_TTL
    )

    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}", state


async def exchange_google_code(code: str, state: str) -> dict:
    """
    用 code 换取 Google 用户信息（sub、email、name、picture）。
    失败抛 AuthError。
    """
    # 验证 state
    redis = get_redis_client()
    state_data = await redis.get(f"oauth:state:{state}")
    if not state_data:
        raise AuthError("无效的 OAuth state，请重新授权")
    await redis.delete(f"oauth:state:{state}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 换 access_token
        token_resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        token_data = token_resp.json()
        if "error" in token_data:
            raise AuthError(f"Google 授权失败：{token_data.get('error_description', '未知错误')}")

        # 获取用户信息
        info_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        )
        user_info = info_resp.json()

    return {
        "sub": user_info.get("sub"),
        "email": user_info.get("email"),
        "email_verified": user_info.get("email_verified", False),
        "nickname": user_info.get("name", "Google 用户"),
        "avatar_url": user_info.get("picture"),
    }
