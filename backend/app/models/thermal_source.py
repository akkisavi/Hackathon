"""The clustered, persistent entity the whole system reasons about.

A ThermalSource is *derived* data: `app/processing/clustering.py` groups
`Detection` rows by location (DBSCAN, ~1 km) and every pipeline run rebuilds
this table from the current detection window. The lifecycle + behaviour
columns below are exactly the discriminating features from Plan.md
(day/night mix, persistence, FRP stability, footprint growth).
"""
from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ThermalSource(Base):
    __tablename__ = "thermal_source"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    centroid_lat: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_lon: Mapped[float] = mapped_column(Float, nullable=False)
    geom: Mapped[object] = mapped_column(Geometry("POINT", srid=4326), nullable=False)

    # lifecycle
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    span_days: Mapped[float] = mapped_column(Float, nullable=False)
    detection_count: Mapped[int] = mapped_column(Integer, nullable=False)
    recurrence_days: Mapped[int] = mapped_column(Integer, nullable=False)  # distinct UTC dates seen

    # intensity / stability
    frp_mean: Mapped[float] = mapped_column(Float, nullable=False)
    frp_std: Mapped[float] = mapped_column(Float, nullable=False)
    frp_max: Mapped[float] = mapped_column(Float, nullable=False)
    frp_trend: Mapped[float] = mapped_column(Float, nullable=False)  # linear slope, MW/day

    # diurnal signature
    day_count: Mapped[int] = mapped_column(Integer, nullable=False)
    night_count: Mapped[int] = mapped_column(Integer, nullable=False)
    day_night_ratio: Mapped[float] = mapped_column(Float, nullable=False)  # day / (day + night)

    # footprint
    bbox_area_km2: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_growth_rate: Mapped[float] = mapped_column(Float, nullable=False)  # km²/day

    # ESA WorldCover class at the centroid (app/ingestion/landcover.py), nullable
    land_cover: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Sentinel-2 burn-scar check for wildfire candidates (app/ingestion/sentinel.py)
    dnbr: Mapped[float | None] = mapped_column(Float, nullable=True)
    burn_scar: Mapped[str | None] = mapped_column(String(16), nullable=True)  # confirmed|low|none

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
