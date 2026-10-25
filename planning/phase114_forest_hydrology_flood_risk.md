# Forest Hydrology And Flood-Risk Optimization Expansion

Status: active (2026-10-25)
Branch: `feature/p114-forest-hydrology-flood-risk`
Parent issue: `#351`
Scope: FEMIC producer layer, WS4 spatial scheduling, FHOPS operations
Entry point: Younes Alila's recent forest-hydrology work, extended with other
hydrology traditions and process models.

## Objective

Add a landscape-level hydrology and flood-risk capability that can answer:

> Given a spatial forest estate, a multi-year harvest plan, and a road
> construction/decommissioning plan, which spatiotemporal pattern minimizes
> flood risk at downstream receptors while remaining economically and
> operationally feasible?

This is a decision-support and screening capability. It is not a regulatory
flood-risk determination, a design-flood service, or a legal riparian
assessment.

## What The Recent Literature Changes

Alila and collaborators argue that the old "harvest area -> mean peak-flow
change" framing is inadequate. Their recent work treats peak flows as a
stochastic, frequency-dependent response:

- Alila, Kuraś, Schnorbus & Hudson (2009), *Forests and floods: A new paradigm
  sheds light on age-old controversies*, Water Resources Research,
  doi:10.1029/2008WR007207.
- Kuraś, Alila & Weiler (2012), *Forest harvesting effects on the magnitude and
  frequency of peak flows can increase with return period*, Water Resources
  Research, doi:10.1029/2011WR010705.
- Green & Alila (2012), *A paradigm shift in understanding and quantifying the
  effects of forest harvesting on floods in snow environments*, Water Resources
  Research, doi:10.1029/2012WR012449.
- Schnorbus & Alila (2013), *Peak flow regime changes following forest
  harvesting in a snow-dominated basin: effects of harvest area, elevation, and
  channel connectivity*, Water Resources Research,
  doi:10.1029/2012WR011901.
- Pham, Alila & Caldwell (2025), *Stochastic framework reveals the controls of
  forest treatment - peakflow causal relations in rain environment*, Journal of
  Hydrology 661:133704.
- Rong, Bishop & Alila (2026), *Stochastic hydrology reveals the controls of
  forest harvesting - peakflow causal relations in snow-transient environment*,
  Advances in Water Resources, doi:10.1016/j.advwatres.2026.105432.
- Pearson-Atkins et al. (2026), *Nonstationary frequency pairing reveals a
  highly sensitive peak flow regime to harvesting*, Forest Ecology and
  Management.

The planning implications are:

1. Report return-period-specific changes, not one mean-peak coefficient.
2. Treat rain, rain-on-snow, and snowmelt regimes separately.
3. Represent landscape position: elevation band, aspect, channel connectivity,
   and the spatial arrangement of harvest, not only total area.
4. Treat roads as a first-class hydrologic disturbance with construction,
   use, maintenance, and decommissioning phases.
5. Carry uncertainty and nonstationarity explicitly; a single deterministic
   response curve is not enough.
6. Keep ECA-style metrics as screening diagnostics only. They are not the
   response model.

Other hydrology traditions must be in the design:

- Paired-watershed and nonstationary flood-frequency analysis (Jones & Grant
  1996; Moore & Wondzell 2005; McEachran et al. 2023).
- Road hydrology and road-stream connectivity (Wemple et al. 1996, 2003;
  Jones et al. 2000; Kastridis 2020).
- Process-based distributed models: DHSVM (Wigmosta et al. 1994), RHESSys
  (Tague & Band 2004), CRHM (Pomeroy et al. 2007), SUMMA (Clark et al. 2015).
- Engineering flood models such as HEC-HMS and SWAT where a regulatory or
  infrastructure question requires them.
- Bayesian hierarchical and machine-learning surrogates for uncertainty and
  fast scenario evaluation.

## What Not To Build

- A single "flood coefficient" applied uniformly across the estate.
- A model that assumes harvest area alone determines risk.
- A model that ignores road construction timing, connectivity, or persistence.
- A process model embedded directly in the MILP inner loop.
- A provincial-scale hydrology mirror or a private-data ingestion path.
- A legal or regulatory flood map presented as authoritative.

## Existing Surfaces To Build On

The expansion should reuse what the repositories already have:

- **FEMIC:** LidarBC discovery/materialization, native terrain and slope,
  stream candidates, product bundles, FWA/stream/riparian source layers in the
  TSR recipes, and public-data/DataLad patterns.
- **WS4:** one-year simulation, fragment/block spatial structure, adjacency and
  patch rules, a road segment network with haul/build/maintenance route
  accounts, used-road outputs, MILP plus heuristic optimization, and a
  compiled-dataset contract.
