import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api.js";
import { auth } from "../lib/auth.js";
import { CLASS_LEGEND } from "../lib/classes.js";
import ThemeToggle from "./ThemeToggle.jsx";

export default function QueryBar({ onResult, onClear, active, exportParams, alerts, onSelectAlert }) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [user, setUser] = useState(auth.getUser());
  const navigate = useNavigate();
  const bellRef = useRef(null);

  function pickAlert(sourceId) {
    if (bellRef.current) bellRef.current.open = false;
    onSelectAlert?.(sourceId);
  }

  // older sessions logged in before role-caching existed have a token but no
  // cached user — fetch it once so the Admin button appears without re-login
  useEffect(() => {
    if (!user) api.me().then((u) => { auth.setUser(u); setUser(u); }).catch(() => {});
  }, [user]);

  function logout() {
    auth.clear();
    navigate("/login", { replace: true });
  }

  async function submit(e) {
    e.preventDefault();
    if (!q.trim()) return;
    setBusy(true); setError(null);
    try {
      const r = await api.query(q.trim());
      const features = r.results?.features ?? [];
      onResult({
        ids: features.map((f) => f.properties.id),
        features,
        summary: r.summary, interpreted: r.interpreted, count: features.length,
      });
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-3 border-b border-zinc-200 bg-white px-4 py-2.5 dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-500 dark:bg-cyan-400 dark:shadow-[0_0_8px_2px_rgba(34,211,238,0.7)]" />
        <span className="font-display text-[12px] font-semibold uppercase tracking-wider text-zinc-900 dark:text-zinc-100">
          Thermal Source Monitor
        </span>
      </div>
      <span className="hidden text-[11px] text-zinc-400 dark:text-zinc-600 sm:inline">NASA FIRMS · NTRO PS 26162</span>

      <form onSubmit={submit} className="ml-4 flex flex-1 items-center gap-2">
        <div className="relative w-full">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            disabled={busy}
            placeholder='Ask: "persistent gas flares near refineries active over 6 months"'
            className="w-full rounded border border-zinc-300 bg-zinc-50 px-3 py-1.5 pr-8 text-[12px] text-zinc-800 placeholder:text-zinc-400 outline-none transition focus:border-amber-500 focus:bg-white disabled:opacity-70 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:placeholder:text-zinc-600 dark:focus:border-cyan-500 dark:focus:bg-zinc-900"
          />
          {busy && (
            <svg
              className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 animate-spin text-amber-500 dark:text-cyan-400"
              viewBox="0 0 24 24" fill="none"
            >
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          )}
        </div>
        <button
          type="submit" disabled={busy}
          className="flex shrink-0 items-center gap-1.5 rounded border border-zinc-300 bg-zinc-100 px-3 py-1.5 text-[12px] font-medium text-zinc-800 transition hover:bg-zinc-200 disabled:cursor-wait disabled:opacity-70 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:hover:bg-zinc-700"
        >
          {busy && (
            <svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          )}
          {busy ? "Searching…" : "Query"}
        </button>
        {active && (
          <button type="button" onClick={() => { setQ(""); onClear(); }}
            className="shrink-0 rounded px-2 py-1.5 text-[12px] text-zinc-500 hover:text-zinc-800 dark:text-zinc-500 dark:hover:text-zinc-100">
            clear
          </button>
        )}
      </form>

      {error && <span className="text-[11px] text-red-600 dark:text-red-400">{error}</span>}

      <div className="flex shrink-0 items-center gap-1.5 text-[11px]">
        <span className="hidden text-zinc-400 dark:text-zinc-600 sm:inline">export</span>
        <a href={api.exportUrl({ ...exportParams, format: "geojson" })}
          className="rounded border border-zinc-300 px-2 py-1 text-zinc-700 transition hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800">GeoJSON</a>
        <a href={api.exportUrl({ ...exportParams, format: "kml" })}
          className="rounded border border-zinc-300 px-2 py-1 text-zinc-700 transition hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800">KML</a>
      </div>

      <details ref={bellRef} className="relative shrink-0">
        <summary className="flex list-none cursor-pointer items-center justify-center rounded border border-zinc-300 p-1.5 text-zinc-700 transition hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800">
          <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
            <path d="M12 22a2.2 2.2 0 0 0 2.2-2.2h-4.4A2.2 2.2 0 0 0 12 22Zm8-6.2v-.6l-1.8-1.8v-4.8a6.2 6.2 0 0 0-5-6.1V2h-2.4v.5a6.2 6.2 0 0 0-5 6.1v4.8L4 15.2v.6Z" />
          </svg>
          {alerts?.length > 0 && (
            <span className="absolute -right-1.5 -top-1.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-600 px-1 text-[9px] font-bold leading-none text-white">
              {alerts.length}
            </span>
          )}
        </summary>
        <div className="absolute right-0 top-full z-30 mt-1.5 w-72 rounded border border-zinc-200 bg-white shadow-lg dark:border-zinc-800 dark:bg-zinc-900">
          <div className="max-h-80 divide-y divide-zinc-200 overflow-y-auto dark:divide-zinc-800">
            {(alerts ?? []).map((a) => (
              <button
                key={a.source_id}
                onClick={() => pickAlert(a.source_id)}
                className="flex w-full flex-col gap-0.5 px-3 py-2 text-left transition hover:bg-zinc-100 dark:hover:bg-zinc-800"
              >
                <div className="flex items-center gap-2 text-[12px]">
                  <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                    a.severity === "unregistered" ? "bg-amber-500 dark:bg-amber-400" : "bg-zinc-400 dark:bg-zinc-600"}`} />
                  <span className="font-medium text-zinc-900 dark:text-zinc-100">
                    {CLASS_LEGEND[a.predicted_class]?.label ?? a.predicted_class ?? "unclassified"}
                  </span>
                  <span className="ml-auto shrink-0 font-mono text-[10px] uppercase text-zinc-500 dark:text-zinc-500">
                    {a.severity}
                  </span>
                </div>
                <div className="pl-3.5 text-[11px] leading-snug text-zinc-500 dark:text-zinc-500">{a.reason}</div>
              </button>
            ))}
            {alerts && alerts.length === 0 && (
              <p className="px-3 py-3 text-[12px] text-zinc-400 dark:text-zinc-600">No active alerts.</p>
            )}
            {!alerts && <p className="px-3 py-3 text-[12px] text-zinc-400 dark:text-zinc-600">Loading…</p>}
          </div>
        </div>
      </details>

      <div className="flex shrink-0 items-center gap-1.5 border-l border-zinc-200 pl-3 text-[11px] dark:border-zinc-800">
        {user?.role === "admin" && (
          <button onClick={() => navigate("/admin")}
            className="rounded border border-zinc-300 px-2 py-1 font-medium text-zinc-700 transition hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800">
            Admin
          </button>
        )}
        <button onClick={() => navigate("/profile")}
          className="rounded border border-zinc-300 px-2 py-1 font-medium text-zinc-700 transition hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800">
          Profile
        </button>
        <button onClick={logout}
          className="rounded border border-zinc-300 px-2 py-1 text-zinc-700 transition hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800">
          Logout
        </button>
        <ThemeToggle />
      </div>
    </div>
  );
}
