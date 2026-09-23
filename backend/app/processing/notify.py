"""Email a recipient list about new alerts, once per hotspot.

`thermal_source` is fully rebuilt every pipeline run (new ids each time),
so "already notified" is tracked by a location+first-seen fingerprint in
`notified_alerts` rather than by source id.
"""
from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.email import send_alert_notification
from app.models.notified_alert import NotifiedAlert
from app.processing.alerts import build_alerts, get_alert


def _fingerprint(a: dict) -> str:
    return f"{a['lat']:.3f}_{a['lon']:.3f}_{a['first_seen'][:10]}"


def notify_new_alerts(db: Session, new_within_days: int = 3) -> int:
    """Send one email covering every alert not previously notified. Returns
    how many were new. No-op if ALERT_NOTIFY_EMAILS is unset."""
    recipients = [e.strip() for e in get_settings().alert_notify_emails.split(",") if e.strip()]
    if not recipients:
        return 0

    alerts = build_alerts(db, new_within_days)
    if not alerts:
        return 0

    seen = {
        f for f, in db.query(NotifiedAlert.fingerprint)
        .filter(NotifiedAlert.fingerprint.in_({_fingerprint(a) for a in alerts}))
    }
    new_alerts = [a for a in alerts if _fingerprint(a) not in seen]
    if not new_alerts:
        return 0

    send_alert_notification(new_alerts, recipients)

    for a in new_alerts:
        db.execute(
            pg_insert(NotifiedAlert)
            .values(fingerprint=_fingerprint(a))
            .on_conflict_do_nothing()
        )
    db.commit()
    return len(new_alerts)


def send_alert_now(db: Session, source_id: int) -> dict:
    """Manual "send alert" button — sends immediately regardless of dedup
    (that's the point of a manual trigger), then marks it notified so the
    next scheduled run doesn't re-send it. Returns None-ish info for the UI."""
    alert = get_alert(db, source_id)
    if alert is None:
        return {"sent": False, "reason": "source not found"}

    recipients = [e.strip() for e in get_settings().alert_notify_emails.split(",") if e.strip()]
    if not recipients:
        return {"sent": False, "reason": "no ALERT_NOTIFY_EMAILS configured"}

    send_alert_notification([alert], recipients)
    db.execute(
        pg_insert(NotifiedAlert)
        .values(fingerprint=_fingerprint(alert))
        .on_conflict_do_nothing()
    )
    db.commit()
    return {"sent": True, "recipients": recipients}
