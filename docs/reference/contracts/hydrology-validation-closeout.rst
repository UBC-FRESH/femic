Hydrology Validation And Closeout Contract
==========================================

Purpose
-------

This page is the source-of-truth contract for FEMIC P114.9 validation, public
pilot, benchmark review, model card, and WS4/FHOPS closeout handoff.

Quick Contract
--------------

- Validation schema: ``femic.hydrology.validation.v1``.
- Pilot-run schema: ``femic.hydrology.pilot.v1``.
- Model-card schema: ``femic.hydrology.model_card.v1``.
- Benchmark evidence version: ``femic.hydrology.benchmark_evidence.2026-10``.
- Public pilot source: Water Survey of Canada annual statistics under the
  Open Government Licence - Canada.
- Benchmarks are directional and order-of-magnitude screens, not point
  estimates.
- A fit that fails the tail check is retained for audit but excluded from
  usable fits.
- Hydrologist review status is explicit and may be ``not_reviewed``.
- The handoff is screening-only. This is not a regulatory flood map or a
  design-flood service. No private, Indigenous, or licence-restricted data is
  tracked.

Pilot Input Contract
--------------------

Gauge metadata records:

- station number and name;
- province and regime;
- drainage area;
- status and contributor;
- vertical datum;
- source and station API URLs;
- licence and retrieval time; and
- notes and known gaps.

Annual maxima record:

- station number;
- year;
- maximum date;
- maximum daily discharge in m3/s; and
- source symbol.

The input must contain positive, finite annual maxima and unique years per
station. The pilot fixture contains no daily series and no private, Indigenous,
or licence-restricted data.

Gauge Backcast Contract
-----------------------

For each gauge the validator:

- fits GEV and LP3 on annual maxima;
- records bootstrap intervals and fit parameters;
- records missing years and estimated values;
- runs an early/late split-sample GEV stability check;
- computes 100-year tail plausibility against the observed maximum; and
- records usable fits.

The tail screen rejects a GEV fit when:

- the shape is outside ``[-0.5, 0.5]``;
- the 100-year quantile is non-finite or non-positive;
- the 100-year quantile exceeds ten times the observed maximum; or
- the 100-year quantile is below half the observed maximum.

The split-sample check is unusable when an early or late GEV fit fails the tail
screen or the window is too short.

Published Benchmark Contract
----------------------------

A benchmark case records:

- case ID and regime;
- hypothesis;
- expected direction: ``increase``, ``decrease``,
  ``frequency_dependent``, or ``no_change``;
- cited sources;
- log10 scale tolerance; and
- notes.

The directional assessment compares observed return-period ratios with the
expectation. It does not require a published point estimate to be reproduced in
a different watershed. A passed screen is consistency evidence, not proof of
hydrologic correctness. A case with no paired baseline/treatment result is
reported as ``not_evaluated`` with a reason.

Model Card Contract
-------------------

The model card records:

- model ID and version;
- intended use and out-of-scope uses;
- regimes;
- validation-report and pilot-run IDs;
- validation summary, usable fits, and data gaps;
- uncertainty and limitations;
- review status and review checklist;
- consumer handoff conditions;
- sources; and
- caveats.

Review status is one of ``not_reviewed``, ``review_pending``, ``reviewed``, or
``reviewed_with_conditions``. A card that is not reviewed must not be presented
as operationally approved.

Validation Report Contract
--------------------------

The validation report records:

- validation ID and timestamp;
- pilot-run ID;
- benchmark evidence version;
- benchmark reviews and statuses;
- full-pilot readiness and data gaps;
- model-card ID;
- summary counts;
- deviations and uncertainty;
- screening-only caveats; and
- consumer handoff conditions.

The validation ID is derived from the pilot identity, benchmark reviews, and
readiness audit. The model-card ID is derived from its model identity,
validation-report ID, and pilot summary.

WS4/FHOPS Handoff
-----------------

WS4 P49 and FHOPS P14 may use a pinned FEMIC response bundle for screening and
decision support. They must:

- verify bundle identity and artifact checksums;
- read the model card and validation report when packaged;
- exclude fits that fail the tail check;
- respect the applicability domain;
- preserve the screening-only caveat; and
- require hydrologist review before operational or regulatory use.

Deviations, Gaps, And Review
----------------------------

The P114.9 bounded run records:

- no full public watershed domain with LiDAR, stream, road, and receptor data;
- no harvest/road disturbance ledger;
- no process-model execution;
- no paired baseline/treatment benchmark execution;
- no downstream damage curve or receptor capacity;
- an unstable GEV tail for Squamish River, rejected by the tail screen; and
- no hydrologist review record.

These are recorded as deviations and gaps, not silently filled.

Cross-References
----------------

- :doc:`../../guides/hydrology-validation-closeout`
- :doc:`hydrology-response-bundles`
- :doc:`hydrology-flood-frequency`
- :doc:`hydrology-tier0-screening`
- :doc:`../api/femic-hydrology-validation`
