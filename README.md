# SIH26162 — AI-Based Detection & Classification of Industrial Fires and Persistent Thermal Sources

See `Plan.md` for the full winning plan (architecture, phases, team roles, cut list).
This README is the **Phase 0 setup checklist** — everyone runs their part in parallel, nobody waits.

## Repo layout

```
backend/   FastAPI + PostGIS + Celery      (M2)
web/       React + MapLibre GL             (M3)
mobile/    React Native (Expo) companion   (M4)
ml/        notebooks + training scripts    (M1, with M5 on labels)
data/      gitignored — raw FIRMS/OSM/labels land here, never committed
```

## Quick start (Windows)

Once `.env` is filled in and deps are installed:

```
.\dev.ps1              # backend :8000 + web :5173, each in its own window
.\dev.ps1 -Mobile      # also start the Expo dev server
.\dev.ps1 -Install     # pip/npm install first, then start
```

## Phase 0 — Setup (Days 1-3)

### 1. Everyone: environment
```
cp .env.example .env
```
Fill in `FIRMS_MAP_KEY` (free, instant: https://firms.modaps.eosdis.nasa.gov/api/map_key/)
and `LLM_API_KEY` (free Gemini key: https://aistudio.google.com/apikey) as soon as you
have them. Never commit `.env`.

### 2. M2 — backend + infra

**Database — hosted Postgres + PostGIS (Supabase, free). Already provisioned; string is in `.env`.**
To set up a fresh one:
1. Create a project at https://supabase.com.
2. Connect → **Connection pooler → Session mode** (the direct `db.<ref>.supabase.co`
   host is not published for free projects — you must use the pooler).
   Shape: `postgresql://postgres.<project-ref>:<PASSWORD>@aws-0-<region>.pooler.supabase.com:5432/postgres`
3. Put it in `.env` as `DATABASE_URL=`. **Percent-encode reserved chars in the password**
   (`@` → `%40`, etc.), or connection parsing fails.
4. Create the schema (enables PostGIS + creates all tables):
   ```
   cd backend && pip install -r requirements.txt
   python -m app.core.db          # -> "Schema ready on postgresql://..."
   ```

**Run the API and the pipeline:**
```
uvicorn app.main:app --reload
curl localhost:8000/health                       # {"status":"ok",...}
curl -X POST "localhost:8000/api/v1/ingest/?days=3"   # pulls FIRMS -> clusters -> stores
curl "localhost:8000/api/v1/sources/"            # GeoJSON of clustered thermal sources
curl "localhost:8000/api/v1/hotspots/?days=3"    # GeoJSON of raw detections
```

`pytest` runs the no-DB logic tests (clustering, FIRMS parsing, API smoke).

**Scheduled refresh** — three ways, pick one:
- On demand: `POST /api/v1/ingest/?days=3`
- No infra: `python scripts/run_pipeline.py` from cron / Task Scheduler (every 6h)
- Celery: point `REDIS_URL` at a free Upstash Redis, then
  `celery -A app.workers.celery_app worker --beat --loglevel=info` (schedule is in `app/workers/celery_app.py`)

**Alternative — all local via Docker** (matches `docker-compose.yml`, needs Docker Desktop):
```
docker compose up --build     # Postgres(PostGIS) + Redis + API + worker
```

### 3. M1 — FIRMS live data
```
pip install -r ml/requirements.txt -r backend/requirements.txt
python ml/scripts/quick_firms_pull.py
```
Should print a non-empty DataFrame of the last 3 days of VIIRS detections over India.
Also: submit the **full-year archive download request** today (it's queued server-side —
starting early matters more than anything else this week).

### 4. M5 — OSM / land cover / labels
- Geofabrik India OSM extract (~500MB): https://download.geofabrik.de/asia/india-latest.osm.pbf
  Pre-filter to just the infra tags, then load into `osm_infra`:
  ```
  osmium tags-filter india-latest.osm.pbf nwr/landuse=industrial,quarry nwr/power=plant nwr/man_made=works -o data/india-infra.osm.pbf
  cd backend && python -m app.ingestion.osm_loader ../data/india-infra.osm.pbf
  ```
- Register Google Earth Engine (via https://earthengine.google.com → Get Started → noncommercial Cloud project). Approval can take ~a day. Needed for ESA WorldCover + Sentinel-2, Phase 2.
- Download the ORNL VIIRS Nightfire flare catalog (2012-2019) for weak labels: https://doi.org/10.3334/ORNLDAAC/1874

### 5. M3 — web dashboard
```
cd web && cp .env.example .env && npm install && npm run dev
```
http://localhost:5173 — dark control-room map of every classified `thermal_source`
(colour = predicted class, size = detections, white ring = unregistered). Left rail:
layer toggles (industrial infrastructure overlay, unregistered-only), class legend +
filter with live counts, alert feed. Top bar: natural-language query box, GeoJSON/KML
export. Click a source for the slide-in detail panel (class, the explainable "why",
per-class scores, LLM incident brief, lifecycle). Needs the API on :8000.

### 6. M4 — mobile companion
```
cd mobile && cp .env.example .env && npm install && npx expo start
```
Scan with Expo Go — view-only: map with class-coloured markers, an Alerts bottom
sheet (`/alerts`), tap a marker for a detail sheet (class + rationale + LLM brief).
Set `EXPO_PUBLIC_API_BASE_URL` to the dev machine LAN IP (Android emulator: `10.0.2.2`).

### 7. API (Phase 1 + 2 + 3 backend — all implemented, see `backend/app/`)
- `GET  /api/v1/hotspots/?days=3` — raw detections, GeoJSON
- `GET  /api/v1/sources/` — classified sources + `predicted_class` / `confidence` / `is_unregistered`.
  Filters: `?predicted_class=`, `?unregistered_only=true`, `?min_detections=`
- `GET  /api/v1/sources/{id}` — full classification (rationale, per-class scores) + lazy LLM narrative
- `GET  /api/v1/infra/` — `osm_infra` as GeoJSON (`?bbox=`, `?kind=`, `?limit=`); `/infra/counts`
- `POST /api/v1/ingest/?days=3` — FIRMS → cluster → classify → store
- `POST /api/v1/query` `{"q": "..."}` — LLM → typed filter (function calling, never raw SQL) → GeoJSON + summary
- `GET  /api/v1/alerts/?new_within_days=3` — unregistered + newly-appeared feed
- `GET  /api/v1/export/?format=geojson|kml` — classified sources for the evaluator's GIS (same filters as `/sources`)

## Phase 0 acceptance criteria
- [x] Live FIRMS CSV loads into a DataFrame (`ml/scripts/quick_firms_pull.py`) — 1,137 rows verified
- [ ] OSM extract downloading; land-cover (GEE) account created; flare catalog downloaded  *(M5)*
- [x] Postgres(PostGIS 3.3) on Supabase; schema created; pipeline verified end-to-end — 1,137 detections → 203 thermal sources; `/sources` `/hotspots` `/ingest` all return real data
- [ ] Web app renders a map with a marker  *(`npm install` in `web/`)*
- [ ] Mobile app renders a map with a marker  *(`npm install` in `mobile/`)*

## Phase 2 — classification + AI layer (backend done)
- [x] Feature engineering (`app/processing/features.py`) — temporal + PostGIS proximity to `osm_infra` / `flare_ref`, degrades gracefully when those are empty
- [x] Stage-1 rule engine (`app/processing/classify.py`) — 7 classes, every prediction carries a plain-language rationale + per-class scores
- [x] Stage-3 Isolation Forest → `is_unregistered` flag (needs `osm_infra` loaded to fire — it is the "no facility on record" signal)
- [x] EOG/VIIRS flare catalogue loaded → `flare_ref` (542 India locations, 2012-2019): `python -m app.ingestion.flare_catalog ../data`
- [x] FIRMS 2025 archive loaded → 647k detections → ~13.9k classified thermal sources: `python scripts/load_archive.py ../data/fire_archive_SV-C2_800603.csv`
- [x] LLM incident narrative (`app/ai/report_generator.py`) + NL query endpoint (`app/api/v1/query.py`) — verified against Gemini
- [x] `osm_infra` populated — 42,255 features via `python -m app.ingestion.osm_loader ../data/india-260906.osm.pbf`
- [x] Stage-2 LightGBM — `python ml/scripts/train_classifier.py` → `ml/models/classifier.pkl`; pipeline auto-uses it (`method: lightgbm`). Weak labels: flare catalogue + OSM + land cover + rule engine
- [x] Land cover — ESA WorldCover 10m via Earth Engine (`app/ingestion/landcover.py`). `python scripts/enrich_landcover.py` samples every source centroid → `thermal_source.land_cover` (cropland 3.8k, built_up 250, bare 185, tree 404, ...). Feeds the rule engine + LightGBM + LLM brief. Needs `earthengine authenticate` + `GEE_PROJECT` in `.env`
- [x] Stage 4 — Sentinel-2 NBR burn-scar confirmation (`app/ingestion/sentinel.py`). `python scripts/confirm_wildfires.py` compares pre/post-fire cloud-masked S2 composites for every `wildfire` prediction + borderline candidate → `dNBR` → `thermal_source.burn_scar` (`confirmed` / `low` / `none`). A `wildfire` with no burn scar gets its confidence cut and a caveat added; a confirmed one gets a boost

## Phase 3 — GIS deliverable + dashboards
- [x] Web dashboard — class-coloured map, infra overlay, unregistered highlight, detail panel, alert feed, NL query, export (verified in browser against live API)
- [x] Mobile companion — class markers, alert feed, detail sheet (Android bundle builds clean)
- [x] GeoJSON + KML export (`/api/v1/export`)
- [x] Validation — `python ml/scripts/validate.py` → `ml/validation_report.md`: **93.8%** accuracy on the reference-labelable subset (96 sources near EOG flares / OSM registry), confusion matrix included
- [ ] QGIS ground-truth pass against named facilities (Jamnagar, Punjab stubble window) *(M5)*

## Phase 4 — hardening
- [x] Demo snapshot — `python backend/scripts/demo_snapshot.py dump|load` freezes/restores the demo-critical tables (`data/demo/*.jsonl`, committed) so the presentation never depends on the FIRMS API
- [ ] Deploy — ngrok or one cloud VM *(M2/M4)*
- [~] Pitch deck + demo script — content drafted in `docs/pitch-deck.md` (12 slides, speaker notes) and `docs/demo-script.md` (4 clicks, timing, fallbacks). M5 builds the actual slides + records the video fallback + rehearses 5+ times.

## Demo runbook — the 4 clicks
1. **India map, all sources** — "FIRMS gives thermal pixels; we colour them by *what* they are." Point out mining in the eastern coal belt, agricultural burning across the north.
2. **Click a gas flare near a refinery** — detail panel: explainable rule rationale + the LLM incident brief naming the nearest facility.
3. **Type a query** — `unregistered brick kilns in West Bengal` → watch it filter the map + summarise.
4. **Toggle "Unregistered only"** — 29 sources. Click one: "persistent, stable, 8 months, no facility on record. That's the one you investigate." Export to KML for the evaluator.

Before presenting: `python backend/scripts/demo_snapshot.py load` to guarantee the DB state.
