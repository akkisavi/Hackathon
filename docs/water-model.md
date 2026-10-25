# ORBIT DELTA — India Water Anomaly Watch

This extends the existing thermal-source platform with a separate, local water model. It measures **open surface-water area in fixed reservoir segments**, detects departures from seasonal patterns, and visualises gained/lost water. It does not estimate storage volume or predict a flood or utility outage.

## Reproduce

From the repository root:

```sh
uv pip install --python .venv/bin/python -r ml/requirements-water.txt
.venv/bin/python ml/scripts/collect_water.py --workers 4
.venv/bin/python ml/scripts/train_water.py
.venv/bin/python run_orbit.py
```

Open `http://127.0.0.1:5173/orbit/water`. Original image inspection and thermal monitoring remain available. The normal server uses the existing authentication dependency; demo access is localhost-only.

Collection can take substantial time. Downloads resume from checksummed local caches in `data/water/<site>/`; source rasters are excluded from Git. `--site hirakud`, `--site nagarjuna-sagar`, `--site sardar-sarovar`, and `--limit 2` support targeted checks. `--cadence-days 3` optionally reduces request count; the default searches all available days. An existing catalogue is cached; remove only `catalog.json` to discover new acquisitions. Run collection and training again to refresh observations. There is no background polling job.

NASA's public service was reachable without a token during development. Availability and quotas may change; archive download paths can require Earthdata Login. Cached observations keep the presentation independent of the upstream service.

## Data and model contract

- Source: NASA OPERA DSWx-HLS `B01_WTR`, April 2023 onward. These are classified satellite observations, not photographic RGB images.
- Preserve acquisition date, source object IDs, tile cloud estimates, checksum, projected bounds, and 30 m pixel spacing.
- Open water = class 1; partial water = class 2, reported separately. Cloud, snow, ocean-mask, and no-data classes are excluded. Only observations with at least 95% valid study-area coverage enter modelling.
- Three fixed study rectangles are versioned in `ml/water/sites.json`. They sample reservoir segments and can include other surface water. They are not complete reservoir boundaries. Training cannot transfer automatically to a new location.
- Native projected 30 m grids support area measurement at 900 m² per pixel. Nearest-neighbour export preserves categories. Change counts use pixels valid at both dates. Visual outlines show up to 40 components per direction of at least 9 pixels; totals include all changed pixels.
- Annual sine/cosine regression provides a per-site seasonal baseline. The fitted residual scale and typical area normalise features for Isolation Forest: seasonal residual, area ratio, elapsed-time-adjusted change, and trailing variability. A gap longer than 60 days suppresses the rate feature. Rolling features use no future observations.
- Train through 2024, select the score threshold on 2025, and report held-out 2026 observations. Minimum: 80 train observations spanning 548 days, 20 validation, and 20 test. Insufficient history suppresses model training; a baseline can remain inspectable when there are at least 20 training observations.
- For a clearly labelled prototype when the 80-date gate is unmet, run `train_water.py --experimental`. This retains the original readiness gate as failed and requires at least 20 training dates over 548 days plus 20 validation and 20 test dates. The UI displays the experimental status. It does not claim event validation.

- The validation score's 95th percentile is a provisional anomaly threshold. Scores are not calibrated probabilities. Historical train/validation scores are retrospective, not operational backtests.

## Evaluation and artifacts

`ml/models/water/evaluation.json` records data sufficiency, exclusions, splits, baseline agreement, test alert frequency, and an explicitly artificial loss-sensitivity probe. **No independent labelled flood or shortage event set is supplied.** Event precision, recall, and warning lead time remain unknown. The artificial probe is not real-world accuracy evidence.

Generated local `.joblib` artifacts include estimator, feature order, seasonal baseline, threshold, scikit-learn version, training timestamp, and manifest hash. JSON observation bundles and evaluation outputs accompany them. Never load untrusted joblib files. Raw data and model binaries remain local; scripts reproduce them.

An anomalous observation can be caused by genuine hydrological change, reservoir operations, extraction, or remaining measurement artefacts. The assessment reports “cause uncertain” and asks for rainfall, gauges, and operating records. No model infers natural versus human cause from water extent alone.

## API

- `GET /api/v1/water/sites`: fixed areas and training readiness.
- `GET /api/v1/water/sites/{id}/observations`: quality-filtered observations, seasonal baseline, scores, source information, and evaluation.
- `GET /api/v1/water/sites/{id}/assessment?date=YYYY-MM-DD`: recomputed saved-model score, comparable gain/loss measurements, geographic polygons, and verification actions. `forecast` is null.
- `GET /api/v1/water/sites/{id}/image?date=YYYY-MM-DD`: cached classified-water PNG. Blue = open water; teal = partial water; tan = non-water; dark = invalid.

Unknown sites/dates return 404; missing datasets/models return 409; malformed dates return 422. An upstream data failure does not silently insert synthetic observations. Esri imagery is contextual and is not labelled as acquisition-date evidence.

## Demo

Select a reservoir. Move the dated timeline or replay observations. Inspect blue gain/orange loss polygons on the map. Switch to before/after and drag the divider. Compare the observed-area curve with its seasonal baseline. Open an anomaly, check its acquisition coverage and held-out/training label, and export the JSON assessment.

## Verification

```sh
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
cd web
npm run build
```

Tests cover no-data exclusion, exact pixel totals, no-future features, chronological training, saved-model score reproduction, insufficient history, geographic polygons, localhost access, and invalid inputs.
