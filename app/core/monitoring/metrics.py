"""
Prometheus 指标定义
MVP 阶段关注核心业务指标，增长阶段补充更细粒度
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge

# ── API 请求指标 ─────────────────────────────────────────
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0],
)

# ── AI 任务指标 ──────────────────────────────────────────
generation_jobs_total = Counter(
    "generation_jobs_total",
    "Total AI generation jobs",
    ["tool_slug", "status"],  # status: submitted | done | failed | cancelled
)

generation_job_duration_seconds = Histogram(
    "generation_job_duration_seconds",
    "AI generation job duration in seconds",
    ["tool_slug", "model_provider"],
    buckets=[1, 5, 10, 30, 60, 120, 300],
)

# ── 积分指标 ─────────────────────────────────────────────
credits_consumed_total = Counter(
    "credits_consumed_total",
    "Total credits consumed",
    ["tool_slug"],
)

# ── 模型网关指标 ─────────────────────────────────────────
model_calls_total = Counter(
    "model_calls_total",
    "Total AI model API calls",
    ["provider", "model", "status"],  # status: success | error | circuit_open
)

model_call_duration_seconds = Histogram(
    "model_call_duration_seconds",
    "AI model API call duration in seconds",
    ["provider", "model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

# ── 队列深度（每 scrape 实时读取）───────────────────────
queue_depth = Gauge(
    "celery_queue_depth",
    "Number of tasks waiting in Celery queue",
    ["queue_name"],
)

# ── 用户指标 ─────────────────────────────────────────────
user_registrations_total = Counter(
    "user_registrations_total",
    "Total user registrations",
    ["method"],  # email | wechat | google
)
