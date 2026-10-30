# INV-01 TSA 23 validation and gap analysis

**Data-root rule:** all project data lives under
`/srv/shared-data/gep/ws4/tmp/inv01-data` on the data drive.  Do not write
INV-01 data, caches, or outputs under `/tmp` or the root drive.

This directory reproduces the VRI screening and omitted-tile priority analysis.
Both outputs are **not** independent field validation.

## VRI reconciliation

```bash
python examples/inv01_tsa23_validation/vri_reconcile.py \
  --features /srv/shared-data/gep/ws4/tmp/inv01-data/inv01_tsa23/features_full.parquet \
  --inventory /srv/shared-data/gep/ws4/tmp/inv01-data/inv01_tsa23/inventory_full.parquet \
  --vri /srv/shared-data/gep/iversen-jamie-msc-thesis/femic-tsa23-instance/data/ria_vri_vclr1p_checkpoint8.feather \
  --boundary /srv/shared-data/gep/iversen-jamie-msc-thesis/femic-tsa23-instance/data/tsa_boundaries.feather \
  --out-dir /srv/shared-data/gep/ws4/tmp/inv01-data/validation-output \
  --write-cells
```

The optional `--write-cells` writes the 8.19 M-row joined table; omit it for a
metrics-only run.  Outputs are `vri_metrics.json` and, if requested,
`cells_vri.parquet`.

## Omitted-tile priority

```bash
python examples/inv01_tsa23_validation/gap_priority.py \
  --selection /srv/shared-data/gep/ws4/tmp/inv01-data/inv01_tsa23/lidarbc_selection_full.json \
  --manifest /srv/shared-data/gep/ws4/tmp/inv01-data/inv01_tsa23/tile_manifest_full.csv \
  --boundary /srv/shared-data/gep/iversen-jamie-msc-thesis/femic-tsa23-instance/data/tsa_boundaries.feather \
  --vri /srv/shared-data/gep/iversen-jamie-msc-thesis/femic-tsa23-instance/data/ria_vri_vclr1p_checkpoint8.feather \
  --vertices /srv/shared-data/gep/ws4/fresh-road/examples/tsa23_c5_network/route_fixture/vertices.csv \
  --destinations /srv/shared-data/gep/ws4/fresh-road/examples/tsa23_c5_network/route_fixture/destinations.csv \
  --out-dir /srv/shared-data/gep/ws4/tmp/inv01-data/validation-output
```

Outputs are `inv01-tsa23-gap-priority.csv`, `.gpkg`, and `.json`.  The score is a
coverage screen, not an economic ranking.

## Full PSP holdout

Fetch the public FAIB PSP archive with Nemora first, then run the holdout script:

```bash
python examples/inv01_tsa23_validation/psp_holdout.py \
  --raw-dir /srv/shared-data/gep/ws4/tmp/inv01-data/psp/raw \
  --selection /srv/shared-data/gep/ws4/tmp/inv01-data/inv01_tsa23/lidarbc_selection_full.json \
  --manifest /srv/shared-data/gep/ws4/tmp/inv01-data/inv01_tsa23/tile_manifest_full.csv \
  --pointcloud-dir /srv/shared-data/gep/ws4/tmp/inv01-data/inv01_tsa23/pointcloud \
  --dem-dir /srv/shared-data/gep/ws4/tmp/inv01-data/inv01_tsa23/lidar_tiles \
  --out-dir /srv/shared-data/gep/ws4/tmp/inv01-data/validation-output \
  --sites 4025090 4025091 4025094 4025095
```

The 2019 point-cloud/DEM files for the four held-out plots must be present in
the two directories.  The script writes `psp_holdout.csv` and
`psp_recent_candidates.csv`.

## Figures

```bash
python examples/inv01_tsa23_validation/make_validation_figures.py \
  --cells-vri /srv/shared-data/gep/ws4/tmp/inv01-data/validation-output/cells_vri.parquet \
  --gap-gpkg /srv/shared-data/gep/ws4/tmp/inv01-data/validation-output/inv01-tsa23-gap-priority.gpkg \
  --selection /srv/shared-data/gep/ws4/tmp/inv01-data/inv01_tsa23/lidarbc_selection_full.json \
  --manifest /srv/shared-data/gep/ws4/tmp/inv01-data/inv01_tsa23/tile_manifest_full.csv \
  --boundary /srv/shared-data/gep/iversen-jamie-msc-thesis/femic-tsa23-instance/data/tsa_boundaries.feather \
  --vertices /srv/shared-data/gep/ws4/fresh-road/examples/tsa23_c5_network/route_fixture/vertices.csv \
  --destinations /srv/shared-data/gep/ws4/fresh-road/examples/tsa23_c5_network/route_fixture/destinations.csv \
  --out-dir /srv/shared-data/gep/ws4/tmp/inv01-data/validation-output/figures
```

## Results

See:

- `notes/reports/inv01-tsa23-vri-reconciliation.md`
- `notes/reports/inv01-tsa23-gap-priority.md`
- `notes/reports/inv01-tsa23-psp-holdout.md`

Key results: VRI disagreement is much larger than the pilot LOOCV errors
(height RMSE 7.65 m, BA 11.49 m2/ha, volume 92.83 m3/ha at cell level), and 907
omitted tiles cover 1,962 km2 inside TSA 23, including 861 km2 of VRI THLB.
