from __future__ import annotations

import math
from pathlib import Path

import laspy
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer

DATA=Path('/srv/shared-data/gep/ws4/tmp/inv01-data')
PC=DATA/'inv01_tsa23/pointcloud'; DEM=DATA/'inv01_tsa23/lidar_tiles'
cand=pd.read_csv(DATA/'psp/high_biomass_lidar_candidates.csv')
cand=cand[(cand.TSA==29)&(cand.vol>=150)&(cand.SITE_IDENTIFIER!=4024282)].copy()
dl=pd.read_csv(DATA/'psp/tsa29_high_download.csv')
cand=cand.merge(dl[['SITE_IDENTIFIER','laz_name','dem_name','point_year']],on='SITE_IDENTIFIER',how='left')
ph=pd.read_csv(DATA/'psp/raw/faib_plot_header.csv',low_memory=False)
ph['SITE_IDENTIFIER']=ph.SITE_IDENTIFIER.astype(int); ph['VISIT_NUMBER']=ph.VISIT_NUMBER.astype(int)
cand=cand.merge(ph[['SITE_IDENTIFIER','VISIT_NUMBER','PLOT_AREA_MAIN']],on=['SITE_IDENTIFIER','VISIT_NUMBER'],how='left')
trans=Transformer.from_crs('EPSG:3005','EPSG:3157',always_xy=True)
rows=[]
for _,r in cand.iterrows():
    laz=PC/r.laz_name; dem=DEM/r.dem_name
    if not laz.exists() or not dem.exists(): print('MISSING',r.SITE_IDENTIFIER,laz.exists(),dem.exists()); continue
    ux,uy=trans.transform(float(r.BC_ALBERS_X),float(r.BC_ALBERS_Y)); radius=math.sqrt(float(r.PLOT_AREA_MAIN)*10000/math.pi)
    xs=[];ys=[];zs=[]
    try:
        with laspy.open(laz) as reader:
            for ch in reader.chunk_iterator(5_000_000):
                x=np.asarray(ch.x); y=np.asarray(ch.y); z=np.asarray(ch.z); rn=np.asarray(ch.return_number)
                m=rn==1; x=x[m];y=y[m];z=z[m]
                keep=(x-ux)**2+(y-uy)**2<=radius**2
                if keep.any(): xs.append(x[keep]);ys.append(y[keep]);zs.append(z[keep])
    except Exception as exc:  # noqa: BLE001 - report the bad tile and continue
        print('READ_FAIL',r.SITE_IDENTIFIER,type(exc).__name__,exc,flush=True); continue
    if not xs: print('NO POINTS',r.SITE_IDENTIFIER); continue
    x=np.concatenate(xs);y=np.concatenate(ys);z=np.concatenate(zs)
    with rasterio.open(dem) as ds: g=np.array([v[0] for v in ds.sample(zip(x,y))],float)
    h=z-g; h=h[np.isfinite(h)]; nall=int(h.size); above=h[h>2.0]
    if above.size<10: print('FEW',r.SITE_IDENTIFIER,nall,above.size); continue
    rows.append({'SITE_IDENTIFIER':int(r.SITE_IDENTIFIER),'TSA':int(r.TSA),'MEAS_YR':int(r.MEAS_YR),'BEC_ZONE':r.BEC_ZONE,
                 'lorey_height_m':float(r.height),'ba_m2_ha':float(r.ba),'vol_m3_ha':float(r.vol),
                 'Lhmean':float(above.mean()),'Lhcv':float(above.std()/above.mean()),'Lhp95':float(np.percentile(above,95)),
                 'CC2m':float(100*above.size/nall),'all_first':nall,'above2m':int(above.size),'radius_m':radius,
                 'laz':r.laz_name,'dem':r.dem_name})
out=pd.DataFrame(rows); out.to_csv(DATA/'psp/tsa29_high_features.csv',index=False)
print(out.to_string(index=False)); print('wrote',DATA/'psp/tsa29_high_features.csv')
