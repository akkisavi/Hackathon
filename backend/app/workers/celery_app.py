"""Celery app for the scheduled FIRMS ingest.

Broker is Redis via `REDIS_URL`. For Upstash use the TLS scheme, e.g.
`rediss://default:<pw>@<host>.upstash.io:6379?ssl_cert_reqs=required`.

Upstash free tier allows ~10k commands/day, so this is tuned to be quiet:
- no result backend (the scheduled task returns nothing anyone reads)
- 30 s broker polling instead of the ~1 s default
- gossip / mingle / heartbeat are disabled on the worker command line
Run it (Windows needs the solo pool):

    celery -A app.workers.celery_app worker --beat --pool=solo --loglevel=info \\
        --without-gossip --without-mingle --without-heartbeat
"""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery("firedetect", broker=settings.redis_url, include=["app.workers.tasks"])

celery_app.conf.update(
    task_ignore_result=True,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    broker_transport_options={"polling_interval": 30.0, "visibility_timeout": 43200},
    timezone="UTC",
    beat_schedule={
        "ingest-firms-every-6-hours": {
            "task": "app.workers.tasks.ingest_firms",
            "schedule": 6 * 60 * 60,
            "kwargs": {"days": 3},
        },
    },
)
