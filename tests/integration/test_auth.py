"""
认证接口集成测试
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """注册成功，返回 Access Token"""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "test@pixelmind.app",
        "password": "Password123!",
        "nickname": "测试用户",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """重复邮箱注册返回 409"""
    payload = {"email": "dup@pixelmind.app", "password": "Password123!"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409
    assert resp.json()["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """密码错误返回 401"""
    await client.post("/api/v1/auth/register", json={
        "email": "login@pixelmind.app",
        "password": "Password123!",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "login@pixelmind.app",
        "password": "WrongPass",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    """健康检查返回 ok"""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
