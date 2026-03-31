"""
模型路由器
根据工具 slug 和用户会员等级选择最合适的 AI 模型
"""

from __future__ import annotations

from app.utils.exceptions import NotFoundError

# ── 工具 → 模型映射表 ─────────────────────────────────────
# 此配置在增长阶段迁移到 tools.model_config 数据库字段，由运营自由调整
TOOL_MODEL_MAP: dict[str, dict] = {
    "character-art": {
        "default":      {"provider": "tongyi",    "model": "wanx-v1"},
        "membership_2": {"provider": "openai",    "model": "dall-e-3"},
        "fallback":     ["tongyi/wanx-v1", "stability/stable-diffusion-xl"],
    },
    "environment-art": {
        "default":      {"provider": "tongyi",    "model": "wanx-v1"},
        "membership_2": {"provider": "openai",    "model": "dall-e-3"},
        "fallback":     ["tongyi/wanx-v1"],
    },
    "sprite-sheet": {
        "default":      {"provider": "stability", "model": "stable-diffusion-xl"},
        "fallback":     ["tongyi/wanx-v1"],
    },
    "motion-preview": {
        "default":      {"provider": "tongyi",    "model": "wanx-video-v1"},
        "fallback":     [],  # 视频暂无降级，直接 fail
    },
    "texture-generator": {
        "default":      {"provider": "stability", "model": "stable-diffusion-xl"},
        "fallback":     ["tongyi/wanx-v1"],
    },
    "ai-retouch": {
        "default":      {"provider": "stability", "model": "stable-diffusion-inpainting"},
        "fallback":     [],  # inpainting 暂无降级
    },
}


def select_model(tool_slug: str, membership_level: int) -> dict[str, str]:
    """
    根据工具 slug 和会员等级选择模型配置。
    返回 {"provider": "...", "model": "..."}

    会员等级优先：membership_2（Pro）> membership_1（Basic）> default（Free）
    """
    config = TOOL_MODEL_MAP.get(tool_slug)
    if config is None:
        raise NotFoundError(f"工具 {tool_slug} 不存在或已下线")

    # 从高到低尝试匹配会员等级
    for level in range(membership_level, -1, -1):
        level_key = f"membership_{level}"
        if level_key in config:
            return config[level_key]

    return config["default"]


def get_fallback_models(tool_slug: str) -> list[str]:
    """获取工具的降级模型列表"""
    config = TOOL_MODEL_MAP.get(tool_slug, {})
    return config.get("fallback", [])


def parse_dimensions(aspect_ratio: str) -> tuple[int, int]:
    """
    将宽高比字符串转换为像素尺寸（SDXL 最优分辨率）。
    返回 (width, height)
    """
    ratio_map = {
        "1:1":  (1024, 1024),
        "2:3":  (832,  1216),
        "3:4":  (896,  1152),
        "9:16": (768,  1344),
        "16:9": (1344, 768),
        "21:9": (1536, 640),
    }
    return ratio_map.get(aspect_ratio, (1024, 1024))
