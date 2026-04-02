Run Config Profile
==================

``femic run`` accepts ``--run-config`` pointing to a YAML or JSON profile.
Profile values seed CLI defaults for FMU/code selection and mode flags.

Schema
------

.. code-block:: yaml

   selection:
     tsa: ["08", "16"]      # optional list[str]; legacy field name for FMU/code selection
     strata: ["SBSdk"]      # optional list[str], currently informational only
     boundary_path: "data/bc/cfa/k3z/CFA K3Z Tenure.shp"  # optional custom boundary path
     boundary_layer: null   # optional layer name/index for multi-layer GIS sources
     boundary_code: "k3z"   # optional label used as FEMIC FMU/code identifier for boundary mode
     stratification:         # optional controls for stratum construction/selection
       bec_grouping: "subzone"                  # zone | subzone | variant | phase
       species_combo_count: 2                   # top-N species in stratum key
       include_tm_species2_for_single: true     # include TM species 2 when N=1
       top_area_coverage: 0.95                  # optional cumulative area cutoff (0,1]
   modes:
     resume: true           # optional bool
     dry_run: false         # optional bool
     verbose: false         # optional bool
     skip_checks: false     # optional bool
     debug_rows: 250        # optional int
     vdyp_sampling_mode: auto  # optional: auto | all | positive int
     vdyp_two_pass_rebin: false  # optional bool
     vdyp_min_stands_per_si_bin: 25  # optional positive int; pre-fit SI bin collapse
     managed_curve_mode: tipsy  # optional: tipsy | vdyp_transform
     managed_curve_x_scale: 0.8  # optional numeric; x' = x * scale
     managed_curve_y_scale: 1.2  # optional numeric; y' = y * scale
     managed_curve_truncate_at_culm: true  # optional bool; flatten after culmination
     managed_curve_max_age: 300  # optional positive int
   run:
     run_id: "dev-profile"  # optional str
     log_dir: "vdyp_io/profile_logs"  # optional str path

Precedence
----------

- CLI values override config values for ``--tsa`` and ``--debug-rows`` when explicitly provided.
- Boolean flags use additive behavior (CLI or config can enable).
- ``--run-id`` overrides ``run.run_id`` when provided.
- ``--log-dir`` overrides config unless left at the default ``vdyp_io/logs``.
- Boundary fields are profile-driven only (no dedicated CLI flags yet). When
  ``selection.boundary_path`` is set, legacy extraction runs in custom-boundary mode
  and bypasses checkpoint reuse.
- ``modes.vdyp_sampling_mode`` controls per-stratum VDYP run sampling:
  ``auto`` (iterative bootstrap), ``all`` (all stand records), or a fixed positive sample size.
- ``modes.vdyp_two_pass_rebin=true`` performs a first VDYP pass, then re-bins L/M/H
  using stand-level SI parsed from VDYP output before smoothing and downstream steps.
- ``modes.vdyp_min_stands_per_si_bin`` sets the pre-fit minimum stand count for each
  SI bin; bins below the threshold are auto-collapsed into adjacent levels before NLLS.
- ``modes.managed_curve_mode=vdyp_transform`` synthesizes managed curves from VDYP
  unmanaged curves (instead of using raw TIPSY yields) using:
  ``x' = x * managed_curve_x_scale`` and ``y' = y * managed_curve_y_scale``, with
  optional post-culmination flattening via ``managed_curve_truncate_at_culm``.
- When ``selection.stratification.top_area_coverage`` is set, 01a selects the
  minimum number of descending-area strata needed to hit the requested
  cumulative area target, instead of using a fixed per-code top-N cutoff.

Compatibility note
------------------

The run-profile schema still uses the legacy ``selection.tsa`` field name
because that key is part of the current CLI/runtime compatibility contract.
Treat it as "selected FMU/code(s)" in generic FEMIC usage unless the case is
literally a BC Timber Supply Area.

Example
-------

A template profile is included at ``instances/reference/config/run_profile.case_template.yaml``
(maintainer reference instance) and as package scaffolding via
``femic instance init``.
When provided, run manifests also record ``run_config_path`` and
``run_config_sha256`` provenance metadata plus output version annotations.
For deterministic VDYP bootstrap sampling, set ``FEMIC_SAMPLING_SEED`` to an
integer value.
Run manifests include a ``runtime_parameters`` section to capture the effective
FEMIC execution settings used for each run.
