# INV-01 standard CLI parity check

## Purpose

Verify that the term-based hybrid bundle runs through the standard
`femic lidar inventory` command, not only the experimental script.

## Inputs

- Bundle: a validated local test bundle generated from the repository LiDAR
  fixture.
- BA card: `experiments/inv01-regional-calibration/model_bundle/models/als_tsa23_idf_basal_area_regional_2026c.json`
- Volume card: `experiments/inv01-regional-calibration/hybrid_bundle/nonlinear/model.json`
- BA feature export: 7,479,672 rows with `Lhmean`, `Lhp95`
- Volume feature export: 4,745,557 rows with `Lhmean`, `CC2m`

## Commands

Explicit model paths:

```bash
femic lidar inventory \
  --bundle <validated-fixture-bundle> \
  --model experiments/inv01-regional-calibration/hybrid_bundle/nonlinear/model.json \
  --features volume_features_cli.csv \
  --output-dir cli_inventory_volume

femic lidar inventory \
  --bundle <validated-fixture-bundle> \
  --model experiments/inv01-regional-calibration/model_bundle/models/als_tsa23_idf_basal_area_regional_2026c.json \
  --features ba_features_cli.csv \
  --output-dir cli_inventory_ba
```

Config-driven rerun against the public TSA23 instance:

```bash
femic lidar inventory \
  --bundle <validated-fixture-bundle> \
  --features ba_features_cli.csv \
  --model-key ba \
  --instance-root <femic-tsa23-instance> \
  --output-dir cli_config_ba \
  --generated-utc 2026-10-31T00:00:00Z

femic lidar inventory \
  --bundle <validated-fixture-bundle> \
  --features volume_features_cli.csv \
  --model-key volume \
  --instance-root <femic-tsa23-instance> \
  --output-dir cli_config_volume \
  --generated-utc 2026-10-31T00:00:00Z
```

## Result

| Attribute | CLI rows | Script rows | Max absolute difference | RMSE difference |
| --- | ---: | ---: | ---: | ---: |
| BA | 7,479,672 | 7,479,672 | 4.3e-14 | 3.5e-15 |
| Volume | 4,745,557 | 4,745,557 | 2.2e-12 | 7.0e-14 |

Both explicit-path outputs are numerically identical to the script-generated
hybrid surface.  The config-driven rerun is **byte-identical** to both explicit
outputs:

| Attribute | Rows | SHA-256 | Explicit output |
| --- | ---: | --- | --- |
| BA | 7,479,672 | `d7f7a8a4...96ce07` | identical |
| Volume | 4,745,557 | `fd9bf1df...d0dab0` | identical |

This confirms that `--model-key` resolves the same cards from
`config/inventory/experimental.yaml` and that the instance root is the correct
base for relative model paths.

## Artifacts

Data-root outputs:

- `inv01_tsa23/cli_inventory_ba/inventory_als.csv`
- `inv01_tsa23/cli_inventory_volume/inventory_als.csv`
- `inv01_tsa23/cli_config_ba/inventory_als.csv`
- `inv01_tsa23/cli_config_volume/inventory_als.csv`
- `inv01_tsa23/inventory_regional_poly_volume.parquet`

The test bundle is only a validation carrier; feature tables are explicit and
the full-grid feature export is the real input.

## Decision

The term-based card is no longer script-only.  `femic lidar inventory` can
consume it directly through the standard model-card path.
