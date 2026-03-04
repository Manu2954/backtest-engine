from __future__ import annotations

from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "backtest_engine",
    broker=settings.celery_broker_url,
    backend=settings.celery_backend_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=120,
    broker_connection_retry_on_startup=True,
    include=["app.tasks.backtest_task"],
)

celery_app.autodiscover_tasks(["app.tasks"])
