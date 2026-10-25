import React, { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { CHANGE_BASE, downloadJson } from '../lib/changeApi.js';
import { auth } from '../lib/auth.js';
import '../water.css';

async function request(path, signal) {
  const token=auth.getToken();
  const r=await fetch(`${CHANGE_BASE}/water${path}`,{signal,headers:token?{Authorization:`Bearer ${token}`}:{}});
  const body=await r.json();
  if(!r.ok) throw new Error(body.detail||'Water data unavailable');
  return body;
}

function WaterMap({site, assessment, visible, selectedRegion, onSelect}) {
  const el=useRef(null), map=useRef(null);
  useEffect(()=>{
    const m=new maplibregl.Map({container:el.current,style:{version:8,sources:{},layers:[{id:'background',type:'background',paint:{'background-color':'#10232b'}}]},center:[79,22],zoom:4});
    m.addControl(new maplibregl.NavigationControl(),'top-right'); map.current=m;
    m.on('load',()=>{
      m.addSource('context',{type:'raster',tiles:['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],tileSize:256,attribution:'Esri World Imagery · contextual composite'});
      m.addLayer({id:'context',type:'raster',source:'context',paint:{'raster-opacity':.65}});
      m.addSource('regions',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
      m.addLayer({id:'regions-fill',type:'fill',source:'regions',paint:{'fill-color':['match',['get','kind'],'gain','#42d8ff','#ff9c64'],'fill-opacity':.7}});
      m.addLayer({id:'regions-line',type:'line',source:'regions',paint:{'line-color':'#fff','line-width':1}});
      m.addLayer({id:'selected-region',type:'line',source:'regions',filter:['==',['get','id'],''],paint:{'line-color':'#fff09c','line-width':4}});
      m.on('click','regions-fill',e=>{const p=e.features[0].properties;onSelect(p.id);new maplibregl.Popup().setLngLat(e.lngLat).setText(`${p.id}: water ${p.kind}, ${(p.component_pixels*.0009).toFixed(3)} km² component`).addTo(m)});
      m.on('mouseenter','regions-fill',()=>{m.getCanvas().style.cursor='pointer'});m.on('mouseleave','regions-fill',()=>{m.getCanvas().style.cursor=''});
    });
    return()=>{m.remove();map.current=null;};
  },[]);
  useEffect(()=>{
    const m=map.current;if(!m||!site)return;
    const update=()=>{m.fitBounds([[site.bbox[0],site.bbox[1]],[site.bbox[2],site.bbox[3]]],{padding:35,duration:800});m.getSource('regions')?.setData(assessment?.regions||{type:'FeatureCollection',features:[]});};
    if(m.getSource('regions'))update();else m.once('load',update);
    return()=>m.off('load',update);
  },[site,assessment]);
  useEffect(()=>{if(visible)map.current?.resize()},[visible]);
  useEffect(()=>{const m=map.current;if(m?.getLayer('selected-region'))m.setFilter('selected-region',['==',['get','id'],selectedRegion||''])},[selectedRegion]);
  return <div ref={el} className="ww-map" aria-label="Reservoir map and water change regions"/>;
}

export default function WaterWatch(){
  const [sites,setSites]=useState([]),[siteId,setSiteId]=useState('hirakud'),[data,setData]=useState(null),[index,setIndex]=useState(0),[assessment,setAssessment]=useState(null),[error,setError]=useState(''),[playing,setPlaying]=useState(false),[image,setImage]=useState(null),[beforeImage,setBeforeImage]=useState(null),[view,setView]=useState('map'),[split,setSplit]=useState(50),[selectedRegion,setSelectedRegion]=useState(null);
  const site=sites.find(s=>s.id===siteId), rows=data?.observations||[], row=rows[index];
  useEffect(()=>{document.title='ORBIT DELTA · Water Anomaly Watch';const c=new AbortController();request('/sites',c.signal).then(setSites).catch(e=>{if(e.name!=='AbortError')setError(e.message)});return()=>c.abort();},[]);
  useEffect(()=>{const c=new AbortController();setData(null);setAssessment(null);setImage(null);setBeforeImage(null);setError('');setPlaying(false);request(`/sites/${siteId}/observations`,c.signal).then(d=>{setData(d);setIndex(d.observations.length-1)}).catch(e=>{if(e.name!=='AbortError')setError(e.message)});return()=>c.abort();},[siteId]);
  useEffect(()=>{if(!row)return;const c=new AbortController();setAssessment(null);setSelectedRegion(null);request(`/sites/${siteId}/assessment?date=${row.date}`,c.signal).then(setAssessment).catch(e=>{if(e.name!=='AbortError')setError(e.message)});return()=>c.abort();},[siteId,row?.date]);
  useEffect(()=>{
    if(!row)return;const c=new AbortController();let urls=[];setImage(null);setBeforeImage(null);
    const token=auth.getToken();
    const dates=[row.date,rows[Math.max(0,index-1)].date];
    Promise.all(dates.map(async date=>{
      const r=await fetch(`${CHANGE_BASE}/water/sites/${siteId}/image?date=${date}`,{signal:c.signal,headers:token?{Authorization:`Bearer ${token}`}:{}});
      if(!r.ok)throw new Error('Source image unavailable');
      const blob=await r.blob();if(c.signal.aborted)return null;
      const url=URL.createObjectURL(blob);urls.push(url);return url;
    })).then(([after,before])=>{if(!c.signal.aborted){setImage(after);setBeforeImage(before)}}).catch(e=>{if(e.name!=='AbortError')setError(e.message)});
    return()=>{c.abort();urls.forEach(url=>URL.revokeObjectURL(url))};
  },[siteId,row?.date]);
  useEffect(()=>{if(!playing)return;const t=setInterval(()=>setIndex(i=>{if(i>=rows.length-1){setPlaying(false);return i}return i+1}),1800);return()=>clearInterval(t)},[playing,rows.length]);
  const max=Math.max(1,...rows.map(r=>Math.max(r.open_water_km2,r.expected_km2||0))), x=i=>20+i/Math.max(1,rows.length-1)*760, y=a=>145-a/max*125;
  return <div className="ww-app">
    <header><a href="/orbit">◉ ORBIT DELTA</a><span>WATER ANOMALY WATCH / INDIA</span><a href="/orbit/thermal">Thermal context ↗</a></header>
    <div className="ww-layout"><aside><div className="ww-eyebrow">MONITORED AREAS</div><h1>A changing<br/>water world.</h1><p>Inspect satellite observations. Find unusual loss and expansion.</p>
      {sites.map(s=><button key={s.id} className={siteId===s.id?'selected':''} onClick={()=>setSiteId(s.id)}><strong>{s.name}</strong><small>{s.state}</small><em>{s.readiness.status==='trained'?'MODEL TRAINED · UNVALIDATED':s.readiness.status==='experimental'?'EXPERIMENTAL MODEL':s.readiness.status.replaceAll('_',' ')}</em></button>)}
      <div className="ww-note">NASA OPERA · 30 m<br/>Actual acquisition dates. Cached observations. Seasonal model, provisional alerts.</div>
    </aside><main>
      <div className="ww-title"><div><div className="ww-eyebrow">SURFACE WATER INTELLIGENCE</div><h2>{site?.name||'Loading monitoring areas'}</h2></div><span className="ww-badge">● REAL SATELLITE DATA</span></div>
      {error&&<div role="alert" className="ww-error">{error}</div>}
      <div className="ww-view"><button aria-pressed={view==='map'} onClick={()=>setView('map')}>Change map</button><button aria-pressed={view==='compare'} onClick={()=>setView('compare')}>Before / after</button></div>
      <div style={{display:view==='map'?'block':'none'}}><WaterMap site={site} assessment={assessment} visible={view==='map'} selectedRegion={selectedRegion} onSelect={setSelectedRegion}/></div>
      {view==='compare'&&<div className="ww-compare">
        {beforeImage&&<img src={beforeImage} alt="Previous NASA classified water observation"/>}
        {image&&<img src={image} alt="Selected NASA classified water observation" style={{clipPath:`inset(0 0 0 ${split}%)`}}/>}
        <div className="ww-divider" style={{left:`${split}%`}}/>
        <div className="ww-dates"><span>{rows[Math.max(0,index-1)]?.date} / Before</span><span>{row?.date} / After</span></div>
        <input aria-label="Before after divider" type="range" min="0" max="100" value={split} onChange={e=>setSplit(+e.target.value)}/>
      </div>}
      <div className="ww-map-caption">Blue: water gain · Orange: water loss · Esri background is a contextual composite</div>
      {row&&<><div className="ww-metrics"><div><small>OBSERVED OPEN WATER</small><strong>{row.open_water_km2.toFixed(2)} <i>km²</i></strong></div><div><small>SEASONAL BASELINE</small><strong>{row.expected_km2.toFixed(2)} <i>km²</i></strong></div><div><small>VALID STUDY AREA</small><strong>{(row.valid_fraction*100).toFixed(1)}<i>%</i></strong></div></div>
      <section className="ww-timeline"><div><strong>Observation history</strong><span>{row.date} · {row.split==='train'?'Training period':row.split==='validation'?'Validation period':'Held-out test period'}</span></div>
      <svg viewBox="0 0 800 170" role="img" aria-label="Water surface area and seasonal baseline history">
        <polyline fill="none" stroke="#77919b" strokeDasharray="4 4" strokeWidth="2" points={rows.map((r,i)=>`${x(i)},${y(r.expected_km2)}`).join(' ')}/>
        <polyline fill="none" stroke="#42d8ff" strokeWidth="2" points={rows.map((r,i)=>`${x(i)},${y(r.open_water_km2)}`).join(' ')}/>
        {rows.filter(r=>r.is_anomaly).map(r=><circle key={r.date} cx={x(rows.indexOf(r))} cy={y(r.open_water_km2)} r="3" fill="#ff9c64"/>)}
        <line x1={x(index)} x2={x(index)} y1="8" y2="150" stroke="white" opacity=".6"/>
        <text x="20" y="168" fill="#9db3bc" fontSize="11">{rows[0].date}</text><text x="690" y="168" fill="#9db3bc" fontSize="11">{rows.at(-1).date}</text>
      </svg><div className="ww-play"><button onClick={()=>{if(index===rows.length-1)setIndex(0);setPlaying(!playing)}}>{playing?'Pause':'▶ Replay'}</button><input aria-label="Observation date" type="range" min="0" max={rows.length-1} value={index} onChange={e=>{setPlaying(false);setIndex(+e.target.value)}}/></div>
      <small>Solid: observed area · Dashed: seasonal baseline · Orange dots: model anomalies</small></section></>}
    </main><section className="ww-inspector"><div className="ww-eyebrow">EVIDENCE / ASSESSMENT</div>
      <h2>{assessment?(!['trained','experimental'].includes(assessment.model_status)?'Baseline only':assessment.is_anomaly?'Unusual water change':'Within learned pattern'):'Inspect an observation'}</h2>
      {row&&<><p>{row.baseline_deviation<0?'Below':'Above'} the seasonal baseline. The model score describes unusual behaviour, not flood probability.</p>
      {assessment?.model_status==='experimental'&&<div className="ww-error">Experimental model · limited training history · readiness gate not met</div>}<div className="ww-score"><span>Anomaly score</span><strong>{assessment?.anomaly_score?.toFixed(3)||'Unavailable'}</strong><small>Alert threshold {data.threshold?.toFixed(3)||'not trained'}</small></div>
      <h3>Measured change</h3>{!assessment?<p>Loading measurements…</p>:<p>Since {assessment?.previous_date||'first observation'}: <b>{assessment?.gained_km2?.toFixed(2)||'0'} km²</b> gained; <b>{assessment?.lost_km2?.toFixed(2)||'0'} km²</b> lost on comparable pixels.</p>}
      {!!assessment?.regions.features.length&&<details><summary>Inspect changed regions</summary>{assessment.regions.features.map((f,i)=><button key={`${f.properties.id}-${i}`} onClick={()=>{setSelectedRegion(f.properties.id);setView('map')}} aria-pressed={selectedRegion===f.properties.id}>{f.properties.id} · {(f.properties.component_pixels*.0009).toFixed(3)} km²</button>)}</details>}
      {image&&<figure><img src={image} alt={`NASA classified water extent on ${row.date}`}/><figcaption>Blue: open water · Teal: partial water · Dark: invalid observation</figcaption></figure>}
      <h3>Possible explanation</h3><p>{assessment?.possible_explanation||'Loading evidence…'}</p><h3>Next verification</h3><p>{assessment?.next_action}</p>
      <button disabled={!assessment} onClick={()=>downloadJson(assessment,`orbit-water-${siteId}-${row.date}.json`)}>↓ Export assessment JSON</button>
      <details><summary>Model and data limits</summary>{data.evaluation.limitations.map(l=><p key={l}>{l}</p>)}<p>{data.version} · {rows.length} quality-filtered observations · {data.trained_at}</p><p>Historical training/validation scores are retrospective. No flood forecast is produced.</p></details></>}
    </section></div></div>;
}
