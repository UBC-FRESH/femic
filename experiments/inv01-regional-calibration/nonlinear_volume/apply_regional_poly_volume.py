from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd
DATA=Path('/srv/shared-data/gep/ws4/tmp/inv01-data')
spec=json.loads((DATA/'psp/regional_poly_volume.json').read_text())
c=np.array(spec['coefficients'],dtype=float)
f=pd.read_parquet(DATA/'inv01_tsa23/features_full.parquet',columns=['fragment_id','Lhmean','CC2m'])
lh=np.log(f.Lhmean.to_numpy(float)); cc=np.log(f.CC2m.to_numpy(float))
valid=(f.Lhmean.between(*spec['range']['Lhmean']))&(f.CC2m.between(*spec['range']['CC2m']))
values=np.full(len(f),np.nan); values[valid]=np.exp(c[0]+c[1]*lh[valid]+c[2]*cc[valid]+c[3]*lh[valid]**2+c[4]*cc[valid]**2+c[5]*lh[valid]*cc[valid])
vol=pd.DataFrame({'fragment_id':f.loc[valid,'fragment_id'],'attribute':'vol_m3_ha','value':values[valid],'model_id':'tsa23-idf-gross_volume-regional-poly2-2026c','rmse':float(spec['external_rmse']),'model_version':'2026.1-exp','unit':'m3/ha','source':'FAIB PSP and LidarBC regional high-biomass fit; nonlinear log-volume model'})
base=pd.read_parquet(DATA/'inv01_tsa23/inventory_regional_full.parquet')
base=base[base.attribute!='vol_m3_ha']
inv=pd.concat([base,vol],ignore_index=True)
inv.to_parquet(DATA/'inv01_tsa23/inventory_regional_poly_volume.parquet',index=False)
summary={'spec':spec,'volume_cells':int(len(vol)),'volume_mean':float(vol.value.mean()),'volume_median':float(vol.value.median()),'volume_min':float(vol.value.min()),'volume_max':float(vol.value.max()),'total_inventory_rows':int(len(inv))}
(DATA/'inv01_tsa23/inventory_regional_poly_volume.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='spec'},indent=2))
