``femic.hydrology.process_models`` Module
==========================================

The :mod:`femic.hydrology.process_models` module defines FEMIC's boundary to
user-supplied process-based hydrology models. It builds scenario manifests,
probes external runtimes, constructs commands for DHSVM and SUMMA, executes
models, and normalizes peak-flow and receptor outputs.

FEMIC does not bundle model binaries or model licences.

Start Here If...
----------------

Use this page first if you are trying to:

- build a process-model scenario manifest;
- check whether DHSVM or SUMMA is available;
- inspect a model command without running it;
- run a user-supplied model and parse normalized outputs; or
- add another process-model adapter behind the same contract.

Typical Usage
-------------

.. code-block:: python

   from pathlib import Path
   from femic.hydrology.process_models import (
       adapter_for_model,
       build_scenario_manifest,
       plan_process_model_run,
       run_process_model,
   )

   manifest = build_scenario_manifest(...)
   adapter = adapter_for_model("dhsvm")
   plan = plan_process_model_run(adapter, manifest, Path("runtime/run"))
   result = run_process_model(
       adapter,
       manifest,
       Path("runtime/run"),
       executable=Path("/opt/dhsvm/bin/dhsvm"),
       timeout_sec=3600,
   )

Key Entry Surfaces
------------------

- :func:`build_scenario_manifest`
- :func:`validate_scenario_manifest`
- :func:`write_scenario_manifest`
- :func:`load_scenario_manifest`
  Build, validate, and persist scenario manifests.
- :func:`process_model_specs`
- :func:`find_process_model_spec`
- :func:`adapter_for_model`
  Inspect the model registry and resolve implemented adapters.
- :func:`plan_process_model_run`
  Probe the runtime and return the command without executing it.
- :func:`run_process_model`
  Execute and normalize outputs.
- :func:`read_peak_flow_series`
- :func:`read_receptor_metrics`
  Read the normalized output contract.
- :class:`ProcessModelResult`
  Normalized model result.

Cross-References
----------------

- :doc:`../../guides/hydrology-process-models`
- :doc:`../contracts/hydrology-process-models`
- :doc:`femic-hydrology-flood`
- :doc:`femic-hydrology-disturbance`

.. toctree::
   :hidden:

   generated/femic.hydrology.process_models

.. automodule:: femic.hydrology.process_models
   :members:
   :undoc-members:
   :show-inheritance:
