"""Train/evaluate per-reservoir anomaly models; no database dependency."""
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import IsolationForest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app.processing.water import VERSION, FEATURES, seasonal_fit, feature_rows


def train_site(manifest):
    rows=[r for r in manifest['observations'] if r['valid_fraction']>=.95]
    train=[r for r in rows if r['date']<'2025-01-01']
    val=[r for r in rows if '2025-01-01'<=r['date']<'2026-01-01']
    test=[r for r in rows if r['date']>='2026-01-01']
    spans=(date.fromisoformat(train[-1]['date'])-date.fromisoformat(train[0]['date'])).days if train else 0
    counts={'train':len(train),'validation':len(val),'test':len(test),'training_span_days':spans,'excluded_quality':len(manifest['observations'])-len(rows)}
    if len(train)<80 or spans<548 or len(val)<20 or len(test)<20:
        return None, {'status':'insufficient_history',**counts,'reason':'Requires 80 training observations over 18 months, 20 validation and 20 test observations.'}
    baseline=seasonal_fit(train)
    featured=feature_rows(rows,baseline)
    x=np.array([r['features'] for r in featured])
    tr=np.array([r['date']<'2025-01-01' for r in rows]); va=np.array(['2025-01-01'<=r['date']<'2026-01-01' for r in rows]); te=~(tr|va)
    model=IsolationForest(n_estimators=200,max_samples='auto',random_state=42,n_jobs=1).fit(x[tr])
    scores=-model.score_samples(x)
    threshold=float(np.quantile(scores[va],.95))
    deviation=np.abs([r['baseline_deviation'] for r in featured])
    base_threshold=float(np.quantile(deviation[va],.95))
    for r,score,dev in zip(featured,scores,deviation):
        r['anomaly_score']=float(score); r['is_anomaly']=bool(score>threshold)
        r['baseline_alert']=bool(dev>base_threshold)
        r['direction']='water_loss' if r['baseline_deviation']<0 else 'water_expansion'
        r['split']='train' if r['date']<'2025-01-01' else 'validation' if r['date']<'2026-01-01' else 'test'
        del r['features']
    model_alert=scores[te]>threshold; base_alert=deviation[te]>base_threshold
    # Sensitivity probe is artificial, never a claim of event accuracy.
    probe=x[te].copy(); probe[:,0]-=5; probe[:,1]*=.7; probe[:,2]-=.3
    report={'status':'trained',**counts,'model':'IsolationForest','features':FEATURES,'threshold':threshold,
            'baseline_threshold':base_threshold,'test_alert_fraction':float(model_alert.mean()),
            'test_baseline_alert_fraction':float(base_alert.mean()),'test_baseline_agreement':float((model_alert==base_alert).mean()),
            'artificial_loss_probe_alert_fraction':float((-model.score_samples(probe)>threshold).mean()),
            'event_precision':None,'event_recall':None,'warning_lead_time':None,
            'limitations':['No independent event labels: event accuracy and warning lead time are unknown.',
                          'Anomaly scores are not flood probabilities. Surface area is not storage volume.',
                          'Fixed study rectangles may include other water bodies; these are not surveyed reservoir boundaries.',
                          'Seasonal fit has fewer than two full annual cycles in the training period.'],
            'examples':sorted([r for r in featured if r['split']=='test'],key=lambda r:r['anomaly_score'],reverse=True)[:5]}
    artifact={'version':VERSION,'model':model,'baseline':baseline,'threshold':threshold,'features':FEATURES,
              'sklearn_version':sklearn.__version__,'trained_at':datetime.now(timezone.utc).isoformat(),
              'manifest_sha256':__import__('hashlib').sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()}
    return (artifact,featured),report


def main():
    out=ROOT/'ml/models/water'; out.mkdir(parents=True,exist_ok=True)
    reports={}
    for site in json.loads((ROOT/'ml/water/sites.json').read_text()):
        path=ROOT/'data/water'/site['id']/'manifest.json'
        if not path.exists(): reports[site['id']]={'status':'not_collected'}; continue
        manifest=json.loads(path.read_text()); result,report=train_site(manifest)
        reports[site['id']]=report
        if result:
            artifact,rows=result
            joblib.dump(artifact,out/f"{site['id']}.joblib")
            bundle={'site':site,'version':VERSION,'source':manifest['observations'][0]['source'],
                    'trained_at':artifact['trained_at'],'threshold':artifact['threshold'],'evaluation':report,
                    'observations':rows,'provenance':'Real NASA OPERA DSWx-HLS observations; cached locally.'}
            (out/f"{site['id']}.json").write_text(json.dumps(bundle,indent=2))
        else:
            # Preserve inspectable observations, but never imply an untrained model is ready.
            (out/f"{site['id']}.joblib").unlink(missing_ok=True)
            good=[r for r in manifest['observations'] if r['valid_fraction']>=.95]
            training=[r for r in good if r['date']<'2025-01-01']
            if len(training)>=20:
                baseline=seasonal_fit(training)
                rows=feature_rows(good,baseline)
                for r in rows:
                    r.pop('features')
                    r.update(anomaly_score=None,is_anomaly=False,baseline_alert=False,
                             direction='water_loss' if r['baseline_deviation']<0 else 'water_expansion',
                             split='train' if r['date']<'2025-01-01' else 'validation' if r['date']<'2026-01-01' else 'test')
                report['limitations']=['Insufficient history for the planned model: seasonal baseline only.',
                    'Fixed reservoir segment, not the entire reservoir. Area is not storage volume.',
                    'Clouds and missed acquisitions limit interpretation. Cause and future flood risk are unverified.']
                bundle={'site':site,'version':VERSION,'threshold':None,'trained_at':None,'evaluation':report,
                        'source':manifest['observations'][0]['source'],'observations':rows,
                        'provenance':'Real NASA OPERA observations; baseline only, no trained anomaly model.'}
                (out/f"{site['id']}.json").write_text(json.dumps(bundle,indent=2))
            else:
                (out/f"{site['id']}.json").unlink(missing_ok=True)
        print(site['id'],json.dumps({k:v for k,v in report.items() if k not in ['examples','limitations']}),flush=True)
    (out/'evaluation.json').write_text(json.dumps(reports,indent=2))

if __name__=='__main__': main()
