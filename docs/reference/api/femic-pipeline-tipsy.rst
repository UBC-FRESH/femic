``femic.pipeline.tipsy`` Module
===============================

The :mod:`femic.pipeline.tipsy` module owns FEMIC's BTC/BatchTIPSY handoff
seam. It translates smoothed VDYP outputs into per-AU TIPSY parameter tables,
writes the canonical ``03_input-*.csv`` handoff plus workbook mirrors, manages
BTC report templates and unattended ``/TSR`` execution, and validates or parses
returned BTC/TIPSY outputs during Stage 01b.

If you are debugging why FEMIC generated the wrong BTC input rows, why a report
template or unattended BTC run produced the wrong output, or why Stage 01b is
refusing to accept an existing returned file, this is the first module to read.
In practice it owns:

- the BTC ``MSYT.csv`` input schema and writer
- candidate evaluation and AU/SI selection for TIPSY parameter generation
- writing the canonical BTC handoff plus the human-readable XLSX mirror
- BTC custom report template parsing/building/writing
- unattended BTC runner argument assembly and manifest support
- fingerprinting and freshness validation for returned BTC or legacy BatchTIPSY
  output
- coherence-based stale-output acceptance logic for repeated dev/test reruns

Start Here If...
----------------

Use this page first if you are trying to:

- understand why ``03_input-*.csv`` is treated as canonical while
  ``tipsy_params_tsa*.xlsx`` is only a mirror
- debug BTC parse failures caused by input-schema mismatch or unsafe report
  templates
- inspect why a stratum/SI candidate was excluded from TIPSY parameter
  generation
- trace why Stage 01b accepted or rejected an older returned BTC/TIPSY output
- understand how ``managed_curve_mode=vdyp_transform`` changes the BTC/TIPSY
  boundary behavior

Typical maintenance path:

1. Start with :func:`build_tipsy_params_for_tsa` and
   :func:`evaluate_tipsy_candidate` if the issue is about which AU/SI/species
   combinations make it into the handoff.
2. Move to :func:`build_tipsy_input_table`,
   :func:`write_tipsy_input_exports`, and :func:`write_btc_input_csv` if the
   problem is about canonical handoff generation.
3. Read :func:`run_btc_cli`, :func:`parse_btc_custom_report_template`, and
   :func:`write_btc_custom_report_template` when the failure is visible at the
   unattended BTC runtime boundary.
4. Read :func:`validate_tipsy_output_is_fresh`,
   :func:`assess_tipsy_input_output_coherence`,
   :func:`write_tipsy_output_input_fingerprint`, and
   :func:`parse_btc_tsr_transposed_output` when the failure is visible at
   Stage 01b resume.

Typical Usage
-------------

The common operator-facing pattern is to let Stage 01a write the canonical BTC
handoff, run unattended BTC, and then parse the returned output before Stage
01b resumes:

.. code-block:: python

   from pathlib import Path
   from femic.pipeline.tipsy import run_btc_cli

   run_btc_cli(
       input_csv_path=Path("data/03_input-tsa08.csv"),
       output_path=Path("data/04_output-tsa08.csv"),
       error_path=Path("data/04_error-tsa08.csv"),
   )

How This Fits Into The Pipeline
-------------------------------

This module owns the default unattended BTC seam plus the remaining legacy
BatchTIPSY compatibility boundary described in:

- :doc:`../../guides/stage-01a-vdyp-tipsy-input`
- :doc:`../../guides/stage-01b-post-tipsy`

At a high level, the owning sequence is:

1. Stage 01a selects eligible AU/SI candidates and builds TIPSY parameter rows
2. FEMIC writes ``03_input-*.csv`` and ``tipsy_params_tsa*.xlsx``
3. BTC runs unattended under FEMIC and returns ``04_output-*.csv`` /
   ``04_error-*.csv``
4. Stage 01b validates/parses that output against the current canonical BTC
   handoff

That means this module is both a data-shaping layer and a workflow boundary
guard. It now runs BTC directly, while still carrying the older DAT/OUT
freshness rules as a compatibility seam.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :func:`build_tipsy_params_for_tsa`
  Generate the per-AU TIPSY parameter payloads from smoothed VDYP outputs.
