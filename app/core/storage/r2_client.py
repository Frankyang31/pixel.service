"""
Cloudflare R2 客户端（S3 兼容 API）
"""

from __future__ import annotations

import asyncio
from typing import Optional

import boto3
from botocore.client import Config

from app.config import settings
from app.utils.exceptions import StorageError

_s3_client = None


def _get_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    return _s3_client


async def upload_file(
    local_path: str,
    storage_key: str,
    content_type: str = "image/webp",
) -> str:
    """
    上传本地文件到 R2，返回公共 CDN URL
    使用 run_in_executor 避免阻塞事件循环（boto3 是同步库）
    """
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(
            None,
            lambda: _get_client().upload_file(
                local_path,
                settings.R2_BUCKET_NAME,
                storage_key,
                ExtraArgs={"ContentType": content_type},
            )
        )
    except Exception as e:
        raise StorageError(f"上传文件失败：{e}")

    return f"{settings.R2_PUBLIC_DOMAIN}/{storage_key}"


async def upload_bytes(
    data: bytes,
    storage_key: str,
    content_type: str = "image/webp",
) -> str:
    """上传字节数据到 R2"""
    loop = asyncio.get_event_loop()
    try:
        import io
        await loop.run_in_executor(
            None,
            lambda: _get_client().upload_fileobj(
                io.BytesIO(data),
                settings.R2_BUCKET_NAME,
                storage_key,
                ExtraArgs={"ContentType": content_type},
            )
        )
    except Exception as e:
        raise StorageError(f"上传数据失败：{e}")

    return f"{settings.R2_PUBLIC_DOMAIN}/{storage_key}"


async def generate_presigned_url(
    storage_key: str,
    expires_in: int = 3600,
) -> str:
    """生成预签名下载 URL（私有文件用）"""
    loop = asyncio.get_event_loop()
    try:
        url = await loop.run_in_executor(
            None,
            lambda: _get_client().generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.R2_BUCKET_NAME, "Key": storage_key},
                ExpiresIn=expires_in,
            )
        )
        return url
    except Exception as e:
        raise StorageError(f"生成下载链接失败：{e}")


async def delete_file(storage_key: str) -> None:
    """删除 R2 文件"""
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(
            None,
            lambda: _get_client().delete_object(
                Bucket=settings.R2_BUCKET_NAME,
                Key=storage_key,
            )
        )
    except Exception as e:
        raise StorageError(f"删除文件失败：{e}")
