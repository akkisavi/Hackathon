# KJSIM Internal SIH Evaluation — Prep Answers

Talking points mapped to the jury rubric (`Internal SIH Jury Evaluation Sheets.pdf`), based on the actual repo state.

**Problem Statement 26162** — AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM & Satellite Data. Organization: NTRO. Theme: Disaster Management. Team size: 5.

## Official Problem Statement

**Background.** Industrial facilities generate thermal signatures observable from space, but current satellite-based monitoring systems like NASA FIRMS cannot distinguish between different types of thermal anomalies.

**Description.** Industrial facilities such as oil refineries, petrochemical complexes, thermal power plants, steel industries, mining areas, and LNG terminals generate thermal signatures that can be observed from space. Accidental industrial fires, gas leaks, explosions, and abnormal thermal events pose significant risks to critical infrastructure, public safety, and the environment. NASA FIRMS provides thermal anomaly detections but does not distinguish between industrial fires, gas flares, agricultural burning, mining activity, and wildfires. The challenge is to develop an AI-enabled geospatial system that automatically identifies, classifies, and monitors industrial fires and persistent thermal sources by integrating thermal anomaly data, land-cover information, industrial infrastructure databases, and satellite imagery.

**Expected Solution/Deliverables:**
1. Classification and segregation of industrial fires from forest fires and other natural fires.
2. GIS-based solution for data storage, visualization of the output as an overlay over maps.

### Cross-check against the repo — both deliverables verified in code, not just claimed

| Deliverable | Status | Evidence |
|---|---|---|
| (i) Segregate industrial fires from forest/natural fires | ✅ Met | `backend/app/processing/classify.py:30-32` defines 7 classes: `industrial_fire`, `gas_flare`, `steel_smelter`, `brick_kiln`, `agricultural_burning`, `mining` (all industrial/human-driven) vs `wildfire` (natural) — each with its own scoring function and an explainable rationale, not a binary guess |
| (ii) GIS-based storage + map overlay visualization | ✅ Met | PostGIS geometry columns on every spatial model (`detection`, `thermal_source`, `osm_infra`, `flare_ref`); GeoJSON served from `/sources`, `/hotspots`, `/infra`, `/query`, plus `/export` for GeoJSON/KML into external GIS tools (QGIS); web dashboard renders it all as map-overlay layers (MapLibre GL) |

Also covers the two adjacent thermal types the description explicitly names but the deliverables don't strictly require: **gas leaks/flares** (`gas_flare` class, matched against the ORNL VIIRS Nightfire flare catalog) and **persistent industrial sources** (the `is_unregistered` Isolation Forest flag) — both go beyond the minimum ask.

---

## ROUND 1 — Idea Screening & Concept Proof

### Problem Understanding & Context (25)
NASA FIRMS gives raw satellite thermal-anomaly pixels — a lat/lon, brightness, and confidence score — with no indication of *what* is burning. A regulator scanning India's FIRMS feed cannot tell a refinery flare from an illegal brick kiln from a wildfire from crop-stubble burning. NTRO needs to know which persistent heat sources are **industrial** (and whether they're **registered**), not just where heat is detected. That's the exact gap we scope to.

### Innovation & Novelty (25)
The differentiator isn't "classify fires" — most teams will build that. Ours is the **unregistered persistent thermal source flag**: an Isolation Forest anomaly detector that checks every persistent, stable heat source against OpenStreetMap + government infrastructure records. A source burning steadily for 8 months with **no facility on record nearby** is the actual enforcement signal — that's what a regulator investigates. We also use a diurnal-signature + persistence table (day/night ratio, FRP stability, recurrence) as the core discriminator instead of raw imagery — cheaper to compute, and fully explainable to a government panel instead of being a black-box CNN.

