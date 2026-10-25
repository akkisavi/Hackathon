from datetime import date, timedelta
import numpy as np
from app.processing.water import measure, change_masks, seasonal_fit, feature_rows


def test_clouds_are_not_water_loss():
    before=np.array([[1,1,0],[2,253,255]],dtype='uint8')
    after=np.array([[253,0,1],[2,1,255]],dtype='uint8')
    gained,lost,valid=change_masks(before,after)
    assert gained.sum()==1 and lost.sum()==1 and valid.sum()==3
    assert measure(before)['open_water_km2']==.0018
    assert measure(before)['valid_pixels']==4


def test_features_do_not_use_future():
    rows=[{'date':(date(2023,4,1)+timedelta(days=i*5)).isoformat(),'open_water_km2':100+np.sin(i)*5} for i in range(90)]
    baseline=seasonal_fit(rows[:60])
    original=feature_rows(rows,baseline)
    altered=feature_rows(rows[:80]+[{**r,'open_water_km2':99999} for r in rows[80:]],baseline)
    assert original[:80]==altered[:80]
    assert np.isfinite([r['features'] for r in original]).all()


def test_identical_has_no_changes():
    a=np.array([[0,1,2,252,253,254,255]],dtype='uint8')
    gained,lost,valid=change_masks(a,a)
    assert not gained.any() and not lost.any() and valid.sum()==3


def test_training_is_chronological_and_artifact_reproduces():
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('train_water',Path(__file__).resolve().parents[2]/'ml/scripts/train_water.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    rows=[]
    for i in range(240):
        d=date(2023,4,1)+timedelta(days=i*5)
        rows.append({'date':d.isoformat(),'open_water_km2':100+20*np.sin(d.timetuple().tm_yday/365.25*2*np.pi)+np.sin(i), 'valid_fraction':1})
    manifest={'observations':rows}
    result,report=module.train_site(manifest)
    assert report['status']=='trained'
    artifact,featured=result
    x=feature_rows(rows,artifact['baseline'])
    scores=-artifact['model'].score_samples([r['features'] for r in x])
    assert np.allclose(scores,[r['anomaly_score'] for r in featured])
    altered=[r if r['date']<'2026-01-01' else {**r,'open_water_km2':999} for r in rows]
    other,_=module.train_site({'observations':altered})
    assert other[0]['threshold']==artifact['threshold']
    assert other[0]['baseline']==artifact['baseline']
    assert report['event_precision'] is None


def test_insufficient_history_does_not_train():
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('train_water',Path(__file__).resolve().parents[2]/'ml/scripts/train_water.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    result,report=module.train_site({'observations':[]})
    assert result is None and report['status']=='insufficient_history'


def test_api_access_validation_and_missing_model(tmp_path,monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.v1 import water
    from app.api.v1.change import loopback_only
    monkeypatch.setattr(water,'MODEL_DIR',tmp_path)
    app=FastAPI();app.include_router(water.build_router(loopback_only))
    c=TestClient(app)
    assert c.get('/water/sites').status_code==200
    assert c.get('/water/sites',headers={'Host':'example.com'}).status_code==403
    assert c.get('/water/sites/unknown/observations').status_code==404
    assert c.get('/water/sites/hirakud/observations').status_code==409
    assert c.get('/water/sites/hirakud/assessment?date=../secret').status_code==422


def test_polygons_are_geographic_and_mask_counts_are_exact():
    from app.api.v1.water import polygons
    mask=np.zeros((20,20),dtype=bool);mask[2:8,3:9]=True
    features=polygons(mask,{'epsg':32644,'bounds':[750000,2380000,750600,2380600]},'gain')
    assert len(features)==1
    assert features[0]['properties']['component_pixels']==36
    lon,lat=features[0]['geometry']['coordinates'][0][0]
    assert 80<lon<85 and 20<lat<23


def test_experimental_model_keeps_readiness_gate():
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('train_water',Path(__file__).resolve().parents[2]/'ml/scripts/train_water.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rows=[{'date':(date(2023,4,1)+timedelta(days=i*15)).isoformat(),'open_water_km2':100+np.sin(i)*10,'valid_fraction':1} for i in range(92)]
    result,strict=module.train_site({'observations':rows})
    assert result is None
    result,report=module.train_site({'observations':rows},allow_experimental=True)
    assert result is not None and report['status']=='experimental'
    assert report['readiness_gate_passed'] is False
    assert 'Fewer than 80' in report['limitations'][0]
