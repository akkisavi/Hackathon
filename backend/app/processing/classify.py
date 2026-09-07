"""Thermal-source classification (Phase 2a + 2b).

Stage 1 — an explainable rule engine encoding the diurnal / persistence /
FRP-stability / footprint logic from Plan.md. Every prediction carries a
plain-language rationale, which matters more than raw accuracy for a
government panel.

Stage 3 — an Isolation Forest over the behavioural feature space. A
source that is persistent, stable, and behaves like a facility
(`gas_flare` / `mining` / `steel_smelter` / ...) but sits far from every
mapped facility *and* every catalogued flare is flagged
`is_unregistered` — the enforcement signal the PS is really asking for.

Stage 2 (LightGBM on weak labels) trains in `ml/scripts/train_classifier.py`
and, when `ml/models/classifier.pkl` exists, refines Stage 1. It is on the
cut list — the rule engine stands alone.

Pure functions here; `app/processing/pipeline.py` does the DB I/O.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

_MODEL_PATH = Path(__file__).resolve().parents[3] / "ml" / "models" / "classifier.pkl"

CLASSES = (
    "industrial_fire", "gas_flare", "steel_smelter", "brick_kiln",
    "agricultural_burning", "mining", "wildfire",
)
# classes that imply a physical facility should exist on record
_FACILITY_CLASSES = {"gas_flare", "mining", "steel_smelter", "brick_kiln", "industrial_fire"}

_ANOMALY_COLS = [
    "persistence", "frp_cv", "span_days", "day_night_ratio",
    "bbox_area_km2", "detection_count", "frp_mean", "frp_trend",
]


def _near(dist, metres) -> bool:
    return dist is not None and not pd.isna(dist) and float(dist) <= metres


def _lc(f: dict, *classes: str) -> bool:
    return f.get("land_cover") in classes


def _score_gas_flare(f: dict) -> tuple[float, list[str]]:
    s, why = 0.0, []
    if 0.35 <= f["day_night_ratio"] <= 0.65:
        s += 2; why.append("≈50/50 day–night detection mix")
    if f["frp_cv"] < 0.45:
        s += 1; why.append("stable FRP")
    if f["frp_cv"] < 0.25:
        s += 1; why.append("very low FRP variance")
    if f["span_days"] >= 10 or f["recurrence_days"] >= 5:
        s += 1; why.append("persistent")
    if f["span_days"] >= 30 or f["recurrence_days"] >= 12:
        s += 1; why.append("burns for months at one point")
    if f["bbox_area_km2"] < 1.0:
        s += 1; why.append("tiny fixed footprint")
    if _near(f.get("dist_to_known_flare_m"), 1500):
        s += 3; why.append("matches a catalogued VIIRS nightfire flare")
    if _near(f.get("dist_to_power_plant_m"), 3000) or _near(f.get("dist_to_industrial_m"), 3000):
        s += 1; why.append("close to a refinery / industrial site")
    if _lc(f, "built_up", "bare"):
        s += 1; why.append("on built-up / bare land")
    return s / 9.0, why


def _score_mining(f: dict) -> tuple[float, list[str]]:
    s, why = 0.0, []
    if 0.30 <= f["day_night_ratio"] <= 0.70:
        s += 2; why.append("burns around the clock")
    if f["frp_cv"] < 0.30:
        s += 2; why.append("near-constant FRP")
    if f["span_days"] >= 30 or f["recurrence_days"] >= 12:
        s += 2; why.append("persistent for months")
    if abs(f["bbox_growth_rate"]) < 0.02:
        s += 1; why.append("static footprint")
    if _near(f.get("dist_to_quarry_m"), 3000):
        s += 3; why.append("adjacent to a mapped mine / quarry")
    if _lc(f, "bare"):
        s += 1; why.append("on bare / excavated ground")
    return s / 9.0, why


def _score_steel_smelter(f: dict) -> tuple[float, list[str]]:
    s, why = 0.0, []
    if f["day_night_ratio"] > 0.55:
        s += 1; why.append("daytime-biased")
    if f["span_days"] >= 10 or f["recurrence_days"] >= 5:
        s += 1; why.append("persistent")
    if f["span_days"] >= 30 or f["recurrence_days"] >= 12:
        s += 1; why.append("runs for months")
    if f["frp_mean"] > 15:
        s += 2; why.append("high sustained heat output")
    if f["bbox_area_km2"] < 3.0:
        s += 1; why.append("compact site")
    if _near(f.get("dist_to_works_m"), 3000) or _near(f.get("dist_to_industrial_m"), 2000):
        s += 2; why.append("at a works / heavy-industry site")
    if _lc(f, "built_up"):
        s += 1; why.append("on built-up land")
    return s / 8.0, why


def _score_brick_kiln(f: dict) -> tuple[float, list[str]]:
    s, why = 0.0, []
    if 0.60 <= f["day_night_ratio"] <= 0.85:
        s += 2; why.append("daytime-biased, cyclic")
    if 0.25 <= f["frp_cv"] <= 0.80:
        s += 1; why.append("moderate cyclic FRP")
    if f["span_days"] >= 10 or f["recurrence_days"] >= 5:
        s += 2; why.append("runs for months in season")
    if f["frp_mean"] <= 15:
        s += 1; why.append("modest heat output")
    if 1.0 <= f["bbox_area_km2"] <= 3.0:
        s += 1; why.append("small cluster")
    if _near(f.get("dist_to_industrial_m"), 5000):
        s += 1; why.append("near an industrial area")
    if _lc(f, "cropland", "bare"):
        s += 1; why.append("on cropland-fringe / bare land")
    return s / 8.0, why


def _score_agricultural_burning(f: dict) -> tuple[float, list[str]]:
    s, why = 0.0, []
    if f["day_night_ratio"] > 0.80:
        s += 3; why.append("strongly daytime-only")
    if f["frp_cv"] > 0.60:
        s += 2; why.append("high FRP variance")
    if f["span_days"] < 20 and f["recurrence_days"] < 12:
        s += 2; why.append("short-lived, no long persistence")
    if f["bbox_area_km2"] > 2.0 or f["bbox_growth_rate"] > 0.05:
        s += 2; why.append("scattered / shifting footprint")
    if f["first_seen_month"] in (4, 5, 10, 11):
        s += 2; why.append("in the stubble-burning window")
    if _lc(f, "cropland"):
        s += 3; why.append("on cropland")
    elif _lc(f, "grassland", "shrubland"):
        s += 1; why.append("on grass / shrub land")
    return s / 12.0, why


def _score_wildfire(f: dict) -> tuple[float, list[str]]:
    s, why = 0.0, []
    if f["bbox_area_km2"] > 10.0:
        s += 3; why.append("large footprint")
    if f["bbox_growth_rate"] > 0.30:
        s += 3; why.append("actively spreading")
    if f["span_days"] < 21:
        s += 1; why.append("days-to-weeks lifespan")
    if f["day_night_ratio"] > 0.70 or f["day_night_ratio"] < 0.30:
        s += 1; why.append("irregular day/night pattern")
    if f["frp_max"] > 30 and f["frp_trend"] != 0:
        s += 1; why.append("intense, evolving fire front")
    if _lc(f, "tree_cover", "shrubland"):
        s += 2; why.append("in forest / shrubland")
    return s / 10.0, why


def _score_industrial_fire(f: dict) -> tuple[float, list[str]]:
    transient = f["span_days"] < 4
    spike = f["frp_spike_ratio"] > 2.5
    if not (transient or spike):
        return 0.0, []  # without a transient/spike signal it is not an accident fire
    s, why = 0.0, []
    if transient:
        s += 3; why.append("sudden, lasts hours–days")
    if spike:
        s += 2; why.append("FRP spikes then dies")
    if f["bbox_area_km2"] < 1.0:
        s += 1; why.append("small fixed footprint")
    if _near(f.get("dist_to_industrial_m"), 3000) or _near(f.get("dist_to_works_m"), 3000):
        s += 2; why.append("at an industrial site")
    if _lc(f, "built_up"):
        s += 1; why.append("on built-up land")
    return s / 9.0, why


_SCORERS = {
    "gas_flare": _score_gas_flare,
    "mining": _score_mining,
    "steel_smelter": _score_steel_smelter,
    "brick_kiln": _score_brick_kiln,
    "agricultural_burning": _score_agricultural_burning,
    "wildfire": _score_wildfire,
    "industrial_fire": _score_industrial_fire,
}


# classes that mean "a facility has run here for months" — not callable from
# a source with almost no history (short FIRMS window), unless there is
# external evidence (a flare-catalogue match)
_PERSISTENT_CLASSES = {"mining", "steel_smelter", "brick_kiln", "gas_flare"}


def rule_classify(f: dict) -> dict:
    """Stage-1 prediction for one feature dict."""
    scored = {cls: scorer(f) for cls, scorer in _SCORERS.items()}

    # "persistent" bar used by the scorers: span >= 10 days OR seen on >= 5 days
    thin_history = f["span_days"] < 10 and f["recurrence_days"] < 5
    flare_match = _near(f.get("dist_to_known_flare_m"), 1500)
    if thin_history:
        for cls in _PERSISTENT_CLASSES:
            if cls == "gas_flare" and flare_match:
                continue
            scored[cls] = (0.0, [])

    ratios = {cls: round(r, 3) for cls, (r, _) in scored.items()}
    best_cls = max(ratios, key=ratios.get)
    best_ratio, best_why = scored[best_cls]

    if best_ratio < 0.35 or not best_why:
        return {
            "predicted_class": "unknown", "confidence": 0.3, "method": "rule",
            "rationale": "no rule pattern matched strongly", "scores": ratios,
        }

    confidence = round(min(0.95, 0.35 + 0.60 * best_ratio), 2)
    rationale = "; ".join(best_why)
    if not f.get("has_infra_context"):
        confidence = min(confidence, 0.70)
        rationale += " — note: no infrastructure registry loaded, location context unavailable"

    return {
        "predicted_class": best_cls, "confidence": confidence, "method": "rule",
        "rationale": rationale, "scores": ratios,
    }


@lru_cache(maxsize=1)
def _load_model():
    """The Stage-2 LightGBM bundle, or None if it hasn't been trained."""
    if not _MODEL_PATH.exists():
        return None
    import joblib
    return joblib.load(_MODEL_PATH)


