from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.change import build_router, loopback_only
from app.api.v1.water import build_router as build_water_router
from app.core.config import get_settings

settings = get_settings()

@asynccontextmanager
async def lifespan(app):
    if settings.orbit_demo and settings.orbit_showcase:
        raise RuntimeError("Choose either local demo or public showcase mode.")
    if settings.orbit_showcase:
        from app.processing.water_bundle import verify_bundle
        verify_bundle()
    yield

app = FastAPI(title=settings.project_name, lifespan=lifespan)

# Dev-open CORS: the web client (vite :5173) and Expo dev server call this
# cross-origin. React Native on a device sends no Origin, so this only
# matters for the browser. Lock down to real origins before any deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"] if settings.orbit_demo else ([] if settings.orbit_showcase else ["*"]),
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.orbit_showcase:
    from app.showcase import ShowcaseMiddleware, showcase_access
    app.add_middleware(ShowcaseMiddleware)
    app.include_router(build_router(showcase_access, demo=True, local_reports=True), prefix=settings.api_v1_prefix)
    app.include_router(build_water_router(showcase_access), prefix=settings.api_v1_prefix)
elif settings.orbit_demo:
    app.include_router(build_router(loopback_only, demo=True), prefix=settings.api_v1_prefix)
    app.include_router(build_water_router(loopback_only), prefix=settings.api_v1_prefix)
else:
    from app.api.v1 import alerts, export, hotspots, infra, ingest, query, sources, auth, admin
    from app.api.dependencies import get_current_user_or_api_key

    for module in (auth, admin, hotspots, sources, infra, ingest, query, alerts, export):
        app.include_router(module.router, prefix=settings.api_v1_prefix)
    app.include_router(build_router(get_current_user_or_api_key), prefix=settings.api_v1_prefix)
    app.include_router(build_water_router(get_current_user_or_api_key), prefix=settings.api_v1_prefix)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.project_name, "orbit_demo": settings.orbit_demo, "showcase": settings.orbit_showcase}


@app.get("/api/v1/capabilities")
def capabilities():
    return {"showcase": settings.orbit_showcase, "fixtures": settings.orbit_showcase or settings.orbit_demo}


if settings.serve_frontend:
    frontend = Path(__file__).resolve().parents[2] / "web/dist"
    if not (frontend / "index.html").exists():
        raise RuntimeError("Build the React frontend before starting the production server.")
    app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend_page(path: str):
        if path.startswith(("api/", "health/")) or path == "api":
            raise HTTPException(404, "Unknown API route")
        if not path and settings.orbit_showcase:
            return RedirectResponse("/orbit/water")
        return FileResponse(frontend / "index.html")
