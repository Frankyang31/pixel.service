"""
Celery Worker 启动入口
独立进程运行，不依赖 FastAPI 上下文
"""

from app.core.task_queue.celery_app import celery_app  # noqa: F401

# 启动命令：
# 图像队列 Worker：
#   celery -A worker.main worker -Q image -c 4 --loglevel=info
# 视频队列 Worker（单并发，GPU 资源密集）：
#   celery -A worker.main worker -Q video -c 1 --loglevel=info
# 定时任务 Beat：
#   celery -A worker.main beat --loglevel=info
