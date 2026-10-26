``femic.hydrology.validation`` Module
======================================

The :mod:`femic.hydrology.validation` module owns P114.9 validation and
closeout. It records published directional benchmarks, runs bounded public-gauge
frequency backcasts, audits full-pilot readiness, and emits the validation
report and model card for the WS4/FHOPS handoff.

Use this page when you are validating the response layer, running the bounded
public-gauge pilot, or checking the model-card conditions.

Start Here If...
----------------

Use this page first if you are trying to:

- run GEV/LP3 backcasts on public gauge annual maxima;
- check tail plausibility and split-sample stability;
- review published paired-watershed expectations;
- run the bounded P114.9 pilot;
- write or inspect the model card; or
- understand the WS4/FHOPS handoff conditions.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path
   from femic.hydrology.validation import build_p1149_closeout

   result = build_p1149_closeout(
       gauges_path=Path("tests/fixtures/hydrology/pilot/gauges.json"),
       annual_maxima_path=Path(
           "tests/fixtures/hydrology/pilot/annual_maxima.csv"
       ),
       output_dir=Path("runtime/hydrology/p114_9_closeout"),
   )
   print(result.validation_report.validation_id)
   print(result.model_card.review_status)

Key Entry Surfaces
------------------

- :func:`load_pilot_gauges`
- :func:`load_pilot_annual_maxima`
  Load the bounded public pilot fixture.
- :func:`build_pilot_sample`
  Build a validated annual-maximum sample.
- :func:`run_gauge_backcast`
  Fit GEV/LP3, run the split-sample check, and apply the tail screen.
- :func:`run_public_gauge_pilot`
  Run all pilot gauges and create a deterministic pilot run.
- :func:`published_benchmarks`
  Return the reviewed directional benchmark catalogue.
- :func:`assess_return_period_ratios`
  Compare observed ratios with a benchmark expectation.
- :func:`build_benchmark_reviews`
  Mark benchmark cases passed, failed, or not evaluated.
- :func:`audit_pilot_readiness`
  Record full-pilot inputs and data gaps.
- :func:`build_validation_report`
- :func:`build_model_card`
  Build the linked closeout records.
- :func:`build_p1149_closeout`
  Run the bounded pilot and write all closeout files.
- :class:`PilotGaugeBackcast`
- :class:`TailCheck`
- :class:`ValidationReport`
- :class:`ModelCard`
  Evidence, audit, and handoff records.

Cross-References
----------------

- :doc:`../../guides/hydrology-validation-closeout`
- :doc:`../contracts/hydrology-validation-closeout`
- :doc:`femic-hydrology-flood`
- :doc:`femic-hydrology-response-bundle`

.. toctree::
   :hidden:

   generated/femic.hydrology.validation

.. automodule:: femic.hydrology.validation
   :members:
   :undoc-members:
   :show-inheritance:
