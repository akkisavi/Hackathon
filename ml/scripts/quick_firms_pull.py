"""M1's Day-1 sanity check — no backend/docker needed.

    export FIRMS_MAP_KEY=your_key_here   # or put it in a .env at repo root
    python ml/scripts/quick_firms_pull.py

Confirms: live FIRMS CSV -> pandas DataFrame (Phase 0 acceptance).
Reuses the same client the backend/Celery task will call in Phase 1, so
there's exactly one place that knows the FIRMS URL shape.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.ingestion.firms_client import fetch_firms_detections  # noqa: E402

if __name__ == "__main__":
    key = os.environ.get("FIRMS_MAP_KEY")
    df = fetch_firms_detections(days=3, map_key=key)
    print(f"Rows: {len(df)}  Columns: {list(df.columns)}")
    print(df.head())
    print(f"\nBrightness range: {df['bright_ti4'].min() if 'bright_ti4' in df else 'n/a'}"
          f" - {df['bright_ti4'].max() if 'bright_ti4' in df else 'n/a'}")
