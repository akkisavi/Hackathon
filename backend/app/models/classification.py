"""Predicted class + explainability for a ThermalSource (Phase 2).

Table only for now. Written by app/processing/classify.py once the
feature pipeline and rule engine / LightGBM land.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Classification(Base):
    __tablename__ = "classification"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thermal_source_id: Mapped[int] = mapped_column(
        ForeignKey("thermal_source.id", ondelete="CASCADE"), index=True, nullable=False
    )

    predicted_class: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)  # rule | lightgbm
    features: Mapped[dict] = mapped_column(JSON, nullable=False)     # feature vector + per-class scores
    rationale: Mapped[str | None] = mapped_column(String, nullable=True)  # human-readable "why"

    anomaly_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # the differentiator: persistent, stable, no infrastructure on record
    is_unregistered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unregistered_reason: Mapped[str | None] = mapped_column(String, nullable=True)

    # LLM incident narrative, generated lazily and cached (Phase 2c)
    narrative: Mapped[str | None] = mapped_column(String, nullable=True)

    # Emissions/economic impact (gas_flare only) — FRP calibrated against the
    # EOG flare survey's own published volumes. See app/processing/emissions.py
    estimated_bcm_per_year: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_co2_tons_per_year: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_value_inr: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
