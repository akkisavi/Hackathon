import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import ChangeMap from "../components/ChangeMap.jsx";
import { changeRequest, downloadJson, downloadImage, imageUrl, isLoopback } from "../lib/changeApi.js";
import "../orbit.css";

const labels = { natural_like: "Natural-like change", human_like: "Human-like change", uncertain: "Cause uncertain", no_change: "No retained change" };
const format = number => new Intl.NumberFormat("en-IN").format(number);

function Icon({ name, size = 18 }) {
  const paths = {
    orbit: <><ellipse cx="12" cy="12" rx="10" ry="4" transform="rotate(-35 12 12)"/><circle cx="12" cy="12" r="4"/><circle cx="19" cy="6" r="1.5" fill="currentColor"/></>,
    layers: <><path d="m12 3 10 6-10 6L2 9Z"/><path d="m2 13 10 6 10-6M2 17l10 6 10-6"/></>,
    arrow: <path d="M5 12h14m-5-5 5 5-5 5"/>,
    download: <><path d="M12 3v12m-4-4 4 4 4-4M4 16v5h16v-5"/></>,
    cross: <><circle cx="12" cy="12" r="7"/><path d="M12 1v6m0 10v6M1 12h6m10 0h6"/></>,
    expand: <path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/>,
    play: <path d="m8 4 13 8-13 8Z" fill="currentColor"/>,
    pause: <><path d="M8 4v16M16 4v16" strokeWidth="4"/></>,
    check: <path d="m5 12 4 4 10-10"/>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.cross}</svg>;
}

