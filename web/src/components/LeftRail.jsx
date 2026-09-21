import { CLASS_KEYS, CLASS_LEGEND, INFRA_LEGEND } from "../lib/classes.js";

export default function LeftRail({
  visibleClasses, onToggleClass, onSetAllClasses,
  showInfra, onToggleInfra, infraCounts,
  unregOnly, onToggleUnreg, unregCount,
  totalCount, highPriorityCount,
  classCounts, alerts, onSelectAlert,
}) {
  const allOn = visibleClasses.size === CLASS_KEYS.length;

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-zinc-200 bg-zinc-50 text-zinc-700">
      <Section title="Overview">
        <div className="grid grid-cols-3 gap-2">
          <Stat n={totalCount} label="Heat sources" />
          <Stat n={highPriorityCount} label="High priority" color="#dc2626" />
          <Stat n={unregCount} label="Unregistered" color="#d97706" />
        </div>
      </Section>

      <Section title="Layers">
        <Toggle checked={showInfra} onChange={onToggleInfra}
          label="Industrial infrastructure"
          hint={infraCounts ? `${infraCounts.total.toLocaleString()} features` : null} />
        {showInfra && (
          <div className="mt-1.5 space-y-1 pl-6">
            {Object.entries(INFRA_LEGEND).map(([k, v]) => (
              <LegendRow key={k} color={v.color} label={v.label}
                count={infraCounts?.by_kind?.[k]} dim />
            ))}
          </div>
        )}
        <Toggle checked={unregOnly} onChange={onToggleUnreg}
          label="Unregistered only"
          hint={unregCount != null ? `${unregCount} flagged` : null} accent />
      </Section>

      <Section title="Source class"
        action={
          <button onClick={() => onSetAllClasses(!allOn)}
            className="text-[11px] text-zinc-500 hover:text-zinc-800">
            {allOn ? "none" : "all"}
          </button>
        }>
        <div className="space-y-0.5">
          {CLASS_KEYS.map((k) => (
            <button key={k} onClick={() => onToggleClass(k)}
              className="flex w-full items-center gap-2 rounded px-1.5 py-1 text-left text-[12px] hover:bg-zinc-100">
              <span className="h-2.5 w-2.5 shrink-0 rounded-sm"
                style={{ background: CLASS_LEGEND[k].color,
                         opacity: visibleClasses.has(k) ? 1 : 0.25 }} />
              <span className={visibleClasses.has(k) ? "" : "text-zinc-400"}>
                {CLASS_LEGEND[k].label}
              </span>
              <span className="ml-auto font-mono text-[11px] text-zinc-500 tabular-nums">
                {classCounts?.[k] ?? 0}
              </span>
            </button>
          ))}
        </div>
      </Section>

      <Section title="Alerts" grow
        action={<span className="font-mono text-[11px] text-zinc-500">{alerts?.length ?? 0}</span>}>
        <div className="-mx-1 divide-y divide-zinc-200 overflow-y-auto">
          {(alerts ?? []).map((a) => (
            <button key={a.source_id} onClick={() => onSelectAlert(a.source_id)}
              className="flex w-full flex-col gap-0.5 px-1 py-2 text-left hover:bg-zinc-100">
              <div className="flex items-center gap-2 text-[12px]">
                <span className={`h-1.5 w-1.5 rounded-full ${
                  a.severity === "unregistered" ? "bg-amber-500" : "bg-zinc-400"}`} />
                <span className="font-medium">
                  {CLASS_LEGEND[a.predicted_class]?.label ?? a.predicted_class ?? "unclassified"}
                </span>
                <span className="ml-auto font-mono text-[10px] uppercase text-zinc-500">
                  {a.severity}
                </span>
              </div>
              <div className="pl-3.5 text-[11px] leading-snug text-zinc-500">{a.reason}</div>
            </button>
          ))}
          {alerts && alerts.length === 0 && (
            <p className="px-1 py-3 text-[12px] text-zinc-400">No active alerts.</p>
          )}
        </div>
      </Section>
    </aside>
  );
}

function Stat({ n, label, color }) {
  return (
    <div className="rounded border border-zinc-200 bg-white px-2 py-1.5">
      <div className="font-mono text-[18px] font-semibold tabular-nums leading-none"
        style={{ color: color ?? "#18181b" }}>
        {(n ?? 0).toLocaleString()}
      </div>
      <div className="mt-1 text-[10px] leading-tight text-zinc-500">{label}</div>
    </div>
  );
}

function Section({ title, action, children, grow }) {
  return (
    <div className={`border-b border-zinc-200 px-3 py-3 ${grow ? "flex min-h-0 flex-1 flex-col" : ""}`}>
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">{title}</h2>
        {action}
      </div>
      <div className={grow ? "min-h-0 flex-1" : ""}>{children}</div>
    </div>
  );
}

function Toggle({ checked, onChange, label, hint, accent }) {
  return (
    <label className="flex cursor-pointer items-center gap-2 py-1 text-[12px]">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)}
        className={`h-3.5 w-3.5 rounded-sm border-zinc-300 bg-white ${accent ? "accent-amber-500" : "accent-zinc-600"}`} />
      <span>{label}</span>
      {hint && <span className="ml-auto font-mono text-[11px] text-zinc-500 tabular-nums">{hint}</span>}
    </label>
  );
}

function LegendRow({ color, label, count, dim }) {
  return (
    <div className={`flex items-center gap-2 text-[11px] ${dim ? "text-zinc-500" : ""}`}>
      <span className="h-2 w-2 rounded-sm" style={{ background: color }} />
      <span>{label}</span>
      {count != null && <span className="ml-auto font-mono tabular-nums">{count.toLocaleString()}</span>}
    </div>
  );
}