- :func:`evaluate_tipsy_candidate`
  Decide whether one stratum/SI candidate is eligible and why.
- :func:`build_tipsy_input_table`
  Turn per-AU parameter payloads into the tabular export surface.
- :func:`write_tipsy_input_exports`
  Write the canonical BTC handoff and workbook mirror for one TSA.
- :func:`write_btc_input_csv`
  Write the canonical ``MSYT.csv``-style BTC input file for one TSA.
- :func:`run_btc_cli`
  Launch unattended ``TIPSYbtc.exe /TSR`` against a canonical BTC handoff.
- :func:`validate_tipsy_output_is_fresh`
  Enforce the Stage 01b freshness guard against the canonical input seam.
- :func:`assess_tipsy_input_output_coherence`
  Decide whether an older output still looks structurally coherent with the
  current input workbook.
- :func:`write_tipsy_output_input_fingerprint`
  Persist the canonical input SHA256 sidecar paired with an accepted output
  file.
- :func:`parse_btc_custom_report_template`
  Read an existing BTC ``.rpt`` custom report into a structured template.
- :func:`build_btc_custom_report_template`
  Build a curated BTC report template from a preset or an existing template.
- :func:`write_btc_custom_report_template`
  Write a BTC ``.rpt`` report file back to disk.
- :func:`parse_btc_tsr_transposed_output`
  Parse the vetted unattended ``/TSR`` transposed CSV output back into FEMIC
  managed-curve rows.

BTC Report Template Support
---------------------------

This module now also carries the first FEMIC-side utilities for BTC custom
report templates. That work is still part of the broader Phase 48 BTC cutover,
but it already supports a useful maintenance pattern:

1. parse an existing BTC ``.rpt`` file,
2. clone or extend its column list in Python, and
3. write a vetted replacement template back out.

The first built-in unattended preset is the transposed TSR mashup that safely
combines:

- merchantable volume
- height
- gross volume
- crown closure

That preset exists because live local probes showed that ``/TSR`` is
report-coupled: replacing ``TimberSupply.rpt`` with a compatible transposed
report template changes what ``/TSR`` emits. Not every report type is a safe
drop-in replacement, so FEMIC should prefer vetted compatible templates over
arbitrary all-fields output experiments.

Critical `/TSR` Overlay Precedence Insight
------------------------------------------

One critical reverse-engineering result must not be lost:

- plain installed ``TIPSYbtc.exe /TSR`` consults the user-overlay report under
  the current user's Windows Documents folder:
  - ``<Documents>\BatchTIPSY Composer\TimberSupply.rpt``
  before falling back to the stock installed ``TimberSupply.rpt``
- a broken overlay can therefore make stock-looking ``/TSR`` runs fail even
  when the installed BTC report under ``Program Files`` is fine
- removing the overlay restores stock fallback behavior
- replacing the overlay with a **stock-based safe enhanced TSR template** lets
  plain installed ``/TSR`` run successfully while still extending the output
  surface

This matters because early copied-install/generated-template probes were too
pessimistic. They were useful clues, but they were not exercising the most
faithful live `/TSR` seam. The safest unattended extension path is now:

1. start from the actual stock ``TimberSupply.rpt`` structure
2. extend it conservatively through the live user-overlay seam
3. test plain installed ``/TSR``

Do not assume a clean-room generated replacement template is equivalent to the
stock report contract just because the visible fields look similar.

FEMIC now resolves that overlay path generically from the current user's
Windows Documents directory instead of relying on a machine-specific OneDrive
path assumption.

The current stock-based unattended patch path also forces the TSR horizon to:

- ``TableRange=0-350:10|# MAX=350 INC=10``

so the unattended BTC output timeline lines up with FEMIC's longer VDYP curve
timeline instead of stopping at the stock 120-year range.

Why This Matters For Richer Indicator Probing
---------------------------------------------

This same overlay insight overturned the first bleak stand-table conclusion.
When the first-batch candidates were re-probed through the **real** overlay
seam instead of a stand-alone generated replacement template, all of these
columns passed cleanly:

- ``MAI``
- ``BasalArea:000``
- ``DBHg:000``
- ``SPH:000``
- ``StemCount000``
- ``StemCount125``
- ``StemCount175``

So the main compatibility rule appears to be structural:

- preserving the hidden stock ``TimberSupply.rpt`` contract matters a great
  deal
- some earlier failures were seam-mismatch artifacts, not proof that the
  columns were impossible through unattended ``/TSR``

Optional Unattended Indicator Banks
-----------------------------------

FEMIC now has real optional BTC indicator-bank switches on top of the
core unattended `/TSR` seam:

- ``--indicator-bank stand-structure-basic``
- ``--indicator-bank log-grades``
- ``--indicator-bank lumber-2-or-better``
- ``--indicator-bank lumber-graded``
- ``--indicator-bank lumber-degraded``
- ``--indicator-bank industrial-logs``
- ``--indicator-bank residual-fibre``

Current bank contents:

- ``stand-structure-basic``:
  - ``MAI``
  - ``BasalArea:000``
  - ``DBHg:000``
  - ``SPH:000``
  - ``StemCount000``
  - ``StemCount125``
  - ``StemCount175``
- ``log-grades``:
  - ``Logs_Grade_D``
  - ``Logs_Grade_F``
  - ``Logs_Grade_H``
  - ``Logs_Grade_I``
  - ``Logs_Grade_J``
  - ``Logs_Grade_U``
  - ``Logs_Grade_X``
  - ``Logs_Grade_Y``
  - ``Logs_Grade_All``
- ``lumber-2-or-better``:
  - ``Lumber_2_or_Better_2x4``
  - ``Lumber_2_or_Better_2x6``
  - ``Lumber_2_or_Better_2x8``
  - ``Lumber_2_or_Better_2x10``
  - ``Lumber_2_or_Better_All``
  - ``LRF_2_or_Better_All``
- ``lumber-graded``:
  - ``Lumber_Graded_SS_2x4``
  - ``Lumber_Graded_SS_2x6``
  - ``Lumber_Graded_SS_2x8``
  - ``Lumber_Graded_SS_2x10``
  - ``Lumber_Graded_1_2x4``
  - ``Lumber_Graded_1_2x6``
  - ``Lumber_Graded_1_2x8``
  - ``Lumber_Graded_1_2x10``
  - ``Lumber_Graded_2_2x4``
  - ``Lumber_Graded_2_2x6``
  - ``Lumber_Graded_2_2x8``
  - ``Lumber_Graded_2_2x10``
  - ``Lumber_Graded_3_2x4``
  - ``Lumber_Graded_3_2x6``
  - ``Lumber_Graded_3_2x8``
  - ``Lumber_Graded_3_2x10``
  - ``Lumber_Graded_4_2x4``
  - ``Lumber_Graded_4_2x6``
  - ``Lumber_Graded_4_2x8``
  - ``Lumber_Graded_4_2x10``
  - ``Lumber_Graded_All``
  - ``LRF_Graded_All``
- ``lumber-degraded``:
  - ``Lumber_Degraded_SS_2x4``
  - ``Lumber_Degraded_SS_2x6``
  - ``Lumber_Degraded_SS_2x8``
  - ``Lumber_Degraded_SS_2x10``
  - ``Lumber_Degraded_1_2x4``
  - ``Lumber_Degraded_1_2x6``
  - ``Lumber_Degraded_1_2x8``
  - ``Lumber_Degraded_1_2x10``
  - ``Lumber_Degraded_2_2x4``
  - ``Lumber_Degraded_2_2x6``
  - ``Lumber_Degraded_2_2x8``
  - ``Lumber_Degraded_2_2x10``
  - ``Lumber_Degraded_3_2x4``
  - ``Lumber_Degraded_3_2x6``
  - ``Lumber_Degraded_3_2x8``
  - ``Lumber_Degraded_3_2x10``
  - ``Lumber_Degraded_4_2x4``
  - ``Lumber_Degraded_4_2x6``
  - ``Lumber_Degraded_4_2x8``
  - ``Lumber_Degraded_4_2x10``
  - ``Lumber_Degraded_All``
  - ``LRF_Degraded_All``
