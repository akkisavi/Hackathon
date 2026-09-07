"""Industrial / power / mining infrastructure from OpenStreetMap.

Populated by `app/ingestion/osm_loader.py` from a Geofabrik extract, and
consumed by `app/processing/features.py` for proximity features in Phase 2.
"""
from __future__ import annotations

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class OsmInfra(Base):
    __tablename__ = "osm_infra"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    osm_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # industrial|quarry|power_plant|works
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    geom: Mapped[object] = mapped_column(Geometry("GEOMETRY", srid=4326), nullable=False)
