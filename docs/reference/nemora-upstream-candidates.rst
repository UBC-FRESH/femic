Nemora Upstream Candidates (Draft)
==================================

This inventory identifies extracted helpers that are good candidates for
upstreaming into Nemora as shared utilities.

.. list-table::
   :header-rows: 1
   :widths: 32 36 24 42

   * - Candidate module/helper
     - Current role in FEMIC
     - Upstream priority
     - Upstream rationale
   * - ``femic.pipeline.io`` (run-config/path resolvers)
     - Canonicalizes CLI run inputs, FMU/code defaults, run env, and
       manifest/checkpoint paths through the legacy ``tsa`` seam
     - High
     - Stable interface and broadly reusable across task wrappers.
   * - ``femic.pipeline.stages.execute_legacy_tsa_stage``
     - Shared stage loader/runner seam for per-FMU/code script execution
       through the legacy ``tsa`` contract
     - High
     - Removes duplicated orchestration loops and enforces consistent stage contracts.
   * - ``femic.pipeline.vdyp_logging`` JSONL/text append helpers
     - Structured diagnostics/event logging for VDYP runs and parse events
     - High
     - Reusable logging primitive for other external-tool wrappers.
   * - ``femic.pipeline.manifest`` run-manifest lifecycle helpers
     - Writes deterministic run manifest artifacts for reproducibility/audit
     - Medium
     - Useful common run-audit contract, but schema should be reviewed first.
   * - ``femic.pipeline.tipsy`` and ``tipsy_config`` path/config validation
     - TIPSY config discovery/validation and output path normalization
     - Medium
     - Reusable where TIPSY handoff exists; may remain domain-specific.
   * - ``femic.pipeline.bundle`` AU/curve bundle path/table helpers
     - Bundle table load/write/validation utilities
     - Medium
     - Reusable for model-input bundle assembly across estate pipelines.
   * - ``femic.pipeline.legacy_runtime`` typed runtime payload builders
     - Typed runtime payloads for legacy stage boundaries
     - Low
     - Valuable pattern, but names/fields are currently legacy-script specific.
