from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "firedetect",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.beat_schedule = {
    "ingest-firms-every-6-hours": {
        "task": "app.workers.tasks.ingest_firms",
        "schedule": 6 * 60 * 60,
    },
}
celery_app.conf.timezone = "UTC"
