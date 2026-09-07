"""Raw FIRMS thermal-anomaly pixel. One row per satellite detection.

`latitude`/`longitude` are kept as plain columns (FIRMS gives them to us
directly and every serializer wants them) alongside the PostGIS `geom`
point, which exists for spatial joins against OSM infrastructure in
Phase 2.
"""
from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Detection(Base):
    __tablename__ = "detection"
    __table_args__ = (
        # One physical satellite observation = one row. FIRMS can hand us the
        # same pixel twice across overlapping pulls; this makes the upsert a
        # no-op on re-ingest.
        UniqueConstraint(
            "latitude", "longitude", "acquired_at", "satellite",
            name="uq_detection_observation",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    geom: Mapped[object] = mapped_column(Geometry("POINT", srid=4326), nullable=False)

    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    daynight: Mapped[str] = mapped_column(String(1), nullable=False)  # "D" | "N"

    brightness: Mapped[float] = mapped_column(Float, nullable=False)   # brightness temp, Kelvin
    frp: Mapped[float] = mapped_column(Float, nullable=False)          # Fire Radiative Power, MW
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    satellite: Mapped[str] = mapped_column(String(16), nullable=False)
    instrument: Mapped[str] = mapped_column(String(16), nullable=False)

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
