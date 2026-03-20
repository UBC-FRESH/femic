CLI Reference
=============

Top-Level Command
-----------------

.. code-block:: text

   python -m femic [OPTIONS] COMMAND [ARGS]...

Options
-------

- ``--version``: Show version and exit.
- ``--debug``: Enable rich tracebacks.
- ``--help``: Show help and exit.

Commands
--------

- ``run``
- ``prep``
- ``vdyp``
- ``tsa``
- ``tipsy``
- ``export``
- ``patchworks``
- ``instance``

Run
---

.. code-block:: text

   python -m femic run [OPTIONS]

- ``--data-root PATH`` (default: ``data``)
- ``--output-root PATH`` (default: ``outputs``)
- ``--tsa TEXT`` (repeatable)
- ``--resume``
- ``--dry-run``
- ``--verbose`` / ``-v``
- ``--skip-checks``
- ``--debug-rows INTEGER``
- ``--run-id TEXT``
- ``--log-dir PATH`` (default: ``vdyp_io/logs``)
- ``--run-config PATH`` (YAML/JSON run profile)
- ``--instance-root PATH`` (optional; defaults to CWD or ``FEMIC_INSTANCE_ROOT`` env)

Prep
----

.. code-block:: text

   python -m femic prep [OPTIONS] COMMAND [ARGS]...

Subcommands

- ``run``: ``python -m femic prep run [OPTIONS]``
- ``validate-case``: ``python -m femic prep validate-case [OPTIONS]``
- ``geospatial-preflight``: ``python -m femic prep geospatial-preflight [OPTIONS]``

``prep run`` options

- ``--data-root PATH`` (default: ``data``)
- ``--output-root PATH`` (default: ``outputs``)
- ``--tsa TEXT`` (repeatable)
- ``--resume``
- ``--dry-run``
- ``--verbose`` / ``-v``

``prep validate-case`` options

- ``--run-config PATH`` (default: ``config/run_profile.case_template.yaml``)
- ``--tipsy-config-dir PATH`` (default: ``config/tipsy``)
- ``--strict-warnings``
- ``--instance-root PATH``

``prep geospatial-preflight`` options

- ``--strict-warnings``
- ``--skip-shapefile-smoke``

VDYP
----

.. code-block:: text

   python -m femic vdyp [OPTIONS] COMMAND [ARGS]...

Subcommands

- ``run``: ``python -m femic vdyp run [OPTIONS]``
- ``report``: ``python -m femic vdyp report [OPTIONS]``

``vdyp run`` options

- ``--data-root PATH`` (default: ``data``)
- ``--output-root PATH`` (default: ``outputs``)
- ``--tsa TEXT`` (repeatable)
- ``--resume``
- ``--dry-run``
- ``--verbose`` / ``-v``

``vdyp report`` options

- ``--curve-log PATH`` (default: ``vdyp_io/logs/vdyp_curve_events.jsonl``)
- ``--run-log PATH`` (default: ``vdyp_io/logs/vdyp_runs.jsonl``)
- ``--expected-first-age FLOAT`` (default: ``1.0``)
- ``--expected-first-volume FLOAT`` (default: ``1e-06``)
- ``--tolerance FLOAT`` (default: ``1e-12``)
- ``--mismatch-limit INTEGER`` (default: ``10``)
- ``--max-curve-warnings INTEGER``
- ``--max-first-point-mismatches INTEGER``
- ``--max-curve-parse-errors INTEGER``
- ``--max-run-parse-errors INTEGER``
- ``--min-curve-events INTEGER``
- ``--min-run-events INTEGER``

TSA
---

.. code-block:: text

   python -m femic tsa [OPTIONS] COMMAND [ARGS]...

Subcommands

- ``run``: ``python -m femic tsa run [OPTIONS]``
- ``post-tipsy``: ``python -m femic tsa post-tipsy [OPTIONS]``

``tsa run`` options

