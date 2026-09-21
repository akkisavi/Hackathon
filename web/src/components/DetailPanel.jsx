import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { CLASS_LEGEND } from "../lib/classes.js";
import {
  priority, plainSummary, heatLevel, activityPattern, persistencePhrase, spreadPhrase,
} from "../lib/humanize.js";

export default function DetailPanel({ sourceId, onClose }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (sourceId == null) return;
    setData(null); setError(null);
    let cancelled = false;
    api.source(sourceId)
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(String(e.message || e)));
    return () => { cancelled = true; };
  }, [sourceId]);

  const open = sourceId != null;
  const p = data?.properties;
  const c = data?.classification;
  const legend = c ? CLASS_LEGEND[c.predicted_class] : null;
  const m = c ? { ...p, ...c } : p;
  const pri = c ? priority(m) : null;

  return (
    <div
      className={`absolute right-0 top-0 z-20 h-full w-[380px] transform border-l border-zinc-200 bg-white text-zinc-700 transition-transform duration-200 ${
        open ? "translate-x-0" : "translate-x-full"
      }`}
    >
      {open && (
        <div className="flex h-full flex-col">
          <header className="flex items-center justify-between border-b border-zinc-200 px-4 py-3">
            <div className="font-mono text-[13px] text-zinc-900">
              Source #{sourceId}
              {data?.geometry && (
                <span className="ml-2 text-[11px] text-zinc-500">
                  {data.geometry.coordinates[1].toFixed(4)}, {data.geometry.coordinates[0].toFixed(4)}
                </span>
              )}
            </div>
            <button onClick={onClose} className="text-zinc-500 hover:text-zinc-800" aria-label="Close">
              ✕
            </button>
          </header>

          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
            {error && <p className="text-[12px] text-red-600">{error}</p>}
            {!data && !error && <Skeleton />}

            {data && (
              <>
                {c ? (
                  <>
                    <div className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-sm" style={{ background: legend?.color }} />
                      <span className="text-[15px] font-semibold text-zinc-900">
                        {legend?.label ?? c.predicted_class}
                      </span>
                      <span className="ml-auto font-mono text-[12px] text-zinc-500 tabular-nums">
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
                        <span className="text-[12px] leading-snug text-zinc-600">{pri.reason}</span>
                      </div>
                    )}

                    <Block label="In plain words">
                      <p className="mb-2.5 text-[12px] leading-relaxed text-zinc-700">
                        {plainSummary(m, legend?.label)}
                      </p>
                      <dl className="space-y-1.5 text-[12px]">
                        <Plain k="Heat"
                          v={`${heatLevel(m.frp_mean)} (${Number(m.frp_mean).toFixed(1)} MW)`} />
                        <Plain k="When active" v={activityPattern(m.day_night_ratio)} />
                        <Plain k="How long" v={cap(persistencePhrase(m.span_days))} />
                        <Plain k="Location" v={spreadPhrase(m.bbox_growth_rate)} />
                        {m.land_cover && (
                          <Plain k="Ground" v={cap(String(m.land_cover).replace(/_/g, " "))} />
                        )}
                        {m.burn_scar === "confirmed" && (
                          <Plain k="Satellite check" v="A real burn scar is visible from space" />
                        )}
                      </dl>
                    </Block>

                    {c.is_unregistered && (
                      <div className="mt-3 rounded border border-amber-400 bg-amber-50 px-3 py-2 text-[12px] text-amber-800">
                        <span className="font-semibold uppercase tracking-wide">Unregistered source</span>
                        <p className="mt-1 leading-snug text-amber-700">{c.unregistered_reason}</p>
                      </div>
                    )}

                    <Block label="Why">
                      <p className="text-[12px] leading-relaxed text-zinc-600">{c.rationale}</p>
                    </Block>

                    {c.scores && (
                      <Block label="Class scores">
                        <div className="space-y-1">
                          {Object.entries(c.scores)
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 5)
                            .map(([k, v]) => (
                              <div key={k} className="flex items-center gap-2 text-[11px]">
                                <span className="w-28 shrink-0 text-zinc-500">
                                  {CLASS_LEGEND[k]?.label ?? k}
                                </span>
                                <span className="h-1 flex-1 rounded bg-zinc-200">
                                  <span
                                    className="block h-full rounded bg-zinc-400"
                                    style={{ width: `${Math.min(100, v * 100)}%` }}
                                  />
                                </span>
                                <span className="w-8 text-right font-mono tabular-nums text-zinc-500">
                                  {v.toFixed(2)}
                                </span>
                              </div>
                            ))}
                        </div>
                      </Block>
                    )}

                    {data.narrative && (
                      <Block label="Incident brief (AI)">
                        <p className="whitespace-pre-line text-[12px] leading-relaxed text-zinc-700">
                          {data.narrative}
                        </p>
                      </Block>
                    )}
                  </>
                ) : (
                  <p className="text-[12px] text-zinc-500">Not classified yet.</p>
                )}

                <details className="mt-4 border-t border-zinc-200 pt-3">
                  <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wider text-zinc-500 hover:text-zinc-800">
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
    <div className="mt-4 border-t border-zinc-200 pt-3">
      <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
        {label}
      </div>
      {children}
    </div>
  );
}

function Metric({ k, v }) {
  return (
    <div className="flex justify-between">
      <dt className="text-zinc-500">{k}</dt>
      <dd className="font-mono tabular-nums text-zinc-900">{String(v)}</dd>
    </div>
  );
}

// Plain-language row: label on the left, a readable sentence on the right.
function Plain({ k, v }) {
  return (
    <div className="flex gap-3">
      <dt className="w-24 shrink-0 text-zinc-500">{k}</dt>
      <dd className="text-zinc-800">{v}</dd>
    </div>
  );
}

const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

function Skeleton() {
  return (
    <div className="space-y-2">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="h-4 animate-pulse rounded bg-zinc-200" style={{ width: `${90 - i * 8}%` }} />
      ))}
    </div>
  );
}
