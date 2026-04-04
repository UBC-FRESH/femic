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
- ``fansier``
- ``export``
- ``patchworks``
- ``instance``

Run
---

.. code-block:: text

   python -m femic run [OPTIONS]

- ``--data-root PATH`` (default: ``data``)
- ``--output-root PATH`` (default: ``outputs``)
- ``--tsa TEXT`` (repeatable; legacy FMU/code selector name)
- ``--resume``
- ``--dry-run``
- ``--verbose`` / ``-v``
- ``--skip-checks``
- ``--debug-rows INTEGER``
- ``--run-id TEXT``
- ``--log-dir PATH`` (default: ``runtime/logs``)
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
- ``--tsa TEXT`` (repeatable; legacy FMU/code selector name)
- ``--resume``
- ``--dry-run``
- ``--verbose`` / ``-v``

``prep validate-case`` options

- ``--run-config PATH`` (default: ``config/run_profile.case_template.yaml``)
- ``--tipsy-config-dir PATH`` (default: ``config/tipsy``)
- ``--strict-warnings``
- ``--instance-root PATH``

On Windows, ``prep validate-case`` now also performs the low-noise
annex/Arbutus checks needed for FEMIC's Arbutus-backed public-data workflow
when that mirror is in play. It can fail fast on:

- unusable ``git-annex`` / DataLad runtime;
- quoted credential values in ``%USERPROFILE%\.config\femic\arbutus.env``;
- missing loaded Arbutus auth vars when a local Arbutus env-file workflow is
  already in use; and
- failed visibility probes for the known public-data Arbutus bucket; and
- unreadable canonical ``data/bc/tsa/FADM_TSA.gdb`` inputs that are more likely
  annex materialization/unlock problems than generic Windows GDAL ghosts.

For the canonical maintainer/bootstrap runbook, including the exact Windows
auth-file and remote-publication sequence, see
``docs/guides/public-data-mirror-runbook.rst``.

``prep geospatial-preflight`` remains the generic Fiona/GDAL/shapefile smoke
check. On Windows, use ``prep validate-case`` to prove that the active FEMIC
case can actually read the annex-backed canonical TSA/FileGDB inputs.

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
- ``--tsa TEXT`` (repeatable; legacy FMU/code selector name)
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

Compatibility note:

- ``tsa`` remains the command-group name for historical/runtime compatibility.
  In generic FEMIC usage, read it as "FMU/code-targeted legacy pipeline
  commands" unless the case is literally a BC Timber Supply Area.

Subcommands

- ``run``: ``python -m femic tsa run [OPTIONS]``
- ``post-tipsy``: ``python -m femic tsa post-tipsy [OPTIONS]``
- ``btc-post-tipsy``: ``python -m femic tsa btc-post-tipsy [OPTIONS]``

``tsa run`` options

- ``--data-root PATH`` (default: ``data``)
- ``--output-root PATH`` (default: ``outputs``)
- ``--tsa TEXT`` (repeatable; selected FMU/code values)
- ``--resume``
- ``--dry-run``
- ``--verbose`` / ``-v``

``tsa post-tipsy`` options

- ``--tsa TEXT`` (repeatable, required; selected FMU/code values)
- ``--verbose`` / ``-v``
- ``--run-id TEXT``
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-config PATH`` (optional; load FMU/code selection and managed-curve mode defaults)
- ``--instance-root PATH``

``tsa btc-post-tipsy`` options

- ``--tsa TEXT`` (repeatable, required; selected FMU/code values)
- ``--verbose`` / ``-v``
- ``--run-id TEXT``
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-config PATH`` (optional; load FMU/code selection and managed-curve mode defaults)
- ``--btc-exe PATH`` (optional explicit ``TIPSYbtc.exe`` override)
- ``--scratch-dir PATH`` (optional scratch root for copied BTC installs and staged run files)
- ``--report-preset TEXT`` (default: ``tsr-unattended-default``)
- ``--instance-root PATH``

TIPSY
-----

.. code-block:: text

   python -m femic tipsy [OPTIONS] COMMAND [ARGS]...

Use this command group when you want direct control of the BTC/TIPSY runtime
boundary rather than the broader Stage 01a/01b orchestration. The current
operator-facing default is the unattended BTC `/TSR` seam through the live
user-overlay ``TimberSupply.rpt`` path.

Subcommands

