Stochastic Flood-Frequency Response
===================================

Purpose
-------

P114.5 adds stochastic flood-frequency fits, paired-watershed response ratios,
and nonstationary GEV response surfaces. These are planning and screening tools
for return-period-specific hydrologic response.

They do not replace hydrologist review, public-gauge calibration, or regulatory
flood analysis. The fit schema is ``femic.hydrology.flood_frequency.v1`` and the
response surface uses ``femic.hydrology.flood_response.v1``. This is not a regulatory flood map. P114.9 owns the public-gauge benchmark and pilot
validation.

Frequency Models
----------------

The module supports:

- stationary GEV on annual maxima;
- LP3 on annual maxima, fitted as Pearson III on log10 flows;
- Poisson-GPD peaks-over-threshold;
- paired baseline/treatment return-level ratios;
- nonstationary GEV with a linear location model in covariates;
- return-period response surfaces from nonstationary scenarios;
- benchmark-envelope checks.

Annual Maxima And POT
---------------------

.. code-block:: python

   from datetime import date
   from femic.hydrology.flood import (
       FloodEvent,
       extract_annual_maxima,
       extract_peaks_over_threshold,
   )

   events = (
       FloodEvent(date(2020, 1, 1), 120.0),
       FloodEvent(date(2020, 1, 3), 110.0),
       FloodEvent(date(2020, 6, 1), 140.0),
   )
   annual = extract_annual_maxima(events, station_id="station-1")
   pot = extract_peaks_over_threshold(
       events,
       threshold=100.0,
       min_separation_days=10,
       station_id="station-1",
   )

POT peaks are selected in descending magnitude with a minimum day separation.

Stationary Fits
---------------

.. code-block:: python

   from femic.hydrology.flood import fit_flood_frequency

   fit = fit_flood_frequency(
       annual,
       method="gev",
       return_periods=(2, 5, 10, 25, 50, 100),
       bootstrap_samples=200,
       seed=42,
   )

Return periods use annual-maximum non-exceedance probability ``1 - 1/T``.
Bootstrap intervals are percentile intervals.

Paired Response
---------------

.. code-block:: python

   from femic.hydrology.flood import paired_frequency_response

   pairing = paired_frequency_response(
       baseline,
       treatment,
       method="gev",
       return_periods=(2, 10, 100),
   )

The result records return-period-specific ratios, differences, and bootstrap
ratio intervals.

Nonstationary Response Surface
------------------------------

.. code-block:: python

   from femic.hydrology.flood import (
       FloodScenario,
       build_response_surface,
       fit_nonstationary_gev,
   )

   fit = fit_nonstationary_gev(
       sample,
       {"harvest_fraction": harvest_fraction_by_year},
       return_periods=(2, 10, 100),
   )
   surface = build_response_surface(
       fit,
       (
           FloodScenario("baseline", {"harvest_fraction": 0.0}),
           FloodScenario("high", {"harvest_fraction": 0.4}),
       ),
   )

The nonstationary GEV uses a linear location model. Coefficients are point
estimates; uncertainty propagation belongs to P114.7.

Uncertainty
-----------

- Stationary fits report bootstrap percentile intervals.
- Paired responses report bootstrap ratio intervals.
- Nonstationary coefficients are point estimates.
- Structural, climate, and record-length uncertainty remain explicit caveats.
- Bootstrap intervals are not a full Bayesian posterior.

Calibration And Validation
--------------------------

``FloodBenchmark`` and ``evaluate_frequency_benchmark`` compare paired response
ratios against a reviewed lower/upper envelope by return period. A benchmark
pass is a consistency check, not proof of hydrological correctness.

Public-gauge calibration and published paired-watershed validation are P114.9.

Limits
------

- No regulatory flood map or design-flood service.
- Short records limit tail inference.
- Nonstationarity is represented only through the supplied covariates.
- Potentially influential covariates must be reviewed; correlation is not
  causation.
- Regionalization and climate projection are later work.
- Hydrologist review is required before operational use.

See Also
--------

- :doc:`hydrology-tier0-screening`
- :doc:`hydrology-disturbance-ledger`
- :doc:`../reference/contracts/hydrology-flood-frequency`
- :doc:`../reference/api/femic-hydrology-flood`