def classify_one(f: dict) -> dict:
    """Full Stage-1 (+ Stage-2 if a model exists) prediction for one source.

    The rule engine always runs — its rationale and per-class scores are
    the explainability layer. When `ml/models/classifier.pkl` is present,
    LightGBM overrides the predicted class and confidence.
    """
    out = rule_classify(f)
    bundle = _load_model()
    if bundle is None:
        return out

    cols = bundle["features"]
    x = np.array([[float(f.get(c) if f.get(c) is not None and not pd.isna(f.get(c))
                          else -1.0) for c in cols]])
    proba = bundle["model"].predict_proba(x)[0]
    idx = int(np.argmax(proba))
    out["predicted_class"] = bundle["classes"][idx]
    out["confidence"] = round(float(proba[idx]), 2)
    out["method"] = "lightgbm"
    out["rationale"] = f"model prediction; rule-engine read: {out['rationale']}"
    return out


def anomaly_scores(frame: pd.DataFrame) -> pd.Series:
    """Isolation-Forest outlier score per source (higher = more unusual).
    Needs a handful of rows; returns zeros otherwise."""
    if len(frame) < 8:
        return pd.Series(0.0, index=frame.index)
    from sklearn.ensemble import IsolationForest

    x = frame[_ANOMALY_COLS].astype(float).fillna(0.0).to_numpy()
    clf = IsolationForest(random_state=0, contamination="auto")
    clf.fit(x)
    raw = -clf.score_samples(x)  # flip so larger = more anomalous
    return pd.Series(np.round(raw, 4), index=frame.index)


def is_unregistered(f: dict, predicted_class: str, anomaly_score: float,
                    anomaly_cut: float) -> tuple[bool, str]:
    """Stage-3 flag: a facility-type source with no facility on record."""
    if not f.get("has_infra_context"):
        return False, "infrastructure registry not loaded — cannot assess"
    if predicted_class not in _FACILITY_CLASSES:
        return False, ""

    long_lived = f["span_days"] >= 30 or f["recurrence_days"] >= 12
    stable = f["frp_cv"] < 0.5
    d_infra = f.get("dist_to_infra_m")
    d_flare = f.get("dist_to_known_flare_m")
    far = d_infra is not None and float(d_infra) > 3000 and (
        d_flare is None or pd.isna(d_flare) or float(d_flare) > 3000
    )
    if long_lived and stable and far and anomaly_score >= anomaly_cut:
        return True, (
            f"persistent, stable {predicted_class.replace('_', ' ')}-type source "
            f"{int(float(d_infra))} m from the nearest mapped facility and absent "
            f"from every flare catalogue"
        )
    return False, ""