- ``industrial-logs``:
  - ``Industrial_Logs_D38L13``
  - ``Industrial_Logs_D38L11``
  - ``Industrial_Logs_D38L8``
  - ``Industrial_Logs_D30L13``
  - ``Industrial_Logs_D30L11``
  - ``Industrial_Logs_D30L8``
  - ``Industrial_Logs_D20L13``
  - ``Industrial_Logs_D20L11``
  - ``Industrial_Logs_D20L8``
  - ``Industrial_Logs_D125L13``
  - ``Industrial_Logs_D125L11``
  - ``Industrial_Logs_D125L8``
  - ``Industrial_Logs_D125L63``
  - ``Industrial_Logs_D125L51``
  - ``Industrial_Logs_D125L5``
  - ``Industrial_Logs_D305``
  - ``Industrial_Logs_D254``
  - ``Industrial_Logs_D203``
  - ``Industrial_Logs_D178``
  - ``Industrial_Logs_D152``
- ``residual-fibre``:
  - ``Residual_Chips``
  - ``Residual_Sawdust``
  - ``Residual_Shavings``
  - ``Residual_Trim``
  - ``Residual_Bark``

Important runtime detail:

- the working implementation patches the real per-user overlay report path
  under ``<Documents>\BatchTIPSY Composer\TimberSupply.rpt`` with
  backup/restore;
- relying only on a copied-install-local ``TimberSupply.rpt`` is not enough,
  because the live overlay can silently shadow that local file and make the
  run appear successful while dropping the requested bank columns from the
  returned output.
- BTC/TIPSY runtime artifacts now default under ``tipsy_io/logs`` and
  ``tipsy_io/scratch`` so operator supervision is not visually mixed into the
  VDYP runtime namespace.
- live unattended ``/TSR`` overlay smokes must be run sequentially, not in
  parallel, because they share the same per-user ``TimberSupply.rpt`` overlay.

Live smoke proof now exists for:

- ``femic tipsy run-btc <MSYT.csv> --indicator-bank stand-structure-basic``
- ``femic tipsy run-btc <MSYT.csv> --indicator-bank log-grades``
- ``femic tipsy run-btc <MSYT.csv> --indicator-bank lumber-2-or-better``
- ``femic tipsy run-btc <MSYT.csv> --indicator-bank lumber-graded``
- ``femic tipsy run-btc <MSYT.csv> --indicator-bank lumber-degraded``
- ``femic tipsy run-btc <MSYT.csv> --indicator-bank industrial-logs``
- ``femic tipsy run-btc <MSYT.csv> --indicator-bank residual-fibre``

That returned a single unattended output CSV with:

- the default conservative families:
  - ``MVcon_*``
  - ``MVdec_*``
  - ``HTcon_*``
  - ``HTdec_*``
  - ``gVol_*``
  - ``CC_*``
- plus the first stand-structure bank:
  - ``MAI_*``
  - ``BasalArea000_*``
  - ``DBHg000_*``
  - ``SPH000_*``
  - ``StemCount000_*``
  - ``StemCount125_*``
  - ``StemCount175_*``
- plus the log-grade bank:
  - ``Logs_Grade_D_*``
  - ``Logs_Grade_F_*``
  - ``Logs_Grade_H_*``
  - ``Logs_Grade_I_*``
  - ``Logs_Grade_J_*``
  - ``Logs_Grade_U_*``
  - ``Logs_Grade_X_*``
  - ``Logs_Grade_Y_*``
  - ``Logs_Grade_All_*``
- plus the lumber-2-or-better bank:
  - ``Lumber_2_or_Better_2x4_*``
  - ``Lumber_2_or_Better_2x6_*``
  - ``Lumber_2_or_Better_2x8_*``
  - ``Lumber_2_or_Better_2x10_*``
  - ``Lumber_2_or_Better_All_*``
  - ``LRF_2_or_Better_All_*``
- plus the lumber-graded bank:
  - ``Lumber_Graded_SS_2x4_*``
  - ``Lumber_Graded_1_2x4_*``
  - ``Lumber_Graded_2_2x4_*``
  - ``Lumber_Graded_3_2x4_*``
  - ``Lumber_Graded_4_2x4_*``
  - ``Lumber_Graded_All_*``
  - ``LRF_Graded_All_*``
- plus the lumber-degraded bank:
  - ``Lumber_Degraded_SS_2x4_*``
  - ``Lumber_Degraded_1_2x4_*``
  - ``Lumber_Degraded_2_2x4_*``
  - ``Lumber_Degraded_3_2x4_*``
  - ``Lumber_Degraded_4_2x4_*``
  - ``Lumber_Degraded_All_*``
  - ``LRF_Degraded_All_*``