- ``validate``: ``python -m femic tipsy validate [OPTIONS]``
- ``write-btc-report-template``: ``python -m femic tipsy write-btc-report-template [OPTIONS]``
- ``run-btc``: ``python -m femic tipsy run-btc [OPTIONS]``

``tipsy validate`` options

- ``--config-dir PATH`` (default: ``config/tipsy``)
- ``--tsa TEXT`` (repeatable; selected FMU/code values)
- ``--instance-root PATH``

``tipsy write-btc-report-template`` options

- ``--preset TEXT`` (required; built-in report-template preset)
- ``OUTPUT`` argument (required)
- ``--source-rpt PATH`` (optional existing ``.rpt`` template to clone/adapt)
- ``--column TEXT`` (repeatable additional BTC output column token)
- ``--instance-root PATH``

``tipsy run-btc`` options

- ``INPUT_CSV`` argument (required)
- ``--output-csv PATH`` (optional; defaults beside input)
- ``--error-csv PATH`` (optional; defaults beside input)
- ``--btc-exe PATH`` (optional explicit ``TIPSYbtc.exe`` override)
- ``--mode TEXT`` (default: ``TSR``)
- ``--report-template PATH`` (optional vetted ``TimberSupply.rpt`` override)
- ``--report-preset TEXT`` (default: ``tsr-unattended-default`` for ``TSR``)
- ``--copy-install`` / ``--use-installed-btc``
- ``--scratch-dir PATH`` (optional writable scratch directory; defaults under ``tipsy_io/scratch``)
- ``--log-dir PATH`` (default: ``tipsy_io/logs``)
- ``--run-id TEXT``
- ``--instance-root PATH``

Operational note:

- runtime artifacts now default under ``tipsy_io/logs`` and
  ``tipsy_io/scratch`` so BTC supervision is visually separate from the VDYP
  runtime namespace.

FAN$IER
-------

.. code-block:: text

   python -m femic fansier [OPTIONS] COMMAND [ARGS]...

Use this command group when you want FEMIC to drive the tracked Windows
FAN$IER batch-extraction seam and optionally normalize the resulting long-report
text files into FEMIC-owned tables.

Subcommands

- ``run-batch``: ``python -m femic fansier run-batch [OPTIONS] RGM_PATH``
- ``parse-batch-output``:
  ``python -m femic fansier parse-batch-output [OPTIONS] REPORT_DIR``
- ``run-and-parse``:
  ``python -m femic fansier run-and-parse [OPTIONS] RGM_PATH``

``fansier run-batch`` options

- ``RGM_PATH`` argument (required)
- ``--out-dir PATH`` (default: ``tipsy_io/logs/fansier_batch``)
- ``--log-dir PATH`` (default: ``tipsy_io/logs``)
- ``--run-id TEXT`` (default: ``fansier_batch``)
- ``--fansier-exe PATH`` (default: installed ``Fansier.exe`` path)
- ``--discount-name TEXT`` (default: ``FEMIC Raw 0%``)
- ``--discount-dis-path PATH`` (optional; load `.dis` before selection)
- ``--report-type TEXT`` (default: ``txt``)
- ``--long-report`` / ``--short-report`` (default: short)
- ``--product-cols`` / ``--no-product-cols``
- ``--activity-cols`` / ``--no-activity-cols`` (default: off)
- ``--select-all-products``
- ``--select-all-ages``
- ``--product-name TEXT`` (used when not selecting all products)
- ``--age-name TEXT`` (used when not selecting all ages)

``fansier parse-batch-output`` options

- ``REPORT_DIR`` argument (required directory of FAN$IER ``.txt`` outputs)
- ``--out-dir PATH`` (default: ``tipsy_io/logs/fansier_parsed``)
- ``--report-glob TEXT`` (default: ``*.txt``)

``fansier run-and-parse`` options

- ``RGM_PATH`` argument (required)
- ``--out-dir PATH`` (default: ``tipsy_io/logs/fansier_batch``)
- ``--parsed-out-dir PATH`` (default: ``tipsy_io/logs/fansier_parsed``)
- ``--log-dir PATH`` (default: ``tipsy_io/logs``)
- ``--run-id TEXT`` (default: ``fansier_batch``)
- ``--fansier-exe PATH`` (default: installed ``Fansier.exe`` path)
- ``--discount-name TEXT`` (default: ``FEMIC Raw 0%``)
- ``--discount-dis-path PATH`` (optional; load `.dis` before selection)
- ``--report-type TEXT`` (currently must be ``txt`` for parsing)
- ``--long-report`` / ``--short-report`` (default: long)
- ``--product-cols`` / ``--no-product-cols``
- ``--activity-cols`` / ``--no-activity-cols`` (default: off)
- ``--select-all-products`` / ``--single-product`` (default: all)
- ``--select-all-ages`` / ``--single-age`` (default: all)
- ``--product-name TEXT`` (used when broad product selection is off)
- ``--age-name TEXT`` (used when broad age selection is off)

