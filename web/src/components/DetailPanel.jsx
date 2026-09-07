import { useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { CLASS_LEGEND } from "../lib/classes.js";

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

  return (
    <div
      className={`absolute right-0 top-0 z-20 h-full w-[380px] transform border-l border-zinc-800 bg-zinc-950 text-zinc-300 transition-transform duration-200 ${
        open ? "translate-x-0" : "translate-x-full"
      }`}
    >
      {open && (
        <div className="flex h-full flex-col">
          <header className="flex items-center justify-between border-b border-zinc-800 px-4 py-3">
            <div className="font-mono text-[13px] text-zinc-100">
              Source #{sourceId}
              {data?.geometry && (
                <span className="ml-2 text-[11px] text-zinc-500">
                  {data.geometry.coordinates[1].toFixed(4)}, {data.geometry.coordinates[0].toFixed(4)}
                </span>
              )}
            </div>
            <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200" aria-label="Close">
              ✕
            </button>
          </header>

          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
            {error && <p className="text-[12px] text-red-400">{error}</p>}
            {!data && !error && <Skeleton />}

            {data && (
              <>
                {c ? (
                  <>
                    <div className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-sm" style={{ background: legend?.color }} />
                      <span className="text-[15px] font-semibold text-zinc-100">
                        {legend?.label ?? c.predicted_class}
                      </span>
                      <span className="ml-auto font-mono text-[12px] text-zinc-400 tabular-nums">
                        {(c.confidence * 100).toFixed(0)}% · {c.method}
                      </span>
                    </div>

                    {c.is_unregistered && (
                      <div className="mt-3 rounded border border-amber-600/40 bg-amber-950/30 px-3 py-2 text-[12px] text-amber-200">
                        <span className="font-semibold uppercase tracking-wide">Unregistered source</span>
                        <p className="mt-1 leading-snug text-amber-200/80">{c.unregistered_reason}</p>
                      </div>
                    )}

                    <Block label="Why">
                      <p className="text-[12px] leading-relaxed text-zinc-400">{c.rationale}</p>
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
                                <span className="h-1 flex-1 rounded bg-zinc-900">
                                  <span
                                    className="block h-full rounded bg-zinc-600"
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
                        <p className="whitespace-pre-line text-[12px] leading-relaxed text-zinc-300">
                          {data.narrative}
                        </p>
                      </Block>
                    )}
                  </>
                ) : (
                  <p className="text-[12px] text-zinc-500">Not classified yet.</p>
                )}

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
    <div className="mt-4 border-t border-zinc-800 pt-3">
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
      <dd className="font-mono tabular-nums text-zinc-200">{String(v)}</dd>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="space-y-2">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="h-4 animate-pulse rounded bg-zinc-900" style={{ width: `${90 - i * 8}%` }} />
      ))}
    </div>
  );
}
