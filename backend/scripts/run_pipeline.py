"""One-shot pipeline run: FIRMS -> detections -> cluster -> classify.

The zero-infrastructure way to keep data fresh — no Redis, no Celery.
Point cron / Windows Task Scheduler at it, or loop it:

    # every 6 hours via cron
    0 */6 * * *  cd /path/backend && python scripts/run_pipeline.py

    # or a plain loop
    while true; do python scripts/run_pipeline.py; sleep 21600; done

For the Celery equivalent (needs a Redis broker) see app/workers/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import SessionLocal  # noqa: E402
from app.processing.pipeline import run_ingest_and_cluster  # noqa: E402

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 3

if __name__ == "__main__":
    db = SessionLocal()
    try:
        result = run_ingest_and_cluster(db, days=DAYS)
        print(f"pipeline ok: {result}")
    finally:
        db.close()
