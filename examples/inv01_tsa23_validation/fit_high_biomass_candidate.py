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
    hold_path=Path(__file__).resolve().parents[2] / 'notes/reports/inv01-tsa23-psp-holdout.csv'
hold=pd.read_csv(hold_path)
hold=hold.rename(columns={'lorey_height_m_obs':'lorey_height_m','ba_m2_ha_obs':'ba_m2_ha','vol_m3_ha_obs':'vol_m3_ha'})
rec=pd.read_csv(DATA/'psp_analysis/recent_pointcloud_visits.csv')
tmap=dict(zip(rec.SITE_IDENTIFIER,rec.tile_id)); tmap.update({int(s):'lidarbc:4:117213' for s in hold.SITE_IDENTIFIER})
cols=['SITE_IDENTIFIER','Lhmean','Lhp95','CC2m','lorey_height_m','ba_m2_ha','vol_m3_ha']
a=train[cols].copy(); h=hold[cols].copy(); d=pd.concat([a,h],ignore_index=True); d['tile_id']=d.SITE_IDENTIFIER.map(tmap); d['region']=np.where(d.SITE_IDENTIFIER.isin(train.SITE_IDENTIFIER),'TSA23-train','TSA23-holdout')
high=pd.read_csv(DATA/'psp/tsa29_high_features.csv')
high['tile_id']=high.SITE_IDENTIFIER.map(pd.read_csv(DATA/'psp/high_biomass_lidar_candidates.csv').set_index('SITE_IDENTIFIER').tile_id)
high['region']='TSA29-high'
d=pd.concat([d,high[cols+['tile_id','region']]],ignore_index=True)

def fit_height(x):
 c=np.linalg.lstsq(np.column_stack([np.ones(len(x)),x.Lhp95]),x.lorey_height_m,rcond=None)[0]; return c
def fit_ba(x):
 c=np.linalg.lstsq(np.column_stack([np.ones(len(x)),np.log(x.Lhmean),np.log(x.CC2m)]),np.log(x.ba_m2_ha),rcond=None)[0]; return c
def fit_vol(x):
 c=np.linalg.lstsq(np.column_stack([np.ones(len(x)),np.log(x.Lhmean),np.log(x.CC2m)]),np.log(x.vol_m3_ha),rcond=None)[0]; return c
def ph(c,x): return c[0]+c[1]*x.Lhp95
def pb(c,x): return np.exp(c[0]+c[1]*np.log(x.Lhmean)+c[2]*np.log(x.CC2m))
def pv(c,x): return np.exp(c[0]+c[1]*np.log(x.Lhmean)+c[2]*np.log(x.CC2m))
def met(pred,obs):
 e=pred-obs; return {'n':len(e),'bias':float(e.mean()),'mae':float(e.abs().mean()),'rmse':float(np.sqrt((e*e).mean()))}
base=d[d.region.isin(['TSA23-train','TSA23-holdout'])]
highd=d[d.region=='TSA29-high']
out={'n':{'tsa23_train':len(train),'tsa23_holdout':len(hold),'tsa29_high':len(highd)},'models':{}}
for key,fit,pred,obs,cur in [
 ('height',fit_height,ph,'lorey_height_m',lambda x:1.9441063309517714+0.8351084469592212*x.Lhp95),
 ('ba',fit_ba,pb,'ba_m2_ha',lambda x:np.exp(-4.724750214946937+0.8686310009684395*np.log(x.Lhmean)+1.3794686095244624*np.log(x.CC2m))*1.008780042159369),
 ('volume',fit_vol,pv,'vol_m3_ha',lambda x:np.exp(-4.009416713953133+1.7395991112544076*np.log(x.Lhmean)+1.1516782963514058*np.log(x.CC2m))*1.004526898452813)]:
    cur_hold=met(cur(hold),hold[obs])
    fit_train=fit(base[base.region=='TSA23-train'])
    fit_plus=fit(base[base.region=='TSA23-train'].pipe(lambda x: pd.concat([x,highd],ignore_index=True)))
    fit_all=fit(d)
    out['models'][key]={
      'current_holdout':cur_hold,
      'fit_tsa23_train_holdout':met(pred(fit_train,hold),hold[obs]),
      'fit_plus_tsa29_holdout':met(pred(fit_plus,hold),hold[obs]),
      'candidate_all_coefficients':[float(v) for v in fit_all],
      'candidate_range':{'min':float(d[obs].min()),'max':float(d[obs].max())},
    }
    if key!='height':
      out['models'][key]['candidate_scale']=1.0
(out_path:=DATA/'psp/high_biomass_refit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
