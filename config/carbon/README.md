# Carbon crosswalks

These files are the reviewed-default crosswalks for the forest carbon domain. They are
inputs to the FEMIC carbon package exporter (P115.2), not a runtime configuration for a
specific instance.

Status: **reviewed against the current VRI/CBM/GIS sources; residual model extensions documented.** Every row carries a `confidence` and a `source` or
`notes` field. Do not treat a `low` or `medium` row as a silent default; the package
manifest must record which crosswalk version was used.

## Files

- `species_map.bc.csv` — BC species code to CBM default species name.
- `eco_boundary.bc.csv` — known TSA code to CBM administrative and eco boundary.
- `ecozone_map.bc.csv` — public VRI `CFS_ECOZONE` code to CBM eco-boundary name.
- `disturbance_map.bc.csv` — normalized WS4 treatment label to CBM disturbance type.
- `land_class.bc.csv` — default CBM land class by IFM state.
- `carbon.example.yaml` — example instance-level `carbon:` block.
- `hwp.bc.yaml` — public harvested-wood-product split, half-life, displacement, and
  end-of-life assumptions consumed by WS4 (`--hwp-config` / `--carbon-hwp`).
- `tsa24.yaml` — TSA24 defaults (Montane Cordillera, TSA `24`).
- `mkrf.yaml` — MKRF defaults (Pacific Maritime, FMU code `mkrf`).

Review packet: `notes/reports/p1151-crosswalk-review.md` (mechanical checks pass;
CBM/CFS science review pending). The checker is
`scripts/check_carbon_crosswalks.py`.

Run `femic carbon validate <package>` (or `--config config/carbon/tsa24.yaml`)
before a cross-repo handoff. The validator checks table hashes, the package
fingerprint, classifiers, the yield grid, area, and boundaries. The public-safe
`tests/fixtures/carbon/tsa24_minimal` package exercises the same contract.

## Rules

- A missing species mapping is a validation error. Use the explicit
  `Unspecified softwood species` or `Unspecified hardwood species` fallback and record
  it; do not map to zero.
- A TSA or model whose eco boundary is not listed must supply the boundary in its
  instance configuration. Do not guess.
- A treatment that does not remove biomass is marked `removes_biomass = false` and uses a
  no-stock-change CBM type.
- `ct` uses `40% commercial thinning` as an upper-bound proxy for 40% basal-area removal
  from below; actual merchantable-volume removal is normally lower.
- `mpb` uses the 10% moderate default as a variable placeholder; use a severity-specific
  type when the instance supplies one.
- Fertilization uses the public TIPSY `FertRespMOF.txt` response table and the
  thesis emissions factors. `femic carbon fertilization-audit` writes the CO2/CH4/N2O
  accounts; `femic.carbon.fertilized_curve` applies the public 10-year response to a
  yield curve. The WS4 runtime consumes the materialized curves and accounts; `f1`-`f3`
  are not mapped to a silent no-op.
- Managed forest land is class `0`; unmanaged forest land is class `16` per CBM-CFS3
  Unmanaged Forest Land. Nonforest area must supply its actual land-use class; unmapped
  IFM states are errors.
- `hwp.bc.yaml` is a public scenario input, not a calibrated estimate. Run a grid over
  half-life and displacement rather than treating the default as the answer; see
  `docs/guides/hwp-lifecycle.rst`.

## Review checklist

- [x] Species codes checked against the BC VRI data dictionary and CBM default species list.
- [x] Eco-boundary rows checked by TSA/ecozone polygon intersection, including split cases.
- [ ] Disturbance rows checked for removal and transition semantics.
- [ ] Land-class choice checked against the reporting question.
- [ ] Manifest provenance names the crosswalk version and the reviewer.
