import { useEffect, useState } from "react";
import "./satellite-preview.css";

export function satelliteBounds([lon, lat], areaKm2) {
  const halfKm = Math.max(0.5, Math.sqrt(Math.max(0, areaKm2 || 0)) * 1.5);
  const dLat = halfKm / 111;
  const dLon = halfKm / (111 * Math.max(0.01, Math.cos(lat * Math.PI / 180)));
  return [lon - dLon, lat - dLat, lon + dLon, lat + dLat];
}

function Preview({ bbox }) {
  const [state, setState] = useState("loading");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (state !== "loading") return;
    const timeout = setTimeout(() => setState("error"), 20000);
    return () => clearTimeout(timeout);
  }, [state, attempt]);
  const params = new URLSearchParams({bbox: bbox.join(","), bboxSR: "4326", imageSR: "4326", size: "600,360", format: "jpg", f: "image"});
  return <figure className="satellite-preview">
    <h3>Satellite view</h3>
    {state === "loading" && <p role="status">Loading satellite imagery…</p>}
    {state !== "error" && <img key={attempt} src={`https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export?${params}&retry=${attempt}`} alt="Photographic satellite composite of the selected location" onLoad={() => setState("ready")} onError={() => setState("error")} />}
    {state === "error" && <div role="status"><p>Satellite imagery is temporarily unavailable. Observation evidence remains available.</p><button onClick={() => {setState("loading");setAttempt(n => n + 1);}}>Retry imagery</button></div>}
    <figcaption>Esri World Imagery · Sources: Esri, Maxar, Earthstar Geographics, and the GIS User Community.<br/>Contextual satellite composite; may not match the observation date.</figcaption>
  </figure>;
}

export default function SatellitePreview({bbox, coordinates, areaKm2}) {
  const bounds = bbox || (coordinates && satelliteBounds(coordinates, areaKm2));
  if (!bounds || bounds.length !== 4 || !bounds.every(Number.isFinite)) return null;
  return <Preview key={bounds.join(",")} bbox={bounds}/>;
}
