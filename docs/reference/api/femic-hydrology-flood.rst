``femic.hydrology.flood`` Module
==================================

The :mod:`femic.hydrology.flood` module owns P114.5 stochastic flood-frequency
work. It extracts annual maxima and POT samples, fits GEV/LP3 and Poisson-GPD
models, computes paired baseline/treatment response ratios, fits nonstationary
GEV location models, builds return-period response surfaces, and checks
benchmark envelopes.

It is decision-support and screening, not regulatory flood analysis.

Start Here If...
----------------

Use this page first if you are trying to:

- fit a stationary GEV or LP3 frequency distribution;
- extract and fit declustered peaks over a threshold;
- compare baseline and treatment return levels;
- fit a nonstationary GEV with harvest/road covariates;
- build a return-period response surface; or
- check response ratios against a reviewed benchmark envelope.

Typical Usage
-------------

.. code-block:: python

   from femic.hydrology.flood import (
       FloodScenario,
       build_response_surface,
       fit_flood_frequency,
       fit_nonstationary_gev,
       paired_frequency_response,
   )

   fit = fit_flood_frequency(
       annual,
       method="gev",
       return_periods=(2, 10, 100),
       bootstrap_samples=200,
       seed=42,
   )
   pairing = paired_frequency_response(
       baseline,
       treatment,
       method="gev",
       return_periods=(2, 10, 100),
   )
   nonstationary = fit_nonstationary_gev(
       sample,
       {"harvest_fraction": harvest_fraction_by_year},
       return_periods=(2, 10, 100),
   )
   surface = build_response_surface(
       nonstationary,
       (
           FloodScenario("baseline", {"harvest_fraction": 0.0}),
           FloodScenario("high", {"harvest_fraction": 0.4}),
       ),
   )

Key Entry Surfaces
------------------

- :func:`extract_annual_maxima`
- :func:`extract_peaks_over_threshold`
  Build annual-maximum and declustered POT samples.
- :func:`fit_flood_frequency`
  Fit GEV or LP3 with bootstrap intervals.
- :func:`fit_pot_frequency`
  Fit Poisson-GPD.
- :func:`paired_frequency_response`
  Compare baseline/treatment return levels.
- :func:`fit_nonstationary_gev`
  Fit a linear-location GEV.
- :func:`predict_nonstationary_quantiles`
  Predict one scenario.
- :func:`build_response_surface`
  Build a return-period surface.
- :func:`evaluate_frequency_benchmark`
  Check paired ratios against a reviewed envelope.
- :class:`FloodResponseSurface`
  Versioned scenario/return-period surface.

Cross-References
----------------

- :doc:`../../guides/hydrology-flood-frequency`
- :doc:`../contracts/hydrology-flood-frequency`
- :doc:`femic-hydrology-screening`
- :doc:`femic-hydrology-disturbance`

.. toctree::
   :hidden:

   generated/femic.hydrology.flood

.. automodule:: femic.hydrology.flood
   :members:
   :undoc-members:
   :show-inheritance:
