Flood-Frequency Response Contract
=================================

Purpose
-------

This page is the short source-of-truth contract for FEMIC P114.5 stochastic
flood-frequency and response-surface work. It defines the sample, distribution,
POT, paired-response, nonstationary, surface, benchmark, and uncertainty
contracts.

Quick Contract
--------------

- Frequency schema: ``femic.hydrology.flood_frequency.v1``.
- Response-surface schema: ``femic.hydrology.flood_response.v1``.
- Stationary methods: GEV and LP3 on annual maxima.
- POT method: Poisson-GPD.
- Paired response: baseline/treatment return-level ratios.
- Nonstationary method: GEV with linear location covariates.
- Return periods are years; annual-maximum probability is ``1 - 1/T``.
- Bootstrap intervals are percentile intervals.
- Nonstationary coefficients are point estimates.
- No regulatory flood map or design-flood service. This is not a regulatory flood map.

Sample Contract
---------------

Annual maxima:

- one value per year;
- positive, finite values;
- unique years;
- at least five values for a fit; ten or more recommended.

POT:

- positive, finite events;
- declustered by minimum separation;
- threshold exceeded by every selected peak;
- annual rate derived from the full record start/end years.

Distribution Contract
---------------------

GEV parameters are reported as SciPy shape, location, and scale. LP3 parameters
are reported on the log10 scale as skew, location, and scale. The fit records
log-likelihood, AIC, sample size, bootstrap count, warnings, and caveats.

POT fits report threshold, annual rate, GPD shape, and GPD scale. Return levels
use the Poisson rate and GPD tail.

Paired Response
---------------

A pairing records:

- baseline and treatment fits;
- return-period-specific ratios;
- differences;
- bootstrap ratio lower/upper bounds;
- warnings and caveats.

A ratio above one means the treatment return level exceeds baseline.

Nonstationary Response Surface
------------------------------

The nonstationary GEV model is:

```text
mu(t) = intercept + sum(beta_j * covariate_j(t))
sigma, shape = constant
```

The fit records coefficients, log-likelihood, AIC, sample size, baseline
covariates, and baseline return levels.

A response surface records one row per scenario/return period with quantile,
baseline quantile, ratio, and difference. The surface uses a deterministic
identity and a named baseline scenario.

Benchmark
---------

``FloodBenchmark`` defines lower/upper ratio envelopes by return period.
``evaluate_frequency_benchmark`` reports whether each paired ratio is inside the
envelope. A pass is a consistency check, not proof of correctness.

Uncertainty And Caveats
-----------------------

- Bootstrap intervals are percentile intervals, not a Bayesian posterior.
- Nonstationary coefficient uncertainty is not propagated in P114.5.
- Short records and nonstationarity limit tail inference.
- Covariate association is not causation.
- Public-gauge calibration and published paired-watershed validation are P114.9.
- Hydrologist review is required before operational use.

Cross-References
----------------

- :doc:`../../guides/hydrology-flood-frequency`
- :doc:`hydrology-tier0-screening`
- :doc:`hydrology-disturbance-ledger`
- :doc:`../api/femic-hydrology-flood`
