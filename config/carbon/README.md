# Carbon crosswalks

These files are the reviewed-default crosswalks for the forest carbon domain. They are
inputs to the FEMIC carbon package exporter (P115.2), not a runtime configuration for a
specific instance.

Status: **draft for CBM/CFS review**. Every row carries a `confidence` and a `source` or
`notes` field. Do not treat a `low` or `medium` row as a silent default; the package
manifest must record which crosswalk version was used.

## Files

- `species_map.bc.csv` — BC species code to CBM default species name.
- `eco_boundary.bc.csv` — known TSA code to CBM administrative and eco boundary.
- `disturbance_map.bc.csv` — normalized WS4 treatment label to CBM disturbance type.
- `land_class.bc.csv` — default CBM land class by IFM state.
- `carbon.example.yaml` — example instance-level `carbon:` block.
- `tsa24.yaml` — TSA24 defaults (Montane Cordillera, TSA `24`).
- `mkrf.yaml` — MKRF defaults (Pacific Maritime, FMU code `mkrf`).

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
- A commercial thinning with unknown intensity uses `Partial cutting` and is flagged for
  replacement when the intensity is known.
- The first version uses land class `0` for both managed and unmanaged area, matching the
  WS3 reference. `16` is available as an opt-in.

## Review checklist

- [ ] Species defaults checked against the CBM default species list.
- [ ] Eco-boundary rows checked against the instance's BEC/TSA metadata.
- [ ] Disturbance rows checked for removal and transition semantics.
- [ ] Land-class choice checked against the reporting question.
- [ ] Manifest provenance names the crosswalk version and the reviewer.
