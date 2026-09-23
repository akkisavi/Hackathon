from datetime import datetime

from sqlalchemy import Column, DateTime, String

from app.core.db import Base


class NotifiedAlert(Base):
    """Dedup record so the same hotspot doesn't re-notify every pipeline run.
    `thermal_source` is fully rebuilt each run (new ids), so the key is a
    location+first-seen fingerprint instead of a foreign key."""
    __tablename__ = "notified_alerts"

    fingerprint = Column(String, primary_key=True)
    notified_at = Column(DateTime, default=datetime.utcnow, nullable=False)
