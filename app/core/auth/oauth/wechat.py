"""
微信 OAuth 2.0 封装
支持网页授权（snsapi_userinfo scope）
"""

from __future__ import annotations

import uuid

import httpx

from app.config import settings
from app.core.cache.redis_client import get_redis_client
from app.utils.exceptions import AuthError

WECHAT_OAUTH_STATE_TTL = 600  # OAuth state 有效期 10 分钟
WECHAT_AUTH_URL = "https://open.weixin.qq.com/connect/oauth2/authorize"
WECHAT_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
WECHAT_USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"


async def get_wechat_oauth_redirect_url() -> tuple[str, str]:
    """
    生成微信 OAuth 授权 URL，并在 Redis 保存 state（防 CSRF）。
    返回 (auth_url, state)
    """
    state = str(uuid.uuid4())
    redis = get_redis_client()
    await redis.set(
        f"oauth:state:{state}",
        '{"provider": "wechat"}',
        ex=WECHAT_OAUTH_STATE_TTL
    )

    params = {
        "appid": settings.WECHAT_OAUTH_APP_ID,
        "redirect_uri": settings.WECHAT_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "snsapi_userinfo",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    auth_url = f"{WECHAT_AUTH_URL}?{query}#wechat_redirect"
    return auth_url, state


async def exchange_wechat_code(code: str, state: str) -> dict:
    """
    用 code 换取用户信息（openid、unionid、nickname、avatar）。
    失败抛 AuthError。
    """
    # 1. 验证 state（防 CSRF）
    redis = get_redis_client()
    state_data = await redis.get(f"oauth:state:{state}")
    if not state_data:
        raise AuthError("无效的 OAuth state，请重新授权")
    await redis.delete(f"oauth:state:{state}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 2. 用 code 换 access_token
        token_resp = await client.get(WECHAT_TOKEN_URL, params={
            "appid": settings.WECHAT_OAUTH_APP_ID,
            "secret": settings.WECHAT_OAUTH_APP_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        })
        token_data = token_resp.json()
        if "errcode" in token_data:
            raise AuthError(f"微信授权失败：{token_data.get('errmsg', '未知错误')}")

        access_token = token_data["access_token"]
        openid = token_data["openid"]

        # 3. 获取用户信息
        info_resp = await client.get(WECHAT_USERINFO_URL, params={
            "access_token": access_token,
            "openid": openid,
            "lang": "zh_CN",
        })
        user_info = info_resp.json()
        if "errcode" in user_info:
            raise AuthError(f"获取微信用户信息失败：{user_info.get('errmsg', '未知错误')}")

    return {
        "openid": user_info.get("openid"),
        "unionid": user_info.get("unionid"),
        "nickname": user_info.get("nickname", "微信用户"),
        "avatar_url": user_info.get("headimgurl"),
    }
