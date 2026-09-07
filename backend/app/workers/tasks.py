from app.core.db import SessionLocal
from app.processing.pipeline import run_ingest_and_cluster
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.ingest_firms")
def ingest_firms(days: int = 3):
    """Every 6 h: pull FIRMS, persist detections, rebuild thermal sources."""
    db = SessionLocal()
    try:
        return run_ingest_and_cluster(db, days=days)
    finally:
        db.close()
