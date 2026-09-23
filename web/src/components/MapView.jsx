import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { classColorExpr, INFRA_LEGEND } from "../lib/classes.js";
import { theme } from "../lib/theme.js";

const DAY = 86400000;
const fmtDay = (ms) => new Date(ms).toISOString().slice(0, 10);
const empty = () => ({ type: "FeatureCollection", features: [] });

function baseStyle(mode) {
  const dark = mode === "dark";
  return {
    version: 8,
    sources: {
      basemap: {
        type: "raster",
        tiles: [
          `https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_${
            dark ? "Dark_Gray" : "Light_Gray"
          }_Base/MapServer/tile/{z}/{y}/{x}`,
        ],
        tileSize: 256,
        attribution: "Esri, OpenStreetMap contributors",
      },
    },
    layers: [
      { id: "bg", type: "background", paint: { "background-color": dark ? "#1c1c1c" : "#f4f4f5" } },
      { id: "basemap", type: "raster", source: "basemap" },
    ],
  };
}

const SOURCE_PAINT = {
  "circle-radius": ["interpolate", ["linear"], ["get", "detection_count"], 1, 3.5, 200, 15],
  "circle-color": classColorExpr,
  "circle-opacity": 0.9,
  "circle-stroke-width": ["case", ["get", "is_unregistered"], 2, 0.6],
  "circle-stroke-color": ["case", ["get", "is_unregistered"], "#18181b", "#ffffff"],
};

const INFRA_PAINT = {
  "circle-radius": 2.4,
  "circle-color": [
    "match", ["get", "kind"],
    ...Object.entries(INFRA_LEGEND).flatMap(([k, v]) => [k, v.color]),
    "#475569",
  ],
  "circle-opacity": 0.5,
};

export default function MapView({
  sources, infra, visibleClasses, showInfra, unregOnly,
  restrictIds, selectedId, onSelectSource, onCountChange,
}) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const [range, setRange] = useState(null);
  const [cursor, setCursor] = useState(null);
  const [timeFilter, setTimeFilter] = useState(false);

  // one-time map init; layer setup is idempotent so it survives style reloads
  useEffect(() => {
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: baseStyle(theme.get()),
      center: [80.0, 22.5],
      zoom: 3.7,
    });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");

    const ensureLayers = () => {
      if (!map.getSource("sources")) {
        map.addSource("sources", { type: "geojson", data: empty() });
        map.addLayer({ id: "sources", type: "circle", source: "sources", paint: SOURCE_PAINT });
        map.on("click", "sources", (e) => onSelectSource(e.features[0].properties.id));
        map.on("mouseenter", "sources", () => (map.getCanvas().style.cursor = "pointer"));
        map.on("mouseleave", "sources", () => (map.getCanvas().style.cursor = ""));
      }
      if (!map.getSource("infra")) {
        map.addSource("infra", { type: "geojson", data: empty() });
        map.addLayer(
          { id: "infra", type: "circle", source: "infra", paint: INFRA_PAINT },
          "sources"  // keep infra beneath the source dots
        );
        map.on("click", "infra", (e) => {
          const p = e.features[0].properties;
          new maplibregl.Popup({ closeButton: false, maxWidth: "220px" })
            .setLngLat(e.lngLat)
            .setHTML(
              `<div style="font:11px 'JetBrains Mono',ui-monospace,monospace">${
                p.name || "(unnamed)"
              }<br><span style="opacity:.6">${p.kind}</span></div>`
            )
            .addTo(map);
        });
      }
    };

    map.on("load", ensureLayers);
    map.on("styledata", ensureLayers);

    const onThemeChange = (e) => map.setStyle(baseStyle(e.detail));
    window.addEventListener("themechange", onThemeChange);

    return () => {
      window.removeEventListener("themechange", onThemeChange);
      map.remove();
    };
  }, [onSelectSource]);

  useEffect(() => {
    const f = sources?.features ?? [];
    if (!f.length) return;
    const a = Math.min(...f.map((x) => Date.parse(x.properties.first_seen)));
    const b = Math.max(...f.map((x) => Date.parse(x.properties.last_seen)));
    setRange([a, b]);
    setCursor((c) => c ?? b);
  }, [sources]);

  // fly to the selected source (e.g. clicked from the alerts list)
  useEffect(() => {
    if (selectedId == null) return;
    const feature = (sources?.features ?? []).find((f) => f.properties.id === selectedId);
    if (!feature) return;
    mapRef.current?.flyTo({ center: feature.geometry.coordinates, zoom: 10, duration: 1200 });
  }, [selectedId, sources]);

  const shownSources = useMemo(() => {
    const f = sources?.features ?? [];
    const allow = restrictIds ? new Set(restrictIds) : null;
    return f.filter((x) => {
      const p = x.properties;
      if (allow && !allow.has(p.id)) return false;
      if (unregOnly && !p.is_unregistered) return false;
      if (!visibleClasses.has(p.predicted_class ?? "unknown")) return false;
      if (timeFilter && cursor != null) {
        const s = Date.parse(p.first_seen), e = Date.parse(p.last_seen);
        if (!(s <= cursor && e >= cursor - 7 * DAY)) return false;
      }
      return true;
    });
  }, [sources, visibleClasses, unregOnly, restrictIds, timeFilter, cursor]);

  useEffect(() => {
    onCountChange?.(shownSources.length, sources?.features?.length ?? 0);
  }, [shownSources, sources, onCountChange]);

  // push data whenever it changes OR the style finishes (re)loading
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const s = map.getSource("sources");
      const i = map.getSource("infra");
      if (s) s.setData({ type: "FeatureCollection", features: shownSources });
      if (i) i.setData(showInfra ? infra ?? empty() : empty());
    };
    if (map.isStyleLoaded() && map.getSource("sources")) apply();
    else map.once("idle", apply);
  }, [shownSources, showInfra, infra]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      {range && (
        <div className="absolute inset-x-0 bottom-0 z-10 border-t border-zinc-200 bg-white/90 px-4 py-2.5 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/85">
          <div className="flex items-center gap-3 text-[11px] text-zinc-600 dark:text-zinc-400">
            <label className="flex shrink-0 cursor-pointer items-center gap-1.5">
              <input type="checkbox" checked={timeFilter}
                onChange={(e) => setTimeFilter(e.target.checked)}
                className="h-3 w-3 rounded-sm accent-amber-500 dark:accent-cyan-500" />
              date filter
            </label>
            <span className="font-mono tabular-nums">{fmtDay(range[0])}</span>
            <input
              type="range" min={range[0]} max={range[1]} step={DAY}
              value={cursor ?? range[1]} disabled={!timeFilter}
              onChange={(e) => setCursor(Number(e.target.value))}
              className="h-1 flex-1 cursor-pointer appearance-none rounded bg-zinc-200 accent-amber-500 disabled:opacity-40 dark:bg-zinc-800 dark:accent-cyan-500"
              aria-label="Active-date cursor"
            />
            <span className="font-mono tabular-nums">{fmtDay(range[1])}</span>
          </div>
          <div className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-500">
            {timeFilter
              ? <>active on <span className="font-mono text-zinc-800 dark:text-zinc-200">{fmtDay(cursor)}</span> (±7 days)</>
              : "showing all dates"}
          </div>
        </div>
      )}
    </div>
  );
}