Operational notes:

- the parsing seam currently expects ``txt`` reports;
- the practical machine-ingest default is `0%` discount posture with product
  columns on and activity columns off.

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

- ``--tsa TEXT`` (repeatable, required; selected FMU/code values)
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

- ``--tsa TEXT`` (repeatable, required; selected FMU/code values)
- ``--bundle-dir PATH`` (default: ``data/model_input_bundle``)
- ``--checkpoint PATH`` (default: ``data/ria_vri_vclr1p_checkpoint7.feather``)
- ``--output-dir PATH`` (default: ``output/woodstock``)
- ``--cc-min-age INTEGER`` (default: ``0``)
- ``--cc-max-age INTEGER`` (default: ``1000``)
- ``--fragments-crs TEXT`` (default: ``EPSG:3005``)
- ``--instance-root PATH``

``export dual`` options

- ``--tsa TEXT`` (repeatable, required; selected FMU/code values)
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
- ``--logs-dir PATH`` (default: ``runtime/logs``)
- ``--run-id TEXT`` (optional)
- ``--strict / --no-strict`` (default: ``--strict``)
- ``--instance-root PATH``

Patchworks Runtime
------------------

.. code-block:: text

   python -m femic patchworks [OPTIONS] COMMAND [ARGS]...

Use this command group when you want FEMIC to inspect or launch registry-backed
Patchworks variants, scenarios, and scenario sets, while still preserving the
lower-level ``run-headless <pin>`` primitive seam.

Subcommands

- ``preflight``: ``python -m femic patchworks preflight [OPTIONS]``
- ``instances list``: ``python -m femic patchworks instances list [OPTIONS]``
- ``build-blocks``: ``python -m femic patchworks build-blocks [OPTIONS]``
- ``matrix-build``: ``python -m femic patchworks matrix-build [OPTIONS]``
- ``run-headless``: ``python -m femic patchworks run-headless [OPTIONS] PIN``
- ``run-default-scenario``: ``python -m femic patchworks run-default-scenario [OPTIONS] VARIANT_ID``
- ``run-default-scenario-set``: ``python -m femic patchworks run-default-scenario-set [OPTIONS] INSTANCE_ID``
- ``run-scenario``: ``python -m femic patchworks run-scenario [OPTIONS] VARIANT_ID SCENARIO_ID``
- ``run-variant``: ``python -m femic patchworks run-variant [OPTIONS] VARIANT_ID``
- ``scenarios list``: ``python -m femic patchworks scenarios list [OPTIONS] VARIANT_ID``
- ``scenario-sets list``: ``python -m femic patchworks scenario-sets list [OPTIONS]``
- ``scenario-sets show``: ``python -m femic patchworks scenario-sets show [OPTIONS] SCENARIO_SET_ID``
- ``variants list``: ``python -m femic patchworks variants list [OPTIONS]``
- ``variants register``: ``python -m femic patchworks variants register [OPTIONS] VARIANT_ID``
- ``variants remove``: ``python -m femic patchworks variants remove [OPTIONS] VARIANT_ID``
- ``variants show``: ``python -m femic patchworks variants show [OPTIONS] VARIANT_ID``
- ``variants update``: ``python -m femic patchworks variants update [OPTIONS] VARIANT_ID``

``patchworks preflight`` options

- ``--config PATH`` (default: ``config/patchworks.runtime.yaml``)

``patchworks instances list`` options

- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)

``patchworks matrix-build`` options

- ``--config PATH`` (default: ``config/patchworks.runtime.yaml``)
- ``--instance-root PATH``
- ``--log-dir PATH`` (default: ``runtime/logs``)
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

``patchworks run-headless`` options

- ``PIN`` argument (required)
- ``--config PATH`` (default: ``config/patchworks.runtime.yaml``)
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-id TEXT`` (optional)
- ``--stage-label TEXT`` (optional)
- ``--iterations INTEGER`` (default: ``1``)
- ``--improvement FLOAT`` (default: ``0.0``)
- ``--scenario-mode TEXT`` (default: ``none``)
- ``--scenario-target TEXT`` (optional)
- ``--scenario-min-annual FLOAT`` (optional)
- ``--instance-root PATH``

