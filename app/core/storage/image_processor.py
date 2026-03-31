"""
图片处理工具
下载原始图片 → WebP 压缩 → 生成缩略图
"""

from __future__ import annotations

import os
import tempfile
from typing import Optional

import httpx
from PIL import Image

WEBP_QUALITY = 85       # WebP 压缩质量
THUMB_MAX_SIZE = 512    # 缩略图最大边长（px）
MAX_OUTPUT_SIZE = 4096  # 输出图片最大边长限制


async def process_image(
    source_url: str,
    job_id: str,
) -> tuple[str, str, int, int, int]:
    """
    下载图片并处理为 WebP + 缩略图
    返回 (webp_path, thumb_path, width, height, file_size_bytes)
    """
    # 下载原始图片
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(source_url)
        resp.raise_for_status()
        raw_data = resp.content

    # 写入临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
        tmp.write(raw_data)
        tmp_path = tmp.name

    try:
        webp_path, thumb_path, w, h, size = _process_local(tmp_path, job_id)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return webp_path, thumb_path, w, h, size


def _process_local(
    source_path: str,
    job_id: str,
) -> tuple[str, str, int, int, int]:
    """同步处理本地图片文件"""
    with Image.open(source_path) as img:
        # 转 RGB（去掉 Alpha 通道，WebP 也支持 RGBA 但保持兼容性）
        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # 尺寸上限裁剪
        if max(img.width, img.height) > MAX_OUTPUT_SIZE:
            img.thumbnail((MAX_OUTPUT_SIZE, MAX_OUTPUT_SIZE), Image.LANCZOS)

        width, height = img.size

        # 保存 WebP
        webp_path = source_path.replace(".tmp", f"_{job_id}.webp")
        img.save(webp_path, "WEBP", quality=WEBP_QUALITY, method=6)
        file_size = os.path.getsize(webp_path)

        # 生成缩略图
        thumb_path = source_path.replace(".tmp", f"_{job_id}_thumb.webp")
        thumb_img = img.copy()
        thumb_img.thumbnail((THUMB_MAX_SIZE, THUMB_MAX_SIZE), Image.LANCZOS)
        thumb_img.save(thumb_path, "WEBP", quality=75, method=6)

    return webp_path, thumb_path, width, height, file_size
