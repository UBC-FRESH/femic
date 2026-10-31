from __future__ import annotations

import math
from pathlib import Path

import laspy
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer

DATA=Path('/srv/shared-data/gep/ws4/tmp/inv01-data'); PC=DATA/'inv01_tsa23/pointcloud'; DEM=DATA/'inv01_tsa23/lidar_tiles'
df=pd.read_csv(DATA/'psp/regional_high_download.csv')
ph=pd.read_csv(DATA/'psp/raw/faib_plot_header.csv',low_memory=False)
ph['SITE_IDENTIFIER']=ph.SITE_IDENTIFIER.astype(int); ph['VISIT_NUMBER']=ph.VISIT_NUMBER.astype(int)
df=df.merge(ph[['SITE_IDENTIFIER','VISIT_NUMBER','PLOT_AREA_MAIN']],on=['SITE_IDENTIFIER','VISIT_NUMBER'],how='left')
EPSG={'utm9':26909,'utm10':26910,'utm11':26911,'utm12':26912}
rows=[]
for _,r in df.iterrows():
    laz=PC/r.laz_name; dem=DEM/r.dem_name
    if not laz.exists() or not dem.exists(): print('MISSING',r.SITE_IDENTIFIER,laz.exists(),dem.exists(),flush=True); continue
    if pd.isna(r.PLOT_AREA_MAIN): print('NO_AREA',r.SITE_IDENTIFIER,flush=True); continue
    crs=EPSG.get(str(r.projection),26910); transformer=Transformer.from_crs('EPSG:3005',f'EPSG:{crs}',always_xy=True)
    ux,uy=transformer.transform(float(r.BC_ALBERS_X),float(r.BC_ALBERS_Y)); radius=math.sqrt(float(r.PLOT_AREA_MAIN)*10000/math.pi)
    xs=[];ys=[];zs=[]
    try:
        with laspy.open(laz) as reader:
            for ch in reader.chunk_iterator(5_000_000):
                x=np.asarray(ch.x); y=np.asarray(ch.y); z=np.asarray(ch.z); rn=np.asarray(ch.return_number)
                m=rn==1; x=x[m];y=y[m];z=z[m]
                keep=(x-ux)**2+(y-uy)**2<=radius**2
                if keep.any(): xs.append(x[keep]);ys.append(y[keep]);zs.append(z[keep])
    except Exception as exc:  # noqa: BLE001 - report bad tile and continue
        print('READ_FAIL',r.SITE_IDENTIFIER,type(exc).__name__,flush=True); continue
    if not xs: print('NO_POINTS',r.SITE_IDENTIFIER,flush=True); continue
    x=np.concatenate(xs);y=np.concatenate(ys);z=np.concatenate(zs)
    try:
        with rasterio.open(dem) as ds: g=np.array([v[0] for v in ds.sample(zip(x,y))],float)
    except Exception as exc:  # noqa: BLE001 - report bad tile and continue
        print('DEM_FAIL',r.SITE_IDENTIFIER,type(exc).__name__,flush=True); continue
    h=z-g; h=h[np.isfinite(h)]; nall=int(h.size); above=h[h>2.0]
    if above.size<10: print('FEW',r.SITE_IDENTIFIER,nall,above.size,flush=True); continue
    rows.append({'SITE_IDENTIFIER':int(r.SITE_IDENTIFIER),'TSA':int(r.TSA),'MEAS_YR':int(r.MEAS_YR),'BEC_ZONE':r.BEC_ZONE,'BEC_SBZ':r.BEC_SBZ,
                 'height':float(r.height),'ba':float(r.ba),'vol':float(r.vol),'Lhmean':float(above.mean()),
                 'Lhcv':float(above.std()/above.mean()),'Lhp95':float(np.percentile(above,95)),'CC2m':float(100*above.size/nall),
                 'all_first':nall,'above2m':int(above.size),'radius_m':radius,'laz':r.laz_name,'dem':r.dem_name,'projection':r.projection})
out=pd.DataFrame(rows); out.to_csv(DATA/'psp/regional_high_features.csv',index=False)
print(out.round(2).to_string(index=False)); print('wrote',DATA/'psp/regional_high_features.csv','rows',len(out))
