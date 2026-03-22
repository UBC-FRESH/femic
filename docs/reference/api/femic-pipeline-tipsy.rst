``femic.pipeline.tipsy`` Module
===============================

The :mod:`femic.pipeline.tipsy` module owns FEMIC's BatchTIPSY handoff seam. It
translates smoothed VDYP outputs into per-AU TIPSY parameter tables, writes the
canonical fixed-width ``02_input-*.dat`` handoff and its XLSX mirror, and
validates whether a returned ``04_output-*.out`` is still safe to reuse during
Stage 01b.

If you are debugging why FEMIC generated the wrong TIPSY input rows, why a DAT
export no longer matches the expected BatchTIPSY column layout, or why Stage 01b
is refusing to accept an existing ``04_output`` file, this is the first module
to read. In practice it owns:

- the fixed-width DAT schema and rendering/validation rules
- candidate evaluation and AU/SI selection for TIPSY parameter generation
- writing the canonical DAT handoff plus the human-readable XLSX mirror
- fingerprinting and freshness validation for returned BatchTIPSY output
- coherence-based stale-output acceptance logic for repeated dev/test reruns

Start Here If...
----------------

Use this page first if you are trying to:

- understand why ``02_input-*.dat`` is treated as canonical while
  ``tipsy_params_tsa*.xlsx`` is only a mirror
- debug BatchTIPSY parse failures caused by field overflow or misaligned fixed
  columns
- inspect why a stratum/SI candidate was excluded from TIPSY parameter
  generation
- trace why Stage 01b accepted or rejected an older ``04_output-*.out`` file
- understand how ``managed_curve_mode=vdyp_transform`` changes the BatchTIPSY
  boundary behavior

Typical maintenance path:

1. Start with :func:`build_tipsy_params_for_tsa` and
   :func:`evaluate_tipsy_candidate` if the issue is about which AU/SI/species
   combinations make it into the handoff.
2. Move to :func:`build_tipsy_input_table` and
   :func:`write_tipsy_input_exports` if the problem is about DAT/XLSX output.
3. Read :func:`validate_tipsy_output_is_fresh`,
   :func:`assess_tipsy_input_output_coherence`, and
   :func:`write_tipsy_output_input_fingerprint` when the failure is visible at
   the manual Stage 01a/01b boundary.

Typical Usage
-------------

The common operator-facing pattern is to let Stage 01a write the canonical DAT
handoff, run BatchTIPSY externally, and then validate the returned output
before Stage 01b resumes:

.. code-block:: python

   from pathlib import Path
   from femic.pipeline.tipsy import validate_tipsy_output_is_fresh

   validate_tipsy_output_is_fresh(
       tipsy_input_excel_path=Path("data/tipsy_params_tsa08.xlsx"),
       tipsy_input_dat_path=Path("data/02_input-tsa08.dat"),
       tipsy_output_path=Path("data/04_output-tsa08.out"),
       allow_stale=False,
   )

How This Fits Into The Pipeline
-------------------------------

This module owns the manual BatchTIPSY boundary described in:

- :doc:`../../guides/stage-01a-vdyp-tipsy-input`
- :doc:`../../guides/stage-01b-post-tipsy`

At a high level, the owning sequence is:

1. Stage 01a selects eligible AU/SI candidates and builds TIPSY parameter rows
2. FEMIC writes ``02_input-*.dat`` and ``tipsy_params_tsa*.xlsx``
3. BatchTIPSY runs manually outside FEMIC and returns ``04_output-*.out``
4. Stage 01b validates that output against the current canonical DAT handoff

That means this module is both a data-shaping layer and a workflow boundary
guard. It does not run BatchTIPSY itself, but it defines the file contracts and
freshness rules that make the manual GUI boundary auditable.

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
  Write the canonical DAT handoff and workbook mirror for one TSA.
- :func:`validate_tipsy_output_is_fresh`
  Enforce the Stage 01b freshness guard against the canonical input DAT.
- :func:`assess_tipsy_input_output_coherence`
  Decide whether an older output still looks structurally coherent with the
  current input workbook.
- :func:`write_tipsy_output_input_fingerprint`
  Persist the DAT SHA256 sidecar paired with an accepted output file.

The small dataclasses in this module are also useful because they define the
candidate/freshness contracts explicitly:

- :class:`TIPSYCandidateEvaluation`
- :class:`TipsyInputOutputCoherence`

Canonical Artifacts And Contracts
---------------------------------

The most important operator/runtime contracts in this module are:

- ``02_input-*.dat`` is the canonical BatchTIPSY input artifact
- ``tipsy_params_tsa*.xlsx`` is a human-readable mirror of the same content,
  not the authoritative freshness source
- ``04_output-*.out`` must match the current DAT handoff or pass the coherence
  policy before Stage 01b should continue
- DAT rows must match the fixed-width schema encoded by
  ``DEFAULT_TIPSY_BATCH_COLUMNS_1BASED`` and the derived row/header offsets
- when a returned output is accepted, FEMIC can store a DAT SHA256 sidecar so
  later reruns know which exact handoff produced that output

These rules are why this module is so sensitive: a seemingly small field-width
change or a misunderstood stale-output policy can silently distort downstream
managed-curve comparisons.

Freshness And Coherence Policy
------------------------------

The key freshness behavior in this module is:

- if ``allow_stale`` is enabled, the hard freshness guard is bypassed entirely
- otherwise FEMIC prefers DAT-based validation over workbook timestamp checks
- if a fingerprint sidecar exists and its stored DAT SHA256 differs from the
  current DAT SHA256, Stage 01b fails fast
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

- DAT layout regressions
  field overflow, wrong alignment, or wrong slice widths can make BatchTIPSY
  reject the handoff or parse the wrong values silently
- candidate exclusion surprises
  low-volume, low-SI, excluded-leading-species, or no-species-candidate paths
  can remove rows operators expected to see in the handoff
- stale output confusion
  the most common Stage 01b operator error is reusing an old ``04_output`` file
  after the canonical ``02_input`` content changed materially
- coherence false assumptions
  timestamp mismatch does not always mean the output is invalid; this module
  explicitly distinguishes structurally coherent reruns from real stale-output
  drift
- workbook-only reasoning
  code or docs that treat the XLSX mirror as canonical will eventually disagree
  with Stage 01b's DAT-first logic

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
