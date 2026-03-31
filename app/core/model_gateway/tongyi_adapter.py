"""
通义万相适配器（图片生成）
使用 DashScope SDK 调用文生图接口
"""

from __future__ import annotations

import time

import dashscope
from dashscope import ImageSynthesis

from app.config import settings
from app.core.model_gateway.base import BaseModelAdapter, GenerateRequest, GenerateResult
from app.utils.exceptions import NonRetryableModelError, RetryableModelError

dashscope.api_key = settings.DASHSCOPE_API_KEY

# 游戏风格预设 → 通义提示词追加
STYLE_PROMPT_MAP = {
    "奇幻RPG":  "fantasy RPG style, highly detailed, epic lighting",
    "二次元":   "anime style, vibrant colors, clean lines, studio quality",
    "像素游戏": "pixel art style, 16-bit retro game aesthetic",
    "写实风格": "photorealistic, cinematic lighting, ultra detailed",
    "赛博朋克": "cyberpunk style, neon lights, dark atmosphere, futuristic",
}


class TongyiAdapter(BaseModelAdapter):
    """通义万相图像生成适配器（wanx-v1）"""

    @property
    def provider(self) -> str:
        return "tongyi"

    def _build_prompt(self, request: GenerateRequest) -> str:
        style_suffix = STYLE_PROMPT_MAP.get(request.style_preset or "", "")
        return f"{request.prompt}, {style_suffix}".strip(", ") if style_suffix else request.prompt

    async def generate(self, request: GenerateRequest) -> GenerateResult:
        """异步生成（实验用，生产任务走 generate_sync）"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate_sync, request)

    def generate_sync(self, request: GenerateRequest) -> GenerateResult:
        """同步生成，供 Celery Worker 调用"""
        prompt = self._build_prompt(request)

        rsp = ImageSynthesis.call(
            model=ImageSynthesis.Models.wanx_v1,
            prompt=prompt,
            negative_prompt=request.negative_prompt,
            n=1,
            size=f"{request.width}*{request.height}",
            style="<auto>" if not request.style_preset else None,
        )

        if rsp.status_code != 200:
            error_code = rsp.code or "unknown"
            if error_code in ("DataInspectionFailed", "ContentFilter"):
                raise NonRetryableModelError(f"Prompt 内容违规：{rsp.message}")
            raise RetryableModelError(f"通义万相调用失败（{error_code}）：{rsp.message}")

        image_url = rsp.output.results[0].url
        return GenerateResult(
            image_url=image_url,
            width=request.width,
            height=request.height,
            model_provider=self.provider,
            model_name="wanx-v1",
        )
