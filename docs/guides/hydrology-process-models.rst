Process-Based Hydrology Model Adapters
======================================

Purpose
-------

P114.6 defines how FEMIC drives user-supplied process-based hydrology models.
It provides scenario manifests, runtime probing, adapter boundaries, and a
normalized peak-flow/receptor output contract.

FEMIC does not bundle model binaries, model licences, or private data. The
operator supplies the model installation and runtime. All runtimes are
user-supplied. The scenario schema is
``femic.hydrology.process_scenario.v1`` and the result schema is
``femic.hydrology.process_result.v1``.

Model Boundaries
----------------

The registry covers:

- DHSVM
- RHESSys
- CRHM
- SUMMA
- HEC-HMS

P114.6 implements executable adapters for **DHSVM** and **SUMMA**. The other
models are registered boundaries and can be added without changing the
scenario or output contract.

Scenario Manifest
-----------------

A scenario records:

- scenario, model, domain, and disturbance-ledger identity;
- scenario kind: baseline, treatment, or ensemble;
- watershed and receptor IDs;
- start/end years and time step;
- CRS, flow units, and area units;
- climate forcing, land cover, road scenario, harvest scenario, model config,
  and output paths;
- provenance and caveats.

.. code-block:: python

   from femic.hydrology.process_models import build_scenario_manifest

   manifest = build_scenario_manifest(
       scenario_id="dhsvm-treatment-2040",
       scenario_name="DHSVM treatment 2040",
       model_id="dhsvm",
       domain_id="example-domain",
       scenario_kind="treatment",
       watershed_ids=("w1",),
       start_year=2020,
       end_year=2040,
       time_step_hours=24.0,
       crs="EPSG:3005",
       climate_forcing_path="climate.csv",
       land_cover_path="landcover.gpkg",
       road_scenario_path="roads.gpkg",
       harvest_scenario_path="harvest.csv",
       model_config_path="dhsvm.config",
       output_dir="output",
       receptor_ids=("r1",),
       ledger_id="ledger-1",
   )

Runtime Probing
---------------

Adapters locate a runtime in this order:

1. an explicit executable path;
2. the model-specific environment variable, such as `FEMIC_DHSVM_EXE` or
   `FEMIC_SUMMA_EXE`;
3. `PATH` lookup by the default executable name.

Probing never downloads or installs a model.

Implemented Adapters
--------------------

DHSVM:

.. code-block:: text

   <dhsvm> <run-dir>/dhsvm.config

SUMMA:

.. code-block:: text

   <summa> -m <run-dir>/fileManager.txt

Use ``plan_process_model_run`` to inspect the command without executing it.

Running A Model
---------------

.. code-block:: python

   from pathlib import Path
   from femic.hydrology.process_models import adapter_for_model, run_process_model

   result = run_process_model(
       adapter_for_model("dhsvm"),
       manifest,
       Path("runtime/hydrology/dhsvm-treatment-2040"),
       executable=Path("/opt/dhsvm/bin/dhsvm"),
       timeout_sec=3600,
   )

The run directory receives the scenario manifest, stdout/stderr logs, and
normalized outputs.

Normalized Outputs
------------------

Peak-flow CSV (``peak_flows.csv``):

.. code-block:: text

   year,peak_flow_m3s
   2020,10.0
   2021,12.5

Receptor metrics CSV (``receptor_metrics.csv``):

.. code-block:: text

   receptor_id,metric,value
   r1,peak_flow_m3s,15.0
   r1,exceedance_probability,0.1

The result normalizes these into a `FloodSample` plus a receptor-metric
mapping. The adapter may need a model-specific post-processing step before
these files exist; P114.6 defines the handoff, not every native output format.

External Runtime And Licensing
------------------------------

- Model binaries, executables, and licences are user-supplied.
- FEMIC does not distribute DHSVM, RHESSys, CRHM, SUMMA, or HEC-HMS.
- Cite and comply with each model's licence and documentation.
- Do not add private or licence-restricted forcing data to tracked files.
- Keep large forcing data and model outputs in DataLad/Arbutus, not git.

Limits
------

- Only DHSVM and SUMMA have executable adapters in P114.6.
- Native model output conversion may require a reviewed post-processor.
- A successful run is not a validated model; calibration and benchmark checks
  remain P114.9.
- FEMIC does not infer or silently transform units, CRS, or time steps.
- Hydrologist review is required before operational use.

See Also
--------

- :doc:`hydrology-flood-frequency`
- :doc:`hydrology-disturbance-ledger`
- :doc:`../reference/contracts/hydrology-process-models`
- :doc:`../reference/api/femic-hydrology-process-models`
