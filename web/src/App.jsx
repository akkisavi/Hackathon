import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./lib/api.js";
import { CLASS_KEYS, CLASS_LEGEND } from "./lib/classes.js";
import { priority } from "./lib/humanize.js";
import MapView from "./components/MapView.jsx";
import LeftRail from "./components/LeftRail.jsx";
import DetailPanel from "./components/DetailPanel.jsx";
import QueryBar from "./components/QueryBar.jsx";

export default function App() {
  const [sources, setSources] = useState(null);
  const [infra, setInfra] = useState(null);
  const [infraCounts, setInfraCounts] = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [loadError, setLoadError] = useState(null);

  const [visibleClasses, setVisibleClasses] = useState(new Set(CLASS_KEYS));
  const [showInfra, setShowInfra] = useState(false);
  const [unregOnly, setUnregOnly] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [query, setQuery] = useState(null);
  const [counts, setCounts] = useState([0, 0]);

  useEffect(() => {
    Promise.all([api.sources(), api.infraCounts(), api.alerts()])
      .then(([s, ic, al]) => {
        setSources(s); setInfraCounts(ic); setAlerts(al.alerts);
      })
      .catch((e) => setLoadError(String(e.message || e)));
  }, []);

  // infra features load lazily the first time the layer is switched on
  useEffect(() => {
    if (showInfra && !infra) api.infra({ limit: 12000 }).then(setInfra).catch(() => {});
  }, [showInfra, infra]);

  const classCounts = useMemo(() => {
    const t = {};
    for (const f of sources?.features ?? []) {
      const k = f.properties.predicted_class ?? "unknown";
      t[k] = (t[k] ?? 0) + 1;
    }
    return t;
  }, [sources]);

  const unregCount = useMemo(
    () => (sources?.features ?? []).filter((f) => f.properties.is_unregistered).length,
    [sources]
  );
  const highPriorityCount = useMemo(
    () => (sources?.features ?? []).filter((f) => priority(f.properties).level === "high").length,
    [sources]
  );
  const totalCount = sources?.features?.length ?? 0;

  // Regulatory-auditor headline: gas actually being flared, estimated from
  // thermal output (FRP), not self-reported by the facility.
  const flareImpact = useMemo(() => {
    let bcm = 0, co2 = 0, inr = 0, unregInr = 0;
    for (const f of sources?.features ?? []) {
      const p = f.properties;
      if (!p.estimated_value_inr) continue;
      bcm += p.estimated_bcm_per_year || 0;
      co2 += p.estimated_co2_tons_per_year || 0;
      inr += p.estimated_value_inr || 0;
      if (p.is_unregistered) unregInr += p.estimated_value_inr || 0;
    }
    return { bcm, co2, inr, unregInr };
  }, [sources]);

  const toggleClass = useCallback((k) => {
    setVisibleClasses((prev) => {
      const n = new Set(prev);
      n.has(k) ? n.delete(k) : n.add(k);
      return n;
    });
  }, []);
  const setAllClasses = useCallback(
    (on) => setVisibleClasses(on ? new Set(CLASS_KEYS) : new Set()), []
  );
  const onCountChange = useCallback((shown, total) => setCounts([shown, total]), []);

  const exportParams = {
    predicted_class: visibleClasses.size === 1 ? [...visibleClasses][0] : undefined,
    unregistered_only: unregOnly || undefined,
  };

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-white text-zinc-800 dark:bg-zinc-950 dark:text-zinc-200">
      <QueryBar
        active={!!query}
        exportParams={exportParams}
        onResult={(r) => { setQuery(r); setSelectedId(null); }}
        onClear={() => setQuery(null)}
        alerts={alerts}
        onSelectAlert={setSelectedId}
      />

      <div className="relative flex min-h-0 flex-1 overflow-hidden">
        <LeftRail
          visibleClasses={visibleClasses}
          onToggleClass={toggleClass}
          onSetAllClasses={setAllClasses}
          showInfra={showInfra} onToggleInfra={setShowInfra} infraCounts={infraCounts}
          unregOnly={unregOnly} onToggleUnreg={setUnregOnly} unregCount={unregCount}
          totalCount={totalCount} highPriorityCount={highPriorityCount}
          flareImpact={flareImpact}
          classCounts={classCounts}
          alerts={alerts}
          onSelectAlert={setSelectedId}
        />

        <main className="relative min-w-0 flex-1">
          {loadError ? (
            <div className="grid h-full place-items-center p-6 text-center text-[13px] text-zinc-600 dark:text-zinc-400">
              Couldn’t reach the API ({loadError}).<br />
              Start it with <code className="text-zinc-900 dark:text-zinc-100">uvicorn app.main:app</code> on :8000.
            </div>
          ) : !sources ? (
            <div className="grid h-full place-items-center text-[13px] text-zinc-500 dark:text-zinc-500">
              <span className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500 dark:bg-cyan-400" />
                Loading thermal sources…
              </span>
            </div>
          ) : (
            <MapView
              sources={sources}
              infra={infra}
              visibleClasses={visibleClasses}
              showInfra={showInfra}
              unregOnly={unregOnly}
              restrictIds={query?.ids}
              selectedId={selectedId}
              onSelectSource={setSelectedId}
              onCountChange={onCountChange}
            />
          )}

          {query && (
            <details open className="absolute left-4 top-4 z-10 max-w-md rounded border border-zinc-200 bg-white/95 text-[12px] shadow-sm backdrop-blur dark:border-zinc-800 dark:bg-zinc-900/95">
              <summary className="cursor-pointer list-none px-3 py-2">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-zinc-900 dark:text-zinc-100">Query · {query.count} results</span>
                  <span className="font-mono text-[11px] text-zinc-500 dark:text-zinc-500">
                    {JSON.stringify(query.interpreted)}
                  </span>
                </div>
                <p className="mt-1 leading-snug text-zinc-600 dark:text-zinc-400">{query.summary}</p>
              </summary>

              {query.features?.length > 0 && (
                <div className="max-h-64 overflow-y-auto border-t border-zinc-200 dark:border-zinc-800">
                  {query.features.map((f) => {
                    const p = f.properties;
                    const legend = CLASS_LEGEND[p.predicted_class];
                    return (
                      <button
                        key={p.id}
                        onClick={() => setSelectedId(p.id)}
                        className={`flex w-full items-center gap-2 px-3 py-1.5 text-left transition hover:bg-zinc-100 dark:hover:bg-zinc-800 ${
                          selectedId === p.id ? "bg-zinc-100 dark:bg-zinc-800" : ""
                        }`}
                      >
                        <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: legend?.color ?? "#a1a1aa" }} />
                        <span className="text-zinc-800 dark:text-zinc-200">{legend?.label ?? p.predicted_class ?? "unclassified"}</span>
                        {p.is_unregistered && (
                          <span className="rounded bg-amber-100 px-1 text-[10px] font-semibold uppercase text-amber-700 dark:bg-amber-500/20 dark:text-amber-400">unreg</span>
                        )}
                        <span className="ml-auto font-mono text-[11px] text-zinc-500 dark:text-zinc-500">#{p.id}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </details>
          )}

          <div className="absolute bottom-14 left-4 z-10 rounded bg-white/80 px-2 py-1 font-mono text-[11px] text-zinc-500 tabular-nums backdrop-blur dark:bg-zinc-950/80 dark:text-zinc-500">
            {counts[0]} / {counts[1]} sources shown
          </div>
        </main>

        <DetailPanel sourceId={selectedId} onClose={() => setSelectedId(null)} />
      </div>
    </div>
  );
}
