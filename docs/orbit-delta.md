# ORBIT DELTA — Track 05

Extends the existing thermal-monitoring project with image-based change inspection and evidence-linked assessments. The original React/MapLibre dashboard, classification pipeline and authenticated APIs remain available.

## Run the self-contained demo

Requires Node 18+ and Python 3.12 (tested). From the repository root:

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r backend/requirements-demo.lock
cd web
npm ci
cd ..
.venv/bin/python run_orbit.py
```

Open **http://127.0.0.1:5173/orbit**. The launcher binds both processes to loopback. PostgreSQL/PostGIS, Redis, Celery, FIRMS and Earth Engine are not imported or contacted in this mode. Font and context-map requests are optional; local imagery and analysis work without them. Stop with Ctrl+C.

For the original application, install `backend/requirements.txt`, configure its services, and launch normally **without** `ORBIT_DEMO=true`. `/orbit` then uses authenticated change endpoints; local fixtures are only served in explicit demo mode. Original login, users and API authorization are not bypassed by the backend.

## Optional Gemini reporting

Put fresh credentials in the repository-root `.env` (gitignored):

```dotenv
LLM_API_KEY=your-key-here
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=your-working-vision-model-id
```

The existing OpenAI-compatible client sends both image data URLs and measured regions to Gemini. No provider key reaches the browser. Missing credentials, provider errors, invalid JSON and unknown evidence references produce a labeled local fallback. A no-change result never calls the provider. Generation has a 15-second request timeout and no retries. Model output is an unvalidated visual hypothesis, not verified causation or calibrated confidence.

## Demo flow (120 seconds)

1. **0–20s:** River overflow; explain the synthetic label and drag the divider.
2. **20–40s:** Select R1/R2 and show pixel count, percentage and assumed-scale area.
3. **40–65s:** Generate assessment. Distinguish observed change from causal hypothesis; show the next verification action.
4. **65–85s:** Replay the explicitly simulated frames; change sensitivity and show assessment invalidation.
5. **85–105s:** Switch to excavation and then unchanged control. The control returns zero retained change.
6. **105–120s:** Export JSON and annotated image. Close with: “We extended our existing thermal-monitoring platform with image-based change inspection and evidence-linked assessments.”

“Thermal monitoring” opens the original committed 4,984-source snapshot without a database, reusing the original MapView and class filters. Snapshot classifications are historical predictions, not live or newly validated results. The live application remains linked from that view.

## Image and API contract

`POST /api/v1/change/analyze`: multipart `before`, `after`, `threshold` (0.05–0.60; default 0.20), optional positive finite `pixel_size_m`. Images must be PNG/JPEG, each exactly 512×512 and under 5 MB. Alignment and comparable lighting must be confirmed by the user; automatic registration and cloud removal are outside the prototype.

Response: `analysis_id`, width/height, threshold, minimum region pixels, changed pixel count/fraction, optional area in square metres, numbered regions (`bbox_xywh`, `polygon_xy`, `pixels`), PNG data URLs for overlay/mask, and a local report. Polygons use image coordinates with origin top-left and implicit closure; outlines may simplify holes and boundaries. Pixel counts come from connected components, never bounding boxes or contour areas.

`POST /api/v1/change/report`: JSON `{ "analysis_id": "…" }`. Returns the analysis ID, `report_mode` (`local`, `gemini`, `local_fallback`), and a report with hypothesis, region-linked evidence, next action and limitations. Hypothesis values: `natural_like`, `human_like`, `uncertain`, `no_change`. Storage is limited to 12 analyses, with a 30-minute lifetime and owner checks. Eviction/restart requires reanalysis. Reports are tied to an analysis, not a mutable source ID.

Demo-only endpoints: `GET /api/v1/change/fixtures`, `GET /api/v1/change/fixtures/{id}/image?frame=0..3`, `GET /api/v1/change/thermal`. Requests with non-loopback clients, non-local Host or non-local Origin are rejected. Do not expose demo mode through a proxy or public tunnel.

Exports include provenance, synthetic status, image/frame identity, analysis settings and report mode. Uploaded imagery has unknown capture dates. Synthetic area uses an assumed 2 m/pixel scale; upload area remains unknown without supplied scale. Synthetic timeline timestamps label a scenario, never real observations or forecasts. dNBR evidence in the original application supports burn-scar detection, not ignition attribution.

## Checks

```sh
cd backend
../.venv/bin/python -m pytest tests/test_change.py -q
cd ../web
npm run build
node src/lib/humanize.selfcheck.mjs
```

The change tests cover control/change fixtures and mask IoU, pixel accounting, units, upload validation, provider fallbacks, evidence validation, analysis expiry/eviction, owner isolation, loopback restrictions and database-free startup. The complete backend suite passes 40 tests, including the original pipeline tests and authenticated-route checks. Two pre-existing smoke tests were corrected to authenticate their validation requests rather than receiving an earlier 401 response. Real satellite accuracy is not established by synthetic tests. Review cloud, seasonality and alignment effects before using real results.

No training, new microservices, hardware, database migrations or 3D terrain dependencies were added. The six-hour spread estimate in the original map is explicitly labeled illustrative.
