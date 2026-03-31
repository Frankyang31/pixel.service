"""
认证路由
POST /api/v1/auth/register       邮箱注册
POST /api/v1/auth/login          邮箱登录
POST /api/v1/auth/refresh        刷新 Token
POST /api/v1/auth/logout         登出
GET  /api/v1/auth/oauth/wechat   微信 OAuth 跳转
GET  /api/v1/auth/oauth/wechat/callback  微信回调
GET  /api/v1/auth/oauth/google   Google OAuth 跳转
GET  /api/v1/auth/oauth/google/callback  Google 回调
"""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.oauth.google import exchange_google_code, get_google_oauth_redirect_url
from app.core.auth.oauth.wechat import exchange_wechat_code, get_wechat_oauth_redirect_url
from app.db.database import get_db
from app.schemas.auth import (
    LoginRequest, RegisterRequest, RefreshTokenRequest, TokenResponse,
)
from app.services import auth_service

router = APIRouter(tags=["认证"])

REFRESH_TOKEN_COOKIE = "refresh_token"
COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 天


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=COOKIE_MAX_AGE,
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    request: Request,
    response: Response,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """邮箱注册，返回 Access Token；Refresh Token 写 HttpOnly Cookie"""
    ip = request.client.host if request.client else None
    tokens = await auth_service.register_with_email(db, body, ip=ip)
    _set_refresh_cookie(response, tokens.refresh_token)
    tokens.refresh_token = ""  # 不在 body 中返回 Refresh Token
    return tokens


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """邮箱登录"""
    ip = request.client.host if request.client else None
    tokens = await auth_service.login_with_email(db, body, ip=ip)
    _set_refresh_cookie(response, tokens.refresh_token)
    tokens.refresh_token = ""
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token_cookie: str | None = Cookie(default=None, alias=REFRESH_TOKEN_COOKIE),
):
    """用 Cookie 中的 Refresh Token 换新 Access Token"""
    if not refresh_token_cookie:
        from app.utils.exceptions import AuthError
        raise AuthError("未找到刷新令牌，请重新登录")

    ip = request.client.host if request.client else None
    tokens = await auth_service.refresh_access_token(db, refresh_token_cookie, ip=ip)
    return tokens


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token_cookie: str | None = Cookie(default=None, alias=REFRESH_TOKEN_COOKIE),
):
    """登出：吊销 Refresh Token，清除 Cookie"""
    if refresh_token_cookie:
        await auth_service.logout(db, refresh_token_cookie)
    response.delete_cookie(REFRESH_TOKEN_COOKIE)


# ── 微信 OAuth ────────────────────────────────────────────

@router.get("/oauth/wechat")
async def wechat_oauth_redirect():
    """生成微信 OAuth 授权 URL 并跳转"""
    auth_url, _ = await get_wechat_oauth_redirect_url()
    return RedirectResponse(url=auth_url)


@router.get("/oauth/wechat/callback", response_model=TokenResponse)
async def wechat_oauth_callback(
    code: str,
    state: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """微信 OAuth 回调"""
    user_info = await exchange_wechat_code(code, state)
    ip = request.client.host if request.client else None
    tokens = await auth_service.login_or_register_with_wechat(
        db=db,
        openid=user_info["openid"],
        unionid=user_info.get("unionid"),
        nickname=user_info["nickname"],
        avatar_url=user_info.get("avatar_url"),
        ip=ip,
    )
    _set_refresh_cookie(response, tokens.refresh_token)
    tokens.refresh_token = ""
    return tokens


# ── Google OAuth ──────────────────────────────────────────

@router.get("/oauth/google")
async def google_oauth_redirect():
    """生成 Google OAuth 授权 URL 并跳转"""
    auth_url, _ = await get_google_oauth_redirect_url()
    return RedirectResponse(url=auth_url)


@router.get("/oauth/google/callback", response_model=TokenResponse)
async def google_oauth_callback(
    code: str,
    state: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Google OAuth 回调"""
    user_info = await exchange_google_code(code, state)
    ip = request.client.host if request.client else None
    tokens = await auth_service.login_or_register_with_google(
        db=db,
        google_sub=user_info["sub"],
        email=user_info.get("email"),
        nickname=user_info["nickname"],
        avatar_url=user_info.get("avatar_url"),
        ip=ip,
    )
    _set_refresh_cookie(response, tokens.refresh_token)
    tokens.refresh_token = ""
    return tokens
