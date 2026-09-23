import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { CLASS_LEGEND } from "../lib/classes.js";
import {
  priority, plainSummary, heatLevel, activityPattern, persistencePhrase, spreadPhrase,
  estimatedSpreadRadiusKm,
} from "../lib/humanize.js";

// Esri World Imagery export — same free provider already used for the basemap.
// bbox padded from the source's footprint so a large wildfire shows a wider
// patch than a tiny flare stack.
function satelliteImageUrl([lon, lat], areaKm2) {
  const halfKm = Math.max(0.5, Math.sqrt(areaKm2 || 0) * 1.5);
  const dLat = halfKm / 111;
  const dLon = halfKm / (111 * Math.cos((lat * Math.PI) / 180));
  const bbox = [lon - dLon, lat - dLat, lon + dLon, lat + dLat].join(",");
  return `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export?bbox=${bbox}&bboxSR=4326&imageSR=4326&size=400,260&format=png32&f=image`;
}

export default function DetailPanel({ sourceId, onClose }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [sendState, setSendState] = useState("idle"); // idle | sending | sent | error
  const [reportedBcm, setReportedBcm] = useState("");

  useEffect(() => {
    if (sourceId == null) return;
    setData(null); setError(null); setSendState("idle"); setReportedBcm("");
    let cancelled = false;
    api.source(sourceId)
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(String(e.message || e)));
    return () => { cancelled = true; };
  }, [sourceId]);

  async function handleSend() {
    setSendState("sending");
    try {
      const r = await api.sendAlert(sourceId);
      setSendState(r.sent ? "sent" : "error");
      if (!r.sent) setError(r.reason);
    } catch (e) {
      setSendState("error");
      setError(String(e.message || e));
    }
  }

  const open = sourceId != null;
  const p = data?.properties;
  const c = data?.classification;
  const legend = c ? CLASS_LEGEND[c.predicted_class] : null;
  const m = c ? { ...p, ...c } : p;
  const pri = c ? priority(m) : null;

  return (
    <div
      className={`absolute right-0 top-0 z-20 h-full w-[380px] transform border-l border-zinc-200 bg-white text-zinc-700 shadow-xl transition-transform duration-200 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-300 dark:shadow-[0_0_40px_-10px_rgba(0,0,0,0.6)] ${
        open ? "translate-x-0" : "translate-x-full"
      }`}
    >
      {open && (
        <div className="flex h-full flex-col">
          <header className="flex items-center justify-between border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
            <div className="font-mono text-[13px] text-zinc-900 dark:text-zinc-100">
              Source #{sourceId}
              {data?.geometry && (
                <span className="ml-2 text-[11px] text-zinc-500 dark:text-zinc-500">
                  {data.geometry.coordinates[1].toFixed(4)}, {data.geometry.coordinates[0].toFixed(4)}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleSend}
                disabled={sendState === "sending"}
                title="Temporary: emails ALERT_NOTIFY_EMAILS about this source now"
                className="rounded border border-amber-400 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-amber-700 transition hover:bg-amber-50 disabled:opacity-50 dark:border-amber-500/50 dark:text-amber-400 dark:hover:bg-amber-500/10"
              >
                {sendState === "sending" ? "Sending…" : sendState === "sent" ? "Sent ✓" : "Send alert"}
              </button>
              <button onClick={onClose} className="text-zinc-500 hover:text-zinc-800 dark:text-zinc-500 dark:hover:text-zinc-100" aria-label="Close">
                ✕
              </button>
            </div>
          </header>

          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
            {error && <p className="text-[12px] text-red-600 dark:text-red-400">{error}</p>}
            {!data && !error && <Skeleton />}

            {data && (
              <>
                {data.geometry && (
                  <Block label="Satellite view">
                    <img
                      src={satelliteImageUrl(data.geometry.coordinates, p?.bbox_area_km2)}
                      alt="Satellite imagery of this location"
                      className="w-full rounded border border-zinc-200 object-cover dark:border-zinc-800"
                      loading="lazy"
                    />
                    <p className="mt-1 text-[10px] text-zinc-500 dark:text-zinc-500">
                      Esri World Imagery — recent composite, not necessarily the detection date
                    </p>
                  </Block>
                )}

                {c ? (
                  <>
                    <div className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-sm" style={{ background: legend?.color }} />
                      <span className="text-[15px] font-semibold text-zinc-900 dark:text-zinc-100">
                        {legend?.label ?? c.predicted_class}
                      </span>
                      <span className="ml-auto font-mono text-[12px] text-zinc-500 tabular-nums dark:text-zinc-500">
                        {(c.confidence * 100).toFixed(0)}% · {c.method}
                      </span>
                    </div>

                    {pri && (
                      <div className="mt-3 flex items-start gap-2">
                        <span
                          className="mt-0.5 shrink-0 rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-white"
                          style={{ background: pri.color }}
                        >
                          {pri.label}
                        </span>
                        <span className="text-[12px] leading-snug text-zinc-600 dark:text-zinc-400">{pri.reason}</span>
                      </div>
                    )}

                    <Block label="In plain words">
                      <p className="mb-2.5 text-[12px] leading-relaxed text-zinc-700 dark:text-zinc-300">
                        {plainSummary(m, legend?.label)}
                      </p>
                      <dl className="space-y-1.5 text-[12px]">
                        <Plain k="Heat"
                          v={`${heatLevel(m.frp_mean)} (${Number(m.frp_mean).toFixed(1)} MW)`} />
                        <Plain k="When active" v={activityPattern(m.day_night_ratio)} />
                        <Plain k="How long" v={cap(persistencePhrase(m.span_days))} />
                        <Plain k="Location" v={spreadPhrase(m.bbox_growth_rate)} />
                        <Plain k="6-hr spread"
                          v={`~${estimatedSpreadRadiusKm(m).toFixed(2)} km radius (shown on map, orange dashed circle)`} />
                        {m.land_cover && (
                          <Plain k="Ground" v={cap(String(m.land_cover).replace(/_/g, " "))} />
                        )}
                        {m.burn_scar === "confirmed" && (
                          <Plain k="Satellite check" v="A real burn scar is visible from space" />
                        )}
                      </dl>
                    </Block>

                    {c.is_unregistered && (
                      <div className="mt-3 rounded border border-amber-400 bg-amber-50 px-3 py-2 text-[12px] text-amber-800 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-300">
                        <span className="font-semibold uppercase tracking-wide">Unregistered source</span>
                        <p className="mt-1 leading-snug text-amber-700 dark:text-amber-400">{c.unregistered_reason}</p>
                      </div>
                    )}

                    {c.estimated_bcm_per_year != null && (
                      <Block label="Emissions & impact (estimated from thermal output)">
                        <dl className="grid grid-cols-3 gap-x-2 gap-y-1.5 text-[12px]">
                          <Metric k="Gas flared" v={`${c.estimated_bcm_per_year.toFixed(3)} BCM/yr`} />
                          <Metric k="CO₂" v={`${Math.round(c.estimated_co2_tons_per_year).toLocaleString()} t/yr`} />
                          <Metric k="Value" v={`₹${(c.estimated_value_inr / 1e7).toFixed(2)} cr/yr`} />
                        </dl>

                        <div className="mt-3 flex items-center gap-2">
                          <label className="text-[11px] text-zinc-500 dark:text-zinc-500">
                            Facility self-reported (BCM/yr)
                          </label>
                          <input
                            type="number" step="0.001" min="0"
                            value={reportedBcm}
                            onChange={(e) => setReportedBcm(e.target.value)}
                            placeholder="from inspection log"
                            className="w-24 rounded border border-zinc-300 bg-white px-1.5 py-0.5 text-[11px] text-zinc-900 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
                          />
                        </div>

                        {reportedBcm !== "" && !Number.isNaN(Number(reportedBcm)) && (() => {
                          const reported = Number(reportedBcm);
                          const gap = c.estimated_bcm_per_year - reported;
                          return gap > 0.0005 ? (
                            <p className="mt-2 rounded border border-red-400 bg-red-50 px-2 py-1.5 text-[11px] font-medium text-red-700 dark:border-red-500/40 dark:bg-red-500/10 dark:text-red-400">
                              ⚠ Under-reporting detected: satellite estimate is{" "}
                              {reported > 0 ? `${(c.estimated_bcm_per_year / reported).toFixed(1)}× ` : ""}
                              higher than reported ({gap.toFixed(3)} BCM/yr unaccounted for).
                            </p>
                          ) : (
                            <p className="mt-2 text-[11px] text-emerald-600 dark:text-emerald-400">
                              ✓ Consistent with reported figure.
                            </p>
                          );
                        })()}
                      </Block>
                    )}

                    <Block label="Why">
                      <p className="text-[12px] leading-relaxed text-zinc-600 dark:text-zinc-400">{c.rationale}</p>
                    </Block>

                    {c.scores && (
                      <Block label="Class scores">
                        <div className="space-y-1">
                          {Object.entries(c.scores)
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 5)
                            .map(([k, v]) => (
                              <div key={k} className="flex items-center gap-2 text-[11px]">
                                <span className="w-28 shrink-0 text-zinc-500 dark:text-zinc-500">
                                  {CLASS_LEGEND[k]?.label ?? k}
                                </span>
                                <span className="h-1 flex-1 rounded bg-zinc-200 dark:bg-zinc-800">
                                  <span
                                    className="block h-full rounded bg-zinc-400 dark:bg-cyan-500"
                                    style={{ width: `${Math.min(100, v * 100)}%` }}
                                  />
                                </span>
                                <span className="w-8 text-right font-mono tabular-nums text-zinc-500 dark:text-zinc-500">
                                  {v.toFixed(2)}
                                </span>
                              </div>
                            ))}
                        </div>
                      </Block>
                    )}

                    {data.narrative && (
                      <Block label="Incident brief (AI)">
                        <p className="whitespace-pre-line text-[12px] leading-relaxed text-zinc-700 dark:text-zinc-300">
                          {data.narrative}
                        </p>
                      </Block>
                    )}
                  </>
                ) : (
                  <p className="text-[12px] text-zinc-500 dark:text-zinc-500">Not classified yet.</p>
                )}

                <details className="mt-4 border-t border-zinc-200 pt-3 dark:border-zinc-800">
                  <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wider text-zinc-500 hover:text-zinc-800 dark:text-zinc-500 dark:hover:text-zinc-100">
                    Technical details
                  </summary>

                <Block label="Site">
                  <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[12px]">
                    <Metric k="Land cover" v={(p.land_cover || "not sampled").replace(/_/g, " ")} />
                    <Metric k="Coordinates"
                      v={`${data.geometry.coordinates[1].toFixed(3)}, ${data.geometry.coordinates[0].toFixed(3)}`} />
                    {p.burn_scar && (
                      <Metric
                        k="Sentinel-2 burn scar"
                        v={`${p.burn_scar} (dNBR ${p.dnbr})`}
                      />
                    )}
                  </dl>
                </Block>

                <Block label="Lifecycle">
                  <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[12px]">
                    <Metric k="First seen" v={String(p.first_seen).slice(0, 10)} />
                    <Metric k="Last seen" v={String(p.last_seen).slice(0, 10)} />
                    <Metric k="Span (days)" v={p.span_days} />
                    <Metric k="Seen on (days)" v={p.recurrence_days} />
                    <Metric k="Detections" v={p.detection_count} />
                    <Metric k="Day/night" v={p.day_night_ratio} />
                    <Metric k="FRP mean (MW)" v={Number(p.frp_mean).toFixed(1)} />
                    <Metric k="FRP trend (MW/d)" v={p.frp_trend} />
                    <Metric k="Footprint (km²)" v={p.bbox_area_km2} />
                    <Metric k="Growth (km²/d)" v={p.bbox_growth_rate} />
                  </dl>
                </Block>
                </details>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Block({ label, children }) {
  return (
    <div className="mt-4 border-t border-zinc-200 pt-3 dark:border-zinc-800">
      <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-500">
        {label}
      </div>
      {children}
    </div>
  );
}

function Metric({ k, v }) {
  return (
    <div className="flex justify-between">
      <dt className="text-zinc-500 dark:text-zinc-500">{k}</dt>
      <dd className="font-mono tabular-nums text-zinc-900 dark:text-zinc-100">{String(v)}</dd>
    </div>
  );
}

// Plain-language row: label on the left, a readable sentence on the right.
function Plain({ k, v }) {
  return (
    <div className="flex gap-3">
      <dt className="w-24 shrink-0 text-zinc-500 dark:text-zinc-500">{k}</dt>
      <dd className="text-zinc-800 dark:text-zinc-300">{v}</dd>
    </div>
  );
}

const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

function Skeleton() {
  return (
    <div className="space-y-2">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="h-4 animate-pulse rounded bg-zinc-200 dark:bg-zinc-800" style={{ width: `${90 - i * 8}%` }} />
      ))}
    </div>
  );
}