### Feasibility & Tech Strategy (25)
Locked, boring, production-proven stack — no buzzword risk:
- **Backend:** FastAPI + PostgreSQL/PostGIS (hosted on Supabase)
- **Web:** React + MapLibre GL + Tailwind
- **Mobile:** React Native (Expo), scoped deliberately as a *view-only* companion, not a second full product
- **ML:** pandas, geopandas, scikit-learn, LightGBM, Isolation Forest
- **Jobs:** Celery + Redis (Upstash) for the 6-hourly FIRMS refresh
- **AI layer:** Google Gemini via its OpenAI-compatible endpoint, for incident narratives + natural-language query

Every stage degrades gracefully — the rule engine alone gets ~60-70% accuracy before ML is even added, so there's no single point of failure.

### Initial Plan & Team Matrix (25)
5 owners, non-overlapping, parallelizable from day 1:

| Role | Owns |
|---|---|
| M1 — Data + ML lead | FIRMS ingestion, clustering, feature engineering, classifier |
| M2 — Backend engineer | FastAPI, PostGIS schema, APIs, LLM integration, Celery |
| M3 — Web frontend | React dashboard, map, alert feed |
| M4 — Mobile + integration | React Native companion, wiring clients to API, deployment |
| M5 — GIS + domain + pitch | OSM/land-cover prep, QGIS validation, labeling, deck, demo script |

Roadmap was phased (Phase 0 setup → Phase 1 pipeline → Phase 2 AI → Phase 3 GIS deliverable → Phase 4 hardening/pitch), with an explicit "never cut" list (clustering entity, class-colored map, unregistered flag) decided up front instead of at 2am.

---

## ROUND 2 — Technical Architecture & Prototype Progress

### Technical Depth & Architecture (30)
```
FIRMS + OSM + WorldCover ingestion (Celery, every 6h)
        ↓
Spatio-temporal clustering (DBSCAN, ~1km/7-day) → "thermal_source" entities
        ↓
Feature engineering (proximity to infra, land cover, day/night ratio, FRP trend, recurrence)
        ↓
Stage 1: rule engine (explainable prior)
Stage 2: LightGBM multiclass (weak-supervised, 7 classes)
Stage 3: Isolation Forest → is_unregistered flag
Stage 4: Sentinel-2 NBR burn-scar confirmation for wildfires
        ↓
LLM reasoning (Gemini) → incident narrative + NL query (function calling, never raw SQL)
        ↓
FastAPI (async, PostGIS, Redis/Celery) → React web + React Native mobile
```
Modular by design: `backend/app/{core,models,ingestion,processing,ai,api,workers}` — each pipeline stage is an independent, swappable module. Clean separation between raw detections, clustered sources, and classification results in the schema.

### Prototype Progress & Completion (30)
This is **not a mockup — it's an end-to-end working system with real data flowing through every stage**:
- 647k raw FIRMS detections ingested → 4,984 persistent thermal sources clustered
- Full classification pipeline live (rule engine + LightGBM `ml/models/classifier.pkl`)
- `osm_infra` populated with 42,255 real OSM features
- Land cover enrichment via Earth Engine (ESA WorldCover)
- Isolation Forest flags 27 sources as unregistered
- LLM incident narratives verified against Gemini
- Web dashboard verified in-browser against the live API
- Mobile app builds clean (Android bundle)
- GeoJSON/KML export working
- 93.8% validation accuracy with a confusion matrix

Every API endpoint listed in the README (`/hotspots`, `/sources`, `/sources/{id}`, `/infra`, `/ingest`, `/query`, `/alerts`, `/export`) is implemented and callable, not stubbed.

### UX/UI Design & Accessibility (20)
Web dashboard is deliberately designed as a **control-room tool for government analysts** — data-dense, trust-first, single restrained accent color, minimal motion (not an agency-portfolio landing page). Layout: left rail (layer toggles, class legend + live-count filters, alert feed), top bar (NL query box, GeoJSON/KML export), map-click slide-in detail panel (class, explainable rationale, per-class scores, LLM brief, lifecycle). Mobile app mirrors the essentials only — map, alerts, detail sheet — kept intentionally minimal so it doesn't dilute engineering time.