- ``--data-root PATH`` (default: ``data``)
- ``--output-root PATH`` (default: ``outputs``)
- ``--tsa TEXT`` (repeatable)
- ``--resume``
- ``--dry-run``
- ``--verbose`` / ``-v``

``tsa post-tipsy`` options

- ``--tsa TEXT`` (repeatable, required)
- ``--verbose`` / ``-v``
- ``--run-id TEXT``
- ``--log-dir PATH`` (default: ``vdyp_io/logs``)
- ``--run-config PATH`` (optional; load TSA and managed-curve mode defaults)
- ``--instance-root PATH``

TIPSY
-----

.. code-block:: text

   python -m femic tipsy [OPTIONS] COMMAND [ARGS]...

Subcommands

- ``validate``: ``python -m femic tipsy validate [OPTIONS]``

``tipsy validate`` options

- ``--config-dir PATH`` (default: ``config/tipsy``)
- ``--tsa TEXT`` (repeatable)
- ``--instance-root PATH``

Export
------

.. code-block:: text

   python -m femic export [OPTIONS] COMMAND [ARGS]...

Subcommands

- ``patchworks``: ``python -m femic export patchworks [OPTIONS]``
- ``woodstock``: ``python -m femic export woodstock [OPTIONS]``
- ``dual``: ``python -m femic export dual [OPTIONS]``
- ``release``: ``python -m femic export release [OPTIONS]``

``export patchworks`` options

- ``--tsa TEXT`` (repeatable, required)
- ``--bundle-dir PATH`` (default: ``data/model_input_bundle``)
- ``--checkpoint PATH`` (default: ``data/ria_vri_vclr1p_checkpoint7.feather``)
- ``--output-dir PATH`` (default: ``output/patchworks``)
- ``--start-year INTEGER`` (default: ``2026``)
- ``--horizon-years INTEGER`` (default: ``300``)
- ``--cc-min-age INTEGER`` (default: ``0``)
- ``--cc-max-age INTEGER`` (default: ``1000``)
- ``--cc-transition-ifm TEXT`` (default: unset; no IFM transition assign)
- ``--fragments-crs TEXT`` (default: ``EPSG:3005``)
- ``--ifm-source-col TEXT`` (optional; explicit checkpoint THLB signal column)
- ``--ifm-threshold FLOAT`` (optional; managed when source value > threshold)
- ``--ifm-target-managed-share FLOAT`` (optional; top-N managed by source value)
- ``--seral-stage-config PATH`` (optional; YAML per-AU seral-stage boundaries)
- ``--instance-root PATH``

``export woodstock`` options

- ``--tsa TEXT`` (repeatable, required)
- ``--bundle-dir PATH`` (default: ``data/model_input_bundle``)
- ``--checkpoint PATH`` (default: ``data/ria_vri_vclr1p_checkpoint7.feather``)
- ``--output-dir PATH`` (default: ``output/woodstock``)
- ``--cc-min-age INTEGER`` (default: ``0``)
- ``--cc-max-age INTEGER`` (default: ``1000``)
- ``--fragments-crs TEXT`` (default: ``EPSG:3005``)
- ``--instance-root PATH``

``export dual`` options

- ``--tsa TEXT`` (repeatable, required)
- ``--bundle-dir PATH`` (default: ``data/model_input_bundle``)
- ``--checkpoint PATH`` (default: ``data/ria_vri_vclr1p_checkpoint7.feather``)
- ``--patchworks-output-dir PATH`` (default: ``output/patchworks``)
- ``--woodstock-output-dir PATH`` (default: ``output/woodstock``)
- ``--with-ws3-smoke / --no-ws3-smoke`` (default: ``--no-ws3-smoke``)
- ``--ws3-command TEXT`` (optional shell command for ws3 simulation smoke)
- ``--ws3-workdir PATH`` (optional command working directory)
- ``--ws3-report PATH`` (default: ``evidence/ws3_smoke_report.latest.json``)
- ``--ws3-require-command / --ws3-allow-no-command`` (default: allow no command)
- ``--ws3-timeout-seconds INTEGER`` (default: ``600``)
- ``--ws3-repo-path PATH`` (optional local ws3 checkout path for builtin smoke)
- ``--ws3-builtin-smoke / --no-ws3-builtin-smoke`` (default: ``--no-ws3-builtin-smoke``)
- ``--ws3-bridge-dir PATH`` (optional output directory for generated ws3 section files)
- ``--instance-root PATH``

