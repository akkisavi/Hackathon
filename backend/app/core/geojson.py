"""Minimal GeoJSON assembly. Both frontends consume FeatureCollections."""
from __future__ import annotations

from typing import Iterable


def point_feature(lon: float, lat: float, properties: dict) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": properties,
    }


def feature_collection(features: Iterable[dict]) -> dict:
    feats = list(features)
    return {"type": "FeatureCollection", "features": feats, "count": len(feats)}
