# SIH 2026 — Winning Plan

**Problem Statement ID:** 26162
**Title:** AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM & Satellite Data
**Organization:** National Technical Research Organisation (NTRO) · **Theme:** Disaster Management · **Category:** Software
**Idea-submission deadline:** 30 September 2026
**Team size:** 5

---

## Stack (locked)

- **Backend:** FastAPI + SQL (PostgreSQL / PostGIS)
- **Web app:** React + MapLibre GL + Tailwind (built using the `design-taste-frontend` skill)
- **Mobile app:** React Native (Expo) — scoped as a lightweight view-only companion
- **ML:** Python, pandas, geopandas, scikit-learn, LightGBM
- **Jobs / cache:** Celery + Redis
- **AI layer:** OpenAI-compatible LLM API — Google Gemini (free tier) primary, NVIDIA build as fallback (narratives + natural-language query)

---

## One honest risk call before we start

The **React Native app is our biggest risk-to-reward mismatch.** It is an explicit deliverable so we keep it, but a full mobile product would eat a whole person's time for something judges glance at for 30 seconds. It is therefore scoped as a **view-only alert companion** (map + alert feed + detail view), not a second full product. Do not let it balloon.

---

## Team roles (lock on Day 1)

| # | Role | Owns | Primary stack |
|---|------|------|---------------|
| M1 | **Data + ML lead** (strongest coder) | FIRMS ingestion, clustering, feature engineering, the classifier, weak-labeling | Python, pandas, geopandas, scikit-learn, LightGBM |
| M2 | **Backend engineer** | FastAPI app, PostGIS schema, all APIs, LLM integration, Celery jobs | FastAPI, SQLAlchemy, PostGIS, Redis/Celery |
| M3 | **Web frontend** | React dashboard, map, timeline, alert feed | React, MapLibre GL, Tailwind (design skill) |
| M4 | **Mobile + integration** | React Native companion app, wiring both clients to the API, deployment | React Native (Expo), Docker |
| M5 | **GIS + domain + pitch lead** | OSM/land-cover prep, QGIS ground-truth validation, labeling with M1, slide deck, demo script, docs | QGIS, GEE, PowerPoint/docs |

> M5 is **not** "the non-coder who makes slides." M5 owns whether the output is actually correct — the thing that separates a winning SIH project from a demo that classified noise with a confident-looking number. Give this to someone rigorous.

---

## The one-line pitch (everyone says the same thing)

> "FIRMS tells you **where** something is hot. We tell you **what** it is — refinery flare, steel plant, stubble burning, or a real wildfire — and we flag persistent thermal sources that **don't match any known facility**, which is the enforcement signal NTRO actually needs."

The winning differentiator is that last clause: **detecting unregistered / undocumented persistent thermal sources.** Everyone else builds a fire classifier. We build a fire classifier **plus** an anomaly detector that finds thermal sources with no matching infrastructure record. Protect it.

---

## Core technical insight (drives the whole design)

FIRMS does not give you "fires." It gives you **thermal anomaly pixels**: a lat/lon, a brightness temperature, an FRP value, a confidence score, and a day/night flag. Everything else must be **inferred** by fusing three signals:

1. **Where** it is — land cover + known industrial infrastructure
2. **How it behaves over time** — persistence, recurrence, diurnal pattern
3. **How intense / stable** it is — FRP magnitude and variance

**Diurnal signature + persistence is a stronger discriminator than raw imagery, and nearly free to compute:**

| Source type | Day/Night ratio | Persistence | FRP stability | Footprint |
|-------------|-----------------|-------------|---------------|-----------|
| Gas flare | ~50/50, constant | Years, same point | Very stable | Tiny, fixed |
| Industrial fire (accident) | Sudden, transient | Hours–days | Spikes then dies | Small, fixed |
| Brick kiln / smelter | Daytime-biased, cyclic | Months–years | Moderate, cyclic | Small cluster |
| Agricultural burning | Strongly daytime | Days, seasonal (Oct–Nov) | High variance | Scattered, moves |
| Mining (coal fire) | 24/7, near-constant | Years | Low variance | Small–medium, fixed |
| Wildfire | Variable, spreads | Days–weeks | Grows then decays | Large, expanding |

