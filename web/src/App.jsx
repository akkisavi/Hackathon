import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./lib/api.js";
import { CLASS_KEYS } from "./lib/classes.js";
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
    <div className="flex h-screen w-screen flex-col bg-white text-zinc-800">
      <QueryBar
        active={!!query}
        exportParams={exportParams}
        onResult={(r) => { setQuery(r); setSelectedId(null); }}
        onClear={() => setQuery(null)}
      />

      <div className="relative flex min-h-0 flex-1">
        <LeftRail
          visibleClasses={visibleClasses}
          onToggleClass={toggleClass}
          onSetAllClasses={setAllClasses}
          showInfra={showInfra} onToggleInfra={setShowInfra} infraCounts={infraCounts}
          unregOnly={unregOnly} onToggleUnreg={setUnregOnly} unregCount={unregCount}
          totalCount={totalCount} highPriorityCount={highPriorityCount}
          classCounts={classCounts}
          alerts={alerts}
          onSelectAlert={setSelectedId}
        />

        <main className="relative min-w-0 flex-1">
          {loadError ? (
            <div className="grid h-full place-items-center p-6 text-center text-[13px] text-zinc-600">
              Couldn’t reach the API ({loadError}).<br />
              Start it with <code className="text-zinc-900">uvicorn app.main:app</code> on :8000.
            </div>
          ) : !sources ? (
            <div className="grid h-full place-items-center text-[13px] text-zinc-500">
              Loading thermal sources…
            </div>
          ) : (
            <MapView
              sources={sources}
              infra={infra}
              visibleClasses={visibleClasses}
              showInfra={showInfra}
              unregOnly={unregOnly}
              restrictIds={query?.ids}
              onSelectSource={setSelectedId}
              onCountChange={onCountChange}
            />
          )}

          {query && (
            <div className="absolute left-4 top-4 z-10 max-w-md rounded border border-zinc-200 bg-white/95 px-3 py-2 text-[12px] shadow-sm backdrop-blur">
              <div className="mb-1 flex items-center gap-2">
                <span className="font-semibold text-zinc-900">Query · {query.count} results</span>
                <span className="font-mono text-[11px] text-zinc-500">
                  {JSON.stringify(query.interpreted)}
                </span>
              </div>
              <p className="leading-snug text-zinc-600">{query.summary}</p>
            </div>
          )}

          <div className="absolute bottom-14 left-4 z-10 font-mono text-[11px] text-zinc-500 tabular-nums">
            {counts[0]} / {counts[1]} sources shown
          </div>
        </main>

        <DetailPanel sourceId={selectedId} onClose={() => setSelectedId(null)} />
      </div>
    </div>
  );
}