### Logic / Hardware Complexity (20)
Well past CRUD-wrapper territory:
- Custom multi-stage ML pipeline: rule-based classifier → gradient-boosted model (LightGBM) trained on **weak supervision** (flare catalog + OSM proximity + rule engine as noisy labels, since no ground-truth labeled dataset exists for this problem)
- Unsupervised anomaly detection (Isolation Forest) for the unregistered-source signal
- Geospatial computation: DBSCAN clustering over real coordinates, PostGIS proximity queries, satellite raster sampling (Earth Engine)
- Satellite image analysis: Sentinel-2 NBR (Normalized Burn Ratio) differencing across pre/post-fire composites for wildfire confirmation
- LLM function-calling translation layer: natural language → typed structured query → PostGIS filter (never raw SQL passed to the LLM, avoiding injection risk)

---

## ROUND 3 — Grand Finale Readiness & Demo Pitch

### Live Demo & Real-Time Execution (35)
Demo runbook is pre-scripted (4 clicks, per `README.md` / `docs/demo-script.md`):
1. India map, all classified sources — point out coal-belt mining, northern agricultural burning
2. Click a gas flare near a refinery — explainable rationale + LLM incident brief naming the nearest facility
3. Type a natural-language query (`unregistered brick kilns in West Bengal`) — live filter + summary
4. Toggle "Unregistered only" — 27 sources; click one — "persistent, 8 months, no facility on record." Export to KML.

Demo-safety net: `python backend/scripts/demo_snapshot.py load` restores a frozen DB snapshot (`data/demo/*.jsonl`, committed) so the live presentation never depends on FIRMS API uptime or rate limits.

### Scalability & Deployment (25)
- Fully containerizable: `docker-compose.yml` brings up Postgres+PostGIS, Redis, API, and worker in one command
- Hosted-DB path already in production use (Supabase, free tier) — decouples the demo from local infra entirely
- Celery + Redis (Upstash) handles scheduled ingestion (every 6h), tuned for the free-tier command cap (30s polling, no result backend) with a documented no-infra fallback (`scripts/run_pipeline.py` via Task Scheduler)
- Stateless FastAPI service — horizontally scalable behind a load balancer with no code changes
- Remaining gap (honest): no CI/CD pipeline or cloud VM deployment yet — planned as ngrok/one cloud VM for the demo, not over-invested in infra per the cut-list philosophy

### Impact & Business Viability (25)
Direct NTRO/disaster-management use case: turns an undifferentiated satellite heat feed into an actionable enforcement tool. The unregistered-source flag is the concrete deliverable — 27 real candidate sites a regulator can dispatch an inspection team to, instead of manually cross-referencing thousands of FIRMS points against facility registries by hand. Low marginal cost (free-tier FIRMS, OSM, Gemini, Supabase, Upstash) makes it deployable at state/national scale without new hardware. Directly answers the PS's requirement for a "GIS-based solution for data storage, visualization as an overlay over maps" with GeoJSON/KML export so results drop straight into the evaluator's own GIS software.

### Presentation, Q&A & Team Synergy (15)
Pitch structure locked: problem → why raw FIRMS fails (day/night + persistence insight) → architecture → live demo → unregistered-source differentiator → validation numbers (93.8% accuracy) → NTRO/disaster-management impact → roadmap. Team roles map directly to who can field which question (M1 on ML/accuracy, M2 on backend/API, M3/M4 on the live apps, M5 on validation methodology and domain grounding). Rehearsal plan: 5+ full run-throughs plus a recorded video fallback in case of live-demo/wifi failure.

---

## Honest gaps to preempt if asked
- QGIS ground-truth pass against additional named facilities (Jamnagar, Punjab stubble window) is still open (`M5`).
- No CI/CD pipeline or persistent cloud deployment yet — demo currently runs via `dev.ps1` (local) or `docker compose up` (containerized local), not a public URL.
- Mobile push notifications were cut early (explicit, documented decision) to protect time for the core differentiator.
