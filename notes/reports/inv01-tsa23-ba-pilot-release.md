# INV-01 TSA 23 BA-only pilot release

## Product

The release contains only the published TSA 23 IDF basal-area model.  Height and
volume are excluded.

| Field | Value |
| --- | --- |
| Model | `tsa23-idf-ba-2026` |
| Attribute | basal area, m2/ha |
| Rows | 2,942,755 |
| 25 m raster valid pixels | 2,942,755 |
| TSA BA coverage | **14.9% of TSA 23** |
| Full-raster coverage | 9.35% (the raster extends outside the TSA) |
| BA mean | 23.87 m2/ha |
| Strict independent validation | 36 in-range plots, RMSE **8.86 m2/ha** |
| Status | pilot; not operational |

## Artifacts

Data archive:

- `inv01_tsa23/inventory_ba_pilot.parquet`
- `inv01_tsa23/tsa23_ba_pilot_25m.tif`
- `inv01_tsa23/inventory_ba_pilot_manifest.json`

Manifest in this repository:

- `metadata/inv01/tsa23_ba_pilot_manifest.json`

## Checksums

- BA table: `800692bb763a685b2b5107e17c8c77f1805e8fb4deb78da22f465b89609cd43f`
- BA raster: `c0bb6905d2cb7448c30e0ee69d1964380677b8012d13bc471aed61c9b576e862`
- Source full grid: `19be051c05e839bebca9b252ba733a1300c138452a354e096892cc69182aaf03`
- BA model card: `c9d2c8de369af5cceb7070531d0e924452cab52b50de39d31dad3e831d82e5a9`
- Default config: `fb1fa162f92ea04dc5ddd60baf57bae7f146ba41e789f2ac8fd08eadb161caa1`

## What was not done

- No model was refit.
- No cells were extrapolated outside the card range.
- No height or volume product is included.
- No operational claim is made.
- No tag or GitHub release was created.

## Verification

- BA table rows and raster valid pixels are both 2,942,755.
- BA table and raster mean are both 23.87 m2/ha.
- The source is the existing full-grid inventory; no point-cloud rerun occurred.
- The default config resolves `--model-key ba`; height and volume require
  explicit research configuration.

## Limits

The strict BA validation has 36 in-range plots and only 7 independent TSA 23
plots.  The product is a coverage-limited pilot, not an operational inventory.