export default function OrbitDelta() {
  const [fixtures, setFixtures] = useState([]);
  const [selected, setSelected] = useState("flood");
  const [frame, setFrame] = useState(3);
  const [threshold, setThreshold] = useState(0.2);
  const [analysis, setAnalysis] = useState(null);
  const [busy, setBusy] = useState(false);
  const [reportBusy, setReportBusy] = useState(false);
  const [error, setError] = useState("");
  const [fixtureError, setFixtureError] = useState("");
  const [regionId, setRegionId] = useState(null);
  const [overlay, setOverlay] = useState(true);
  const [split, setSplit] = useState(50);
  const [view, setView] = useState("compare");
  const [playing, setPlaying] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [upload, setUpload] = useState(false);
  const [beforeFile, setBeforeFile] = useState(null);
  const [afterFile, setAfterFile] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  const [scale, setScale] = useState("");
  const [fileUrls, setFileUrls] = useState([null, null]);
  const [fixtureImages, setFixtureImages] = useState(null);
  const [fileRevision, setFileRevision] = useState(0);
  const reportController = useRef(null);
  const currentKey = useRef("");

  const incident = fixtures.find(f => f.id === selected);
  const fixtureKey = `${selected}:${frame}`;
  const key = JSON.stringify([selected, frame, threshold, upload, fileRevision, confirmed, scale]);
  currentKey.current = key;
  const result = analysis?.key === key ? analysis.data : null;
  const region = result?.regions.find(r => r.id === regionId) ?? result?.regions[0];
  const preview = fixtureImages?.key === fixtureKey ? fixtureImages : null;
  const beforeUrl = upload ? fileUrls[0] : preview?.urls[0];
  const afterUrl = upload ? fileUrls[1] : preview?.urls[1];

  useEffect(() => {
    const title = document.title;
    document.title = "ORBIT DELTA · Earth change intelligence";
    return () => { document.title = title; };
  }, []);

  useEffect(() => {
    if (!isLoopback) return;
    const controller = new AbortController();
    changeRequest("/fixtures", { signal: controller.signal }).then(setFixtures).catch(e => {
      if (e.name !== "AbortError") setFixtureError("Fixture mode is unavailable. Start the local demo server, or upload a pair with the authenticated API.");
    });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const urls = [beforeFile, afterFile].map(file => file ? URL.createObjectURL(file) : null);
    setFileUrls(urls);
    return () => urls.forEach(url => url && URL.revokeObjectURL(url));
  }, [beforeFile, afterFile]);

  useEffect(() => {
    if (upload || !incident) { setFixtureImages(null); return; }
    const controller = new AbortController();
    let urls = [];
    Promise.all([incident.frames[0], incident.frames[frame]].map(async item => {
      const response = await fetch(imageUrl(item.image_url), { signal: controller.signal, cache: "no-store" });
      if (!response.ok) throw new Error("Could not load scene imagery. Check the local server.");
      return response.blob();
    })).then(images => {
      if (controller.signal.aborted) return;
      urls = images.map(image => URL.createObjectURL(image));
      setFixtureImages({ key: fixtureKey, images, urls });
    }).catch(error => {
      if (error.name !== "AbortError") setError("Could not load scene imagery. Check the local server.");
    });
    return () => { controller.abort(); urls.forEach(url => URL.revokeObjectURL(url)); };
  }, [incident, frame, upload]);

  useEffect(() => {
    setBusy(false); setError(""); setRegionId(null); setReportBusy(false);
    reportController.current?.abort();
    const controller = new AbortController();
    if (upload ? !(beforeFile && afterFile && confirmed) : !incident || fixtureImages?.key !== fixtureKey) return () => controller.abort();
    setBusy(true);
    const timer = setTimeout(async () => {
      try {
        const images = upload ? [beforeFile, afterFile] : fixtureImages.images;
        const body = new FormData();
        body.append("before", images[0], "before.png"); body.append("after", images[1], "after.png");
        body.append("threshold", threshold);
        if (!upload || scale) body.append("pixel_size_m", upload ? scale : incident.pixel_size_m);
        const data = await changeRequest("/analyze", { method: "POST", body, signal: controller.signal });
        if (!controller.signal.aborted) setAnalysis({ key, data });
      } catch (e) { if (e.name !== "AbortError") setError(e.message); }
      finally { if (!controller.signal.aborted) setBusy(false); }
    }, 180);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [key, incident, fixtureImages]);

  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => setFrame(previous => {
      if (previous >= 3) { setPlaying(false); return 3; }
      return previous + 1;
    }), 1800);
    return () => clearInterval(timer);
  }, [playing]);

  useEffect(() => {
    const escape = event => { if (event.key === "Escape") setExpanded(false); };
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("keydown", escape); reportController.current?.abort(); };
  }, []);

  async function generateReport() {
    if (!result) return;
    const capturedKey = key;
    const id = result.analysis_id;
    const controller = new AbortController();
    reportController.current?.abort(); reportController.current = controller;
    setReportBusy(true); setError("");
    try {
      const report = await changeRequest("/report", { method: "POST", signal: controller.signal,
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ analysis_id: id }) });
      setAnalysis(previous => previous?.key === capturedKey && previous.data.analysis_id === id
        ? { ...previous, data: { ...previous.data, ...report } } : previous);
    } catch (e) {
      if (e.name !== "AbortError" && currentKey.current === capturedKey) setError(e.message);
    } finally { if (currentKey.current === capturedKey) setReportBusy(false); }
  }

  function choose(id) {
    setSelected(id); setFrame(3); setUpload(false); setPlaying(false); setView("compare");
  }

  function exportAssessment() {
    if (!result) return;
    const { overlay: annotated, mask, ...measured } = result;
    downloadJson({ version: "1.0", ...measured, synthetic: !upload,
      provenance: upload ? "User-supplied images; alignment confirmed by user; capture dates not supplied."
        : incident.provenance,
      before: upload ? beforeFile.name : incident.frames[0],
      after: upload ? afterFile.name : incident.frames[frame],
      coordinate_system: "Image pixels, origin top-left; polygons are implicitly closed outlines.",
    }, `orbit-delta-${upload ? "upload" : selected}.json`);
  }

  return <div className="od-app">
    <header className="od-header">
      <a className="od-brand" href="/orbit"><span className="od-brand-mark"><Icon name="orbit" size={27}/></span><span>ORBIT<span className="od-brand-delta">DELTA</span><small>EARTH CHANGE INTELLIGENCE</small></span></a>
      <div className="od-header-center"><span className="od-live-dot"/>{upload ? "IMAGE INSPECTION" : "SCENARIO WORKSPACE"}<span className="od-separator">/</span>ORCA · TRACK 05</div>
      <Link className="od-thermal-link" to="/orbit/water">Water Anomaly Watch ↗</Link>
      <Link className="od-thermal-link" to={isLoopback ? "/orbit/thermal" : "/"}>Thermal monitoring <Icon name="arrow" size={15}/></Link>
    </header>

    <div className="od-layout">
      <aside className="od-sidebar">
        <div className="od-section-label">INVESTIGATION DESK <span>03</span></div>
        <h1>Change deserves<br/>a closer look.</h1>
        <p className="od-intro">Compare the evidence.<br/>Understand what comes next.</p>
        <div className="od-scene-heading">SCENARIOS <span>SYNTHETIC</span></div>
        {fixtures.map((f, i) => <button key={f.id} className={`od-incident ${!upload && selected === f.id ? "active" : ""}`} onClick={() => choose(f.id)}>
          <div className="od-incident-top"><span className="od-number">0{i + 1}</span><span className="od-scene-dot" style={{ background: f.color }}/><span className="od-incident-arrow">↗</span></div>
          <strong>{f.name}</strong><small>{f.location.split(" · ")[0]}</small>
          <span className="od-incident-kind">{i === 0 ? "WATER EXTENT" : i === 1 ? "LAND DISTURBANCE" : "REFERENCE CONTROL"}</span>
        </button>)}
        {fixtureError && <p className="od-inline-error">{fixtureError}</p>}
        <button className={`od-upload-button ${upload ? "active" : ""}`} onClick={() => { setUpload(true); setPlaying(false); setView("compare"); }}><Icon name="layers"/>Inspect your images <span>+</span></button>
        <div className="od-sidebar-bottom"><Icon name="orbit" size={30}/><p>A clear view of change.<br/><span>A measured view of cause.</span></p><small>PROTOTYPE / ORCA CODER 2026</small></div>
      </aside>

      <main className={`od-workspace ${expanded ? "od-expanded" : ""}`}>
        <div className="od-workspace-heading"><div><div className="od-eyebrow">{upload ? "USER-SUPPLIED IMAGERY" : "SYNTHETIC SCENARIO / NOT SATELLITE CAPTURES"}</div><h2>{upload ? "Compare your image pair" : incident?.name ?? "Preparing workspace"}</h2><p>{upload ? "Aligned 512 × 512 images · PNG or JPEG · up to 5 MB each" : incident?.description}</p></div>
          <button className="od-icon-button" aria-label={expanded ? "Collapse comparison" : "Expand comparison"} onClick={() => setExpanded(!expanded)}><Icon name="expand"/></button></div>
        {upload && <div className="od-upload-form">
          <label>Before image<input type="file" accept="image/png,image/jpeg" onChange={e => { setBeforeFile(e.target.files[0] ?? null); setFileRevision(n => n + 1); setConfirmed(false); }}/></label>
          <label>After image<input type="file" accept="image/png,image/jpeg" onChange={e => { setAfterFile(e.target.files[0] ?? null); setFileRevision(n => n + 1); setConfirmed(false); }}/></label>
          <label>Metres/pixel (optional)<input type="number" min="0.001" step="any" value={scale} onChange={e => setScale(e.target.value)} placeholder="Unknown"/></label>
          <label className="od-confirm"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/>Same footprint, aligned, comparable lighting</label>
        </div>}
        <div className="od-view-toolbar"><div className="od-tabs"><button className={view === "compare" ? "active" : ""} onClick={() => setView("compare")}>◫ &nbsp; Compare</button><button disabled={upload || !incident} className={view === "map" ? "active" : ""} onClick={() => setView("map")}>⌖ &nbsp; Location</button></div>
          <label className="od-overlay-toggle"><input type="checkbox" checked={overlay} onChange={e => setOverlay(e.target.checked)}/><span/>Change regions</label>
        </div>
        {error && <p className="od-inline-error" role="alert">{error}</p>}
        <div className="od-canvas">
          {view === "map" && incident && <ChangeMap incident={incident} image={afterUrl} measurement={result} selectedRegion={region?.id} onSelectRegion={setRegionId} showOverlay={overlay}/>}
          {view === "compare" && <div className="od-image-well">
            {beforeUrl && afterUrl ? <div className="od-comparison" data-testid="comparison">
              <img src={afterUrl} alt="After image" crossOrigin="anonymous" draggable="false"/>
              <img className="od-before" src={beforeUrl} alt="Before image" crossOrigin="anonymous" draggable="false" style={{ clipPath: `inset(0 ${100 - split}% 0 0)` }}/>
              {overlay && result && <svg className="od-region-overlay" viewBox="0 0 512 512" aria-label="Measured change regions">
                {result.regions.map(r => <g key={r.id} className={r.id === region?.id ? "selected" : ""}>
                  <polygon points={r.polygon_xy.map(p => p.join(",")).join(" ")} onClick={() => setRegionId(r.id)} role="button" tabIndex="0" aria-label={`Select region ${r.id}`} onKeyDown={e => { if (["Enter", " "].includes(e.key)) { e.preventDefault(); setRegionId(r.id); } }}/>
                  <text x={r.bbox_xywh[0] + 4} y={Math.max(16, r.bbox_xywh[1] - 5)}>{r.id}</text>
                </g>)}
              </svg>}
              <div className="od-split-line" style={{ left: `${split}%` }}><button aria-label="Drag comparison divider" role="slider" aria-valuemin={0} aria-valuemax={100} aria-valuenow={split}
                onPointerDown={e => e.currentTarget.setPointerCapture(e.pointerId)}
                onPointerMove={e => { if (e.currentTarget.hasPointerCapture(e.pointerId)) { const rect = e.currentTarget.closest(".od-comparison").getBoundingClientRect(); setSplit(Math.round(Math.max(0, Math.min(100, (e.clientX - rect.left) / rect.width * 100)))); } }}
                onPointerUp={e => e.currentTarget.releasePointerCapture(e.pointerId)}
                onKeyDown={e => { if (["ArrowLeft", "ArrowRight"].includes(e.key)) { e.preventDefault(); setSplit(n => Math.max(0, Math.min(100, n + (e.key === "ArrowLeft" ? -5 : 5)))); } }}>‹ ›</button></div>
              <div className="od-image-label before">BEFORE <span>{upload ? "Uploaded" : "20 OCT · 00:00 UTC"}</span></div>
              <div className="od-image-label after">AFTER <span>{upload ? "Uploaded" : `${String(frame * 6).padStart(2, "0")}:00 UTC`}</span></div>
            </div> : <div className="od-empty"><Icon name="layers" size={40}/><p>{upload ? "Choose two images to begin" : "Loading illustrative imagery…"}</p></div>}
          </div>}
          <div className="od-canvas-footer"><span><span className="od-coordinate-cross">+</span>{upload ? "IMAGE SPACE / 512 × 512" : incident ? `${incident.center[1].toFixed(4)}° N   ${incident.center[0].toFixed(4)}° E · ILLUSTRATIVE` : "LOCAL WORKSPACE"}</span><span>{upload ? "SCALE AS SUPPLIED" : "2 m/px · ASSUMED"}</span></div>
          {busy && <div className="od-analyzing" role="status">Measuring structural change…</div>}
        </div>
        {view === "compare" && <label className="od-split-control"><span>BEFORE</span><input aria-label="Before and after split" type="range" min="0" max="100" value={split} onChange={e => setSplit(Number(e.target.value))}/><span>AFTER</span></label>}
        {!upload && <div className="od-timeline"><div className="od-timeline-title"><span>SCENARIO REPLAY</span><small>Simulated frames · not a forecast</small></div><div className="od-playback"><button className="od-play-button" aria-label={playing ? "Pause replay" : "Play replay"} onClick={() => { if (frame === 3 && !playing) setFrame(0); setPlaying(!playing); }}><Icon name={playing ? "pause" : "play"} size={15}/></button><div className="od-timeline-track">{[0,1,2,3].map(i => <button key={i} className={frame === i ? "active" : ""} onClick={() => { setFrame(i); setPlaying(false); }}><span className="od-tick"/><strong>{i === 0 ? "Baseline" : `+${i*6} hours`}</strong><small>{String(i*6).padStart(2, "0")}:00 UTC</small></button>)}</div><span className="od-frame-count">0{frame + 1}<small>/ 04</small></span></div></div>}
        <div className="od-method-note"><Icon name="check" size={14}/>{upload ? "Measurements use supplied pixels. Capture dates and image alignment are not independently verified." : "Reproducible synthetic scenes. Measurements are computed from pixels; cause remains a hypothesis."}</div>
      </main>

      <aside className="od-inspector">
        <div className="od-inspector-title"><Icon name="cross"/><strong>Evidence & assessment</strong><span className="od-beta">BETA</span></div>
        <section className="od-metrics"><div className="od-eyebrow">MEASURED CHANGE</div><div className="od-big-number" data-testid="changed-percent">{result ? (result.changed_fraction * 100).toFixed(2) : "—"}<span>%</span></div><p>of the compared image</p><div className="od-metric-row"><span>Changed pixels</span><strong>{result ? format(result.changed_pixels) : "—"}</strong></div><div className="od-metric-row"><span>Retained regions</span><strong>{result?.regions.length ?? "—"}</strong></div><div className="od-metric-row"><span>{upload ? "Area (supplied scale)" : "Area (assumed scale)"}</span><strong>{result?.area_m2 != null ? `${(result.area_m2 / 10000).toFixed(2)} ha` : "Unknown"}</strong></div></section>
        <section className="od-sensitivity"><label htmlFor="threshold">Detection threshold<strong>{threshold.toFixed(2)}</strong></label><input id="threshold" type="range" min="0.05" max="0.6" step="0.01" value={threshold} onChange={e => { setThreshold(Number(e.target.value)); setPlaying(false); }}/><div><span>More sensitive</span><span>Less sensitive</span></div></section>
        <section className="od-region-list"><div className="od-section-label">REGION EVIDENCE <span>{result?.regions.length ?? "—"}</span></div>
          {result?.regions.length ? result.regions.map(r => <button key={r.id} className={r.id === region?.id ? "active" : ""} onClick={() => setRegionId(r.id)}><span className="od-region-id">{r.id}</span><span><strong>{format(r.pixels)} pixels</strong><small>{r.bbox_xywh[2]} × {r.bbox_xywh[3]} px bounding extent</small></span><Icon name="arrow" size={14}/></button>) : <p className="od-muted">{result ? "No retained regions at this threshold." : "Regions appear after analysis."}</p>}
        </section>
        <section className="od-assessment"><div className="od-section-label">POSSIBLE EXPLANATION <span>AI + EVIDENCE</span></div><h3>{result ? labels[result.report.hypothesis] : "Awaiting evidence"}</h3><span className={`od-report-source ${result?.report_mode === "gemini" ? "generated" : ""}`}>{result?.report_mode === "gemini" ? "Gemini · image-grounded" : result?.report_mode === "local_fallback" ? "Local fallback · AI unavailable" : "Local measurements"}</span>
          {result?.report.evidence.filter(e => e.region_id === region?.id).map((e,i) => <p key={i} className="od-observation"><b>{e.region_id}</b>{e.observation}</p>)}
          <button className="od-generate" disabled={!result || busy || reportBusy || playing} onClick={generateReport}><Icon name="orbit"/>{reportBusy ? "Reviewing image evidence…" : "Generate assessment"}<Icon name="arrow" size={16}/></button>
          <div className="od-next-action"><span>NEXT VERIFICATION</span><p>{result?.report.next_action ?? "Compare an image pair to begin."}</p></div>
          <details className="od-limitations"><summary>Limits of this assessment</summary>{result?.report.limitations.map((text,i) => <p key={i}>{text}</p>)}</details>
        </section>
        <div className="od-export"><button disabled={!result} onClick={exportAssessment}><Icon name="download" size={16}/>Assessment JSON</button><button disabled={!result} onClick={() => downloadImage(result.overlay, "orbit-delta-annotated.png")}><Icon name="download" size={16}/>Annotated image</button></div>
        <div className="od-inspector-footer">OBSERVE. MEASURE. VERIFY.</div>
      </aside>
    </div>
    <footer className="od-status"><span><span className="od-live-dot"/>{busy ? "ANALYZING" : result ? "ANALYSIS READY" : "READY FOR IMAGERY"}</span><span>SSIM + STRUCTURAL REGIONS <i>·</i> {upload ? "USER IMAGERY" : "SYNTHETIC DEMONSTRATION"}</span><span>ORBIT DELTA / v1.0</span></footer>
  </div>;
}
