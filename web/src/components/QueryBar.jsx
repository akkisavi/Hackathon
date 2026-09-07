import { useState } from "react";
import { api } from "../lib/api.js";

export default function QueryBar({ onResult, onClear, active, exportParams }) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function submit(e) {
    e.preventDefault();
    if (!q.trim()) return;
    setBusy(true); setError(null);
    try {
      const r = await api.query(q.trim());
      const ids = (r.results?.features ?? []).map((f) => f.properties.id);
      onResult({ ids, summary: r.summary, interpreted: r.interpreted, count: ids.length });
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-3 border-b border-zinc-800 bg-zinc-950 px-4 py-2.5">
      <span className="text-[12px] font-semibold uppercase tracking-wider text-zinc-100">
        Thermal Source Monitor
      </span>
      <span className="text-[11px] text-zinc-600">NASA FIRMS · NTRO PS 26162</span>

      <form onSubmit={submit} className="ml-4 flex flex-1 items-center gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder='Ask: "persistent gas flares near refineries active over 6 months"'
          className="w-full rounded border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-[12px] text-zinc-200 placeholder:text-zinc-600 focus:border-amber-600 focus:outline-none"
        />
        <button
          type="submit" disabled={busy}
          className="shrink-0 rounded border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-[12px] text-zinc-200 hover:bg-zinc-700 disabled:opacity-50"
        >
          {busy ? "…" : "Query"}
        </button>
        {active && (
          <button type="button" onClick={() => { setQ(""); onClear(); }}
            className="shrink-0 rounded px-2 py-1.5 text-[12px] text-zinc-400 hover:text-zinc-200">
            clear
          </button>
        )}
      </form>

      {error && <span className="text-[11px] text-red-400">{error}</span>}

      <div className="flex shrink-0 items-center gap-1.5 text-[11px]">
        <span className="text-zinc-600">export</span>
        <a href={api.exportUrl({ ...exportParams, format: "geojson" })}
          className="rounded border border-zinc-800 px-2 py-1 text-zinc-300 hover:bg-zinc-900">GeoJSON</a>
        <a href={api.exportUrl({ ...exportParams, format: "kml" })}
          className="rounded border border-zinc-800 px-2 py-1 text-zinc-300 hover:bg-zinc-900">KML</a>
      </div>
    </div>
  );
}
