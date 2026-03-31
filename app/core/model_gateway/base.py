"""
模型网关基础抽象类和公共数据类型
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GenerateRequest:
    """模型调用请求（统一格式）"""
    prompt: str
    width: int = 768
    height: int = 1024
    negative_prompt: Optional[str] = None
    style_preset: Optional[str] = None
    reference_url: Optional[str] = None
    extra_params: dict = field(default_factory=dict)


@dataclass
class GenerateResult:
    """模型调用结果（统一格式）"""
    image_url: str                    # 模型返回的原始图片 URL（临时，需下载后上传 R2）
    width: int = 0
    height: int = 0
    model_provider: str = ""
    model_name: str = ""
    raw_response: dict = field(default_factory=dict)


class BaseModelAdapter(ABC):
    """
    AI 模型适配器基类
    每个第三方模型实现此接口，屏蔽差异，网关层统一调用
    """

    @property
    @abstractmethod
    def provider(self) -> str:
        """模型提供商名称，如 openai / tongyi / stability"""
        ...

    @abstractmethod
    async def generate(self, request: GenerateRequest) -> GenerateResult:
        """
        异步生成图像（供 FastAPI 直接调用，内部实验/调试用）
        Worker 任务使用同步版本 generate_sync
        """
        ...

    @abstractmethod
    def generate_sync(self, request: GenerateRequest) -> GenerateResult:
        """
        同步生成图像（供 Celery Worker 调用）
        """
        ...