``export release`` options

- ``--case-id TEXT`` (default: ``case``)
- ``--output-root PATH`` (default: ``releases``)
- ``--bundle-dir PATH`` (default: ``data/model_input_bundle``)
- ``--patchworks-dir PATH`` (default: ``output/patchworks_k3z_validated``)
- ``--woodstock-dir PATH`` (optional)
- ``--logs-dir PATH`` (default: ``vdyp_io/logs``)
- ``--run-id TEXT`` (optional)
- ``--strict / --no-strict`` (default: ``--strict``)
- ``--instance-root PATH``

Patchworks Runtime
------------------

.. code-block:: text

   python -m femic patchworks [OPTIONS] COMMAND [ARGS]...

Subcommands

- ``preflight``: ``python -m femic patchworks preflight [OPTIONS]``
- ``build-blocks``: ``python -m femic patchworks build-blocks [OPTIONS]``
- ``matrix-build``: ``python -m femic patchworks matrix-build [OPTIONS]``

``patchworks preflight`` options

- ``--config PATH`` (default: ``config/patchworks.runtime.yaml``)

``patchworks matrix-build`` options

- ``--config PATH`` (default: ``config/patchworks.runtime.yaml``)
- ``--instance-root PATH``
- ``--log-dir PATH`` (default: ``vdyp_io/logs``)
- ``--run-id TEXT``
- ``--interactive``
- ``--instance-root PATH``

``patchworks build-blocks`` options

- ``--config PATH`` (default: ``config/patchworks.runtime.yaml``)
- ``--model-dir PATH`` (optional; inferred from runtime config when omitted)
- ``--fragments-shp PATH`` (optional; defaults to runtime fragments ``.shp``)
- ``--topology-radius FLOAT`` (default: ``200.0``)
- ``--with-topology / --no-topology`` (default: ``--with-topology``)
- ``--instance-root PATH``

Instance Workspace
------------------

.. code-block:: text

   python -m femic instance [OPTIONS] COMMAND [ARGS]...

Subcommands

- ``init``: ``python -m femic instance init [OPTIONS]``
- ``rebuild``: ``python -m femic instance rebuild [OPTIONS]``
- ``validate-spec``: ``python -m femic instance validate-spec [OPTIONS]``
- ``promote-evidence``: ``python -m femic instance promote-evidence [OPTIONS]``
- ``refresh-reference-evidence``: ``python -m femic instance refresh-reference-evidence [OPTIONS]``
- ``account-surface``: ``python -m femic instance account-surface [OPTIONS]``
- ``ws3-smoke``: ``python -m femic instance ws3-smoke [OPTIONS]``

``instance init`` options

- ``--instance-root PATH`` (optional; defaults to CWD)
- ``--overwrite`` (overwrite existing scaffold template files)
- ``--download-bc-vri / --no-download-bc-vri`` (default: ``--download-bc-vri``)
- ``--yes`` / ``-y`` (assume yes for prompts)

``instance rebuild`` options

- ``--spec PATH`` (default: ``config/rebuild.spec.yaml``)
- ``--run-config PATH`` (default: ``config/run_profile.case_template.yaml``)
- ``--tipsy-config-dir PATH`` (default: ``config/tipsy``)
- ``--log-dir PATH`` (default: ``vdyp_io/logs``)
- ``--run-id TEXT`` (optional; defaults to UTC timestamp)
- ``--with-patchworks / --no-patchworks`` (default: ``--no-patchworks``)
- ``--dry-run`` (print planned step sequence without execution)
- ``--patchworks-config PATH`` (default: ``config/patchworks.runtime.yaml``)
- ``--baseline PATH`` (default: ``config/rebuild.baseline.json``)
- ``--write-baseline`` (write/update baseline snapshot before diff evaluation)
- ``--allowlist PATH`` (default: ``config/rebuild.allowlist.yaml``)
- ``--instance-root PATH``

