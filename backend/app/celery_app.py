from __future__ import annotations

import platform

from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "backtest_engine",
    broker=settings.celery_broker_url,
    backend=settings.celery_backend_url,
)

# Base configuration
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=120,  # Default 2 min for regular backtests
    task_soft_time_limit=110,  # Soft limit for graceful shutdown
    broker_connection_retry_on_startup=True,
    include=["app.tasks.backtest_task", "app.tasks.robustness_task"],
)

# macOS: use 'threads' pool to avoid fork issues with numpy/pandas
# while still allowing concurrent task execution (unlike 'solo')
if platform.system() == "Darwin":
    celery_app.conf.update(
        worker_pool="threads",
        worker_concurrency=4,
    )

celery_app.autodiscover_tasks(["app.tasks"])
