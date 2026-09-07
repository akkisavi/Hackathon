"""Natural-language query over thermal sources (Phase 2c).

The LLM never sees the database and never writes SQL. It only fills in a
fixed, typed parameter set via function calling; we translate those
parameters into a parameterised SQLAlchemy query. Worst case the model
picks bad filters — it cannot inject.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.llm_client import chat, get_client
from app.core.config import get_settings
from app.core.db import get_db
from app.core.geojson import feature_collection, point_feature
from app.models.classification import Classification
from app.models.thermal_source import ThermalSource
from app.processing.classify import CLASSES

router = APIRouter(prefix="/query", tags=["query"])

# rough state bounding boxes (min_lon, min_lat, max_lon, max_lat) — enough to
# scope a demo query like "flares in Gujarat"
_STATE_BBOX = {
    "gujarat": (68.1, 20.1, 74.5, 24.7), "punjab": (73.8, 29.5, 76.9, 32.6),
    "haryana": (74.4, 27.6, 77.6, 30.9), "rajasthan": (69.5, 23.0, 78.3, 30.2),
    "odisha": (81.3, 17.8, 87.5, 22.6), "jharkhand": (83.3, 21.9, 87.9, 25.4),
    "chhattisgarh": (80.2, 17.8, 84.4, 24.1), "maharashtra": (72.6, 15.6, 80.9, 22.0),
    "west bengal": (85.8, 21.5, 89.9, 27.2), "madhya pradesh": (74.0, 21.1, 82.8, 26.9),
    "uttar pradesh": (77.1, 23.9, 84.6, 30.4), "tamil nadu": (76.2, 8.1, 80.3, 13.6),
    "karnataka": (74.0, 11.6, 78.6, 18.5), "assam": (89.7, 24.1, 96.0, 28.2),
}

_TOOL = {
    "type": "function",
    "function": {
        "name": "find_thermal_sources",
        "description": "Filter classified thermal sources detected from NASA FIRMS.",
        "parameters": {
            "type": "object",
            "properties": {
                "predicted_class": {"type": "string", "enum": list(CLASSES),
                                    "description": "restrict to one predicted source type"},
                "state": {"type": "string", "enum": sorted(_STATE_BBOX),
                          "description": "Indian state to restrict the search to"},
                "min_span_days": {"type": "number",
                                  "description": "minimum days between first and last detection"},
                "min_recurrence_days": {"type": "number",
                                        "description": "minimum distinct days the source was seen"},
                "min_frp_mean": {"type": "number", "description": "minimum mean Fire Radiative Power (MW)"},
                "min_detections": {"type": "integer"},
                "unregistered_only": {"type": "boolean",
                                      "description": "only sources flagged as having no facility on record"},
                "limit": {"type": "integer", "description": "max results, default 50"},
            },
        },
    },
}


class QueryIn(BaseModel):
    q: str


def _interpret(q: str) -> dict:
    resp = get_client().chat.completions.create(
        model=get_settings().llm_model,
        messages=[
            {"role": "system", "content": "Translate the user's request into a "
             "find_thermal_sources call. Use months*30 for durations given in months. "
             "Omit filters the user did not ask for."},
            {"role": "user", "content": q},
        ],
        tools=[_TOOL], tool_choice={"type": "function", "function": {"name": "find_thermal_sources"}},
        temperature=0,
    )
    calls = resp.choices[0].message.tool_calls
    if not calls:
        raise HTTPException(422, detail="could not interpret the query")
    return json.loads(calls[0].function.arguments or "{}")


def _run(params: dict, db: Session):
    stmt = (
        select(ThermalSource, Classification)
        .join(Classification, Classification.thermal_source_id == ThermalSource.id, isouter=True)
    )
    if params.get("predicted_class"):
        stmt = stmt.where(Classification.predicted_class == params["predicted_class"])
    if params.get("unregistered_only"):
        stmt = stmt.where(Classification.is_unregistered.is_(True))
    if params.get("min_span_days") is not None:
        stmt = stmt.where(ThermalSource.span_days >= float(params["min_span_days"]))
    if params.get("min_recurrence_days") is not None:
        stmt = stmt.where(ThermalSource.recurrence_days >= int(params["min_recurrence_days"]))
    if params.get("min_frp_mean") is not None:
        stmt = stmt.where(ThermalSource.frp_mean >= float(params["min_frp_mean"]))
    if params.get("min_detections") is not None:
        stmt = stmt.where(ThermalSource.detection_count >= int(params["min_detections"]))
    if params.get("state") in _STATE_BBOX:
        lo_lon, lo_lat, hi_lon, hi_lat = _STATE_BBOX[params["state"]]
        stmt = stmt.where(
            ThermalSource.centroid_lon.between(lo_lon, hi_lon),
            ThermalSource.centroid_lat.between(lo_lat, hi_lat),
        )
    limit = min(int(params.get("limit") or 50), 500)
    stmt = stmt.order_by(ThermalSource.detection_count.desc()).limit(limit)
    return db.execute(stmt).all()


def _summarise(q: str, params: dict, rows: list) -> str:
    by_class: dict[str, int] = {}
    for _, c in rows:
        k = c.predicted_class if c else "unclassified"
        by_class[k] = by_class.get(k, 0) + 1
    facts = {"result_count": len(rows), "filters_applied": params, "class_breakdown": by_class}
    try:
        return chat([
            {"role": "system", "content": "Summarise these thermal-source query results for an "
             "analyst in 1-2 sentences. Use only the numbers given."},
            {"role": "user", "content": f"Question: {q}\nResults: {json.dumps(facts)}"},
        ], temperature=0.2, max_tokens=800).strip()
    except Exception:
        return f"{len(rows)} matching sources. Breakdown: {by_class}."


@router.post("/")
def nl_query(body: QueryIn, db: Session = Depends(get_db)):
    params = _interpret(body.q)
    rows = _run(params, db)
    fc = feature_collection(
        point_feature(s.centroid_lon, s.centroid_lat, {
            "id": s.id,
            "predicted_class": c.predicted_class if c else None,
            "confidence": c.confidence if c else None,
            "is_unregistered": bool(c and c.is_unregistered),
            "span_days": s.span_days,
            "recurrence_days": s.recurrence_days,
            "frp_mean": s.frp_mean,
            "detection_count": s.detection_count,
        })
        for s, c in rows
    )
    return {"interpreted": params, "summary": _summarise(body.q, params, rows), "results": fc}
