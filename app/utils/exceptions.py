"""
自定义异常体系
与 api/README.md 中的错误码规范对齐
"""

from __future__ import annotations


class AppError(Exception):
    """所有业务异常的基类"""
    http_status: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str = "服务器内部错误"):
        self.message = message
        super().__init__(message)


class AuthError(AppError):
    http_status = 401
    error_code = "UNAUTHORIZED"

    def __init__(self, message: str = "未授权，请先登录"):
        super().__init__(message)


class TokenExpiredError(AuthError):
    error_code = "TOKEN_EXPIRED"

    def __init__(self, message: str = "登录已过期，请重新登录"):
        super().__init__(message)


class PermissionDeniedError(AppError):
    http_status = 403
    error_code = "FORBIDDEN"

    def __init__(self, message: str = "权限不足"):
        super().__init__(message)


class MembershipRequiredError(PermissionDeniedError):
    error_code = "MEMBERSHIP_REQUIRED"

    def __init__(self, min_level: int = 1):
        level_names = {1: "基础会员", 2: "Pro 会员", 3: "企业会员"}
        msg = f"此功能需要{level_names.get(min_level, '会员')}，请升级后使用"
        super().__init__(msg)


class NotFoundError(AppError):
    http_status = 404
    error_code = "NOT_FOUND"

    def __init__(self, message: str = "资源不存在"):
        super().__init__(message)


class ConflictError(AppError):
    http_status = 409
    error_code = "CONFLICT"

    def __init__(self, message: str = "资源冲突"):
        super().__init__(message)


class ValidationError(AppError):
    http_status = 422
    error_code = "VALIDATION_ERROR"

    def __init__(self, message: str = "参数校验失败"):
        super().__init__(message)


class InsufficientCreditsError(AppError):
    http_status = 422
    error_code = "INSUFFICIENT_CREDITS"

    def __init__(self, current: float = 0, required: float = 0):
        msg = f"积分不足，当前余额 {current}，需要 {required}"
        super().__init__(msg)


class ConcurrentModificationError(AppError):
    http_status = 409
    error_code = "CONCURRENT_MODIFICATION"

    def __init__(self, message: str = "数据并发冲突，请重试"):
        super().__init__(message)


class RateLimitError(AppError):
    http_status = 429
    error_code = "RATE_LIMITED"

    def __init__(self, message: str = "请求过于频繁，请稍后再试"):
        super().__init__(message)


class RetryableModelError(AppError):
    """AI 模型可重试错误（Celery 会自动重试）"""
    http_status = 503
    error_code = "MODEL_UNAVAILABLE"

    def __init__(self, message: str = "AI 模型暂时不可用，正在重试"):
        super().__init__(message)


class NonRetryableModelError(AppError):
    """AI 模型不可重试错误（直接标记失败并退还积分）"""
    http_status = 422
    error_code = "MODEL_REJECTED"

    def __init__(self, message: str = "生成请求被拒绝，请修改描述后重试"):
        super().__init__(message)


class CircuitOpenError(AppError):
    """熔断器开启，拒绝请求"""
    http_status = 503
    error_code = "CIRCUIT_OPEN"

    def __init__(self, provider: str = ""):
        msg = f"模型 {provider} 暂时不可用，请稍后再试" if provider else "AI 服务暂时不可用"
        super().__init__(msg)


class PaymentError(AppError):
    http_status = 400
    error_code = "PAYMENT_ERROR"

    def __init__(self, message: str = "支付处理失败"):
        super().__init__(message)


class StorageError(AppError):
    http_status = 500
    error_code = "STORAGE_ERROR"

    def __init__(self, message: str = "文件存储失败"):
        super().__init__(message)