``patchworks run-variant`` options

- ``VARIANT_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-id TEXT`` (optional)
- ``--stage-label TEXT`` (optional)
- ``--iterations INTEGER`` (default: ``1``)
- ``--improvement FLOAT`` (default: ``0.0``)
- ``--scenario-mode TEXT`` (default: ``none``)
- ``--scenario-target TEXT`` (optional)
- ``--scenario-min-annual FLOAT`` (optional)
- ``--allow-large-download`` (skip the materialization confirmation prompt when
  known estimated downloads exceed the threshold)
- ``--materialization-threshold-mib INTEGER`` (default: ``100``)

``patchworks scenarios list`` options

- ``VARIANT_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)

``patchworks scenario-sets list`` options

- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--instance-id TEXT`` (optional instance id filter)

``patchworks scenario-sets show`` options

- ``SCENARIO_SET_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)

``patchworks run-scenario`` options

- ``VARIANT_ID`` argument (required)
- ``SCENARIO_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-id TEXT`` (optional)
- ``--stage-label TEXT`` (optional override; falls back to the registry scenario when set there)
- ``--allow-large-download`` (skip the materialization confirmation prompt when
  known estimated downloads exceed the threshold)
- ``--materialization-threshold-mib INTEGER`` (default: ``100``)

``patchworks run-default-scenario`` options

- ``VARIANT_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-id TEXT`` (optional)
- ``--stage-label TEXT`` (optional override; falls back to the registry default scenario when set there)
- ``--allow-large-download`` (skip the materialization confirmation prompt when
  known estimated downloads exceed the threshold)
- ``--materialization-threshold-mib INTEGER`` (default: ``100``)

``patchworks run-default-scenario-set`` options

- ``INSTANCE_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-id TEXT`` (optional; step runs derive ``_01``, ``_02``, ...)
- ``--stage-label TEXT`` (optional; per-step stage labels derive ``_01``,
  ``_02``, ...)
- ``--allow-large-download`` (skip the materialization confirmation prompt when
  known estimated downloads exceed the threshold)
- ``--materialization-threshold-mib INTEGER`` (default: ``100``)

``patchworks run-scenario-set`` options

- ``SCENARIO_SET_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-id TEXT`` (optional; step runs derive ``_01``, ``_02``, ...)
- ``--stage-label TEXT`` (optional; per-step stage labels derive ``_01``,
  ``_02``, ...)
- ``--allow-large-download`` (skip the materialization confirmation prompt when
  known estimated downloads exceed the threshold)
- ``--materialization-threshold-mib INTEGER`` (default: ``100``)

``patchworks variants list`` options

- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--instance-id TEXT`` (optional filter)

``patchworks variants register`` options

- ``VARIANT_ID`` argument (required)
- ``--label TEXT`` (required)
- ``--instance-id TEXT`` (required)
- ``--instance-label TEXT`` (optional)
- ``--instance-root PATH`` (required)
- ``--analysis-pin PATH`` (required)
- ``--runtime-config PATH`` (required)
- ``--variant-family TEXT`` (default: ``default``)
- ``--kind TEXT`` (default: ``patchworks``)
- ``--default / --no-default`` (default: ``--no-default``)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; writes the user overlay)

``patchworks variants update`` options

- ``VARIANT_ID`` argument (required)
- ``--label TEXT`` (optional)
- ``--instance-id TEXT`` (optional)
- ``--instance-label TEXT`` (optional)
- ``--instance-root PATH`` (optional)
- ``--analysis-pin PATH`` (optional)
- ``--runtime-config PATH`` (optional)
- ``--variant-family TEXT`` (optional)
- ``--kind TEXT`` (optional)
- ``--default BOOL`` (optional explicit override: ``true`` or ``false``)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; writes the user overlay)

``patchworks variants remove`` options

- ``VARIANT_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; removes only user-overlay entries)

``patchworks variants show`` options

- ``VARIANT_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--materialization-threshold-mib INTEGER`` (default: ``100``; used when
  summarizing registry-declared materialization)

``patchworks variants materialization-plan`` options

- ``VARIANT_ID`` argument (required)
- ``--registry PATH`` (default: ``~/.femic/variants.yaml``; built-ins always loaded)
- ``--materialization-threshold-mib INTEGER`` (default: ``100``; used when
  deciding whether the current plan would require confirmation)

