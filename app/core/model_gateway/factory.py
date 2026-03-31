"""
模型适配器工厂
根据 provider 和 model 返回对应适配器实例（单例模式）
"""

from __future__ import annotations

from app.core.model_gateway.base import BaseModelAdapter
from app.utils.exceptions import NotFoundError

_adapters: dict[str, BaseModelAdapter] = {}


def get_adapter(provider: str, model: str) -> BaseModelAdapter:
    """
    获取模型适配器（懒加载 + 单例）
    不同 provider 返回对应适配器实例
    """
    cache_key = f"{provider}/{model}"
    if cache_key in _adapters:
        return _adapters[cache_key]

    adapter: BaseModelAdapter

    if provider == "openai":
        from app.core.model_gateway.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter()

    elif provider == "tongyi":
        from app.core.model_gateway.tongyi_adapter import TongyiAdapter
        adapter = TongyiAdapter()

    elif provider == "stability":
        from app.core.model_gateway.stability_adapter import StabilityAdapter
        adapter = StabilityAdapter(model=model)

    else:
        raise NotFoundError(f"未知模型提供商：{provider}")

    _adapters[cache_key] = adapter
    return adapter
