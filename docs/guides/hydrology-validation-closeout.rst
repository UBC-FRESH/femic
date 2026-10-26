Hydrology Validation And P114 Closeout
======================================

Purpose
-------

P114.9 closes the FEMIC forest-hydrology producer phase with a bounded public
gauge pilot, a published-evidence review, explicit data gaps, a model card, and
the WS4/FHOPS handoff recommendation.

This page records what was validated, what failed, and what remains
unvalidated. The closeout records use ``femic.hydrology.validation.v1``,
``femic.hydrology.pilot.v1``, and ``femic.hydrology.model_card.v1``. This is
not a regulatory flood map and does not claim design-flood suitability or
operational safety certification.

What Was Validated
------------------

The validation layer checks:

- public-gauge annual-maximum frequency backcasts with GEV and LP3;
- split-sample early/late tail stability;
- tail plausibility against the observed record;
- directional expectations from published paired-watershed work;
- full-pilot readiness and missing inputs; and
- the model-card and consumer-handoff conditions.

The published benchmark cases are directional and order-of-magnitude checks.
They are not point estimates to be copied into another watershed.

Public Gauge Pilot
------------------

Three public Water Survey of Canada gauges were used:

- Carnation Creek at the Mouth (`08HB048`), coastal rain-dominated regime;
- Coldwater River near Brookmere (`08LG048`), interior snow-transient regime;
- Squamish River near Brackendale (`08GA022`), coastal mountain
  rain-on-snow regime.

The bounded fixture retains only annual maximum daily discharge, date, and
source symbol under the Open Government Licence - Canada. It does not include
daily series or private/Indigenous data.

100-year return levels use 200 bootstrap samples. Values are in m3/s.

.. list-table::
   :header-rows: 1

   * - Gauge
     - Regime
     - Years
     - GEV 100-year
     - LP3 100-year
     - Early/late 100-year ratio
     - Usable fits
   * - 08HB048 Carnation Creek
     - Rain
     - 51 (1973-2024)
     - 27.05
     - 27.07
     - 0.94
     - GEV, LP3
   * - 08LG048 Coldwater River
     - Snow-transient
     - 58 (1966-2024)
     - 112.55
     - 114.03
     - 0.89
     - GEV, LP3
   * - 08GA022 Squamish River
     - Rain-on-snow
     - 71 (1923-2025)
     - Rejected
     - 2,928.24
     - Unusable
     - LP3

Carnation Creek has a missing 2018 annual maximum. Coldwater River has a
missing 2021 value. Squamish River has gaps in 1926-1954, 1996, and 2019-2020.
Several recent values carry an `Estimated` source symbol. These are recorded as
quality caveats.

Tail Plausibility Failure
-------------------------

The unconstrained GEV fit for Squamish River produced a shape of about -5.68
and a non-physical 100-year tail. The validation layer rejected that fit:
the shape is outside the screening range [-0.5, 0.5] and the fitted 100-year
quantile is many orders of magnitude above the observed maximum. The early and
late split-sample GEV fits failed the same check, so the split-sample ratios are
not usable.

This is a P114.5 fit-stability finding, not a data-entry error. The LP3 fit for
Squamish River remains plausible. A response bundle must not use a fit that
fails the tail check.

**P118.2 remediation:** the stationary GEV now falls back to a bounded shape
``[-0.5, 0.5]`` and records ``fit_strategy="constrained"``. The Squamish GEV
fit now returns a finite constrained tail and is usable under the same tail
screen. The original finding remains the reason for the guard; the constrained
strategy and warning must still be reviewed before operational use.

Published Benchmark Review
---------------------------

The published benchmark catalogue records five directional expectations:

- snow-transient high-return-period increase;
- rain high-return-period increase;
- frequency dependence, where a long-return-period ratio exceeds a
  short-return-period ratio;
- snowmelt high-return-period increase; and
- paired control-watershed no-change.

