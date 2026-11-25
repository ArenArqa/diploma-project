from celery import Celery

from app.core.config import get_settings

celery_app = Celery(
    "marketplace", broker=get_settings().celery_broker_url, include=["app.tasks.market_statistics"]
)
celery_app.conf.update(
    timezone="UTC",
    task_serializer="json",
    accept_content=["json"],
    task_ignore_result=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "market-every-five-minutes": {
            "task": "marketplace.recalculate_market",
            "schedule": 300.0,
        }
    },
)
