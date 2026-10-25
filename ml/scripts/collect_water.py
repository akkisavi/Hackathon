"""Resume NASA OPERA collection. Run from repo root: .venv/bin/python ml/scripts/collect_water.py."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import time

import numpy as np
from pyproj import Transformer
import rasterio
from rasterio.io import MemoryFile
import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
from app.processing.water import measure

SERVICE = 'https://gis.earthdata.nasa.gov/portal/rest/services/C2617126679-POCLOUD/OPERA_L3_DSWX-HLS_V1_B01_WTR/ImageServer'
DATA = ROOT/'data/water'
SITES = json.loads((ROOT/'ml/water/sites.json').read_text())


def get(url, **params):
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=90)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == 2: raise
            time.sleep(2**attempt)


def catalog(site):
    p = DATA/site['id']/'catalog.json'
    if p.exists(): return json.loads(p.read_text())
    xmin,ymin,xmax,ymax = site['bbox']
    geometry = json.dumps(dict(xmin=xmin,ymin=ymin,xmax=xmax,ymax=ymax,spatialReference={'wkid':4326}))
    rows = []
    while True:
        body = get(SERVICE+'/query', f='json', where="tileid IS NOT NULL AND category = 1 AND datetime >= timestamp '2023-04-01 00:00:00'",
                   geometry=geometry, geometryType='esriGeometryEnvelope', inSR=4326,
                   spatialRel='esriSpatialRelIntersects', outFields='objectid,datetime,tileid,cloud_coverage',
                   returnGeometry='false', resultRecordCount=1000, resultOffset=len(rows), orderByFields='datetime ASC,objectid ASC').json()
        if 'error' in body: raise RuntimeError(body['error'])
        batch = [f['attributes'] for f in body.get('features',[])]
        rows.extend(batch)
        if not body.get('exceededTransferLimit') or not batch: break
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(rows))
    return rows


def grid(site):
    transform = Transformer.from_crs(4326, site['epsg'], always_xy=True)
    x0,y0,x1,y1 = transform.transform_bounds(*site['bbox'], densify_pts=21)
    bounds = [int(np.floor(x0/30)*30),int(np.floor(y0/30)*30),int(np.ceil(x1/30)*30),int(np.ceil(y1/30)*30)]
    width,height = (bounds[2]-bounds[0])//30,(bounds[3]-bounds[1])//30
    if max(width,height)>2048: raise ValueError('Study area exceeds service 2048px export limit')
    return bounds,width,height


def export(site, day, records):
    folder = DATA/site['id']; path=folder/f'{day}.tif'; meta=folder/f'{day}.json'
    bounds,w,h = grid(site)
    if path.exists() and meta.exists():
        saved=json.loads(meta.read_text())
        if saved.get('bounds')==bounds and saved.get('epsg')==site['epsg'] and saved.get('sha256')==sha256(path.read_bytes()).hexdigest():
            return saved
    # Lock only the actual acquisition rasters, never the service's global overview.
    ids = [r['objectid'] for r in records]
    r = get(SERVICE+'/exportImage', f='image', bbox=','.join(map(str,bounds)), bboxSR=site['epsg'],
            imageSR=site['epsg'],size=f'{w},{h}',format='tiff',pixelType='U8',noData=255,
            interpolation='RSP_NearestNeighbor',renderingRule=json.dumps({'rasterFunction':'None'}),
            mosaicRule=json.dumps({'mosaicMethod':'esriMosaicLockRaster','lockRasterIds':ids,'mosaicOperation':'MT_FIRST'}))
    with MemoryFile(r.content) as mem, mem.open() as src:
        array=src.read(1)
        if src.count != 1 or array.shape != (h,w): raise ValueError('Unexpected NASA raster shape')
        if src.crs.to_epsg()!=site['epsg'] or not np.allclose([src.transform.a,src.transform.e],[30,-30],atol=.01):
            raise ValueError('Export is not on the required projected 30m grid')
        if not set(np.unique(array)).issubset({0,1,2,252,253,254,255}): raise ValueError('Unexpected water classes')
    from uuid import uuid4
    temporary=folder/f'{day}.{uuid4().hex}.part'
    temporary.write_bytes(r.content); temporary.replace(path)
    info={'date':day,**measure(array),'sha256':sha256(r.content).hexdigest(),'raster':path.name,
          'object_ids':ids,'acquisitions':records,'source':SERVICE,'epsg':site['epsg'],'bounds':bounds,'pixel_size_m':30}
    temporary=folder/f'{day}.{uuid4().hex}.part'
    temporary.write_text(json.dumps(info,indent=2)); temporary.replace(meta)
    return info


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--site',choices=[s['id'] for s in SITES]); parser.add_argument('--workers',type=int,default=4); parser.add_argument('--limit',type=int); parser.add_argument('--cadence-days',type=int,default=1)
    args=parser.parse_args()
    for site in SITES:
        if args.site and args.site!=site['id']: continue
        groups={}
        for r in catalog(site):
            day=datetime.fromtimestamp(r['datetime']/1000,timezone.utc).date().isoformat()
            groups.setdefault(day,[]).append(r)
        # One acquisition day per 3-day bin; prefer lower tile-cloud estimates.
        chosen={}
        for day,records in groups.items():
            bucket=datetime.fromisoformat(day).toordinal()//max(1,args.cadence_days)
            cloud=np.mean([r.get('cloud_coverage') if r.get('cloud_coverage') is not None else 100 for r in records])
            if bucket not in chosen or cloud<chosen[bucket][2]: chosen[bucket]=(day,records,cloud)
        jobs=sorted(chosen.values())
        if args.limit: jobs=jobs[:args.limit]
        rows=[]; errors=[]
        print(site['id'],len(groups),'available days;',len(jobs),'sampled days',flush=True)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures={pool.submit(export,site,d,rs):d for d,rs,_ in jobs}
            for i,f in enumerate(as_completed(futures),1):
                try: rows.append(f.result())
                except Exception as exc: errors.append({'date':futures[f],'error':str(exc)[:180]})
                if i%20==0 or i==len(jobs): print(site['id'],i,'/',len(jobs),'valid',sum(r['valid_fraction']>=.95 for r in rows),'errors',len(errors),flush=True)
        # Include previously cached observations, allowing limited runs to resume safely.
        rows=[json.loads(p.read_text()) for p in (DATA/site['id']).glob('????-??-??.json')]
        manifest={'site':site,'collected_at':datetime.now(timezone.utc).isoformat(),'observations':sorted(rows,key=lambda r:r['date']),'errors':errors,'sampling':f'lowest tile-cloud day per {args.cadence_days}-day bin; local validity checked separately'}
        (DATA/site['id']/'manifest.json').write_text(json.dumps(manifest,indent=2))

if __name__=='__main__': main()
