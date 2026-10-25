import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import MapView from "../components/MapView.jsx";
import { CLASS_KEYS, CLASS_LEGEND } from "../lib/classes.js";
import { changeRequest } from "../lib/changeApi.js";
import "../orbit.css";

export default function ThermalSnapshot() {
  const [sources, setSources] = useState(null);
  const [error, setError] = useState("");
  const [visible, setVisible] = useState(new Set(CLASS_KEYS));
  const [selected, setSelected] = useState(null);
  const [unregistered, setUnregistered] = useState(false);
  const [counts, setCounts] = useState([0, 0]);
  const countChange = useCallback((shown, total) => setCounts([shown, total]), []);
  useEffect(() => {
    const controller = new AbortController();
    changeRequest("/thermal", { signal: controller.signal }).then(setSources).catch(e => {
      if (e.name !== "AbortError") setError("Start the localhost fixture server to inspect the bundled thermal snapshot.");
    });
    return () => controller.abort();
  }, []);
  const chosen = sources?.features.find(f => f.properties.id === selected);
  const p = chosen?.properties;

  return <div className="od-app">
    <header className="od-header"><Link className="od-brand" to="/orbit">ORBIT<span className="od-brand-delta">DELTA</span></Link><span className="od-eyebrow">THERMAL MONITORING / HISTORICAL SNAPSHOT</span><Link to="/orbit">← Image inspector</Link></header>
    <div className="od-thermal-layout">
      <aside className="od-sidebar"><div className="od-section-label">SOURCE CLASSES</div><p className="od-muted" style={{ margin: "15px 0" }}>Existing classifications from the bundled project snapshot. Not live data.</p>
        {CLASS_KEYS.map(key => <label key={key} className="od-thermal-filter"><input type="checkbox" checked={visible.has(key)} onChange={() => setVisible(previous => { const next = new Set(previous); next.has(key) ? next.delete(key) : next.add(key); return next; })}/><span style={{ background: CLASS_LEGEND[key].color }}/>{CLASS_LEGEND[key].label}</label>)}
        <label className="od-thermal-filter"><input type="checkbox" checked={unregistered} onChange={e => setUnregistered(e.target.checked)}/>Unregistered only</label>
        <p className="od-muted" style={{ marginTop: 20 }}>{counts[0].toLocaleString()} / {counts[1].toLocaleString()} sources shown</p>
        <Link className="od-upload-button" to="/">Open original live application →</Link>
      </aside>
      <main className="od-thermal-map">{sources ? <MapView sources={sources} infra={null} visibleClasses={visible} showInfra={false} unregOnly={unregistered} selectedId={selected} onSelectSource={setSelected} onCountChange={countChange}/> : <div className="od-empty">{error || "Reading bundled thermal records…"}</div>}</main>
      <aside className="od-inspector"><div className="od-inspector-title">Source evidence</div><section className="od-assessment">{p ? <><div className="od-eyebrow">SOURCE #{p.id}</div><h3>{CLASS_LEGEND[p.predicted_class]?.label ?? "Unclassified"}</h3><p className="od-observation">{p.rationale}</p><div className="od-metric-row"><span>Detections</span><strong>{p.detection_count}</strong></div><div className="od-metric-row"><span>First seen</span><strong>{p.first_seen.slice(0,10)}</strong></div><div className="od-metric-row"><span>Last seen</span><strong>{p.last_seen.slice(0,10)}</strong></div><p className="od-observation">Any spread circle is an illustrative area-growth extrapolation, not a validated fire forecast. A burn scar does not establish ignition cause.</p></> : <p className="od-muted">Select a source on the map to inspect its stored classification.</p>}</section></aside>
    </div><footer className="od-status"><span>FROZEN SNAPSHOT · EXISTING PREDICTIONS</span><span>ORBIT DELTA / SUPPORTING CONTEXT</span></footer>
  </div>;
}
