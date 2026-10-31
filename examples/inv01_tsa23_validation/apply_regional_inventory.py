from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--features',type=Path,required=True); ap.add_argument('--cards',type=Path,required=True); ap.add_argument('--height-card',type=Path,required=True); ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    f=pd.read_parquet(a.features,columns=['fragment_id','x_center','y_center','Lhmean','Lhp95','CC2m'])
    cards=json.loads(a.cards.read_text())['cards']
    hm=json.loads(a.height_card.read_text())
    rows=[]
    def add(attr, valid, values, card):
        part=f.loc[valid,['fragment_id']].copy(); part['attribute']=attr; part['value']=values; part['model_id']=card.get('model_id','current-height'); part['rmse']=float(card.get('rmse',card.get('external_holdout_rmse'))); part['model_version']=card.get('model_version','2026.1'); part['unit']=card['unit']; part['source']=card.get('source','regional open-data calibration'); rows.append(part)
    # height current card
    hvalid=f.Lhp95.between(*hm['predictor_ranges']['Lhp95'])
    hvals=hm['intercept']+hm['coefficients']['Lhp95']*f.loc[hvalid,'Lhp95']*hm.get('output_scale',1.0)
    add('lorey_height_m',hvalid,hvals,hm)
    for card in cards:
        if card['attribute']=='ba_m2_ha':
            preds=list(card['coefficients']); ok=np.ones(len(f),bool)
            for name in preds: ok &= f[name].between(*card['predictor_ranges'][name])
            v=np.exp(card['intercept']+sum(card['coefficients'][n]*np.log(f.loc[ok,n]) for n in preds))*card.get('output_scale',1.0)
            add('ba_m2_ha',ok,v,card)
        elif card['attribute']=='vol_m3_ha':
            preds=list(card['coefficients']); ok=np.ones(len(f),bool)
            for name in preds: ok &= f[name].between(*card['predictor_ranges'][name])
            v=np.exp(card['intercept']+sum(card['coefficients'][n]*np.log(f.loc[ok,n]) for n in preds))*card.get('output_scale',1.0)
            add('vol_m3_ha',ok,v,card)
    inv=pd.concat(rows,ignore_index=True)
    a.out.parent.mkdir(parents=True,exist_ok=True); inv.to_parquet(a.out,index=False)
    summary={}
    for attr,g in inv.groupby('attribute'):
        summary[attr]={'cells':len(g),'mean':float(g.value.mean()),'median':float(g.value.median()),'min':float(g.value.min()),'max':float(g.value.max()),'rmse':float(g.rmse.iloc[0]),'model_id':str(g.model_id.iloc[0])}
    a.out.with_suffix('.json').write_text(json.dumps({'feature_cells':len(f),'attributes':summary},indent=2)+'\n')
    print(json.dumps({'feature_cells':len(f),'attributes':summary},indent=2))
if __name__=='__main__': main()
