"""On-demand pipeline trigger. Same work as the 6-hourly Celery task, run
synchronously — handy in dev and to prime the demo DB."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.processing.pipeline import run_ingest_and_cluster

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/")
def trigger_ingest(days: int = Query(3, ge=1, le=10), db: Session = Depends(get_db)):
    return run_ingest_and_cluster(db, days=days)
