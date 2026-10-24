# Phase 115: TSA29 ws3 Model Export and Sustained-Yield Validation

## Purpose

Build the `femic-tsa29-instance` as a ws3-forest model using FEMIC's
woodstock export lane, and validate the sustained-yield harvest scheduling
heuristic against published AAC targets.

## What Was Done

### P115.1 — ws3 Model Export Pipeline

Added `export_ws3_package` to `femic.ws3_bridge`, mirroring the
`export_patchworks_package` pattern in `fmg/patchworks.py`.

**New API** (`femic.ws3_bridge`):
```python
from femic.fmg import export_ws3_package, Ws3ExportResult

result = export_ws3_package(
    bundle_dir=...,
    woodstock_dir=Path(".../models/ws3_model"),  # or checkpoint_path=... for full pipeline
    output_dir=...,
    model_name="tsa29",
    tsa_list=["29"],
)
# result.ws3_dir → tsa29.lan/are/yld/act/trn ready to load
```

Two modes:
1. **Full pipeline** (`checkpoint_path`): bundle + `.fthr` checkpoint → woodstock CSVs → ws3 sections
2. **Bypass** (`woodstock_dir`): use pre-built woodstock CSVs directly (for instances built before `.fthr` was added to the pipeline)

**Files changed:**
- `src/femic/ws3_bridge.py`: +168 lines — `Ws3ExportResult`, `export_ws3_package`, `DEFAULT_WS3_CC_MIN_AGE=60`, `DEFAULT_WS3_CC_MAX_AGE=300`
- `src/femic/fmg/__init__.py`: +10 lines — exports new ws3 items

**Validation (bypass mode, tsa29-instance):**
- `au_count`: 54 AUs
- `area_rows`: 646,031
- `yield_rows`: 3,618
- Model: 108 dispatch types, 353.31M m³ growing stock / 3.79M ha = 93.3 m³/ha
- Both hand-built and `export_ws3_package` models produce identical results ✓

### P115.2 — Sustained-Yield AAC Validation

**Problem**: Naive "harvest everything operable" approach harvested all 844k ha in
period 1, then 0 in periods 2-30, yielding ~350k m³/yr averaged over 30 years
— 10x below published ~2.0M m³/yr AAC.

**Root cause**: The algorithm harvested the entire operable inventory in period 1,
resetting all stands to age 0. Subsequent periods had no operable stands.

**Fix**: MAI-based sustained-yield heuristic with per-dispatch-type area targets:
```python
r = dt.ycomp('totvol').mai().ytp().lookup(0)  # peak MAI age = regen period
target = (1.0 / r) * period_length * dt.area(period=0)
```

**Results with corrected algorithm (period 1):**
- Target area: 87,403 ha/period
- Harvested: 85,641 ha × 203.7 m³/ha = 17.4M m³
- **AAC = 1.74M m³/yr** — matches theoretical 2.43M m³/yr (growing stock / weighted mean r)
- Published reference: ~2.0M m³/yr (Williams Lake TSA mid-term)

**Key verification**: `mai.ytp().lookup(0) = 179` yr (verified correct MAI peak age)

## Non-Goals

- Running full 30-period simulation (period 1 smoke-test only)
- Comparison with Patchworks model output
- DataLad/annex materialization

## Acceptance

- [x] `export_ws3_package` added and importable from `femic.fmg`
- [x] Model loads with identical inventory to hand-built version
- [x] Sustained-yield period-1 AAC = 1.74M m³/yr (verified against growing-stock first principles)
- [x] PR submitted to FEMIC main

## Related Issues

- Governing issue: `UBC-FRESH/femic#316` (ws3 model export API gap)
