Nemora Task Map (Draft)
=======================

This table maps the current ``femic`` CLI surface to a draft Nemora-oriented
task taxonomy so command intent can be aligned before upstream integration.

.. list-table::
   :header-rows: 1
   :widths: 28 32 28 40

   * - FEMIC CLI entrypoint
     - Current purpose
     - Draft Nemora task key
     - Notes
   * - ``femic run``
     - End-to-end legacy pipeline wrapper
     - ``pipeline.run_legacy``
     - Main orchestration entrypoint with preflight, run manifest, and
       legacy ``--tsa`` FMU/code selection.
   * - ``femic prep run``
     - Data-prep workflow wrapper
     - ``pipeline.prep.run``
     - Narrow wrapper path for prep-only sequencing.
   * - ``femic vdyp run``
     - VDYP-focused workflow wrapper
     - ``pipeline.vdyp.run``
     - Executes VDYP stages under shared run options.
   * - ``femic vdyp report``
     - Summarize VDYP run/curve diagnostics logs
     - ``pipeline.vdyp.report``
     - Candidate for shared diagnostics/reporting utility in Nemora.
   * - ``femic tsa run``
     - legacy-named FMU/code-scoped workflow wrapper
     - ``pipeline.tsa.run``
     - Parallel shape to ``prep run``/``vdyp run`` with shared run-option
       contract.
   * - ``femic tipsy validate``
     - Validate TIPSY handoff config files
     - ``pipeline.tipsy.validate``
     - Standalone config-validation step; low coupling, likely reusable as shared util.
