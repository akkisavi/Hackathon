"""Alert feed: unregistered / newly-appeared thermal sources (Phase 2b/3)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.api.dependencies import get_current_user_or_api_key
from app.processing.alerts import build_alerts
from app.processing.notify import send_alert_now

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/")
def list_alerts(new_within_days: int = Query(3, ge=1, le=30), db: Session = Depends(get_db), current_user: User = Depends(get_current_user_or_api_key)):
    alerts = build_alerts(db, new_within_days)
    return {"count": len(alerts), "alerts": alerts}


@router.post("/{source_id}/notify")
def notify_alert(source_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_or_api_key)):
    """Manual send-now button — emails ALERT_NOTIFY_EMAILS about this one
    source immediately, bypassing the auto-notify dedup window."""
    result = send_alert_now(db, source_id)
    if result.get("reason") == "source not found":
        raise HTTPException(status_code=404, detail="thermal source not found")
    return result
