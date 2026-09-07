"""Stage-2 classifier: LightGBM multiclass on weak labels (Plan.md 2a).

Weak supervision — there is no hand-labelled truth set, so labels come from:

  * EOG/VIIRS flare catalogue proximity  -> gas_flare        (high trust)
  * OSM quarry / works / industrial proximity -> mining / steel_smelter
  * the Stage-1 rule engine               -> everything else  (noisy)

The model then generalises those signals to sources with no nearby
reference. It is on the cut list: if this underperforms, the pipeline
falls back to the rule engine (which is what runs until
`ml/models/classifier.pkl` exists).

    python ml/scripts/train_classifier.py

Reads features straight from the database via the backend package, so the
pipeline must have populated `thermal_source` first.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.db import SessionLocal            # noqa: E402
from app.processing.classify import rule_classify  # noqa: E402
from app.processing.features import build_feature_frame  # noqa: E402

MODEL_PATH = ROOT / "ml" / "models" / "classifier.pkl"
FEATURE_COLS = [
    "span_days", "detection_count", "recurrence_days", "frp_mean", "frp_std",
    "frp_max", "frp_trend", "frp_cv", "frp_spike_ratio", "day_night_ratio",
    "persistence", "bbox_area_km2", "bbox_growth_rate", "first_seen_month",
    "dist_to_infra_m", "dist_to_known_flare_m", "land_cover_code",
]


def weak_label(f: dict) -> str:
    d_flare = f.get("dist_to_known_flare_m")
    if d_flare is not None and not pd.isna(d_flare) and d_flare < 500:
        return "gas_flare"
    if _lt(f.get("dist_to_quarry_m"), 1000):
        return "mining"
    if _lt(f.get("dist_to_works_m"), 500):
        return "steel_smelter"
    if f.get("land_cover") == "cropland" and f.get("first_seen_month") in (4, 5, 10, 11) \
            and f.get("day_night_ratio", 0) > 0.8:
        return "agricultural_burning"
    return rule_classify(f)["predicted_class"]


def _lt(v, thr) -> bool:
    return v is not None and not pd.isna(v) and float(v) < thr


def main() -> None:
    import lightgbm as lgb
    from sklearn.metrics import classification_report
    from sklearn.model_selection import train_test_split

    db = SessionLocal()
    try:
        frame = build_feature_frame(db)
    finally:
        db.close()
    if frame.empty:
        sys.exit("no thermal sources — run the pipeline first")

    frame = frame.copy()
    frame["label"] = [weak_label(r._asdict() if hasattr(r, "_asdict") else dict(r))
                      for _, r in frame.iterrows()]
    frame = frame[frame["label"] != "unknown"]

    x = frame[FEATURE_COLS].astype(float).fillna(-1.0)
    y = frame["label"].astype("category")
    classes = list(y.cat.categories)

    x_tr, x_te, y_tr, y_te = train_test_split(
        x, y.cat.codes, test_size=0.2, random_state=0, stratify=y.cat.codes
    )
    model = lgb.LGBMClassifier(
        objective="multiclass", n_estimators=400, learning_rate=0.05,
        num_leaves=31, subsample=0.8, colsample_bytree=0.8, random_state=0,
    )
    model.fit(x_tr, y_tr)

    pred = model.predict(x_te)
    print(classification_report(y_te, pred, target_names=classes, zero_division=0))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "classes": classes, "features": FEATURE_COLS}, MODEL_PATH)
    print(f"saved -> {MODEL_PATH}  ({np.bincount(y.cat.codes).tolist()} per class)")


if __name__ == "__main__":
    main()