This table is most of the "AI." A gradient-boosted classifier on these engineered features beats a black-box CNN on raw imagery, trains faster, and — critically for a government use case — is **explainable**.

---

## Datasets — what to use and how to get it

| Priority | Dataset | Use | How to get it |
|----------|---------|-----|---------------|
| Mandatory | **NASA FIRMS** (thermal anomalies) | Core detections | Free `MAP_KEY` at firms.modaps.eosdis.nasa.gov → Area API (bbox, not Country). Submit an **archive download request** for a full year (queued — start early). |
| Mandatory | **OpenStreetMap** (industrial/power/mining infra) | Proximity features | Geofabrik `india-latest.osm.pbf` → load to PostGIS via osm2pgsql. Filter `landuse=industrial\|quarry`, `power=plant`, `man_made=works`. **Do not** call live Overpass per hotspot. |
| Strong | **ESA WorldCover 10m** (land cover) | Land-cover feature | Google Earth Engine `ESA/WorldCover/v200` (fastest), or public S3 `s3://esa-worldcover/` with rasterio. |
| Strong | **ORNL VIIRS Nightfire flare catalog 2012–2019** | Weak labels for "gas flare" | Open on NASA Earthdata / ORNL DAAC (doi:10.3334/ORNLDAAC/1874). Use as training labels only — **not** a runtime dependency (live VNF went license-gated in Jan 2025). |
| Optional | **Sentinel-2** (NBR / burn scar) | Wildfire confirmation | Via GEE `COPERNICUS/S2_SR_HARMONIZED` (reuse the GEE auth) or Copernicus Data Space Ecosystem. |
| India enrichment | **data.gov.in**, **ISRO Bhuvan** | Power plants, mines, stubble-burning products | OSM India tagging is patchy; cross-validate with gov datasets. |

---

## Architecture

```
INGESTION (Celery every 6h)
  FIRMS Area API (CSV, MAP_KEY, bbox, days)
  OSM extract (osm2pgsql → PostGIS, refresh weekly)
  ESA WorldCover (GEE point sample)
        │
        ▼
SPATIO-TEMPORAL CLUSTERING
  Raw pixels → DBSCAN (~1km eps, ~7-day window)
  → "Thermal Source" entities: first_seen, last_seen,
    detection_count, centroid, geometry
        │
        ▼
FEATURE ENGINEERING (per source)
  dist_to_industrial_polygon, dist_to_power_plant/refinery/mine,
  land_cover_class, day_night_ratio, FRP mean/std/trend,
  recurrence_days, bbox_growth_rate
        │
        ▼
ML CLASSIFICATION
  Stage 1: rule-based prior (explainable, ~60-70%)
  Stage 2: LightGBM multiclass (weak-supervised)
  Stage 3: Isolation Forest → "unregistered persistent source"
  Stage 4 (optional): Sentinel-2 NBR wildfire confirmation
        │
        ▼
LLM REASONING (OpenAI-compatible API — Gemini / NVIDIA)
  per cluster → incident narrative + recommended action + caveats
  NL query endpoint → PostGIS query via function calling
        │
        ▼
FASTAPI BACKEND (async, PostGIS, Redis/Celery)
        │
        ▼
React + MapLibre web  ·  React Native companion
```

### Repo structure

```
fire-detect/
├── backend/          # FastAPI + PostGIS
├── web/              # React + MapLibre
├── mobile/           # React Native (Expo)
├── ml/               # notebooks + training scripts + model artifacts
├── data/             # gitignored: raw FIRMS, OSM, labels
└── docker-compose.yml
```

### Backend structure

```
backend/app/
├── main.py
├── core/{config.py, db.py}
├── models/{detection.py, thermal_source.py, classification.py, osm_infra.py}
├── ingestion/{firms_client.py, osm_loader.py, landcover.py}
├── processing/{clustering.py, features.py, classify.py}
├── ai/{llm_client.py, report_generator.py}
├── api/v1/{hotspots.py, sources.py, query.py, alerts.py}
└── workers/{celery_app.py, tasks.py}
```

