# P109.4 Plan: CT Diameter Response Modulator on MKRF CT Structure

## Objective

Key the QMD response modulator on `(bucket, intensity)` rather than the flat K3Z CT shape, and resolve the double-counting risk against bucket-anchored `thn*` residual curves.

## Current State

### MKRF CT Structure
- 3 age buckets: CT35, CT40, CT45
- 3 intensity variants: low (0.35), medium (0.45), high (0.55)
- `default_intensity: "medium"`
- Current QMD config uses per-bucket values (CT35: 0.10, CT40: 0.12, CT45: 0.15)
- All buckets use the same intensity (medium) in the current runtime

### Core CT Path
- `_resolve_commercial_thinning_config_for_au()` supports `qmd_response_fraction_by_bucket`
- Keys only on `bucket_label`, not on `(bucket, intensity)`
- Falls back to flat `qmd_response_fraction` default (0.10)

### Double-Counting Risk
The concern is that if we add QMD response to:
1. The standing-stock curve (via `feature.QMD.managed.*`)
2. The CT extraction curve (via `product.QMDNumerator.managed.*`)

We might double-count the diameter response. The QMD response should only apply to the **standing-stock** curve, not the extraction curve. The extraction curve should reflect the **pre-thinning** diameter distribution.

## Plan

**Note**: The MKRF builder does NOT use the core CT path (`_resolve_commercial_thinning_config_for_au`). It builds the ForestModel XML directly via `et.SubElement` in `initialize_mkrf_runtime_package()`. Therefore, the core CT path change is not strictly necessary for MKRF, but it's good for consistency and future use.

### Phase A: Core CT path per-(bucket, intensity) override (optional, for consistency)

**Goal**: Extend the core CT `_resolve_commercial_thinning_config_for_au()` to accept a per-(bucket, intensity) `qmd_response_fraction_by_bucket_intensity` dict.

**Changes**:
- `src/femic/fmg/patchworks.py`:
  - In `_resolve_commercial_thinning_config_for_au()`, after checking `qmd_response_fraction_by_bucket`, check for `qmd_response_fraction_by_bucket_intensity` in the payload.
  - If present and the current `(bucket, intensity)` pair is in the dict, use that value; otherwise fall back to the per-bucket value; otherwise fall back to the flat value.
  - Pass the resolved value through to the config dict.

**Verification**:
- Add a unit test in `tests/test_fmg_patchworks.py` for the per-(bucket, intensity) override.
- Confirm existing tests still pass.

### Phase B: MKRF config update

**Goal**: Update `config/silviculture.mkrf.yaml` to include intensity-specific QMD response fractions.

**Changes**:
- `external/femic-mkrf-instance/config/silviculture.mkrf.yaml`:
  ```yaml
  qmd:
    enabled: true
    harvested_product_accounts_enabled: true
    qmd_response_fraction_by_bucket_intensity:
      CT35_low: 0.08
      CT35_medium: 0.10
      CT35_high: 0.12
      CT40_low: 0.10
      CT40_medium: 0.12
      CT40_high: 0.14
      CT45_low: 0.12
      CT45_medium: 0.15
      CT45_high: 0.18
    notes:
      - "Response fractions scale with intensity: higher removal -> larger QMD response."
      - "Values are placeholders pending calibration against MKRF staff guidance."
  ```

**Verification**:
- Confirm the config loads without errors.

### Phase C: MKRF builder intensity-aware QMD curve emission

**Goal**: Update `initialize_mkrf_runtime_package()` to use the correct intensity when building QMD curves.

**Changes**:
- `external/femic-mkrf-instance/src/mkrf_femic/workflows/mkrf.py`:
  - Import the intensity from the CT config (default to "medium").
  - When building QMD curves, use the intensity to resolve the correct QMD response fraction from the `qmd_response_fraction_by_bucket_intensity` dict.
  - Ensure the QMD curve is only applied to the standing-stock curve, not the extraction curve.

**Verification**:
- Rebuild the ForestModel XML.
- Confirm QMD curves are present and use the correct intensity-specific response fraction.

### Phase D: Validation

**Goal**: Validate that QMD surfaces are correctly emitted and no double-counting occurs.

**Changes**:
- Run matrix build and headless load.
- Inspect `tracks/features.csv` for `feature.QMD.managed.*`.
- Inspect `tracks/products.csv` for `product.QMDNumerator.managed.*`.
- Validate that QMD response is only on standing-stock, not on extraction.

**Verification**:
- Confirm all QMD surfaces are present and populated.
- Confirm no double-counting (QMD response only on standing-stock).

## Open Decisions

1. **Intensity-specific QMD response fractions**: Placeholder values that scale with intensity (higher removal -> larger response). Calibration will follow.
2. **Double-counting resolution**: QMD response only applies to standing-stock curve, not extraction curve. The extraction curve reflects pre-thinning diameter distribution.

## Timeline

- Phase A: 1 day (core change, tested)
- Phase B: 0.5 day (config only)
- Phase C: 1 day (builder update)
- Phase D: 1 day (build + validation)

Total: ~3.5 days.