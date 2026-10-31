from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA=Path('/srv/shared-data/gep/ws4/tmp/inv01-data')
train=pd.read_csv('/srv/shared-data/gep/ws4/femic/notes/reports/inv01-tsa23-training-plots.csv')
train['SITE_IDENTIFIER']=train.SITE_IDENTIFIER.astype(int)
hold_path=DATA/'validation-output/psp_holdout.csv'
if not hold_path.exists():
    hold_path=Path('/srv/shared-data/gep/ws4/tmp/femic-inv01-pathfix/notes/reports/inv01-tsa23-psp-holdout.csv')
hold=pd.read_csv(hold_path)
hold=hold[['SITE_IDENTIFIER','Lhmean','Lhp95','CC2m','lorey_height_m_obs','ba_m2_ha_obs','vol_m3_ha_obs']].rename(columns={'lorey_height_m_obs':'height','ba_m2_ha_obs':'ba','vol_m3_ha_obs':'vol'})
high=pd.read_csv(DATA/'psp/regional_high_features.csv')
# Training: 14 TSA23 + all non-TSA23 high; TSA23 holdout stays out.
a=train[['SITE_IDENTIFIER','Lhmean','Lhp95','CC2m','lorey_height_m','ba_m2_ha','vol_m3_ha']].rename(columns={'lorey_height_m':'height','ba_m2_ha':'ba','vol_m3_ha':'vol'})
a['region']='TSA23'
b=high[high.TSA!=23][['SITE_IDENTIFIER','Lhmean','Lhp95','CC2m','height','ba','vol','TSA']].copy(); b['region']='TSA'+b.TSA.astype(int).astype(str)
d=pd.concat([a[['SITE_IDENTIFIER','Lhmean','Lhp95','CC2m','height','ba','vol','region']],b[['SITE_IDENTIFIER','Lhmean','Lhp95','CC2m','height','ba','vol','region']]],ignore_index=True).drop_duplicates('SITE_IDENTIFIER')
# XGBoost? no; keep same linear forms but wider range and include region dummies? For a robust open baseline use no dummies first.
def fit_height(x): return np.linalg.lstsq(np.column_stack([np.ones(len(x)),x.Lhp95]),x.height,rcond=None)[0]
def fit_ba(x): return np.linalg.lstsq(np.column_stack([np.ones(len(x)),np.log(x.Lhmean),np.log(x.CC2m)]),np.log(x.ba),rcond=None)[0]
def fit_vol(x): return np.linalg.lstsq(np.column_stack([np.ones(len(x)),np.log(x.Lhmean),np.log(x.CC2m)]),np.log(x.vol),rcond=None)[0]
def ph(c,x): return c[0]+c[1]*x.Lhp95
def pb(c,x): return np.exp(c[0]+c[1]*np.log(x.Lhmean)+c[2]*np.log(x.CC2m))
def pv(c,x): return np.exp(c[0]+c[1]*np.log(x.Lhmean)+c[2]*np.log(x.CC2m))
def met(p,o):
 e=p-o; return {'n':len(e),'bias':float(e.mean()),'mae':float(e.abs().mean()),'rmse':float(np.sqrt((e*e).mean()))}
out={'n':{'training':len(d),'tsa23_training':14,'regional_high':len(high[high.TSA!=23]),'holdout':len(hold)},'sites':{'holdout':hold.SITE_IDENTIFIER.astype(int).tolist()},'models':{}}
for key,fit,pred,obs,cur in [
 ('height',fit_height,ph,'height',lambda x:1.9441063309517714+0.8351084469592212*x.Lhp95),
 ('ba',fit_ba,pb,'ba',lambda x:np.exp(-4.724750214946937+0.8686310009684395*np.log(x.Lhmean)+1.3794686095244624*np.log(x.CC2m))*1.008780042159369),
 ('volume',fit_vol,pv,'vol',lambda x:np.exp(-4.009416713953133+1.7395991112544076*np.log(x.Lhmean)+1.1516782963514058*np.log(x.CC2m))*1.004526898452813)]:
 c=fit(d)
 out['models'][key]={'current_holdout':met(cur(hold),hold[obs]),'regional_holdout':met(pred(c,hold),hold[obs]),'coefficients':[float(v) for v in c],'range_observed':[float(d[obs].min()),float(d[obs].max())],'range_predictor':{'Lhmean':[float(d.Lhmean.min()),float(d.Lhmean.max())],'Lhp95':[float(d.Lhp95.min()),float(d.Lhp95.max())],'CC2m':[float(d.CC2m.min()),float(d.CC2m.max())]}}
(DATA/'psp/regional_refit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