- **FHOPS:** `RoadConstruction` jobs, road build/availability/dependency
  variables in tactical planning, road capacity and cost handling, and
  operational harvest/road sequencing.

The missing pieces are the hydrologic domain/response layer, the disturbance
ledger that connects schedules to watershed response, and a risk objective that
spans all three repositories.

## Architecture

### FEMIC: producer of hydrologic data and response products

FEMIC should own:

- Watershed, stream-reach, road, and receptor domains.
- Hydrologic response units and disturbance ledgers.
- Screening metrics and their caveats.
- Stochastic flood-frequency response surfaces.
- Process-model adapters and scenario manifests.
- Surrogate training, validation, and applicability domains.
- Versioned hydrologic response bundles for WS4 and FHOPS.

### WS4: spatial harvest scheduling and risk optimization

WS4 should own:

- Harvest-timing decision variables at fragment/block level.
- Spatial pattern metrics and adjacency/green-up rules.
- Road construction/decommission decision variables at the scheduling layer.
- Flood-risk objective and constraints from the FEMIC response bundle.
- Multi-objective and robust optimization.
- Schedule validation and Pareto reporting.

### FHOPS: operational road and harvest execution

FHOPS should own:

- Road-construction job attributes: length, soil profile, crossing type,
  connectivity, culvert, decommissioning, and timing.
- Harvest-system and road-access sequencing.
- Cost, productivity, and operational feasibility of the road/harvest plan.
- Operational scenario export into the FEMIC disturbance ledger.

### Shared contract

The delivery boundary is a versioned hydrologic response bundle, analogous to
the LidarBC product bundle. Proposed schemas:

- `femic.hydrology.domain.v1`: watersheds, stream reaches, road segments,
  receptors, HRUs, gauge links, CRS, resolution, and provenance.
- `femic.hydrology.disturbance.v1`: annual harvest, road, retention, and
  recovery states by spatial unit, with source schedule lineage.
- `femic.hydrology.response.v1`: return-period response surfaces, uncertainty,
  applicability domain, model lineage, and caveats.
- `femic.hydrology.flood_risk.v1`: receptor-level risk metrics and scenario
  summaries.

Every bundle carries CRS, units, resolution, time step, model version,
calibration/validation evidence, licence, checksum, and a screening-only
caveat.

## Model Ladder

Use a ladder, not a single model:

| Tier | Method | Use | Cost | Confidence |
| --- | --- | --- | --- | --- |
| 0 | ECA, road density, connected disturbed area, riparian proximity, elevation-band exposure | Screening, diagnostics, UI | Low | Low |
| 1 | Stochastic flood-frequency response; GEV/LP3; nonstationary frequency pairing; Bayesian uncertainty | Planning response surfaces | Medium | Medium |
| 2 | Process-based distributed hydrology: DHSVM, RHESSys, CRHM, SUMMA, HEC-HMS | Design scenarios and validation | High | High but structural uncertainty |
| 3 | Surrogate/ML trained on Tier 2; Gaussian process, random forest, gradient boosting, neural network | Optimization inner loop | Low at query time | Conditional on applicability domain |

Rules:

- Tier 1 is calibrated to public gauges and paired-watershed evidence, with
  regime-specific priors.
- Tier 2 is used to generate a designed scenario library and to validate the
  surrogate out of sample.
- Tier 3 reports applicability domain and uncertainty; it is not allowed to
  extrapolate silently.
- The final selected schedule is re-run through Tier 2 before any operational
  recommendation.

## Flood-Risk Metrics

At each receptor and return period, record:

- Baseline and scenario peak-flow quantiles.
- Ratio and absolute change in peak flow.
- Probability of exceeding channel capacity or a receptor threshold.
- Expected annual damage (EAD) if a damage curve exists.
- Duration or frequency of elevated flow, where the model supports it.
- Risk by return period, not only the 100-year event.

At the landscape level, record:

- Risk by watershed and receptor.
- Spatial concentration of risk.
- Timing of risk: construction-phase, harvest-phase, recovery-phase, and
  cumulative.
- Uncertainty intervals and scenario spread.

## Optimization Sketch

Sets: stands/blocks `i`, periods `t`, road segments `r`, watersheds `w`,
receptors `k`, return periods `T`, climate/event scenarios `s`.

Decision variables:

- Harvest timing `x[i,t]`.
- Road construction `y[r,t]` and decommissioning `z[r,t]`.
- Retention/buffer choices where the estate model supports them.
- Access/road-use choices where FHOPS or WS4 requires them.

