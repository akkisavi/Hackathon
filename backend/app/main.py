from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.change import build_router, loopback_only
from app.api.v1.water import build_router as build_water_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.project_name)

# Dev-open CORS: the web client (vite :5173) and Expo dev server call this
# cross-origin. React Native on a device sends no Origin, so this only
# matters for the browser. Lock down to real origins before any deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"] if settings.orbit_demo else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.orbit_demo:
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
    return {"status": "ok", "service": settings.project_name, "orbit_demo": settings.orbit_demo}