- plus the industrial-logs bank:
  - ``Industrial_Logs_D38L13_*``
  - ``Industrial_Logs_D30L13_*``
  - ``Industrial_Logs_D20L13_*``
  - ``Industrial_Logs_D125L13_*``
  - ``Industrial_Logs_D125L5_*``
  - ``Industrial_Logs_D305_*``
  - ``Industrial_Logs_D152_*``
- plus the residual-fibre bank:
  - ``Residual_Chips_*``
  - ``Residual_Sawdust_*``
  - ``Residual_Shavings_*``
  - ``Residual_Trim_*``
  - ``Residual_Bark_*``

while still honoring the 350-year unattended TSR timeline.

The small dataclasses in this module are also useful because they define the
candidate/freshness contracts explicitly:

- :class:`TIPSYCandidateEvaluation`
- :class:`TipsyInputOutputCoherence`

Canonical Artifacts And Contracts
---------------------------------

The most important operator/runtime contracts in this module are:

- ``03_input-*.csv`` is the canonical BTC/BatchTIPSY input artifact
- ``tipsy_params_tsa*.xlsx`` is a human-readable mirror of the same content,
  not the authoritative freshness source
- ``04_output-*.csv`` / ``04_error-*.csv`` are the default returned BTC
  artifacts for Stage 01b
- legacy ``02_input-*.dat`` / ``04_output-*.out`` remain supported only for
  compatibility with older manual BatchTIPSY workflows
- when a returned output is accepted, FEMIC can store an input SHA256 sidecar
  so later reruns know which exact handoff produced that output

These rules are why this module is so sensitive: a seemingly small field-width
change or a misunderstood stale-output policy can silently distort downstream
managed-curve comparisons.

Freshness And Coherence Policy
------------------------------

The key freshness behavior in this module is:

- if ``allow_stale`` is enabled, the hard freshness guard is bypassed entirely
- otherwise FEMIC prefers canonical-input-based validation over workbook
  timestamp checks
- if a fingerprint sidecar exists and its stored canonical input SHA256 differs
  from the current canonical input SHA256, Stage 01b fails fast
- if output timestamps are older than the current canonical input, FEMIC now
  performs a structural coherence check using AU/table coverage before deciding
  whether to stop
- coherent timestamp mismatch warns and continues by default
- ``strict_timestamp_mismatch`` converts that coherent warning path back into a
  hard error
- when ``managed_curve_mode != tipsy`` the broader workflow may skip this
  boundary because managed curves are no longer driven by refreshed TIPSY output

This is the code-level owner of the guidance documented in the Stage 01b guide.
If the docs and runtime ever seem inconsistent about stale ``04_output`` reuse,
inspect this module first.

Failure Seams To Watch
----------------------

The common failure boundaries in this module are:

- BTC handoff/report regressions
  schema drift, unsafe report columns, or report-template mismatches can make
  BTC reject the handoff or crash during batch processing
- candidate exclusion surprises
  low-volume, low-SI, excluded-leading-species, or no-species-candidate paths
  can remove rows operators expected to see in the handoff
- stale output confusion
  the most common Stage 01b operator error is reusing an old ``04_output`` file
  after the canonical input content changed materially
- coherence false assumptions
  timestamp mismatch does not always mean the output is invalid; this module
  explicitly distinguishes structurally coherent reruns from real stale-output
  drift
- workbook-only reasoning
  code or docs that treat the XLSX mirror as canonical will eventually disagree
  with Stage 01b's canonical-input-first logic

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../../guides/stage-01a-vdyp-tipsy-input`
- :doc:`../../guides/stage-01b-post-tipsy`
- :doc:`../../guides/cross-platform-runtime-smoke`
- :doc:`../../guides/troubleshooting`
- :doc:`../../guides/pipeline-overview`
- :doc:`../run-config`

Related API pages:

- :doc:`femic-pipeline-vdyp-stage`
- :doc:`generated/femic.pipeline.siteprod`
- :doc:`generated/femic.workflows.legacy`

.. toctree::
   :hidden:

   generated/femic.pipeline.tipsy

.. automodule:: femic.pipeline.tipsy
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
