"""Turn a classified ThermalSource into a human-readable incident brief
(Phase 2c). Generated lazily on first request for a source and cached on
the `classification.narrative` column.
"""
from __future__ import annotations

from app.ai.llm_client import chat

_SYSTEM = (
    "You are a geospatial analyst supporting India's disaster-management and "
    "industrial-safety authorities. You are given a thermal source detected by "
    "NASA FIRMS and a rule-based classification of it. Write a short incident "
    "brief for a government analyst. Be factual and measured; do not invent "
    "facilities, place names, or numbers beyond what is provided."
)

_TEMPLATE = """\
Thermal source #{sid}
Location: {lat:.4f}, {lon:.4f}
Predicted type: {cls} (rule-engine confidence {conf:.0%})
Why: {rationale}
Lifecycle: first seen {first_seen}, last seen {last_seen}, {span:.0f} days span, \
seen on {recurrence} distinct days, {det} detections
Behaviour: day/night ratio {dnr:.2f}, FRP mean {frp_mean:.1f} MW (variability {frp_cv:.2f}), \
footprint {bbox:.2f} km^2, growth {growth:+.3f} km^2/day
Land cover at the site: {land_cover}
Sentinel-2 burn scar: {burn_scar}
Nearest mapped infrastructure: {infra}
Unregistered-source flag: {unreg}

Write 3-4 sentences:
1. What this source most likely is and how confident we are.
2. The single strongest piece of evidence.
3. One recommended action for the authority (inspection, monitoring, cross-check with records, or none needed).
4. One caveat about what could make this classification wrong.
Return plain prose, no headings or bullet points."""


def build_prompt(source, cls, feats: dict) -> str:
    infra = "not available (no infrastructure registry loaded)"
    if feats.get("has_infra_context") and feats.get("dist_to_infra_m") is not None:
        name = feats.get("nearest_infra_name") or "unnamed"
        infra = (f"{feats.get('nearest_infra_kind', 'site')} '{name}', "
                 f"{float(feats['dist_to_infra_m']):.0f} m away")
    unreg = cls.unregistered_reason if cls.is_unregistered else "not flagged"

    return _TEMPLATE.format(
        sid=source.id, lat=source.centroid_lat, lon=source.centroid_lon,
        cls=cls.predicted_class, conf=cls.confidence, rationale=cls.rationale,
        first_seen=source.first_seen.date(), last_seen=source.last_seen.date(),
        span=source.span_days, recurrence=source.recurrence_days, det=source.detection_count,
        dnr=source.day_night_ratio, frp_mean=source.frp_mean,
        frp_cv=feats.get("frp_cv", 0.0), bbox=source.bbox_area_km2,
        growth=source.bbox_growth_rate,
        land_cover=(source.land_cover or "not sampled").replace("_", " "),
        burn_scar=(
            f"{source.burn_scar} (dNBR {source.dnbr})"
            if source.burn_scar else "not checked"
        ),
        infra=infra, unreg=unreg,
    )


def generate_narrative(source, cls, feats: dict) -> str:
    """Returns the incident brief, or "" if the LLM call fails (narrative is
    optional — the classification and rationale stand on their own)."""
    try:
        # generous cap: gemini-2.5-flash spends output budget on hidden
        # reasoning tokens before the visible answer
        return chat(
            [{"role": "system", "content": _SYSTEM},
             {"role": "user", "content": build_prompt(source, cls, feats)}],
            temperature=0.3, max_tokens=2000,
        ).strip()
    except Exception:
        return ""