Sources include Alila et al. (2009, doi:10.1029/2008WR007207), Kuraś et al.
(2012, doi:10.1029/2011WR010705), Green & Alila (2012,
doi:10.1029/2012WR012449), Schnorbus & Alila (2013,
doi:10.1029/2012WR011901), Pham et al. (2025, Journal of Hydrology 661:133704),
and Rong, Bishop & Alila (2026, doi:10.1016/j.advwatres.2026.105432).

No public paired baseline/treatment frequency result was assembled in P114.9.
All five cases therefore remain ``not_evaluated`` for the public pilot. The
directional assessment harness is implemented and tested with synthetic paired
ratios; it is ready for a reviewed paired-watershed dataset in a follow-up
phase. A passed directional screen would not prove hydrologic correctness.

Pilot Readiness And Data Gaps
-----------------------------

The full two-watershed process pilot was not completed. The bounded run records
these gaps:

- no public hydrology domain manifest with LiDAR, stream, road, and receptor
  layers was supplied;
- no annual harvest/road disturbance ledger was supplied;
- no executable process model was available for the pilot;
- no downstream receptor capacity or damage curve was available; and
- no hydrologist review record was supplied.

The gauge backcast is therefore a frequency-estimation check, not a treatment
or process-model validation.

Uncertainty And Deviations
--------------------------

- Bootstrap intervals are percentile intervals, not a Bayesian posterior.
- Short records and nonstationarity limit tail inference.
- Missing years and estimated values affect the fits.
- The GEV fit for Squamish River is rejected by the tail screen.
- No paired treatment/control response was available.
- Gauge-frequency behaviour does not identify harvest or road causality.
- Climate projection, regionalization, and damage-curve validation are outside
  P114.9.
- No hydrologist review has been recorded.

Model Card
----------

The closeout writes a versioned model card with:

- intended use and out-of-scope uses;
- regimes and validation summary;
- data gaps and usable fits;
- uncertainty and limitations;
- a review checklist; and
- the consumer handoff conditions.

The model card status is ``not_reviewed``. It is provisional until a
hydrologist records approval, conditions, or rejection.

WS4/FHOPS Handoff
-----------------

The FEMIC response contract is stable for **screening and decision support**,
with conditions:

- WS4 P49 may ingest a pinned response bundle for spatial scheduling screens.
- FHOPS P14 may ingest the same bundle for operational road/harvest tradeoff
  reporting.
- Both consumers must verify ``bundle_id``, ``bundle_version``, and artifact
  SHA-256 values.
- Both must carry the screening-only caveat and refuse queries outside the
  recorded applicability domain.
- A fit that fails the tail check must not be used for risk reporting.
- Hydrologist review and a completed process-model pilot are required before
  operational use or regulatory interpretation.

The phase can hand off a bounded, versioned screening layer. It cannot hand off
a regulatory or design-flood product.

Closeout Statement
------------------

P114.9 closes the FEMIC producer phase with a conditional handoff:

- public gauge backcasts completed and recorded;
- published evidence catalogued as directional benchmarks;
- the GEV instability recorded and rejected by the tail screen;
- data gaps, uncertainty, and review status recorded; and
- WS4/FHOPS consumer conditions documented.

The next work is a reviewed paired-watershed/process-model validation and a
hydrologist-approved model card, not a claim that the current layer is fully
validated.

Reproduce The Bounded Pilot
---------------------------

.. code-block:: shell

   python -m femic hydrology pilot \
     --gauges tests/fixtures/hydrology/pilot/gauges.json \
     --annual-maxima tests/fixtures/hydrology/pilot/annual_maxima.csv \
     --output-dir runtime/hydrology/p114_9_closeout \
     --bootstrap-samples 200 \
     --seed 42

The command writes ``pilot_run.json``, ``validation_report.json``, and
``model_card.json``. Passing a public domain manifest, disturbance ledger, or
review record upgrades the readiness audit; those inputs were not available for
this bounded closeout.

See Also
--------

- :doc:`hydrology-response-bundles`
- :doc:`hydrology-flood-frequency`
- :doc:`hydrology-surrogate-models`
- :doc:`../reference/contracts/hydrology-validation-closeout`
- :doc:`../reference/api/femic-hydrology-validation`
