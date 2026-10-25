"""Image analysis endpoints shared by authenticated app and loopback demo."""
from collections import OrderedDict
from ipaddress import ip_address
from threading import Lock
from time import monotonic
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.ai.change_report import generate_change_report, local_report
from app.processing.change import MAX_IMAGE_BYTES, analyze_pair, decode_image, encode_png
from app.processing.change_fixtures import fixture_manifest, render_fixture, thermal_snapshot

MAX_ANALYSES = 12
TTL_SECONDS = 30 * 60
_analyses = OrderedDict()
_lock = Lock()


def loopback_only(request: Request):
    host = request.client.host if request.client else ""
    try:
        local = ip_address(host).is_loopback
    except ValueError:
        local = host == "testclient"
    origin = request.headers.get("origin")
    if (not local or request.url.hostname not in {"localhost", "127.0.0.1", "::1", "testserver"}
            or (origin and urlparse(origin).hostname not in {"localhost", "127.0.0.1", "::1"})):
        raise HTTPException(403, "Fixture demo is available on localhost only.")
    return "local-demo"


def _owner(principal):
    return str(getattr(principal, "id", principal))


class ReportRequest(BaseModel):
    analysis_id: str


def build_router(access_dependency, demo=False, local_reports=False):
    router = APIRouter(prefix="/change", tags=["change"])

    @router.post("/analyze")
    def analyze(before: UploadFile = File(...), after: UploadFile = File(...),
                threshold: float = Form(0.2, ge=0.05, le=0.6),
                pixel_size_m: float | None = Form(None, gt=0),
                principal=Depends(access_dependency)):
        try:
            images = [decode_image(f.file.read(MAX_IMAGE_BYTES + 1)) for f in (before, after)]
            measurement = analyze_pair(*images, threshold, pixel_size_m)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        analysis_id = str(uuid4())
        with _lock:
            now = monotonic()
            for key in list(_analyses):
                if now - _analyses[key]["created"] > TTL_SECONDS:
                    del _analyses[key]
            while len(_analyses) >= MAX_ANALYSES:
                _analyses.popitem(last=False)
            _analyses[analysis_id] = {"owner": _owner(principal), "images": images,
                                      "measurement": measurement, "created": now}
        return {"analysis_id": analysis_id, **measurement,
                "report": local_report(measurement), "report_mode": "local"}

    @router.post("/report")
    def report(body: ReportRequest, principal=Depends(access_dependency)):
        with _lock:
            saved = _analyses.get(body.analysis_id)
            if (not saved or saved["owner"] != _owner(principal)
                    or monotonic() - saved["created"] > TTL_SECONDS):
                raise HTTPException(404, "Analysis expired or unavailable. Analyze the pair again.")
        if local_reports:
            return {"analysis_id": body.analysis_id, "report": local_report(saved["measurement"]), "report_mode": "local", "report_notice": "Public showcase mode uses a local assessment based on measured regions."}
        return {"analysis_id": body.analysis_id,
                **generate_change_report(*saved["images"], saved["measurement"])}

    if demo:
        @router.get("/thermal")
        def thermal(principal=Depends(access_dependency)):
            return thermal_snapshot()

        @router.get("/fixtures")
        def fixtures(principal=Depends(access_dependency)):
            return fixture_manifest()

        @router.get("/fixtures/{fixture_id}/image")
        def image(fixture_id: str, frame: int = Query(3, ge=0, le=3),
                  principal=Depends(access_dependency)):
            try:
                return Response(encode_png(render_fixture(fixture_id, frame)), media_type="image/png",
                                headers={"Cache-Control": "private, max-age=3600", "Vary": "Origin"})
            except ValueError as exc:
                raise HTTPException(404, str(exc)) from exc

    return router