``instance rebuild`` writes a machine-readable report to
``vdyp_io/logs/instance_rebuild_report-<run_id>.json`` and records discovered
manifest/log artifact references under ``artifact_references``.
It also writes ``diagnostics.account_surface`` when ``tracks/accounts.csv`` is
available, including a deterministic
``total_ok_species_empty_signature`` flag and recommended next checks.
It also evaluates configured rebuild-spec invariants and appends measured
``metrics`` plus ``invariant_results`` to the report. Any invariant with
``severity: fatal`` that evaluates false causes command failure with a
remediation summary.
When a baseline snapshot is available, the report also includes a ``baseline``
section with table/XML structural diffs and aggregate ``baseline_match`` /
``baseline_diff_count`` metrics. If an allowlist file is present, rebuild also
computes ``baseline_allowlist_match`` and ``baseline_unexpected_diff_count``
for explicit intentional-delta tracking.
Rebuild exits non-zero when unexpected baseline diffs exceed
``runtime.baseline_unexpected_diff_threshold`` from ``rebuild.spec.yaml``
(default ``0``), and writes ``regression_gate`` details into the report.

``instance validate-spec`` options

- ``--spec PATH`` (default: ``config/rebuild.spec.yaml``)
- ``--instance-root PATH``

``instance promote-evidence`` options

- ``--report PATH`` (optional; defaults to latest rebuild report in ``--log-dir``)
- ``--output PATH`` (default: ``evidence/reference_rebuild_report.latest.json``)
- ``--log-dir PATH`` (default: ``vdyp_io/logs``)
- ``--max-warn-increase INT`` (optional drift warning threshold)
- ``--max-baseline-diff-increase INT`` (optional drift warning threshold)
- ``--instance-root PATH``

Promoted evidence summary also includes:

- ``summary.account_surface_total_ok_species_empty_signature``
- ``summary.account_surface_species_count``

``instance refresh-reference-evidence`` options

- ``--report PATH`` (optional; defaults to latest report in reference ``vdyp_io/logs``)
- ``--reference-root PATH`` (default: ``instances/reference``)
- ``--max-warn-increase INT`` (optional drift warning threshold)
- ``--max-baseline-diff-increase INT`` (optional drift warning threshold)

``instance account-surface`` options

- ``--config PATH`` (default: ``config/patchworks.runtime.yaml``)
- ``--output PATH`` (optional JSON output path for diagnostics summary)
- ``--instance-root PATH``

``instance account-surface`` reads ``tracks/accounts.csv`` from the configured
Patchworks matrix output folder and summarizes species-level account coverage
(``product.Yield.managed.*`` and ``product.HarvestedVolume.managed.*.CC``)
plus AU-level seral account coverage.
When ``tracks/products.csv`` and ``tracks/curves.csv`` are available it also
computes a deterministic diagnosis for the
``total OK, species-wise empty`` failure signature and prints recommended
next-check steps.

``instance ws3-smoke`` options

- ``--woodstock-dir PATH`` (default: ``output/woodstock``)
- ``--output PATH`` (default: ``evidence/ws3_smoke_report.latest.json``)
- ``--ws3-command TEXT`` (optional shell command for ws3 simulation smoke)
- ``--ws3-workdir PATH`` (optional command working directory)
- ``--require-command / --allow-no-command`` (default: allow no command)
- ``--timeout-seconds INTEGER`` (default: ``600``)
- ``--ws3-repo-path PATH`` (optional local ws3 checkout path for builtin smoke)
- ``--builtin-model-smoke / --no-builtin-model-smoke`` (default: ``--builtin-model-smoke``)
- ``--ws3-bridge-dir PATH`` (optional output directory for generated ws3 section files)
- ``--instance-root PATH``
