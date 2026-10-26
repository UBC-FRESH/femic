Process-Model Adapter Contract
==============================

Purpose
-------

This page is the short source-of-truth contract for FEMIC P114.6 process-model
adapters. It defines scenario manifests, runtime probing, implemented adapters,
the normalized output contract, execution boundaries, and licensing rules.

FEMIC does not bundle model binaries or model licences.

Quick Contract
--------------

- Scenario schema: ``femic.hydrology.process_scenario.v1``.
- Result schema: ``femic.hydrology.process_result.v1``.
- Registered models: DHSVM, RHESSys, CRHM, SUMMA, HEC-HMS.
- Executable adapters: DHSVM and SUMMA.
- Runtime order: explicit path -> model-specific environment variable -> PATH.
- Normalized peak-flow CSV: ``year,peak_flow_m3s``.
- Normalized receptor CSV: ``receptor_id,metric,value``.
- No bundled binaries, private forcing data, or silent unit/CRS conversion.

Scenario Manifest
-----------------

A scenario records:

- ``scenario_id``, ``scenario_name``, ``model_id``, and ``domain_id``;
- optional ``ledger_id``;
- ``scenario_kind``: ``baseline``, ``treatment``, or ``ensemble``;
- watershed and receptor IDs;
- start/end year and time step in hours;
- CRS and flow/area units;
- climate forcing, land cover, road scenario, harvest scenario, model config,
  and output paths;
- provenance and caveats.

All path fields are required. A scenario is rejected if the model is unknown,
the year range is inverted, the time step is not positive, or IDs are blank.

Runtime Probing
---------------

An adapter probes:

1. an explicit executable;
2. the model's environment variable;
3. `PATH` lookup of the default executable.

A probe returns availability, executable path, source, and warnings. A missing
runtime is a clear unavailable result, not an install attempt.

Implemented Adapters
--------------------

DHSVM command:

```text
<dhsvm> <run-dir>/<model_config_path>
```

SUMMA command:

```text
<summa> -m <run-dir>/<model_config_path>
```

RHESSys, CRHM, and HEC-HMS are registered boundaries without executable
adapters in P114.6.

Output Contract
---------------

The run directory must contain:

- ``peak_flows.csv`` with ``year`` and ``peak_flow_m3s``; and
- optionally ``receptor_metrics.csv`` with ``receptor_id, metric, value``.

The adapter normalizes the peak-flow CSV into a `FloodSample` and the receptor
CSV into a nested metric mapping. A missing peak-flow file is an error.

Execution
---------

``run_process_model``:

- validates the scenario;
- probes the runtime;
- refuses to run when unavailable;
- writes the scenario manifest into the run directory;
- captures stdout/stderr into log files;
- fails on a non-zero return code;
- parses normalized outputs.

Timeout is explicit. FEMIC does not silently retry a failed model run.

Licensing And Data
------------------

- Model binaries and licences are user-supplied.
- Do not commit private or licence-restricted forcing data.
- Keep large forcing data and model outputs in DataLad/Arbutus.
- A successful run is not a validated model; calibration and benchmark checks
  remain P114.9.

Cross-References
----------------

- :doc:`../../guides/hydrology-process-models`
- :doc:`hydrology-flood-frequency`
- :doc:`hydrology-disturbance-ledger`
- :doc:`../api/femic-hydrology-process-models`
