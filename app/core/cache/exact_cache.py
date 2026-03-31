"""
Prompt 精确缓存
相同 prompt + 参数命中缓存时，直接复用已生成的资产 URL，跳过 AI 调用和积分扣减
"""

from __future__ import annotations

import hashlib
import json

from redis.asyncio import Redis

CACHE_TTL_SECONDS = 86400  # 24 小时


def _build_cache_key(
    tool_slug: str,
    prompt: str,
    negative_prompt: str | None,
    aspect_ratio: str,
    style_preset: str | None,
    model_provider: str,
    model_name: str,
) -> str:
    """
    生成精确缓存 key：对所有影响输出的参数做 SHA-256，避免 key 过长。
    """
    payload = {
        "tool": tool_slug,
        "prompt": prompt,
        "neg": negative_prompt or "",
        "ratio": aspect_ratio,
        "style": style_preset or "",
        "provider": model_provider,
        "model": model_name,
    }
    payload_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    sha = hashlib.sha256(payload_str.encode()).hexdigest()
    return f"cache:exact:{sha}"


async def get_cached_result(
    redis: Redis,
    tool_slug: str,
    prompt: str,
    negative_prompt: str | None,
    aspect_ratio: str,
    style_preset: str | None,
    model_provider: str,
    model_name: str,
) -> str | None:
    """
    查询缓存。命中返回 CDN URL，未命中返回 None。
    """
    key = _build_cache_key(
        tool_slug, prompt, negative_prompt, aspect_ratio, style_preset,
        model_provider, model_name
    )
    return await redis.get(key)


async def set_cached_result(
    redis: Redis,
    cdn_url: str,
    tool_slug: str,
    prompt: str,
    negative_prompt: str | None,
    aspect_ratio: str,
    style_preset: str | None,
    model_provider: str,
    model_name: str,
) -> None:
    """缓存生成结果 URL"""
    key = _build_cache_key(
        tool_slug, prompt, negative_prompt, aspect_ratio, style_preset,
        model_provider, model_name
    )
    await redis.set(key, cdn_url, ex=CACHE_TTL_SECONDS)
