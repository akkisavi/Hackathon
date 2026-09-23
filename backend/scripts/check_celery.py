"""Sanity-check the Celery broker (Redis/Upstash) and fire one ingest task.

    python scripts/check_celery.py

Needs REDIS_URL set in .env. A worker must be running for the task to
actually execute; without one this still confirms the broker connection.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.workers.celery_app import celery_app
from app.workers.tasks import ingest_firms

if __name__ == "__main__":
    conn = celery_app.connection()
    try:
        conn.ensure_connection(max_retries=2)
        print(f"broker OK: {conn.as_uri()}")
    except Exception as e:
        sys.exit(f"broker connection FAILED: {e}")

    r = ingest_firms.delay(days=3)
    print(f"enqueued task {r.id} — run a worker to execute it:")
    print("  celery -A app.workers.celery_app worker --beat --pool=solo --loglevel=info "
          "--without-gossip --without-mingle --without-heartbeat")