Both ``patchworks variants show`` and
``patchworks variants materialization-plan`` now print:

- one aggregate materialization summary;
- one dataset-root grouped summary per touched dataset; and
- the supporting raw per-action detail lines.

Operational notes:

- built-ins are always loaded from FEMIC's packaged registry;
- ``~/.femic/variants.yaml`` is a writable user overlay, not the only source
  of truth;
- launch-time materialization consent is driven by the grouped dataset summary
  before the raw per-action detail lines.

Instance Workspace
------------------

.. code-block:: text

   python -m femic instance [OPTIONS] COMMAND [ARGS]...

Subcommands

- ``init``: ``python -m femic instance init [OPTIONS]``
- ``config show``: ``python -m femic instance config show``
- ``config set-managed-external-root``:
  ``python -m femic instance config set-managed-external-root <path>``
- ``config set-user-instance-root``:
  ``python -m femic instance config set-user-instance-root <path>``
- ``builtins list``: ``python -m femic instance builtins list``
- ``builtins install``: ``python -m femic instance builtins install <builtin-id|all>``
- ``rebuild``: ``python -m femic instance rebuild [OPTIONS]``
- ``validate-spec``: ``python -m femic instance validate-spec [OPTIONS]``
- ``promote-evidence``: ``python -m femic instance promote-evidence [OPTIONS]``
- ``refresh-reference-evidence``: ``python -m femic instance refresh-reference-evidence [OPTIONS]``
- ``account-surface``: ``python -m femic instance account-surface [OPTIONS]``
- ``ws3-smoke``: ``python -m femic instance ws3-smoke [OPTIONS]``

``instance init`` options

- ``--instance-root PATH`` (optional; defaults to CWD)
- ``--instance-name TEXT`` (optional; create under configured visible user
  instance root; mutually exclusive with ``--instance-root``)
- ``--overwrite`` (overwrite existing scaffold template files)
- ``--download-bc-vri / --no-download-bc-vri`` (default: ``--download-bc-vri``)
- ``--yes`` / ``-y`` (assume yes for prompts)

``instance config show`` output

- current config path
- whether ``user.yaml`` exists yet
- resolved managed built-in root
- resolved visible user-instance root
- the default values FEMIC would use if the config file is absent

``instance builtins list`` output

- builtin id and label
- install status
- resolved install path
- standalone repo URL
- declared support-repo dependencies/notes

``instance builtins install`` behavior

- clones missing built-in repos into the configured managed built-in root
- clones declared support repos if missing
- skips already-installed git worktrees
- does **not** run ``datalad get`` automatically
- prints next-step guidance for payload materialization instead

Operational notes:

- packaged-install config now lives at ``~/.femic/user.yaml`` (or the Windows
  equivalent);
- FEMIC uses that config for managed built-ins and the visible user workspace
  root;
- normal operational runtime precedence is still
  ``--instance-root`` -> ``FEMIC_INSTANCE_ROOT`` -> current working directory.

``instance rebuild`` options

- ``--spec PATH`` (default: ``config/rebuild.spec.yaml``)
- ``--run-config PATH`` (default: ``config/run_profile.case_template.yaml``)
- ``--tipsy-config-dir PATH`` (default: ``config/tipsy``)
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--run-id TEXT`` (optional; defaults to UTC timestamp)
- ``--with-patchworks / --no-patchworks`` (default: ``--no-patchworks``)
- ``--dry-run`` (print planned step sequence without execution)
- ``--patchworks-config PATH`` (default: ``config/patchworks.runtime.yaml``)
- ``--baseline PATH`` (default: ``config/rebuild.baseline.json``)
- ``--write-baseline`` (write/update baseline snapshot before diff evaluation)
- ``--allowlist PATH`` (default: ``config/rebuild.allowlist.yaml``)
- ``--instance-root PATH``

``instance rebuild`` writes a machine-readable report to
``runtime/logs/instance_rebuild_report-<run_id>.json`` and records discovered
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
- ``--log-dir PATH`` (default: ``runtime/logs``)
- ``--max-warn-increase INT`` (optional drift warning threshold)
- ``--max-baseline-diff-increase INT`` (optional drift warning threshold)
- ``--instance-root PATH``

Promoted evidence summary also includes:

- ``summary.account_surface_total_ok_species_empty_signature``
- ``summary.account_surface_species_count``

``instance refresh-reference-evidence`` options

- ``--report PATH`` (optional; defaults to latest report in reference ``runtime/logs``)
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
