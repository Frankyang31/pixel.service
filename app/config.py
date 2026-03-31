"""
PixelMind 全局配置
通过 Pydantic Settings 从 .env 文件加载，提供类型安全和默认值。
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── 应用 ────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_NAME: str = "PixelMind"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    PORT: int = 8000

    # ── 安全 ────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 2
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── 数据库 ─────────────────────────────────────────
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # ── Redis ─────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50

    # ── Celery ─────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── CORS ───────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # ── AI 模型 ─────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    DASHSCOPE_API_KEY: str = ""
    STABILITY_API_KEY: str = ""

    # ── Cloudflare R2 ──────────────────────────────────
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "pixelmind-assets"
    R2_PUBLIC_DOMAIN: str = "https://assets.pixelmind.app"

    @property
    def R2_ENDPOINT_URL(self) -> str:
        return f"https://{self.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    # ── 微信支付 ────────────────────────────────────────
    WECHAT_PAY_MCH_ID: str = ""
    WECHAT_PAY_APP_ID: str = ""
    WECHAT_PAY_API_V3_KEY: str = ""
    WECHAT_PAY_PRIVATE_KEY_PATH: str = ""
    WECHAT_PAY_CERT_SERIAL: str = ""

    # ── Stripe ─────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # ── 微信 OAuth ──────────────────────────────────────
    WECHAT_OAUTH_APP_ID: str = ""
    WECHAT_OAUTH_APP_SECRET: str = ""
    WECHAT_OAUTH_REDIRECT_URI: str = ""

    # ── Google OAuth ────────────────────────────────────
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    GOOGLE_OAUTH_REDIRECT_URI: str = ""

    # ── 邮件 ───────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "PixelMind <noreply@pixelmind.app>"

    # ── 腾讯云短信 ──────────────────────────────────────
    TENCENT_SMS_SECRET_ID: str = ""
    TENCENT_SMS_SECRET_KEY: str = ""
    TENCENT_SMS_APP_ID: str = ""
    TENCENT_SMS_SIGN: str = "PixelMind"

    # ── Sentry ─────────────────────────────────────────
    SENTRY_DSN: str = ""

    # ── 日志 ───────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── 业务参数 ────────────────────────────────────────
    # 积分相关
    SIGNUP_BONUS_CREDITS: int = 30          # 注册赠送积分
    DAILY_SIGNIN_CREDITS: int = 3           # 每日签到积分

    # 文件上传限制
    UPLOAD_MAX_SIZE_MB: int = 10
    UPLOAD_ALLOWED_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]

    # Prompt 长度限制
    PROMPT_MAX_LENGTH: int = 2000
    PROMPT_MIN_LENGTH: int = 5

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache()
def get_settings() -> Settings:
    """获取全局配置单例（带缓存，避免重复加载）"""
    return Settings()


settings = get_settings()