---

## Phase 0 — Setup (Days 1–3, everyone in parallel)

Nobody waits on anyone.

- **M1:** Register FIRMS `MAP_KEY` today. Submit the **archive download request** immediately (queued server-side). Meanwhile pull last-3-days NRT via the Area API so live data flows.
- **M5:** Start the **Geofabrik India OSM extract** download (~500MB). Register a **Google Earth Engine** account (WorldCover + Sentinel-2). Download the **ORNL VNF flare catalog (2012–2019)** for weak labels.
- **M2:** Repo skeleton, `docker-compose` with **PostGIS + Redis**, FastAPI hello-world, folder structure, `.env` (`FIRMS_MAP_KEY`, `DATABASE_URL`, `LLM_API_KEY`).
- **M3 & M4:** Scaffold React (Vite) and React Native (Expo), render a map with one hardcoded marker. Agree the API contract with M2 **on paper** first.

**Acceptance:** live FIRMS CSV in a DataFrame; OSM + land cover accessible; both frontends render a map with a marker; `docker-compose up` brings up Postgres + Redis + API.

---

## Phase 1 — Data pipeline + the "unit of the system" (Days 4–9)

The core realization the whole architecture depends on: **the system reasons about *thermal sources* — clustered, persistent entities with a lifecycle — not raw pixels.** Build that entity first.

- **M1:** Ingest FIRMS → `detection` rows → **DBSCAN cluster** (~1km eps, 7-day window) into `thermal_source` entities carrying `first_seen`, `last_seen`, `detection_count`, `centroid`, `frp_mean/std/trend`, `day_night_ratio`, `recurrence_days`, `bbox_growth_rate`.
- **M2:** PostGIS schema + models for `detection`, `thermal_source`, `osm_infra`, `classification`. `POST /ingest` + Celery task running ingest→cluster every 6h.
- **M5:** Load OSM industrial/power/mining features into PostGIS; enrich with data.gov.in power-plant / mining datasets.
- **M3:** Map renders real `thermal_source` centroids (plain points for now) + a date/time slider.
- **M4:** Mobile map renders the same source list.

**Acceptance:** the map shows clustered thermal sources over India that update on a schedule, each with an inspectable lifecycle. **This alone is a working system** — if everything after fails, you still demo this.

---

## Phase 2 — The AI: features → classification → anomaly flag (Days 10–18)

### 2a. Classifier (M1, with M5 on labels)

Per source, engineer: `dist_to_nearest_industrial_polygon`, `dist_to_power_plant/refinery/mine`, `land_cover_class` (GEE sample), plus temporal features from Phase 1. Then:

- **Stage 1 — rule engine:** encodes diurnal/persistence logic (50/50 day-night + years-persistent + tiny footprint near a refinery = gas flare; strongly-daytime + seasonal + scattered over cropland = agricultural burning). Catches 60–70% and is **fully explainable** — huge for a government panel.
- **Stage 2 — LightGBM multiclass:** trained on **weak labels** (ORNL flare catalog + OSM proximity + rule engine as noisy labels). Say "weak supervision" in the pitch — it answers the "where's your labeled data?" question.
- **Classes:** `industrial_fire`, `gas_flare`, `steel/smelter`, `brick_kiln`, `agricultural_burning`, `mining`, `wildfire`.

### 2b. Differentiator (M1) — Isolation Forest anomaly flag

A persistent, stable, 24/7 source with **no matching OSM/gov infrastructure nearby** → flag as **"unregistered persistent thermal source."** This is the finding NTRO cares about.

### 2c. AI integration / LLM layer (M2)

- Per flagged cluster → LLM with feature vector + class probabilities + nearest-facility name → **human-readable incident narrative + recommended action + confidence caveats**. Makes the output actionable, not just a colored dot.
- **NL query endpoint** (`POST /query`): "show persistent gas flares near refineries in Gujarat active over 6 months" → LLM translates to a PostGIS query via function calling → results + summary. A genuine wow-moment in a live demo.

