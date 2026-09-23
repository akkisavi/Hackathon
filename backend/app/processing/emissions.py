"""Estimate flared-gas volume, cost, and CO2 for sources classified as
`gas_flare` — the "how much is being wasted" number for the regulatory-
auditor pitch.

Method: NOAA/World Bank's Global Gas Flaring Tracker calibrates flared
volume against VIIRS Nightfire's radiant-heat product; we don't have
Nightfire's radiant-heat pipeline, so instead we self-calibrate a simple
FRP -> volume regression against the EOG global flare survey's own
published volumes (`flare_ref.flr_volume_bcm`) for the flares closest to
each of our own sources. Same idea, our own ground truth.

Kept deliberately narrow: applied only to `gas_flare` predictions, because
that's the class the calibration data (all gas flares) actually covers.
"""
from __future__ import annotations

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

# Assumptions — documented, not hidden. Override via env/config if you have
# better local figures for the pitch.
GAS_PRICE_INR_PER_M3 = 8.0       # order-of-magnitude India domestic gas price
CO2_KG_PER_M3_FLARED = 2.75      # IPCC / World Bank GGFR default flaring factor
_MATCH_RADIUS_M = 2000
_MIN_CALIBRATION_PAIRS = 10


def fit_frp_to_volume(db: Session) -> tuple[float, float] | None:
    """(slope, intercept) for flr_volume_bcm ~ frp_mean, fit on flares
    matched to a nearby thermal_source. None if too little ground truth."""
    rows = db.execute(text("""
        SELECT fr.flr_volume_bcm AS bcm, near.frp_mean AS frp_mean
        FROM flare_ref fr
        JOIN LATERAL (
            SELECT ts.frp_mean, ST_Distance(ts.geom::geography, fr.geom::geography) AS d
            FROM thermal_source ts
            ORDER BY ts.geom <-> fr.geom LIMIT 1
        ) near ON near.d < :radius
        WHERE fr.flr_volume_bcm IS NOT NULL
    """), {"radius": _MATCH_RADIUS_M}).all()

    if len(rows) < _MIN_CALIBRATION_PAIRS:
        return None
    x = np.array([r.frp_mean for r in rows], dtype=float)
    y = np.array([r.bcm for r in rows], dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    return float(slope), float(intercept)


def estimate_flare_impact(frp_mean: float, calibration: tuple[float, float]) -> dict:
    """BCM/year, tons CO2/year, and INR/year for one gas_flare source."""
    slope, intercept = calibration
    bcm_per_year = max(0.0, slope * frp_mean + intercept)
    m3_per_year = bcm_per_year * 1e9
    return {
        "estimated_bcm_per_year": round(bcm_per_year, 4),
        "estimated_co2_tons_per_year": round(m3_per_year * CO2_KG_PER_M3_FLARED / 1000, 1),
        "estimated_value_inr": round(m3_per_year * GAS_PRICE_INR_PER_M3, 0),
    }
