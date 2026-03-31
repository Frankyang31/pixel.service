"""
OpenAI DALL-E 3 适配器（Pro 会员专属）
"""

from __future__ import annotations

from openai import OpenAI

from app.config import settings
from app.core.model_gateway.base import BaseModelAdapter, GenerateRequest, GenerateResult
from app.utils.exceptions import NonRetryableModelError, RetryableModelError

_client = OpenAI(api_key=settings.OPENAI_API_KEY)


class OpenAIAdapter(BaseModelAdapter):
    """OpenAI DALL-E 3 适配器，Pro 会员专属"""

    @property
    def provider(self) -> str:
        return "openai"

    def _get_dalle_size(self, width: int, height: int) -> str:
        """DALL-E 3 只支持 1024x1024、1024x1792、1792x1024"""
        if width == height:
            return "1024x1024"
        elif height > width:
            return "1024x1792"
        else:
            return "1792x1024"

    async def generate(self, request: GenerateRequest) -> GenerateResult:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate_sync, request)

    def generate_sync(self, request: GenerateRequest) -> GenerateResult:
        size = self._get_dalle_size(request.width, request.height)

        try:
            response = _client.images.generate(
                model="dall-e-3",
                prompt=request.prompt,
                size=size,  # type: ignore
                quality="hd",
                n=1,
            )
        except Exception as e:
            err_str = str(e).lower()
            if "content_policy_violation" in err_str or "safety" in err_str:
                raise NonRetryableModelError(f"Prompt 内容被 OpenAI 拒绝：{e}")
            raise RetryableModelError(f"DALL-E 3 调用失败：{e}")

        image_url = response.data[0].url
        if not image_url:
            raise RetryableModelError("DALL-E 3 未返回图片 URL")

        return GenerateResult(
            image_url=image_url,
            width=request.width,
            height=request.height,
            model_provider=self.provider,
            model_name="dall-e-3",
        )
