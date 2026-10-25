import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

// An image source stays visible even when external basemap tiles fail.
export default function ChangeMap({ incident, image, measurement, selectedRegion, onSelectRegion, showOverlay }) {
  const host = useRef(null);
  const mapRef = useRef(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    let map;
    try {
      map = new maplibregl.Map({
        container: host.current, center: [91.72, 26.18], zoom: 13,
        style: {
          version: 8, sources: { context: { type: "raster", tileSize: 256,
            tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
            attribution: "Context basemap © Esri; scenario imagery is synthetic" } },
          layers: [{ id: "background", type: "background", paint: { "background-color": "#dbe4dc" } },
            { id: "context", type: "raster", source: "context", paint: { "raster-opacity": 0.55, "raster-saturation": -0.5 } }],
        },
      });
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
      map.on("load", () => setReady(true));
      map.on("error", () => setError(true));
      mapRef.current = map;
    } catch { setError(true); }
    return () => { map?.remove(); mapRef.current = null; };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || !incident || !image) return;
    const [west, south, east, north] = incident.bbox;
    const coordinates = [[west, north], [east, north], [east, south], [west, south]];
    const controller = new AbortController();
    let localUrl;
    fetch(image, { signal: controller.signal, cache: "no-store" }).then(response => {
      if (!response.ok) throw new Error("Image unavailable");
      return response.blob();
    }).then(blob => {
      if (controller.signal.aborted) return;
      localUrl = URL.createObjectURL(blob);
      if (map.getSource("scene")) map.getSource("scene").updateImage({ url: localUrl, coordinates });
      else {
        map.addSource("scene", { type: "image", url: localUrl, coordinates });
        map.addLayer({ id: "scene", type: "raster", source: "scene", paint: { "raster-fade-duration": 0 } },
          map.getLayer("changes-fill") ? "changes-fill" : undefined);
      }
    }).catch(error => { if (error.name !== "AbortError") setError(true); });
    map.fitBounds([[west, south], [east, north]], { padding: 65, duration: 900, maxZoom: 15 });
    return () => { controller.abort(); if (localUrl) URL.revokeObjectURL(localUrl); };
  }, [ready, incident, image]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || !incident) return;
    const [west, south, east, north] = incident.bbox;
    const data = { type: "FeatureCollection", features: showOverlay ? (measurement?.regions ?? []).map(r => {
      const ring = r.polygon_xy.map(([x, y]) => [west + x / 512 * (east - west), north - y / 512 * (north - south)]);
      return { type: "Feature", properties: { id: r.id, selected: r.id === selectedRegion },
        geometry: { type: "Polygon", coordinates: [[...ring, ring[0]]] } };
    }) : [] };
    if (map.getSource("changes")) map.getSource("changes").setData(data);
    else {
      map.addSource("changes", { type: "geojson", data });
      map.addLayer({ id: "changes-fill", type: "fill", source: "changes", paint: {
        "fill-color": "#e09153", "fill-opacity": ["case", ["get", "selected"], 0.3, 0.13] } });
      map.addLayer({ id: "changes-line", type: "line", source: "changes", paint: {
        "line-color": "#ffe0a6", "line-width": ["case", ["get", "selected"], 3, 1.5] } });
    }
  }, [ready, incident, measurement, selectedRegion, showOverlay]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const select = e => onSelectRegion(e.features[0].properties.id);
    map.on("click", "changes-fill", select);
    return () => map.off("click", "changes-fill", select);
  }, [ready, onSelectRegion]);

  return <div className="od-map"><div ref={host} className="od-map-canvas" />
    <span className="od-map-note">{error ? "Context map unavailable · image comparison remains available" : "Illustrative location · synthetic image footprint"}</span>
  </div>;
}
