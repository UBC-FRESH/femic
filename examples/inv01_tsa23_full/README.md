# INV-01 TSA 23 full-mosaic runbook

**Data-root rule:** project data and caches belong under
`/srv/shared-data/gep/ws4/tmp/inv01-data` on the data drive.  Do not write
INV-01 data or outputs under `/tmp` or the root drive.

This directory preserves the exact workflow used for the 2026-10-30 TSA 23
point-cloud run.  It is a research runbook, not a production scheduler.

## Result

- 5,899 point-cloud/DEM tile pairs
- 93 batches of 64 tiles
- 9,523,476 TSA-clipped 25 m cells
- 6,573,196 height-domain cells
- 2,942,755 basal-area/volume-domain cells
- means: 16.09 m height, 23.87 m2/ha BA, 139.33 m3/ha volume
- coverage: 64% of TSA 23 by tile footprint; 48% by modelled cell area

The model cards are the 14-plot TSA 23 IDF pilot cards.  Results are not an
operational inventory.

## Architecture

```text
LidarBC public HTTPS
        |
        | download (Sockeye login/DTN)
        v
Sockeye /scratch/st-gep-1/gep/inv01/raw
        |
        | per-tile first-return metrics, global 25 m grid
        v
Sockeye /scratch/st-gep-1/gep/inv01/parts/batch_XXXX.parquet
        |
        | rsync to local VM
        v
local reduce: TSA clip, dedup, model cards, GeoTIFF

Chinook archive:
  inv01/raw/laz, inv01/raw/dem, inv01/parts2, inv01/products
  uploaded through Globus guest collection "UBC FRESH Chinook Allocation"
```

Compute nodes have no public internet.  The public LidarBC data is downloaded to
Sockeye scratch first; Chinook is the durable archive.

## 1. Build the tile manifest

Run from the FEMIC repository with the `femic` environment:

```bash
python examples/inv01_tsa23_full/build_manifest.py \
  --selection /path/to/lidarbc_selection_full.json \
  --boundary /path/to/tsa23_boundary.gpkg \
  --output tile_manifest_full.csv
```

The selection JSON is produced by:

```bash
femic lidar discover \
  --bbox 1257085.3,668473.7,1395390.7,811393.5 \
  --product point_cloud \
  --product dem \
  --manifest-path lidarbc_selection_full.json
```

The manifest pairs each point-cloud tile with a 1 m DEM tile.  If the TSA
boundary file has multiple features, dissolve it first.

## 2. Download to Sockeye scratch

Make the directories:

```bash
export INV01_ROOT=/scratch/st-gep-1/gep/inv01
mkdir -p "$INV01_ROOT"/{raw/laz,raw/dem,parts,manifests/logs,logs}
```

Split the manifest into download shards and compute batches:

```bash
python examples/inv01_tsa23_full/split_manifest.py \
  --manifest tile_manifest_full.csv \
  --download-shards 2 \
  --batch-size 64 \
  --output-dir "$INV01_ROOT/manifests"
```

Download on a data-transfer node, or on a login node for a short pilot:

```bash
python examples/inv01_tsa23_full/download_tiles.py \
  "$INV01_ROOT/manifests/download_a.csv" \
  "$INV01_ROOT/raw/laz" \
  "$INV01_ROOT/raw/dem" 8
```

The downloader resumes `.part` files and treats a complete `.part` that returns
HTTP 416 as success.

## 3. Process batches

Install the compute environment on Sockeye:

```bash
module load gcc/7.5.0 python/3.12.7
python3 -m venv /arc/project/st-gep-1/gep/venv-inv01-312
/arc/project/st-gep-1/gep/venv-inv01-312/bin/pip install \
  numpy pandas rasterio 'laspy[lazrs]' pyarrow geopandas shapely pyproj fiona
```

Edit the account/path variables in `compute_batches.sbatch`, then set the
execution paths and submit:

```bash
export INV01_ROOT=/scratch/st-gep-1/gep/inv01
export PYTHON=/arc/project/st-gep-1/gep/venv-inv01-312/bin/python
export FEMIC_SRC="$PWD/src"
export RUNBOOK_DIR="$PWD/examples/inv01_tsa23_full"
cd "$INV01_ROOT"
sbatch "$RUNBOOK_DIR/compute_batches.sbatch"
```

The worker uses a global grid in UTM 10N:

- `grid_origin_x = 549275`
- `grid_origin_y = 5784675`
- `grid_size_m = 25`
- `min_returns = 10`
- `min_cover_pct = 10`

A batch job writes one Parquet part.  Existing parts are skipped.

## 4. Reduce locally

```bash
python examples/inv01_tsa23_full/reduce_full.py \
  --parts /srv/shared-data/gep/ws4/tmp/inv01-data/full-output/parts \
  --boundary /srv/shared-data/gep/iversen-jamie-msc-thesis/femic-tsa23-instance/data/tsa_boundaries.feather \
  --models femic/config/inventory/models \
  --out-dir /srv/shared-data/gep/ws4/tmp/inv01-data/full-output
```

The reducer:

- concatenates all batch parts;
- deduplicates `fragment_id`;
- clips cell centres to the TSA 23 polygon;
- applies the TSA 23 IDF model cards within their predictor ranges;
- writes `features_full.parquet`, `inventory_full.parquet`, `summary_full.json`;
- optionally writes a 3-band 25 m GeoTIFF.

## 5. Archive through Globus

Use the `UBC FRESH Chinook Allocation` guest collection.  The run archived:

- `inv01/raw/laz` — 5,899 LAZ, 2.16 TB
- `inv01/raw/dem` — 3,167 DEM, 20.6 GB
- `inv01/parts2` — 95 Parquet files
- `inv01/products` — features, inventory, summary, GeoTIFF

## Known limits

- 907 point-cloud tiles had no matching 1 m DEM and were skipped.
- 24 tiles had no cells with enough first returns.
- 64% tile-footprint coverage; 48% modelled-cell coverage.
- S3 object reads were AccessDenied from both local and Sockeye; the run used
  Globus and Sockeye scratch.  Do not treat S3 as the active data path.
- No independent P48/P49 or full VRI validation.
