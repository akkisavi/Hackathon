"""Catalogued gas flares from the EOG / VIIRS Nightfire global flare survey.

Reference data (2012–2019), loaded once by `app/ingestion/flare_catalog.py`.
Used two ways: a proximity feature ("is this hotspot a known flare?") and
weak labels for the LightGBM classifier. A location that appears in
multiple survey years is a very high-confidence flare.
"""
from __future__ import annotations

from geoalchemy2 import Geometry
from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class FlareRef(Base):
    __tablename__ = "flare_ref"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    geom: Mapped[object] = mapped_column(Geometry("POINT", srid=4326), nullable=False)

    flare_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # upstream/downstream
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_year: Mapped[int] = mapped_column(Integer, nullable=False)
    last_year: Mapped[int] = mapped_column(Integer, nullable=False)
    years_seen: Mapped[int] = mapped_column(Integer, nullable=False)
