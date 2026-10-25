"""Local cached NASA water evidence; uses the application's existing access dependency."""
from functools import lru_cache
import io
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
import numpy as np
from PIL import Image

from app.processing.water import change_masks, feature_rows

ROOT=Path(__file__).resolve().parents[4]
MODEL_DIR=ROOT/'ml/models/water'
DATA_DIR=ROOT/'data/water'
SITES=json.loads((ROOT/'ml/water/sites.json').read_text())


def get_site(site_id):
    site=next((s for s in SITES if s['id']==site_id),None)
    if not site: raise HTTPException(404,'Unknown monitoring site.')
    return site


def bundle(site_id):
    path=MODEL_DIR/f'{site_id}.json'
    if not path.exists(): raise HTTPException(409,'Model unavailable: collect sufficient observations and run train_water.py.')
    return json.loads(path.read_text())


@lru_cache(maxsize=3)
def load_model(site_id, modified):
    import joblib
    import sklearn
    from app.processing.water import VERSION, FEATURES
    artifact=joblib.load(MODEL_DIR/f'{site_id}.joblib')
    if artifact['version']!=VERSION or artifact['features']!=FEATURES or artifact['sklearn_version']!=sklearn.__version__:
        raise HTTPException(409,'Model environment changed. Retrain with the current dependencies.')
    return artifact


def summary(row):
    fields=['date','open_water_km2','partial_water_km2','valid_fraction','expected_km2','baseline_deviation','anomaly_score','is_anomaly','baseline_alert','direction','split','gap_days']
    return {k:row[k] for k in fields if k in row}


def arrays(site_id, day):
    import rasterio
    path=DATA_DIR/site_id/f'{day}.tif'
    if not path.exists(): raise HTTPException(404,'Cached source raster unavailable. Run the collector to restore it.')
    with rasterio.open(path) as src: return src.read(1)


def selected_rows(data, day):
    rows=data['observations']
    index=next((i for i,r in enumerate(rows) if r['date']==day),None)
    if index is None: raise HTTPException(404,'No usable observation on that date.')
    return rows[:index+1]


def polygons(mask, transform, kind):
    import cv2
    from pyproj import Transformer
    # Contours are visual outlines; pixel totals always come from the full mask.
    n,labels,stats,centers=cv2.connectedComponentsWithStats(mask.astype('uint8'),8)
    features=[]
    for label in np.argsort(stats[1:,cv2.CC_STAT_AREA])[::-1][:40]+1:
        pixels=int(stats[label,cv2.CC_STAT_AREA])
        if pixels<9: continue
        contours,_=cv2.findContours((labels==label).astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            points=cv2.approxPolyDP(contour,1.5,True)[:,0,:]
            if len(points)<3: continue
            x=transform['bounds'][0]+(points[:,0]+.5)*30
            y=transform['bounds'][3]-(points[:,1]+.5)*30
            lon,lat=Transformer.from_crs(transform['epsg'],4326,always_xy=True).transform(x,y)
            ring=list(map(list,zip(lon.tolist(),lat.tolist()))); ring.append(ring[0])
            features.append({'type':'Feature','properties':{'id':f'{kind}-{label}','kind':kind,'component_pixels':pixels},'geometry':{'type':'Polygon','coordinates':[ring]}})
    return features


def build_router(access_dependency):
    router=APIRouter(prefix='/water',tags=['water'])

    @router.get('/sites')
    def sites(principal=Depends(access_dependency)):
        evaluation=MODEL_DIR/'evaluation.json'
        reports=json.loads(evaluation.read_text()) if evaluation.exists() else {}
        return [{**site,'readiness':reports.get(site['id'],{'status':'not_collected'})} for site in SITES]

    @router.get('/sites/{site_id}/observations')
    def observations(site_id:str,principal=Depends(access_dependency)):
        get_site(site_id); data=bundle(site_id)
        return {'site':data['site'],'version':data['version'],'threshold':data['threshold'],
                'provenance':data['provenance'],'trained_at':data['trained_at'],'model_id':data.get('model_id'),
                'evaluation':data['evaluation'],'observations':[summary(r) for r in data['observations']]}

    @router.get('/sites/{site_id}/assessment')
    def assessment(site_id:str,date:str=Query(...,pattern=r'^\d{4}-\d{2}-\d{2}$'),principal=Depends(access_dependency)):
        get_site(site_id); data=bundle(site_id); rows=selected_rows(data,date); current=rows[-1]
        artifact_path=MODEL_DIR/f'{site_id}.joblib'
        trained=data['evaluation']['status'] in {'trained','experimental'}
        if trained and not artifact_path.exists(): raise HTTPException(409,'Trained model artifact unavailable.')
        score=None
        if trained:
            artifact=load_model(site_id,artifact_path.stat().st_mtime_ns)
            if artifact.get('model_id')!=data.get('model_id'): raise HTTPException(409,'Model bundle changed. Reload the observations.')
            feature=feature_rows(rows,artifact['baseline'])[-1]
            score=float(-artifact['model'].score_samples([feature['features']])[0])
        result={'site_id':site_id,'version':data['version'],'observation':summary(current),
                'model_status':data['evaluation']['status'],'model_id':data.get('model_id'),'trained_at':data['trained_at'],
                'anomaly_score':score,'threshold':data['threshold'],'is_anomaly':bool(trained and score>data['threshold']),
                'possible_explanation':'Cause uncertain. Rainfall, reservoir operations, and withdrawals require independent verification.',
                'next_action':'Inspect shoreline changes and compare with rainfall, gauge and reservoir-operation records.',
                'limitations':data['evaluation']['limitations'],
                'regions':{'type':'FeatureCollection','features':[]},'source':data['source'],
                'observation_mode':'cached_real_satellite','forecast':None}
        if len(rows)>1:
            previous=rows[-2]; before=arrays(site_id,previous['date']); after=arrays(site_id,date)
            gained,lost,valid=change_masks(before,after)
            result.update(previous_date=previous['date'],gained_km2=float(gained.sum()*.0009),
                          lost_km2=float(lost.sum()*.0009),comparable_pixels=int(valid.sum()),
                          region_note='Largest components of at least 9 pixels shown; measurements include every changed pixel.')
            result['regions']['features']=polygons(gained,current,'gain')+polygons(lost,current,'loss')
        return result

    @router.get('/sites/{site_id}/image')
    def image(site_id:str,date:str=Query(...,pattern=r'^\d{4}-\d{2}-\d{2}$'),principal=Depends(access_dependency)):
        get_site(site_id); data=bundle(site_id); selected_rows(data,date)
        a=arrays(site_id,date)
        rgb=np.full((*a.shape,3),[33,45,52],dtype='uint8')
        rgb[a==0]=[196,194,158]; rgb[a==1]=[38,148,199]; rgb[a==2]=[114,195,189]
        img=Image.fromarray(rgb); img.thumbnail((900,900)); out=io.BytesIO(); img.save(out,format='PNG')
        return Response(out.getvalue(),media_type='image/png',headers={'Cache-Control':'private,max-age=3600','Vary':'Origin'})
    return router
