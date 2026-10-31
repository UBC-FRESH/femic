from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.features import rasterize
from shapely import wkb
from shapely.geometry import box
from shapely.ops import transform

CLASSES={0:'no_public_point_cloud',1:'omitted_no_fine_dem',2:'processed_no_model_cell',3:'height_only',4:'ba_volume_valid'}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--features',type=Path,required=True); ap.add_argument('--inventory',type=Path,required=True)
    ap.add_argument('--selection',type=Path,required=True); ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--boundary',type=Path,required=True); ap.add_argument('--reference-raster',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    with rasterio.open(a.reference_raster) as ref:
        transform_ref=ref.transform; shape=(ref.height,ref.width); crs=ref.crs; bounds=ref.bounds
    # TSA boundary to 3157
    b=pd.read_feather(a.boundary); geom=wkb.loads(b.geometry.iloc[0])
    geom=transform(Transformer.from_crs('EPSG:3005',str(crs),always_xy=True).transform,geom)
    tsa=rasterize([(geom,1)],out_shape=shape,transform=transform_ref,fill=0,dtype='uint8',all_touched=False).astype(bool)
    sel=json.loads(a.selection.read_text()); points=[t for t in sel['tiles'] if t['product']=='point_cloud']
    by_id={t['tile_id']:t for t in points}
    matched_ids=set(pd.read_csv(a.manifest).tile_id)
    tile_transform=Transformer.from_crs('EPSG:3005',str(crs),always_xy=True)
    def tile_geom(tile):
        return transform(tile_transform.transform, box(*tile['bbox_epsg3005']))
    all_shapes=[(tile_geom(t),1) for t in points]
    matched_shapes=[(tile_geom(by_id[i]),1) for i in matched_ids if i in by_id]
    all_mask=rasterize(all_shapes,out_shape=shape,transform=transform_ref,fill=0,dtype='uint8',all_touched=False).astype(bool)
    matched_mask=rasterize(matched_shapes,out_shape=shape,transform=transform_ref,fill=0,dtype='uint8',all_touched=False).astype(bool)
    status=np.zeros(shape,dtype='uint8')
    status[tsa & all_mask & ~matched_mask]=1
    status[tsa & matched_mask]=2
    # feature / model status
    feat=pd.read_parquet(a.features,columns=['fragment_id','x_center','y_center','Lhmean','Lhp95','CC2m'])
    inv=pd.read_parquet(a.inventory,columns=['fragment_id','attribute','value'])
    inv=inv.pivot_table(index='fragment_id',columns='attribute',values='value',aggfunc='first').reset_index()
    feat=feat.merge(inv[['fragment_id','lorey_height_m','ba_m2_ha','vol_m3_ha']],on='fragment_id',how='left')
    col=np.floor((feat.x_center.to_numpy()-bounds.left)/25).astype(np.int32)
    row=np.floor((bounds.top-feat.y_center.to_numpy())/25).astype(np.int32)
    ok=(col>=0)&(col<shape[1])&(row>=0)&(row<shape[0]); feat=feat.loc[ok].copy(); col=col[ok]; row=row[ok]
    # default processed cells with features are status 3; valid BA/volume status 4
    status[row,col]=2
    has_height=feat.lorey_height_m.notna()
    status[row[has_height],col[has_height]]=3
    valid=feat.ba_m2_ha.notna() & feat.vol_m3_ha.notna()
    status[row[valid],col[valid]]=4
    ba_out=(feat.Lhmean.notna() & (~feat.Lhmean.between(5.8017,14.1882))) | (feat.CC2m.notna() & (~feat.CC2m.between(56.3442,86.3423)))
    h_out=feat.Lhp95.notna() & (~feat.Lhp95.between(9.508,24.07))
    band2=np.zeros(shape,dtype='uint8'); band3=np.zeros(shape,dtype='uint8')
    band2[row[ba_out],col[ba_out]]=1; band3[row[h_out],col[h_out]]=1
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with rasterio.open(a.out,'w',driver='GTiff',height=shape[0],width=shape[1],count=3,dtype='uint8',crs=crs,transform=transform_ref,compress='deflate',tiled=True) as ds:
        ds.write(status,1); ds.write(band2,2); ds.write(band3,3)
        ds.set_band_description(1,'model_status'); ds.set_band_description(2,'ba_vol_predictor_outside'); ds.set_band_description(3,'height_predictor_outside')
    total=float(tsa.sum()*625/1e6); summary={'tsa_area_km2':total,'classes':{}}
    for v,n in CLASSES.items():
        c=int(((status==v)&tsa).sum()); summary['classes'][str(v)]={ 'name':n,'pixels':c,'km2':float(c*625/1e6),'share':float(c*625/1e6/total) if total else None}
    summary['ba_vol_outside_km2']=float(((band2==1)&tsa).sum()*625/1e6)
    summary['height_outside_km2']=float(((band3==1)&tsa).sum()*625/1e6)
    a.out.with_suffix('.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
