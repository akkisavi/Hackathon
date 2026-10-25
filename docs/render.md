# Deploy ORBIT DELTA to Render

This deployment is a public showcase of cached NASA observations, experimental water models, thermal snapshots, and image comparison. It needs no database, Redis, NASA credentials, or Gemini key.

## Deploy

1. In Render, choose **New → Blueprint** and connect `akkisavi/Hackathon`.
2. Select branch `feature/orbit-delta`. Render reads the root `render.yaml` and builds the root Dockerfile.
3. Review the **Starter** paid service selection before creating the service. No persistent disk is required.
4. Wait for `/health` to pass, then open `/orbit/water`. `/orbit` and `/orbit/thermal` are also available directly.

Render binds the service through `PORT`; the container listens on `0.0.0.0` and serves the built React application and API from the same origin. HTTPS is provided by Render. There are no required secrets. Do not enable `ORBIT_DEMO` on the hosted service.

## Evidence and readiness

The repository includes all 341 quality-filtered classification arrays, original acquisition metadata and raster checksums, plus three trusted trained models. The packaged arrays are lossless. The full raw collection is excluded. Rebuild the bundle after an intentional model/data update with `python scripts/package_water.py`; this requires the original local rasters.

Startup verifies every packaged file, decoded array checksum, and model identity/version. Missing or corrupt data prevents readiness. Models retain their experimental status and original validation limitations. Dates are cached observations; this deployment does not poll NASA or predict floods.

## Public service limits

Image analysis accepts aligned 512×512 PNG/JPEG pairs, with existing 5 MiB per-image limits and an 11 MiB request cap. Analyses are held in one process: at most 12, expiring after 30 minutes, and isolated by signed anonymous cookies. A restart invalidates sessions and uploaded analyses. Download assessments before leaving. Analysis/report requests have a per-client limit of 10 per minute. Water assessments allow 120 per minute so observation replay can continue. Use one worker; scaling replicas requires shared session/storage/rate infrastructure.

Reports are deterministic in public showcase mode. Existing authenticated application mode and localhost-only demo mode remain separate. This configuration does not expose login administration, ingestion or email actions.

Satellite photographs use external Esri World Imagery, with attribution and explicit contextual-composite labels. Provider failure leaves classified observations, local analysis and exports available. Photographs do not establish historical conditions on an acquisition date.

## Verification

The GitHub `Showcase container` workflow builds and starts the exact production container without data mounts, then tests the three water sites, image responses, thermal snapshot and direct frontend routes.

Local equivalent (Docker required):

```sh
docker build -t orbit-showcase .
docker run --rm -p 10000:10000 -e PORT=10000 orbit-showcase
python scripts/smoke_showcase.py http://localhost:10000
```

Backend tests: from `backend`, run `../.venv/bin/python -m pytest tests -q` after building the frontend. Local showcase frontend build: from `web`, run `VITE_API_BASE_URL=/api/v1 VITE_ORBIT_SHOWCASE=true npm run build`.

Roll back by redeploying the previous known-good commit in Render. Each image contains immutable evidence and models, so no database rollback is necessary.
