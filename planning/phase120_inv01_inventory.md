# Phase 120: INV-01 TSA 23 LiDAR Inventory Closure

Parent issue: #536

Branch: `feature/p120-inv01-inventory`

Status: active

## Goal

Close the INV-01 TSA 23 LiDAR inventory work with a default product that only
contains attributes supported by independent validation, and with an auditable
validation record.

## Scope

- Validate the published height card on the strict 38-plot set and the 435-plot
  time-lag sensitivity set.
- If height fails independent validation, remove it from the default product.
- Keep BA only if it remains the supported default.
- Keep volume research-only; it is withheld from the default product.
- Record the decision and evidence in the roadmap, changelog, notes, and public
  TSA23 instance.
- Run the repository gates and open the phase pull request for approval.

## Out of scope

- New model fitting.
- Operational inventory claims.
- Changes to forest-level objectives, constraints, growth, or solver behavior.
- New field-data acquisition.
- Changes to the public instance beyond the default model configuration and
  documentation.

## Existing evidence

The INV-01 work was merged before this phase issue existed.  This phase provides
the missing phase/task governance and closes the product decision.  Prior merged
work includes:

- `#469` inventory.als contract and reader.
- `#470` TSA 23 IDF pilot cards.
- `#475` full TSA 23 inventory run and reproducibility.
- `#477` full PSP holdout check.
- `#480` high-biomass domain expansion.
- `#494` regional BA calibration.
- `#499` regional model bundle.
- `#505` hybrid regional bundle.
- `#506` term-based model support.
- `#513` config-driven inventory CLI.
- `#516` hybrid-versus-current comparison.
- `#518` config-driven full-grid parity.
- `#520` independent BC IDF validation.
- `#524` default published model config.
- `#528` refit and applicability experiment.
- `#530` strict validation and time-lag sensitivity.
- `#532` time-aware refit.
- `#534` BA-height default documentation.
- `#535` public instance pointer.

The prior branches were not named `feature/p120-...` and did not have P120
issues.  That is recorded as a deviation in the phase closeout; it is not
presented as compliant history.

## Validation decision

- Strict current-condition set: 38 independent plots within five years.
- Expanded recent set: 56 plots, including 18 fallback tiles at 6-11 years.
- Time-lag sensitivity: 435 independent plots.
- BA: strict 36 in-range, RMSE 8.86 m2/ha.
- Volume: strict 28 in-range, RMSE 67.02 m3/ha; no independent TSA 23 volume
  plot is in range.
- Height: strict 19 in-range, RMSE 2.54 m; TSA 23 strict 6 in-range, RMSE
  4.18 m.  Height fails the independent check.

Therefore the default product is **BA only**.  Height and volume remain
available as explicit research cards, not default products.

## Tasks

- [ ] P120.1 Validate height and finalize the default product (`#537`).
  - [ ] Extract height observations.
  - [ ] Evaluate strict and time-lag sets.
  - [ ] Set the default product to BA only.
  - [ ] Update docs, roadmap, changelog, and public instance.
  - [ ] Run gates and smoke test.
  - [ ] Open the phase pull request.

## Acceptance criteria

- Height strict/time-lag evaluation is recorded with in-range counts.
- The default config is BA-only and resolves through `--model-key ba`.
- Volume and height require explicit research configuration/card paths.
- Tests, lint, types, and Sphinx pass.
- The phase pull request is open for maintainer approval.

## Verification

- `pytest -q tests/test_lidar_inventory.py`
- `ruff check src tests`
- `mypy src`
- `sphinx-build -b html docs _build/html -W`
- One-row default-config CLI smoke test using the public TSA23 instance.

## Artifacts

- `notes/reports/inv01-tsa23-height-validation.md`
- `notes/reports/phase120-closeout.md`
- `config/inventory/default.yaml` in the public TSA23 instance
