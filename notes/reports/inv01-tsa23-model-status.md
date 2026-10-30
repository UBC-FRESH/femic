# INV-01 TSA 23 model-status mask

## Purpose

The current 25 m surface is a pilot, not a wall-to-wall inventory.  This status
mask makes its applicability explicit so the map is not used outside the
domain the cards actually cover.

## Classes

| Code | Class | Area km2 | Share of TSA |
| ---: | --- | ---: | ---: |
| 0 | No public point cloud | 2,465.7 | 20.0% |
| 1 | Omitted / no fine 1 m DEM | 1,936.7 | 15.7% |
| 2 | Processed, but no model cell | 1,993.5 | 16.1% |
| 3 | Height only | 4,113.0 | 33.3% |
| 4 | BA/volume valid | 1,839.2 | 14.9% |

The rasterized TSA area is 12,348.0 km2; the vector TSA area used elsewhere is
12,353.2 km2.  The difference is the 25 m edge approximation.

Only **14.9%** of TSA 23 has BA/volume predictions.  Height is available on
48.2% (classes 3+4).  The remaining 51.8% has no height/BA/volume surface:
20.0% has no public point cloud, 15.7% is in omitted/no-DEM tiles, and 16.1% is
processed but has no usable 25 m feature cell.

## Raster

`tsa23_model_status_25m.tif` is a three-band UInt8 raster in EPSG:3157, at the
same 25 m origin and extent as `tsa23_idf_full_25m.tif`:

1. `model_status` — 0 no point cloud, 1 omitted/no fine DEM, 2 processed/no model
   cell, 3 height only, 4 BA/volume valid.
2. `ba_vol_predictor_outside` — 1 where a feature cell is outside the published
   BA/volume predictor range.
3. `height_predictor_outside` — 1 where a feature cell is outside the published
   height predictor range.

The map is a companion product, not a replacement for the inventory raster.  It
does not add predictions; it only labels the existing surface.

## Interpretation

- Do not treat class 2, 3, or 4 as “valid everywhere”.
- Class 3 is height-only; BA/volume are unsupported.
- Classes 0 and 1 are coverage gaps, not zero biomass.
- High-biomass stands above `Lhmean` 14.1882 m / `Lhp95` 24.07 m are outside the
  published card domain; they are not fixed by this mask.
- TSA 22 (Okanagan) is not part of this product; TSA 29 is an exploratory
  transfer experiment, not a TSA 23 calibration.

## Reproduce

The mask is built by `examples/inv01_tsa23_validation/build_status_mask.py` from
the feature table, inventory table, LidarBC selection, manifest, TSA boundary,
and the reference 25 m raster.  Outputs are under the data drive, never `/tmp`:

```text
/srv/shared-data/gep/ws4/tmp/inv01-data/inv01_tsa23/tsa23_model_status_25m.tif
```

See also `inv01-tsa23-acquisition-request.md` for the next data requirement.
