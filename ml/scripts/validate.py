"""Validate the classifier against independent reference data.

There is no hand-labelled truth set. Instead we derive high-confidence
reference labels for the *labelable subset* of thermal sources from data
the model does not get to see as a hard label:

  * within 700 m of an EOG flare seen in >= 3 survey years  -> gas_flare
  * within 600 m of a mapped OSM quarry                      -> mining
  * within 400 m of a mapped OSM works                       -> steel_smelter
  * > 25 km from ANY mapped facility, strongly day-biased,
    high FRP variance, short span, on cropland-scale footprint -> agricultural_burning

Then we score the current `classification` rows against those labels and
write a confusion matrix + accuracy. Everything outside the labelable
subset is reported as "unlabelled" — we do not guess.

    python ml/scripts/validate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.db import engine  # noqa: E402

REPORT = ROOT / "ml" / "validation_report.md"

# nearest-feature via the GiST KNN operator (<->), geography distance only on
# the one winning row — the correlated-min form defeats the spatial index and
# times out on Supabase.
_SQL = text("""
SELECT ts.id, cl.predicted_class,
       ts.span_days, ts.day_night_ratio, ts.recurrence_days, ts.bbox_area_km2,
       ts.frp_std / NULLIF(ts.frp_mean, 0) AS frp_cv,
       sf.d AS d_strong_flare, qq.d AS d_quarry, wk.d AS d_works, ai.d AS d_any_infra
FROM thermal_source ts
JOIN classification cl ON cl.thermal_source_id = ts.id
LEFT JOIN LATERAL (
  SELECT ST_Distance(f.geom::geography, ts.geom::geography) d
  FROM flare_ref f WHERE f.years_seen >= 3 ORDER BY f.geom <-> ts.geom LIMIT 1
) sf ON true
LEFT JOIN LATERAL (
  SELECT ST_Distance(o.geom::geography, ts.geom::geography) d
  FROM osm_infra o WHERE o.kind = 'quarry' ORDER BY o.geom <-> ts.geom LIMIT 1
) qq ON true
LEFT JOIN LATERAL (
  SELECT ST_Distance(o.geom::geography, ts.geom::geography) d
  FROM osm_infra o WHERE o.kind = 'works' ORDER BY o.geom <-> ts.geom LIMIT 1
) wk ON true
LEFT JOIN LATERAL (
  SELECT ST_Distance(o.geom::geography, ts.geom::geography) d
  FROM osm_infra o ORDER BY o.geom <-> ts.geom LIMIT 1
) ai ON true
""")


def reference_label(r) -> str | None:
    if r.d_strong_flare is not None and r.d_strong_flare < 700:
        return "gas_flare"
    if r.d_quarry is not None and r.d_quarry < 600 and r.recurrence_days >= 5:
        return "mining"
    if r.d_works is not None and r.d_works < 400:
        return "steel_smelter"
    if (r.d_any_infra is not None and r.d_any_infra > 25000
            and r.day_night_ratio > 0.85 and (r.frp_cv or 0) > 0.6
            and r.span_days < 25 and r.bbox_area_km2 and r.bbox_area_km2 > 1.5):
        return "agricultural_burning"
    return None


def main() -> None:
    from sklearn.metrics import classification_report, confusion_matrix

    df = pd.read_sql(_SQL, engine)
    df["ref"] = [reference_label(r) for r in df.itertuples(index=False)]
    labelled = df.dropna(subset=["ref"]).copy()

    labels = sorted(labelled["ref"].unique())
    cm = confusion_matrix(labelled["ref"], labelled["predicted_class"], labels=labels)
    acc = (labelled["ref"] == labelled["predicted_class"]).mean()
    rep = classification_report(labelled["ref"], labelled["predicted_class"],
                                labels=labels, zero_division=0)

    lines = [
        "# Classifier validation - SIH26162", "",
        f"- Thermal sources classified: **{len(df):,}**",
        f"- Labelable against reference data (EOG flare catalogue + OSM registry): "
        f"**{len(labelled):,}** ({len(labelled) / len(df):.0%})",
        f"- Accuracy on the labelable subset: **{acc:.1%}**", "",
        "Reference labels are derived from proximity to independent authoritative",
        "datasets, not hand annotation; classes without a reliable reference signal",
        "(brick_kiln, wildfire, industrial_fire) are excluded from the matrix.", "",
        "## Confusion matrix (rows = reference, cols = predicted)", "",
        "| ref \\ pred | " + " | ".join(labels) + " |",
        "|" + "---|" * (len(labels) + 1),
    ]
    for name, row in zip(labels, cm):
        lines.append(f"| **{name}** | " + " | ".join(str(x) for x in row) + " |")
    lines += ["", "## Per-class precision / recall", "", "```", rep, "```"]

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwritten -> {REPORT}")


if __name__ == "__main__":
    main()