State:

- Forest cover/age and recovery.
- Road network connectivity and hydrologic disturbance.
- Annual disturbance metrics by HRU and watershed.

Response:

- `delta_Q[w,k,T,t,s] = f(disturbance pattern, regime, climate scenario)`.
- Implemented as a precomputed response surface or piecewise-linear surrogate.

Risk:

- `risk[k,t,s] = P(Q > capacity)` or EAD.
- Constraints: `risk[k,t,s] <= risk_max`, cumulative risk budgets, or
  watershed-level risk caps.
- Objective: maximize NPV minus a risk penalty, or compute a Pareto frontier.

Solution strategy:

- MILP with piecewise-linear response surfaces for small/medium instances.
- Simulation-optimization or heuristic search for large instances.
- Scenario-based robust optimization or CVaR for uncertainty.
- Validate the chosen schedule with Tier 2 before acceptance.

## Proposed Phase Tree

### FEMIC P114: Forest hydrology response and flood-risk products

1. P114.1 Domain and receptor contract (`#352`).
2. P114.2 Public hydrology data bundle (`#353`).
3. P114.3 Disturbance ledger for harvest, roads, retention, and recovery
   (`#354`).
4. P114.4 Tier 0 screening metrics and caveats (`#355`).
5. P114.5 Stochastic flood-frequency response layer (`#356`).
6. P114.6 Process-model adapters and scenario manifests (`#357`).
7. P114.7 Surrogate training, validation, and applicability domain (`#358`).
8. P114.8 Versioned hydrologic response and flood-risk bundles (`#359`). Complete.
9. P114.9 Benchmark, bounded pilot, and phase closeout (`#360`).

### WS4 P49: Flood-risk-aware spatial scheduling

1. P49.1 Ingest the FEMIC response bundle.
2. P49.2 Add spatial disturbance and road-construction decision surfaces.
3. P49.3 Add flood-risk objective and constraints.
4. P49.4 Add temporal/cumulative/recovery risk accounting.
5. P49.5 Add multi-objective and robust scenario optimization.
6. P49.6 Pilot, Pareto reporting, and validation.

### FHOPS P14: Operational road and harvest hydrology integration

1. P14.1 Extend road-construction contracts with hydrology attributes.
2. P14.2 Link road jobs to the disturbance ledger.
3. P14.3 Add cost/risk tradeoff reporting to tactical planning.
4. P14.4 Export validated operational scenarios and close out.

## Validation

- Benchmark direction and order of magnitude against published paired-watershed
  and stochastic-hydrology results. Do not force exact replication across
  different watersheds.
- Backcast against public WSC gauge records where available.
- Split-sample and cross-watershed validation.
- Compare Tier 3 surrogate against held-out Tier 2 simulations.
- Report structural, parameter, and climate uncertainty.
- Require hydrologist review of the model card and pilot results.
- Record every deviation and applicability limit.

## Pilot

Choose one bounded public watershed only after a data audit. The pilot should
have:

- LiDAR DEM/DSM coverage.
- Public stream and road networks.
- At least one usable hydrometric gauge or paired-watershed analogue.
- A mix of harvest and road history.
- A downstream receptor or channel-capacity question.

Candidate regimes should include one snow-transient interior watershed and one
rain/rain-on-snow coastal watershed before any provincial generalization.

## Risks And Open Questions

- LiDAR coverage and DEM artefacts; culvert and road-crossing data gaps.
- Stream-network and road-network positional error.
- Confounding between harvest, roads, climate, and natural variability.
- Structural uncertainty across hydrology models.
- Surrogate extrapolation outside the training domain.
- Computational cost of process-based ensembles.
- Damage curves, receptor definitions, and legal/regulatory status.
- Indigenous and private data governance.
- Which pilot watershed and which regulatory-versus-screening target.

## Current Edge

FEMIC P114 is active. P114.1 (`#352`) through P114.8 (`#359`) are complete: the
domain/receptor contract, public source registry, bundle manifest,
licence/checksum validation, annual disturbance ledger, Tier 0 screening,
stochastic flood-frequency/response surfaces, DHSVM/SUMMA process-model
adapters, bounded surrogates, and versioned response/flood-risk bundles are in
place. The response bundle records deterministic identity, artifact SHA-256
checksums, provenance, applicability and uncertainty metadata, and the
WS4/FHOPS consumer read order. Next is P114.9 (`#360`): benchmark, bounded
public pilot, and phase closeout. Do not create the WS4 P49 or FHOPS P14
implementation issues until P114.9 declares the FEMIC response contract
stable.