**M3/M4 in parallel:** color markers by predicted class (locked legend); per-source detail panel with lifecycle chart + classification + LLM narrative.

**Acceptance:** click any hotspot → class, the explainable "why," LLM narrative, and unregistered-flag status. NL query box returns real results.

---

## Phase 3 — GIS deliverable + both apps polished (Days 19–24)

The PS explicitly demands *"GIS based solution for data storage, visualization as an overlay over maps."* Make it unmistakable.

- **M3 (web):** Toggleable overlay layers — hotspots, land cover, industrial infrastructure, wildfire-vs-industrial split. Timeline scrubber for source history. Alert feed of newly-flagged sources. **Apply the design skill here:** declare the design read as *"internal geospatial monitoring tool for government analysts, trust-first + data-dense, clean Tailwind utility system with a single restrained accent."* That pushes density up, motion down, no agency-portfolio flourishes. It's a control room, not a landing page.
- **M4 (mobile):** view-only companion — map, alert feed, tap-for-detail, push notification on new critical/unregistered source. Minimal on purpose.
- **M5:** Validate in **QGIS** against known facilities (Jamnagar refinery, thermal plants, a Punjab stubble-burning window from the archive). Produce a **defensible confusion matrix / accuracy number.** Add GeoJSON/KML export so output drops into the evaluator's own GIS.

**Acceptance:** web dashboard demo-ready with layer toggles; mobile shows alerts; validated accuracy figure; export works.

---

## Phase 4 — Harden, pitch, rehearse (Days 25–30)

Winning is 60% build, 40% story. Do not skip this.

- **M2/M4:** Dockerize everything; deploy to one cloud VM (or ngrok for the demo — don't over-invest in infra). Seed the demo DB with a curated set of sources so the demo never depends on a live API that might rate-limit mid-presentation.
- **M5:** Build the deck — problem → why FIRMS alone fails (day/night + persistence insight) → architecture → **live demo** → the unregistered-source differentiator → validation numbers → NTRO/disaster-management impact → roadmap (Sentinel-2 NBR confirmation, SMS alerts to district authorities).
- **Everyone:** rehearse the demo 5+ times. Pre-script exact clicks. Record a video fallback in case wifi dies.

### Demo script — the 4 clicks that win

1. India map with classified hotspots → "FIRMS can't do this coloring; we can."
2. Click a gas flare near a refinery → explainable features + LLM narrative.
3. Type a natural-language query → watch it return filtered results.
4. Click a flagged **unregistered** source → "no facility on record, burning steady for 8 months. That's the one you investigate."

---

## Cut list (decide early, not at 2am)

Cut in this order (nothing has been cut — all built):

1. Mobile push notifications — cut
2. ~~Sentinel-2 NBR confirmation~~ — built (`app/ingestion/sentinel.py`, Stage 4)
3. ~~LightGBM~~ — built (`ml/scripts/train_classifier.py`)
4. ~~NL query endpoint~~ — built (`app/api/v1/query.py`)

**Never cut:** the clustering/lifecycle entity, the class-colored map, and the unregistered-source flag. Those three are the demo.

---

## Deliverables checklist (maps to the PS)

- [x] Classification and segregation of industrial fires from forest/natural fires — Stage-1 rule engine (7 classes, explainable) + Stage-2 LightGBM on weak labels
- [x] GIS-based data storage (PostGIS on Supabase) + map-overlay visualization — web dashboard with class/infra/unregistered layers
- [x] React web app — control-room dashboard, verified in browser against live API
- [x] React Native mobile app — view-only companion (map + alert feed + detail), Android bundle builds clean
- [x] FastAPI + SQL backend
- [x] AI integrated — anomaly flag (`is_unregistered`, 27 sources), LLM incident narrative, NL query endpoint (Phase 2b/2c)
- [x] Validation accuracy figure + confusion matrix — 93.8% on the reference-labelable subset (`ml/validation_report.md`)
- [x] Export to GeoJSON/KML — `/api/v1/export`
- [ ] Pitch deck + rehearsed live demo + video fallback *(M5 / everyone)*
