# Roadmap Notes Archive

This file preserves long-form roadmap narrative and superseded structural fragments that were extracted from `ROADMAP.md` when the roadmap was rebuilt as a compact control surface.

## Former ROADMAP.md lines 920-932 - superseded duplicate Phase 33 snapshot

- Original insertion context: Legacy duplicate Phase 33 block that was occupying the main roadmap before the cleanup.
- Affected phases/issues: `P33.1`-`P33.3` legacy TSA29 DataLad standalone publishing snapshot.

### Extracted Content

## Phase 33: TSA29 DataLad Standalone Publishing
- [ ] P33.1 Define the TSA29 shippable Patchworks-instance artifact contract
  - [ ] P33.1a Expand FEMIC docs/contracts so standalone launch-ready publication explicitly requires shipped `blocks/` runtime assets in addition to the existing XML/fragments/tracks surfaces.
  - [ ] P33.1b Distinguish three artifact tiers for TSA29 publication: launch-critical runtime assets, editable rebuild/overlay assets, and transient local spill that must not be published.
  - [ ] P33.1c Tighten release-packaging / validation semantics so standalone launch-ready checks cover `blocks` sidecars, topology CSVs, and analysis/PIN launch surfaces.
- [ ] P33.2 Convert `external/femic-tsa29-instance` to a large-artifact DataLad dataset
  - [ ] P33.2a Initialize the TSA29 instance repo as a DataLad/git-annex dataset using large-only annexing.
  - [ ] P33.2b Define and document the annex policy for TSA29 instance publication, keeping docs/config/small canonical text in Git while annexing bulky instance payloads and oversized rebuild/runtime artifacts.
  - [ ] P33.2c Document bootstrap, special-remote enablement, publish, and materialization workflow for collaborators.
- [ ] P33.3 Publish the current TSA29 PoC package under the new dataset contract
  - [ ] P33.3a Save the current TSA29 standalone model package under the DataLad-managed policy, including shipped `blocks`, `tracks`, validated `forestmodel.xml`, and validated `fragments`.
  - [ ] P33.3b Refresh artifact checksums / lineage notes so the published package is auditable.
  - [ ] P33.3c Verify cold-start usability from a freshly materialized checkout using Patchworks preflight plus a representative GUI or headless smoke launch.

## Former ROADMAP.md lines 934-7858 - Phase 23 closeout status plus first extracted roadmap note block

- Original insertion context: Large historical narrative block removed from the main roadmap during the control-surface cleanup.
- Affected phases/issues: Phase 23 follow-up through the pre-K3Z True-TIPSY provenance era; affected phases/issues are preserved verbatim inside the extracted content.

### Extracted Content

### Phase 23 Windows Closeout Status
- Windows-side Phase 23 closeout is complete on branch feature/phase23-windows-runtime-parity.
- The remaining open work in Phase 23 is Linux-specific parity verification under P23.3.
- Treat the following tasks as **Linux dev environment required** before Phase 23 can be called fully closed:
  - P23.3a
  - P23.3b
  - Linux sign-off portion of P23.3c
- Once those Linux tasks are completed and documented, mark top-level P23.3 and P23 complete.
  - 2026-03-21 update: Linux tasks (`P23.3a`, `P23.3b`, `P23.3c`) are now completed and documented; Phase 23 parity closeout criteria are satisfied.
## Detailed Next Steps Notes

- Opened `#153` to restore `config/tsr/thlb_reconstruction_comparison.{md,json}`
  as the trustworthy dashboard for the active TSA29 strict-lane adjudication
  pass.
  - Rebuild early-ladder rows and milestone values from the current locked clean
    GLB, step-2, step-3, step-4, and AFLB checkpoint results.
  - Mark later rows explicitly stale/unrefreshed until they are re-adjudicated.
- Opened `#154` for the bounded TSA29 step-6 repair.
  - Keep parks/protected areas as the exact spatial overlay.
  - Replace the woodlot / miscellaneous-lease side with a documented residual
    aspatial fallback calibrated to the TSR benchmark because current public
    `F_OWN` is too blunt to separate the active subset TSR actually removed.

- Implemented **#152**:
  - strict reconstructed runs that reach the `GLB -> AFLB` boundary now emit:
    - `data/tsr/aflb_checkpoint.feather` as the canonical restart artifact
    - `data/tsr/aflb_checkpoint.gpkg` by default as the GIS-facing companion
  - `femic tsr thlb-netdown-run` now supports `--no-aflb-gpkg` to suppress only
    the GeoPackage companion export
  - `--checkpoint-path data/tsr/aflb_checkpoint.feather` is now the documented
    downstream restart seam for later `AFLB -> LHLB -> THLB` experimentation
  - bounded TSA29 acceptance from the clean raw GLB baseline produced:
    - `aflb_checkpoint_area_ha = 3,110,576.672`
  - scope remained additive only:
    - settled step-2/3/4 semantics were not changed by this side quest
    - GLB build behavior was not changed

- `#128` strict THLB adjudication:
  - the reconstructed LU-wise source-backed `exclude` bug is now resolved in code:
    the LU execution lane was bypassing compiled `source_attribute_filters` and
    loading raw source polygons directly, which could corrupt any source-backed
    reconstructed exclusion step, not just TSA29 step 2;
  - bounded verification on TSA29 step 2 now shows the LU path matches the
    corrected filtered source logic, reducing the old bogus `936,055 ha`
    removal to `195,843.189 ha`;
  - next bounded follow-on is **step-2 ownership filtering semantics**, not LU
    mechanics: determine which additional ownership categories / reviewed
    discriminators are actually needed to reach the TSR step-2 benchmark
    without reintroducing the old overcut;
  - governing bounded follow-on issue: **#149** `Bug: correct TSA29 strict
    step-2 ownership filtering semantics against TSR benchmark`.

- New pipeline guardrail follow-on opened as **#150**:
  - add hard GIGO protection for THLB overlay steps so reused GIS overlay
    artifacts cannot silently enter production runs when their extent/scope does
    not match the active AOI/checkpoint extent;
  - separate smoke-test / subset overlay artifacts from production-grade full-AOI
    artifacts so reuse cannot "shit in the well" again.

- 2026-04-12 raw-GLB strict AFLB bounded check:
  - bounded reconstructed diagnostic slice only, indices `0..6` (`GLB -> AFLB` executable prefix only)
  - baseline signal: `checkpoint1_raw_glb_initialization`
  - raw strict baseline managed area: `5,158,940.544 ha`
  - step 2 strict removed: `950,193.180 ha` vs TSR `697,033.000 ha`
  - step 3 strict removed: `22,138.326 ha` vs TSR `1,105,908.000 ha`
  - step 4 strict removed: `50,434.000 ha` vs TSR `50,434.000 ha`
  - step 5 AFLB milestone remaining area after steps 2-4: `4,145,680.368 ha`
  - step 5 AFLB delta vs TSR `3,098,168.000 ha`: `+1,047,512.368 ha`
  - bounded artifacts only:
    - `runtime/logs/tsr/reconstructed_diagnostics/raw_glb_glb_to_aflb_20260412T082632Z/glb_to_aflb.audit.json`
    - `runtime/logs/tsr/reconstructed_diagnostics/raw_glb_glb_to_aflb_20260412T082632Z/glb_to_aflb.diag.json`
    - `runtime/logs/tsr/reconstructed_diagnostics/raw_glb_glb_to_aflb_20260412T082632Z/glb_to_aflb_summary.{md,json}`
  - restart the adjudication game from step 2 using this raw-GLB early-ladder result; do not use the older AFLB-conditioned early-step readouts.
- 2026-04-12 step 3 strict fix:
  - fixed reconstructed `select_attribute` execution so checkpoint-attribute exclusions no longer require fetched source polygons
  - reran the same bounded raw-GLB `GLB -> AFLB` slice only, again using indices `0..6`
  - corrected early-ladder read:
    - step 2 strict removed: `950,193.180 ha` vs TSR `697,033.000 ha`
    - step 3 strict removed: `1,802,314.490 ha` vs TSR `1,105,908.000 ha`
      - attribute substep: `1,798,325.607 ha`
      - water substep: `3,988.883 ha`
    - step 4 strict removed: `50,434.000 ha` vs TSR `50,434.000 ha`
    - step-5 AFLB milestone remaining area after steps 2-4: `3,273,312.070 ha`
    - step-5 AFLB delta vs TSR `3,098,168.000 ha`: `+175,144.070 ha`
  - bounded artifacts only:
    - `runtime/logs/tsr/reconstructed_diagnostics/raw_glb_glb_to_aflb_step3fix_20260412T084715Z/glb_to_aflb.audit.json`
    - `runtime/logs/tsr/reconstructed_diagnostics/raw_glb_glb_to_aflb_step3fix_20260412T084715Z/glb_to_aflb.diag.json`
    - `runtime/logs/tsr/reconstructed_diagnostics/raw_glb_glb_to_aflb_step3fix_20260412T084715Z/glb_to_aflb_step3fix_summary.{md,json}`

- 2026-04-10 (Issue `#134` completed: stage-aware THLB review UX hardening is
  now landed on top of the TSA29 table-first parser):
  - Implemented review-surface changes:
    - THLB recipe/status Markdown now opens with a shared review dashboard and
      explicit lock/convergence summary;
    - parent and compiled THLB rows now show deterministic exact FEMIC logic
      summaries plus active user-override provenance where applicable; and
    - the generated THLB workbench notebook now mirrors the same review
      contract, including review prompts that treat exact logic and lock state
      as first-class approval signals.
  - TSA29 acceptance pass:
    - rebuilt the THLB recipe/status/workbench surfaces against the live TSA29
      instance;
    - normalized placeholder lock metadata so generated reports no longer leak
      literal `None`/`null` values into review surfaces; and
    - hardened approved-step preservation so accepted user-reviewed no-op logic
      such as step `023` survives rebuilds consistently in both parent-step and
      flattened compiled-step render paths.
  - Recommended next sequence after this UX pass:
    - `#133` to document the reconstruction ladder/reconciliation contract more
      explicitly for future TSA work; then
    - `#131` to keep pushing execution/runtime seams now that parser/schema and
      review-surface contracts are both cleaner.
- 2026-04-10 (Issue `#134` active implementation: stage-aware THLB review UX
  hardening on top of the TSA29 table-first parser):
  - Governing contract for this slice:
    - keep the existing THLB CLI/build/workbench commands;
    - change the generated review surfaces so they read like a coherent
      netdown-process dashboard instead of a mixed extraction dump; and
    - keep execution semantics unchanged while making lock state, override
      provenance, ratchet state, and exact compiled logic easier to review.
  - Required implementation focus:
    - front-load stage/backbone/benchmark/lock summaries in the THLB Markdown
      reports;
    - add deterministic human-readable exact-logic summaries for parent and
      compiled THLB steps;
    - make user-overlay logic visibly distinct from FEMIC core logic;
    - reshape the generated THLB workbench notebook so it mirrors the same
      stage-aware review contract; and
    - refresh the TSA29 generated review surfaces as the acceptance pass.
  - Acceptance surface for the issue:
    - rebuild the TSA29 THLB recipe/status report and workbench notebook;
    - verify the generated outputs clearly expose stage grouping, exact logic,
      override state, and lock-state dependencies; and
    - leave runner behavior to `#131` / `#132`.
- 2026-04-10 (Issue `#135` active implementation: TSA29-first stage-aware THLB
  parser/schema hardening):
  - Governing contract for this slice:
    - treat TSA29 Table 3 as the canonical ordered THLB parent-step backbone;
    - treat Section 6.2 / 6.3 / 6.4 prose as supporting rationale and
      provenance only, not the stage authority; and
    - treat older-cycle TSR documents as hints only, never silent replacements
      for current-cycle row meaning.
  - Required implementation focus:
    - introduce an explicit row-classification layer for TSA29 Table 3 parent
      rows before draft-subrule generation;
    - make stage assignment deterministic for the known milestone/reference and
      operational rows (`GLB -> AFLB`, `AFLB -> LHLB`, `LHLB -> THLB`,
      `reference_target`, `context`);
    - keep benchmark marginal/cumulative propagation anchored on the Table 3
      row model; and
    - harden subsection extraction/matching so TOC-like noise and duplicate
      headings cannot reclassify clearly table-derived parent rows.
  - Acceptance surface for the issue:
    - rebuild the TSA29 THLB recipe through the normal `thlb-netdown-build`
      path;
    - verify `parent_steps` and flattened `steps` stay stage-consistent; and
    - refresh changelog / issue notes only after parser tests and the normal
      lint/type/test/doc validation set pass.
  - Completion checkpoint:
    - landed an explicit TSA29 Table 3 row-classification layer so the known
      Williams Lake parent rows no longer depend on subsection-stage drift for
      their `land_base_stage` / `execution_class` semantics;
    - hardened subsection parsing against duplicate heading echoes; and
    - verified locally via `thlb-netdown-build` that the live TSA29 recipe
      still places `Future roads` in `LHLB -> THLB`, then restored the
      generated instance files so this issue does not overwrite the separate
      user-reviewed THLB closeout surfaces.
- 2026-04-08 (Issue `#141` guardrail follow-up: block smoke-scale overlays from
  contaminating full-TSA THLB validation):
  - Problem statement:
    - later-stage TSA29 reconciliation exposed that clipped AOI artifacts from
      smoke acquisitions had leaked into full-TSA step `017`/`018` production
      runs, yielding materially false benchmark gaps while still looking
      superficially runnable.
  - Required implementation contract:
    - source-layer acquisitions that carry an AOI must record whether they are
      production-full-TSA, smoke-subset, or AOI-scoped-unknown;
    - AOI-scoped smoke acquisitions must materialize under a separate
      `data/downloads/bcdc/smoke/` root rather than cohabiting with the
      production library;
    - THLB spatial execution must compare source artifact extent against the
      current checkpoint extent and block obvious mismatches instead of quietly
      reusing the layer;
    - runtime JSON/status surfaces must preserve that failure mode explicitly as
      an extent-mismatch blocker, not collapse it into generic
      missing-source noise.
  - Validation targets for this pass:
    - recipe-run test proving AOI metadata and smoke-root placement are
      recorded;
    - parent-step/workbench test proving a clipped overlay is marked
      `blocked_extent_mismatch`;
    - docs/contracts updated so future coding agents do not treat smoke-scale
      artifacts as production-valid GIS inputs.

- TSA29 THLB validation checkpoint: step 21 (`Cultural heritage and archaeological resources`) no longer falls through the generic candidate-layer heuristics. The recipe/workbench now uses a curated aspatial-reduction interpretation tied to TSA29 section 6.4.9, with no fake spatial candidate layers and no bogus road-feature linkage. Next ratchet should resume from this cleaned surface rather than the earlier junk draft-state artifact.

- 2026-04-03 (Issue `#91` launched: TSA29 standalone DataLad publication is the next post-PoC lane):
  - Prior TSA29 rollout umbrella `#84` remains conceptually complete at the
    first runnable Patchworks PoC boundary and should be closed separately
    after the earlier branch/merge hygiene pass; do **not** fold the next TSA29
    work bundle back into `#84`.
  - New post-PoC umbrella:
    - GitHub issue `#91`
    - branch `feature/issue-91-tsa29-datalad-instance-publishing`
  - Child issue gear-train:
    - issue `#93`: define the TSA29 shippable Patchworks-instance artifact
      contract for standalone publication;
    - issue `#94`: convert `external/femic-tsa29-instance` to a large-artifact
      DataLad dataset;
    - issue `#92`: publish the current TSA29 PoC artifact set into the
      DataLad-managed instance and verify cold-start usability.
  - Working contract for this lane:
    - `models/tsa29_patchworks_model/blocks/blocks.shp` sidecar set is now
      treated as a required shipped runtime asset because Patchworks cannot
      launch the TSA29 prototype without it;
    - `models/tsa29_patchworks_model/tracks/` is likewise a required shipped
      runtime asset;
    - `output/patchworks_tsa29_validated/forestmodel.xml` plus
      `output/patchworks_tsa29_validated/fragments/` sidecar set must also ship
      as the anti-lock-in rebuild surface for manual overlays / manual local
      variants outside FEMIC.
  - Storage policy decision:
    - use large-only annexing for TSA29 publication;
    - keep docs/config/small canonical text artifacts in Git;
    - annex bulky instance payloads and oversized rebuild/runtime artifacts;
    - do **not** publish transient local spill such as headless saved-stage
      dumps, scratch logs, temp launchers, or local probe outputs.
  - Immediate next active step:
    - execute issue `#93` first so the standalone publication contract is
      explicit before converting the TSA29 instance repo itself to DataLad in
      issue `#94`;
    - once the contract and dataset policy are explicit, publish and validate
      the current TSA29 PoC artifact set under issue `#92`.

- 2026-04-03 (Issue `#93` complete: standalone TSA29 Patchworks publication contract made explicit):
  - Switched active execution from umbrella branch `feature/issue-91-tsa29-datalad-instance-publishing`
    to issue branch `feature/issue-93-tsa29-standalone-artifact-contract`.
  - Expanded FEMIC's Patchworks readiness language from a two-tier minimum to a
    publication-ready tier ladder:
    - Matrix-Builder-ready
    - post-matrix-build compiled minimum
    - standalone launch-ready published minimum
    - editable anti-lock-in publication tier
  - The standalone launch-ready published tier now explicitly requires:
    - compiled `tracks/*.csv`
    - `blocks/blocks.shp` plus required sidecars
    - the topology CSV used by the shipped analysis surface
    - the analysis/PIN launch surfaces needed to open the model directly
  - The anti-lock-in publication tier now explicitly preserves validated
    `forestmodel.xml` plus validated `fragments/*` as the user-visible rebuild
    and manual-overlay escape hatch, even when the compiled model could
    technically launch without revisiting them.
  - Tightened release-packaging semantics so the module/docs clearly describe
    the **export-bundle** minimum only:
    - renamed the module-facing constant to
      `REQUIRED_PATCHWORKS_EXPORT_FILES` with backward-compatible aliasing;
    - updated release handoff notes to warn that export packaging alone does
      not equal a full standalone Patchworks runtime package.
  - Updated TSA29 instance docs so the local rebuild/runbook contract now names
    `blocks`, topology, and shipped analysis/PIN surfaces as part of the
    runnable standalone model tier.
  - Validation for this contract pass:
    - `python -m pytest tests/test_release_packaging.py`
    - `python -m ruff check src/femic/release_packaging.py tests/test_release_packaging.py`
    - TSA29 standalone docs build passed with
      `python -m sphinx -b html docs _build/html -W -n`
      from `external/femic-tsa29-instance/`
    - the parent-repo Sphinx build is still blocked by a large set of
      pre-existing unrelated API/reference warnings, so that global warning
      wall remains a separate hygiene problem rather than a blocker to `#93`.
  - Immediate next active step:
    - move to issue `#94` and convert `external/femic-tsa29-instance` into the
      large-only DataLad/git-annex dataset defined by the new publication
      contract;
    - after the dataset conversion is in place, publish the current TSA29 PoC
      artifact set and cold-start validation bundle under issue `#92`.

- 2026-04-03 (Issue `#94` closeout in progress: TSA29 instance converted to a DataLad dataset with large-only publication policy):
  - Switched active execution to issue branch
    `feature/issue-94-tsa29-datalad-dataset`.
  - Converted `external/femic-tsa29-instance` into a live DataLad/git-annex
    dataset and preserved the initializer metadata in the instance repo.
  - Tightened the TSA29 dataset classification policy:
    - small docs/config/checksum/launch-wrapper text stays in Git;
    - bulky runtime and rebuild payloads are classified for annex-backed
      storage; and
    - transient runtime spill such as saved-stage dumps and scratch logs stays
      local-only.
  - Updated TSA29 instance docs so collaborators now have an explicit dataset
    bootstrap and maintainer publication workflow:
    - `README.md`
    - `docs/getting-started.rst`
    - `docs/data-and-provenance.rst`
    - `docs/docs-ownership-and-release.rst`
  - Important scope boundary:
    - issue `#94` establishes the dataset and policy surface;
    - issue `#92` remains responsible for publishing the current TSA29 PoC
      payload set, wiring the canonical special-remote bootstrap name, and
      proving cold-start materialization/launch from the published package.
  - Validation:
    - `python -m sphinx -b html docs _build/html -W -n`
      from `external/femic-tsa29-instance/`
    - `git annex info --fast`
    - DataLad status inspection against the TSA29 instance dataset
  - Detailed Next Steps:
    - close issue `#94` with an explicit note that remote publication/bootstrap
      proof moves to issue `#92`;
    - publish the current TSA29 PoC runtime plus rebuild payload set under the
      new dataset policy in issue `#92`;
    - refresh lineage/checksum ledgers as needed for the published payload set;
      and
    - verify a cold-start materialized checkout can still reach the current
      runnable TSA29 Patchworks prototype boundary.

- 2026-04-03 (Issue `#92` closeout in progress: current TSA29 PoC package published into the DataLad-managed instance and cold-start validated):
  - Switched active execution to issue branch
    `feature/issue-92-tsa29-publish-cold-start`.
  - Published the current TSA29 PoC package into the DataLad-managed instance:
    - refreshed bundle/curve inputs and BTC seam files under `data/`;
    - published the standalone Patchworks runtime surfaces under
      `models/tsa29_patchworks_model/{analysis,blocks,tracks}/`;
    - published the validated editable rebuild surfaces under
      `output/patchworks_tsa29_validated/{forestmodel.xml,fragments/}`;
    - refreshed provenance/checksum ledgers under `metadata/`; and
    - added curated runtime manifests tying the package to the issue `#85`,
      `#87`, and `#90` validation passes.
  - Cold-start validation from a fresh local clone:
    - cloned `external/femic-tsa29-instance` into a fresh thin DataLad clone;
    - confirmed annex-backed placeholders initially resolved only to `origin`;
    - materialized the published package with `datalad get`;
    - confirmed annex-backed copies for `blocks.shp`, validated
      `fragments.shp`, `forestmodel.xml`, and `vdyp_results-tsa29.pkl` were
      then present `here`; and
    - ran `python -m femic patchworks preflight --instance-root <fresh-clone> --config config/patchworks.runtime.windows.yaml`,
      which passed against the freshly materialized checkout.
  - Important non-blocking caveat discovered during cold-start replay:
    - `femic prep validate-case` against the fresh clone still expects the
      older broader full-rebuild cache surface (for example
      `ria_vri_vclr1p_checkpoint1.feather`) and is therefore not yet the right
      acceptance gate for the standalone published package.
  - Detailed Next Steps:
    - close issue `#92` with the published-package and cold-start evidence;
    - close umbrella issue `#91` if no additional TSA29 DataLad publication
      work remains in this bundle; and
    - consider a narrower follow-up issue if we want the standalone published
      package and `prep validate-case` expectations to converge more tightly.

- 2026-04-03 (Next TSA29 publication follow-up identified: wire named Arbutus S3 special remote for the TSA29 dataset):
  - Governing issue:
    - GitHub issue `#95`
  - Related child issue:
    - GitHub issue `#96` tracks whether FEMIC itself can reliably own
      Arbutus bucket creation/preflight across Linux and Windows, rather than
      relying on manual out-of-band bucket creation.
  - Planned branch:
    - `feature/issue-95-tsa29-arbutus-special-remote`
  - Scope:
    - configure the named `arbutus-s3` git-annex special remote for
      `external/femic-tsa29-instance`;
    - push annexed TSA29 package content to Arbutus S3;
    - set GitHub publish dependency on the S3 remote; and
    - validate a fresh cold clone using `git annex enableremote arbutus-s3`
      plus `datalad get -r .`.
  - Known-good remote shape from the Linux bootstrap environment:
    - endpoint: `https://object-arbutus.cloud.computecanada.ca`
    - region: `ca-west-1`
    - host: `object-arbutus.cloud.computecanada.ca`
    - protocol: `https`
    - port: `80`
    - request style: `path`
    - chunk: `1GiB`
    - storage class: `STANDARD`
    - encryption: `none`
  - Important execution boundary:
    - do not commit credentials or secret shell snippets into the repo;
    - execute the remote bootstrap only from a shell/session with secure
      `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`,
      `S3_ENDPOINT_URL`, and `S3_BUCKET_NAME` values already injected.
  - Current blocker observed in this Windows session:
    - those secure environment variables are not set here yet, so the actual
      `git annex initremote arbutus-s3 ...` step remains pending.
  - Progress made on the auth bootstrap seam:
    - implemented a Windows-local canonical secret file at
      `%USERPROFILE%\.config\femic\arbutus.env` using plain `KEY=VALUE`
      lines with no quotes and no `export`;
    - added sibling loader scripts:
      - `%USERPROFILE%\.config\femic\load-arbutus-env.ps1`
      - `%USERPROFILE%\.config\femic\load-arbutus-env.sh`
    - verified the PowerShell loader by dot-sourcing it under
      `powershell -ExecutionPolicy Bypass -NoProfile ...`;
    - verified the Git Bash loader by sourcing it under
      `C:\Program Files\Git\bin\bash.exe` with `HOME` pointed at the Windows
      home directory; and
    - intentionally deferred optional PowerShell profile / `.bashrc` hooks
      pending explicit approval.
  - Current execution status on Windows:
    - the TSA29 submodule now has a dedicated
      `feature/issue-95-tsa29-arbutus-special-remote` branch;
    - the local auth loader now yields non-empty values for all required
      AWS/S3 variables in both PowerShell and Git Bash;
    - `git -C external/femic-public-data annex enableremote arbutus-s3`
      succeeds from this Windows host, confirming the existing public-data
      remote remains reachable/enable-able here; but
    - `git annex initremote arbutus-s3 ...` inside
      `external/femic-tsa29-instance` still fails at the bucket-creation step
      with:
      `XmlException {xmlErrorMessage = "Missing error Message"}`.
  - Additional debugging evidence:
    - direct boto3 probes against the Arbutus endpoint from this Windows host
      return `404` for `HeadBucket` on both the intended TSA29 bucket and the
      known public-data bucket name; and
    - boto3 `create_bucket(...)` attempts against the intended TSA29 bucket
      return `NoSuchKey`, so the current blocker is specifically the bucket
      creation / endpoint semantics, not the local loader workflow.
  - Updated state after Linux-side bucket creation:
    - the Linux environment created and verified
      `ubc-fresh-femic-tsa29-instance`, which cleared the original “bucket must
      exist first” blocker;
    - despite that, rerunning `git annex initremote arbutus-s3 ...` from this
      Windows checkout still fails with the same
      `XmlException {xmlErrorMessage = "Missing error Message"}` as if the
      bucket were invisible;
    - repeating direct boto3 `HeadBucket` / `ListBuckets` probes from the same
      loaded Windows session still returns `404` / `NoSuchKey` for both the new
      TSA29 bucket and the known public-data bucket; and
    - `git -C external/femic-public-data annex testremote arbutus-s3` now
      shows the broader problem clearly: the existing Arbutus remote is
      `unavailable` from this Windows-native path and repeatedly throws the
      same `XmlException` during S3 operations.
  - Next likely resolution path:
    - treat the bucket-existence prerequisite as solved and move the active
      blocker to a broader Windows-native Arbutus S3 access seam;
    - tighten the immediate debug target further before any more `git-annex`
      retries:
      - the Windows session is loading a stable-looking redacted
        `AWS_ACCESS_KEY_ID` fingerprint and the intended endpoint/region/bucket
        values; but
      - from that same loaded session, direct boto3 `HeadBucket` probes still
        return `404` for both `ubc-fresh-femic-public-data` and
        `ubc-fresh-femic-tsa29-instance`;
      - this makes Windows-side credential/account-scope parity with the known
        good Linux environment the next thing to confirm before retrying
        `initremote`;
    - continue issue `#95` only once we have either a Windows-native fix or a
      Linux/WSL-backed execution path that can actually perform `git-annex` S3
      operations against Arbutus from this workstation.
  - Follow-on design question now split out:
    - issue `#96` will determine whether FEMIC should gain a cross-platform
      Arbutus bucket bootstrap/preflight helper so future instance-publication
      work does not depend on manual bucket creation outside FEMIC.
  - Final resolution reached on this Windows host:
    - the immediate Windows-side failure was a local auth-input bug, not a new
      Arbutus API mystery:
      - `%USERPROFILE%\.config\femic\arbutus.env` still had single quotes
        wrapped around `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`;
      - interactive dot-sourcing of `load-arbutus-env.ps1` was also being
        blocked by execution policy unless the session used
        `Set-ExecutionPolicy -Scope Process Bypass -Force` or
        `powershell -ExecutionPolicy Bypass -NoProfile ...`;
    - once the quotes were removed and the loader was executed in a bypassed
      session, direct boto3 `HeadBucket` probes returned `head_ok` for both:
      - `ubc-fresh-femic-public-data`
      - `ubc-fresh-femic-tsa29-instance`;
    - `git annex initremote arbutus-s3 ...` then advanced to a different,
      legitimate conflict:
      - the bucket contained only a stale `annex-uuid` marker from an earlier
        aborted initialization attempt;
      - after confirming the bucket held no real payload beyond that single
        marker, deleting `annex-uuid` and retrying `initremote` succeeded;
    - annex payload publication then succeeded with
      `git annex copy --to arbutus-s3 --all`;
    - Git publication dependency was wired with
      `remote.origin.datalad-publish-depends=arbutus-s3`;
    - the TSA29 dataset repo `main` branch was fast-forwarded to the current
      published-package commit (`ccdb50e`) so GitHub cold clones now see the
      actual `models/tsa29_patchworks_model` tree instead of the stale
      pre-publication state; and
    - a fresh clone validated the end-to-end path:
      - `git annex enableremote arbutus-s3` succeeded;
      - required shipped assets were materialized from Arbutus, including:
        - `models/tsa29_patchworks_model/blocks/blocks.shp`
        - `output/patchworks_tsa29_validated/fragments/fragments.shp`
        - `output/patchworks_tsa29_validated/forestmodel.xml`
        - `data/vdyp_results-tsa29.pkl`
      - `python -m femic patchworks preflight --instance-root <fresh-clone> --config config/patchworks.runtime.windows.yaml`
        passed from the fresh clone.
  - Result:
    - issue `#95` is now complete;
    - issue `#96` remains the follow-on investigation into whether FEMIC
      should proactively catch/normalize these local auth-file and bucket
      bootstrap seams instead of leaving them to operator debugging.
  - Immediate documentation hardening follow-up now needed:
    - governing issue:
      - GitHub issue `#97`
    - planned branch:
      - `feature/issue-97-windows-arbutus-bootstrap-docs`
    - the `#95` recovery path depended on facts that were not discoverable
      fast enough from the current user-facing docs, agent-facing notes, or
      CLI/API surfaces for a fresh Windows environment;
    - this dedicated docs issue/branch will turn the successful Windows
      bootstrap path into a short, explicit “new FEMIC instance dataset +
      Arbutus special remote” runbook;
    - that docs pass should make the following points impossible to miss:
      - `%USERPROFILE%\.config\femic\arbutus.env` must use plain
        `KEY=VALUE` lines with no quotes;
      - interactive PowerShell loading needs an execution-policy-bypass path;
      - the recommended lowest-noise validation sequence is:
        - load env file
        - confirm non-empty vars
        - run direct `HeadBucket` probe(s)
        - only then run `git annex initremote`
      - if `initremote` reports an existing conflicting `annex-uuid`, inspect
        the bucket contents before reusing or clearing it;
      - after remote init, publish order matters:
        - `git annex copy --to arbutus-s3 --all`
        - `remote.origin.datalad-publish-depends=arbutus-s3`
        - push `main` and `git-annex`
        - cold-clone / materialization validation;
      - for fresh Windows clones, prefer `git annex get` or an explicit
        materialization check when `datalad get` is not the active entry point
        in the current shell.
  - Documentation hardening delivered under `#97`:
    - updated the canonical Arbutus/DataLad maintainer runbook at
      `docs/guides/public-data-mirror-runbook.rst` with:
      - the recommended Windows local env-file pattern;
      - the no-quotes rule for `arbutus.env`;
      - execution-policy-safe PowerShell loading;
      - the lowest-noise `HeadBucket -> initremote` debug order;
      - the known-good `initremote` parity flags;
      - stale-`annex-uuid` recovery guidance;
      - explicit publish order; and
      - Windows cold-clone materialization guidance;
    - added cross-links and guardrails in:
      - `AGENTS.md`
      - `README.md`
      - `docs/reference/contracts/repo-runtime-invariants.rst`
      - `planning/femic_public_data_datalad_bootstrap.md`
    - validation:
      - `python -m sphinx -b html docs _build/html -W` passed after the docs
        edits.
  - Preflight hardening delivered under `#96`:
    - extended the existing Windows annex/DataLad seam inside
      `femic prep validate-case` rather than adding a new top-level command;
    - when a Windows local Arbutus env-file workflow is actually in play,
      `validate-case` now fails fast on:
      - quoted credential values in `arbutus.env`;
      - missing loaded Arbutus auth vars in the current shell; and
      - failed low-noise bucket visibility probes against the known Arbutus
        public-data bucket;
    - the new logic remains detect/report only:
      - no auto-rewrites of user-local auth files;
      - no bucket creation;
      - no `initremote`/publication automation; and
      - no stale-bucket mutation;
    - docs/reference guidance was updated so `validate-case` is now described
      as the intended low-noise place to catch these Windows Arbutus seams.
  - GitHub hygiene follow-up:
    - close umbrella issue `#84` separately as completed post-PoC tracking,
      rather than keeping it open under the new Arbutus/preflight lane.

- 2026-04-03 (Issue `#85` curve refresh ready for `@gparadis` review):
  - Parent rollout umbrella:
    - GitHub issue `#84`
  - Active issue / branch:
    - GitHub issue `#85`
    - branch `feature/issue-85-tsa29-curve-refresh-post-81-82`
  - What was required to execute the bounded cache-only refresh in this
    checkout:
    - restored the missing TSA29-local execution prerequisites from the
      preserved clean validation clone into
      `external/femic-tsa29-instance/data/`:
      `tsa_boundaries.feather`, the `ria_vri_vclr1p_checkpoint1..8.feather`
      ladder, and the cached `vdyp_prep-tsa29.pkl` /
      `vdyp_results-tsa29.pkl` pair;
    - confirmed `femic prep geospatial-preflight` still passes;
    - observed that `femic prep validate-case` is currently blocked by a
      narrower DataLad status-check seam on `external/femic-public-data` even
      though the submodule worktree itself is clean.
  - Execution completed for run `issue85_curve_refresh_20260403a`:
    - deleted only `data/vdyp_curves_smooth-tsa29.feather` to force Stage 01a
      smoothing replay while keeping raw VDYP bootstrap results cached;
    - reran
      `python -m femic run --instance-root external/femic-tsa29-instance --run-config config/run_profile.tsa29.yaml --run-id issue85_curve_refresh_20260403a`
      and rebuilt the TSA29 smoothed-curve surface plus fresh Stage 01a handoff
      artifacts from cached inputs only;
    - reran
      `python -m femic tsa btc-post-tipsy --instance-root external/femic-tsa29-instance --run-config config/run_profile.tsa29.yaml --tsa 29 --run-id issue85_curve_refresh_20260403a`
      to regenerate the AU-wise review overlays from the refreshed handoff.
  - Fresh review artifacts now available:
    - `external/femic-tsa29-instance/data/vdyp_curves_smooth-tsa29.feather`
      (`413842` bytes; refreshed 2026-04-03 12:19 local);
    - `external/femic-tsa29-instance/data/03_input-tsa29.csv`,
      `tipsy_params_tsa29.xlsx`, `04_output-tsa29.csv`,
      `04_error-tsa29.csv`, `tipsy_curves_tsa29.csv`, and
      `tipsy_sppcomp_tsa29.csv`;
    - `54` refreshed
      `external/femic-tsa29-instance/plots/tipsy_vdyp_tsa29-*.png` overlays;
    - `54` refreshed
      `external/femic-tsa29-instance/plots/vdyp_fitdiag_tsa29-*.png` fit
      diagnostics;
    - `external/femic-tsa29-instance/runtime/logs/run_manifest-issue85_curve_refresh_20260403a.json`
      and
      `external/femic-tsa29-instance/runtime/logs/btc_manifest-issue85_curve_refresh_20260403a_tsa29.json`;
    - `external/femic-tsa29-instance/runtime/logs/vdyp_curve_events-tsa29-issue85_curve_refresh_20260403a.jsonl`.
  - Immediate next step:
    - pause for explicit `@gparadis` review of the refreshed AU plot family;
    - do not start issue `#86` or any downstream XML/tracks work until that
      review gives the hard-freeze green light.

- 2026-04-03 (Issue `#85` review checkpoint corrected after direct plot QA):
  - Direct review of `external/femic-tsa29-instance/plots/tipsy_vdyp_tsa29-23009.png`
    exposed that the earlier `issue85_curve_refresh_20260403a` checkpoint was
    not actually review-ready: the refreshed smoothing step had reused a stale
    raw VDYP cache entry and produced an obviously degenerate straight-line
    `ESSF_SE / H` curve.
  - Root cause:
    - `external/femic-tsa29-instance/data/vdyp_results-tsa29.pkl` still
      contained eleven TSA29 stratum/SI bins with only a single cached VDYP
      table even though the cached prep checkpoint held hundreds to thousands of
      candidate stands for those bins.
    - That stale raw-cache seam produced duplicated and inverted curves that a
      human review should have caught immediately, so the earlier pause point
      was a false completion signal.
  - Repair work completed from cached prep evidence only:
    - replayed the already-isolated `ESSF_SE / H` bucket through raw VDYP with
      run `issue85_essf_se_h_repair_20260403d`, replaced the broken raw cache
      entry, regenerated the smoothed `ESSF_SE / H` curve, and then refreshed
      downstream TIPSY-vs-VDYP overlays;
    - replayed the remaining thin raw-cache bins from the cached
      `vdyp_prep-tsa29.pkl` checkpoint with run
      `issue85_cache_repair_20260403e`:
      `SBPS_PLI / H`, `ESSF_SE / L`, `ESSF_SE / M`, `SBPS_SX / H`,
      `SBS_FDI / M`, `SBS_FDI / H`, `ESSF_PLI / M`, `ESSF_PLI / H`,
      `ICH_CW / L`, `SBS_SX / L`, and `SBS_SX / M`;
    - rebuilt `data/vdyp_results-tsa29.pkl`,
      `data/vdyp_curves_smooth-tsa29.feather`, the `vdyp_fitdiag_tsa29-*.png`
      family, and reran
      `femic tsa btc-post-tipsy --run-id issue85_cache_repair_20260403e` to
      refresh the full `tipsy_vdyp_tsa29-*.png` family plus
      `data/model_input_bundle/*`, `tipsy_curves_tsa29.csv`, and
      `tipsy_sppcomp_tsa29.csv`.
  - Post-repair sanity scan:
    - no TSA29 raw VDYP cache bins remain below 20 tables;
    - the exact duplicate-curve collision between `ESSF_SE / L` and
      `ICH_CW / L` is gone;
    - the catastrophic `ESSF_SE` L/M/H ordering inversion is gone;
    - a small set of mild productivity-order oddities still appears at select
      early/late ages (`SBPS_PLI`, `SBPS_SX`, `SBS_FDI`, `SBS_SX`), but the
      family-wide scan no longer shows the obviously broken one-table/straight-line
      pathology that invalidated the earlier review handoff.
  - Updated review-ready evidence for `@gparadis` is now the repaired
    `issue85_cache_repair_20260403e` output set, not the earlier
    `issue85_curve_refresh_20260403a` checkpoint.

- 2026-04-03 (Issues `#85` and `#86` complete: TSA29 upstream baseline approved and frozen):
  - `@gparadis` explicitly approved the repaired TSA29 AU review bundle after
    direct review of the refreshed `plots/tipsy_vdyp_tsa29-*.png` family.
  - Issue `#85` is now complete; the approved review-ready checkpoint is the
    repaired `issue85_cache_repair_20260403e` artifact set.
  - Issue `#86` is now complete and the TSA29 upstream baseline is frozen for
    downstream work:
    - authoritative upstream artifacts now include
      `external/femic-tsa29-instance/data/vdyp_results-tsa29.pkl`,
      `external/femic-tsa29-instance/data/vdyp_curves_smooth-tsa29.feather`,
      `external/femic-tsa29-instance/plots/tipsy_vdyp_tsa29-*.png`,
      `external/femic-tsa29-instance/plots/vdyp_fitdiag_tsa29-*.png`, and the
      current `data/model_input_bundle/{au_table,curve_table,curve_points_table}.csv`
      set;
    - governing repair run IDs are
      `issue85_essf_se_h_repair_20260403d` and
      `issue85_cache_repair_20260403e`.
  - Policy from this freeze point onward:
    - for TSA29, Stage 00/01 inventory and yield inputs are now treated as
      frozen baseline input to downstream Patchworks assembly;
    - any future change to that upstream baseline requires a new explicit issue
      rather than being folded into downstream rebuild work.
  - Immediate next active step:
    - move to issue `#87` and rebuild TSA29 Patchworks XML plus tracks from the
      frozen upstream bundle without rebuilding fragments, blocks, or topology;
    - after rebuild, inspect the resulting `tracks/*/{features,protoaccounts,accounts}.csv`
      surfaces directly before declaring the Patchworks input layer sane.

- 2026-04-03 (Issues `#87` and `#88` complete: TSA29 Patchworks XML/tracks rebuilt and QA'd):
  - Switched active execution to branch
    `feature/issue-87-tsa29-xml-tracks-rebuild`.
  - Reused the frozen TSA29 upstream bundle and regenerated only
    `external/femic-tsa29-instance/output/patchworks_tsa29_validated/forestmodel.xml`
    through the lower-level XML builder path, explicitly avoiding a fragments
    rebuild.
  - Restored the previously validated fragments shapefile payload into the thin
    TSA29 checkout from the preserved clean TSA29 clone so the canonical
    Matrix Builder input pair was available locally without rerunning
    fragments/topology generation.
  - Patchworks runtime evidence:
    - `femic patchworks preflight --instance-root external/femic-tsa29-instance --config config/patchworks.runtime.windows.yaml`
      passed with the expected local Patchworks install and inherited
      `SPS_LICENSE_SERVER` seat;
    - `femic patchworks matrix-build --instance-root external/femic-tsa29-instance --config config/patchworks.runtime.windows.yaml --run-id issue87_xml_tracks_20260403a`
      completed successfully against the refreshed XML-plus-fragments pair;
    - authoritative logs/manifests are
      `external/femic-tsa29-instance/runtime/logs/patchworks_matrixbuilder_manifest-issue87_xml_tracks_20260403a.json`,
      `...stdout-issue87_xml_tracks_20260403a.log`, and
      `...stderr-issue87_xml_tracks_20260403a.log`.
  - Direct tracks QA summary:
    - rebuilt outputs now live under
      `external/femic-tsa29-instance/models/tsa29_patchworks_model/tracks/`;
    - `features.csv` has `2380` rows;
    - `protoaccounts.csv` has `215` rows;
    - `accounts.csv` has `215` rows and matches `protoaccounts.csv` exactly;
    - `messages.csv` contains only the header row;
    - Matrix Builder stdout reports `217425` fragments/blocks/strata,
      total area `2990475.2087286147`, managed area `2236461.9634461775`,
      passive area `754013.2452824372`, and excluded area `0.0`.
  - Snapshot comparison:
    - `protoaccounts.csv` and `accounts.csv` match the last saved known-good
      TSA29 tracks snapshot exactly;
    - `features.csv` changed as expected with refreshed feature/curve wiring
      from the rebuilt XML, but the expected feature/account label families are
      still present.
  - Immediate next active step:
    - move to issue `#89` and audit whether FEMIC already states the minimal
      functional Patchworks-instance contract clearly enough for TSA29;
    - if gaps remain, harden docs/contracts/preflight logic before attempting
      the first runnable TSA29 scenario/PIN PoC in issue `#90`.

- 2026-04-03 (Issue `#89` complete: Patchworks instance contract made explicit and enforceable):
  - Switched active execution to branch
    `feature/issue-89-tsa29-patchworks-instance-contract`.
  - Hardened FEMIC strict release-packaging logic in
    `src/femic/release_packaging.py` so a Patchworks package is no longer
    treated as complete with only `forestmodel.xml` plus `fragments.shp`;
    the required fragments sidecar set is now:
    `fragments.shp`, `fragments.dbf`, `fragments.shx`,
    `fragments.prj`, and `fragments.cpg`.
  - Added/update contract guidance in:
    - `docs/reference/contracts/stage-boundaries-and-canonical-artifacts.rst`
    - `docs/reference/contracts/recovery-and-external-runtime-boundaries.rst`
    - `docs/guides/model-input-bundle-and-export.rst`
    - `docs/reference/api/femic-release-packaging.rst`
    - `external/femic-tsa29-instance/docs/rebuild-and-qa.rst`
  - The documented minimal contract is now explicit at two tiers:
    - Matrix-Builder-ready: Patchworks runtime config, compiled
      `forestmodel.xml`, full fragments sidecar set, and a host/runtime surface
      that passes `femic patchworks preflight`;
    - post-matrix-build compiled minimum: everything above plus the compiled
      `tracks/` tables (`curves.csv`, `features.csv`, `products.csv`,
      `treatments.csv`, `protoaccounts.csv`, and `accounts.csv`).
  - Validation for this contract-hardening pass:
    - `ruff check src/femic/release_packaging.py tests/test_release_packaging.py`
    - `pytest tests/test_release_packaging.py`
    - `python -m sphinx -b html docs _build/html -W -n`
    - `python -m sphinx -b html docs _build/html -W -n`
      from `external/femic-tsa29-instance/`
  - Immediate next active step:
    - move to issue `#90` and use the rebuilt TSA29 Patchworks package to
      reach the first runnable scenario/PIN boundary with saved outputs or a
      clear actionable runtime error surface.

- 2026-04-03 (Issue `#90` in-flight caution: Patchworks "headless" remains a fragile proving-ground seam):
  - TSA29 has now crossed the first runnable Patchworks scenario/PIN boundary:
    the reconstructed TSA29 launch surface (`analysis/base.pin` +
    restored `blocks/` + rebuilt `tracks/`) successfully completed one
    `max-even-flow-smoke` headless launch with run
    `issue90_tsa29_headless_20260403a` and saved a stage under
    `external/femic-tsa29-instance/runtime/logs/headless_stage/issue90_tsa29_headless_20260403a/`.
  - Important operator caveat:
    - Patchworks can still display execution-blocking modal dialogs that expect
      a human to click `Continue`, `Ignore All`, or `Quit`;
    - those modal windows can break unattended FEMIC runs even when the nominal
      BeanShell/AppChooser launch seam works;
    - Patchworks should therefore be treated as a fragile proving-ground
      headless seam rather than a fully solved unattended runtime.
  - Interpretation rule for issue `#90`:
    - the current success proves TSA29 now has a real runnable launch surface
      and can produce saved-stage output under favorable conditions;
    - it does **not** yet prove that Patchworks modal-dialog handling is solved
      generally or that all TSA29/K3Z headless runs are robustly unattended.

- 2026-04-03 (Issue `#90` complete: TSA29 reached first runnable Patchworks PoC boundary):
  - Closed issue `#90` after confirming that TSA29 now has a genuinely runnable
    Patchworks surface rather than stopping at XML/tracks compilation only.
  - Final PoC ingredients now in place for TSA29:
    - frozen approved upstream inventory/yield baseline from issues `#85`/`#86`;
    - rebuilt canonical Patchworks XML/tracks from issues `#87`/`#88`;
    - explicit minimal Patchworks-instance contract from issue `#89`;
    - restored validated fragments plus restored blocks/topology payload;
    - minimal launch wiring under
      `external/femic-tsa29-instance/models/tsa29_patchworks_model/analysis/`
      and `.../scripts/targets/`.
  - Runnable proof:
    - `femic patchworks run-headless models/tsa29_patchworks_model/analysis/base.pin --instance-root external/femic-tsa29-instance --config config/patchworks.runtime.windows.yaml --run-id issue90_tsa29_headless_20260403a --scenario-mode max-even-flow-smoke --scenario-target product.Yield.managed.Total --iterations 100000`
      completed with `returncode=0`;
    - authoritative runtime evidence is
      `external/femic-tsa29-instance/runtime/logs/patchworks_headless_manifest-issue90_tsa29_headless_20260403a.json`
      plus the saved stage under
      `external/femic-tsa29-instance/runtime/logs/headless_stage/issue90_tsa29_headless_20260403a/`.
  - Closure interpretation:
    - first runnable TSA29 Patchworks PoC: achieved;
    - robust unattended Patchworks runtime: still **not** fully solved because
      modal dialogs can still interrupt nominally headless runs.
  - Post-PoC development mode now changes shape:
    - follow-on work can be scoped as narrower runtime-hardening, packaging,
      policy-cleanup, and scenario-definition issues against an actually
      runnable TSA29 model surface.

- 2026-04-03 (Issue `#90` reopened for TSA29 interactive dev-mode runtime polish):
  - Extend the newly runnable TSA29 Patchworks prototype with two explicit
    development-mode runtime adjustments requested by `@gparadis`:
    - provide an explicitly documented GUI-friendly TSA29 PIN launch surface so
      the prototype can be test-run interactively by a human operator; and
    - temporarily reduce the runtime topology search distance from `100 m` to
      `0 m` in the TSA29 analysis wiring so Patchworks loads a simpler
      adjacency graph during active model development.
  - Scope guard:
    - do **not** reopen upstream inventory/yield compilation;
    - do **not** rebuild fragments or topology geometry;
    - only adjust the TSA29 runtime launch surface / analysis wiring plus any
      directly required Matrix Builder refresh if the changed runtime contract
      demands it.

- 2026-04-03 (Issue `#90` interactive dev-mode polish implemented):
  - Added an explicit operator-facing GUI launch wrapper at
    `external/femic-tsa29-instance/models/tsa29_patchworks_model/analysis/base_gui.pin`
    so `@gparadis` can test the first TSA29 prototype directly in Patchworks
    GUI mode without depending on the fragile headless path.
  - Updated the shared TSA29 analysis wiring to load
    `../blocks/topology_blocks_0r.csv` with topology distance `0 m` during the
    current development cycle.
  - Regenerated the runtime topology CSV with
    `femic patchworks build-blocks --with-topology --topology-radius 0`,
    which produced
    `external/femic-tsa29-instance/models/tsa29_patchworks_model/blocks/topology_blocks_0r.csv`
    for the new lean-load runtime surface.
  - Boundary preserved:
    - no upstream TSA29 inventory or yield artifacts were reopened;
    - no fragments were rebuilt;
    - topology geometry itself was not recomputed beyond the requested `0 m`
      runtime adjacency CSV refresh.

- 2026-04-03 (Issue `#90` re-closed after TSA29 interactive GUI smoke green-light):
  - `@gparadis` confirmed a quick interactive Patchworks GUI smoke test of the
    TSA29 prototype showed no obvious broken runtime surfaces.
  - With both:
    - a successful FEMIC-driven headless saved-stage smoke run; and
    - a successful operator-driven GUI sanity smoke run through
      `models/tsa29_patchworks_model/analysis/base_gui.pin`,
    issue `#90` can close again as complete.
  - Caveat still preserved:
    - unattended Patchworks runtime remains a narrower future hardening seam
      because modal dialogs can still interrupt nominally headless runs.

- 2026-04-03 (TSA29 rollout kickoff after issues `#81` and `#82`):
  - issues `#81` and `#82` repaired real TSA29 VDYP curve-compilation
    defects, so the next active TSA29 lane is now the structured push from
    refreshed AU curve review to the first runnable Patchworks PoC.
  - Immediate execution order:
    - rebuild TSA29 cached VDYP best-fit curves and TIPSY comparison plots
      from cached Stage 01a evidence only;
    - pause for explicit `@gparadis` review of the regenerated AU-wise
      `plots/tipsy_vdyp_tsa29-*.png` family;
    - once approved, hard-freeze the upstream stratified inventory and yield
      baseline with exact artifact and run-ID references;
    - rebuild TSA29 Patchworks XML and tracks from that frozen baseline
      without rebuilding fragments or topology;
    - inspect rebuilt `tracks/*/{features,protoaccounts,accounts}.csv`
      directly for structural and semantic sanity;
    - tighten FEMIC's minimal functional Patchworks-instance contract if any
      required folders/files/runtime seams are still too implicit; and
    - drive TSA29 to a first runnable Patchworks scenario/PIN with saved
      outputs or a clear actionable runtime error surface.
  - Explicit non-scope for this lane:
    - do not rerun raw VDYP from source stands;
    - do not rebuild fragments; and
    - do not rerun topology builder unless a later issue proves the current
      topology invalid.

- 2026-04-03 (Issue `#83` kickoff): add explicit Windows VS Code/Codex local
  file-link recovery guidance so FEMIC contributors can quickly bootstrap-fix a
  broken coding-agent environment instead of getting stuck on browser-opened
  file links.
  - Governing issue:
    - GitHub issue `#83`
  - Immediate execution order:
    - add a short repo-root clue in `AGENTS.md` for agents running inside a
      broken Windows Codex extension;
    - add a concise Windows recovery note to `README.md`;
    - extend `docs/guides/vscode-coding-agent-onboarding.rst` with a focused
      recovery section pointing to `UBC-FRESH/codex-local-file-link-patch`;
    - add short cross-links from deployment/case onboarding docs so new
      contributors can discover the fix from normal FEMIC entry points; and
    - validate the docs build with Sphinx warnings treated as errors before
      closing out the docs push.
- 2026-04-02 (Issue #10 runtime checkpoint): resume TSA29 rebuild execution from
  the synced current-`origin/main` BTC-first workspace and carry the runtime
  findings forward in-repo before the final evidence pass.
  - Tracking issue:
    - GitHub issue #10 ("TSA29 P19.5 rebuild validation and evidence closeout")
  - Current proven status:
    - `femic prep validate-case` and `femic prep geospatial-preflight` pass in
      the synced workspace after restoring the thin-instance checkpoint ladder
      (`tsa_boundaries.feather`, `ria_vri_vclr1p_checkpoint1..8.feather`) from
      the preserved local backup as execution-only forensic inputs;
    - `femic run --run-id tsa29_btc_boundary_smoke_20260402b` reaches the BTC
      seam and emits fresh `03_input-tsa29.csv`, `tipsy_params_tsa29.xlsx`,
      the legacy `02_input-tsa29.dat` mirror, and `vdyp_results-tsa29.pkl`;
    - `femic tsa btc-post-tipsy --run-id tsa29_btc_boundary_smoke_20260402b`
      completes on current main and rebuilds `04_output-tsa29.csv`,
      `04_error-tsa29.csv`, and `data/model_input_bundle/*`;
    - thin TSA29 checkouts do not carry the externalized validated fragments
      shapefile set, so `femic export patchworks --tsa 29 ... --output-dir
      output/patchworks_tsa29_validated` is now part of the practical local
      recovery path before Patchworks preflight;
    - `femic patchworks preflight` passes after that fragments regeneration.
  - Runtime blockers and next actions:
    - keep the parent fix for infinite VDYP sample targets (`b47ad35`) in the
      active branch and include it in the eventual issue closeout;
    - treat `femic patchworks build-blocks --with-topology` with the default
      Python backend as non-viable for the full TSA29 validated surface and use
      `--topology-backend patchworks-raster` for Windows rebuilds;
    - rerun `femic patchworks build-blocks` and `femic patchworks matrix-build`
      once a Patchworks license seat is available; current matrix-build attempts
      stop on `No license available`;
    - once the license-backed Patchworks steps complete, refresh the TSA29
      evidence package and promote the final issue `#10` closeout summary into
      the linked submodule docs plus GitHub.
- 2026-03-28 (Phase 49 kickoff): start issue `#54` on branch
  `feature/patchworks-headless-runner` to turn the documented
  `classic_GUI(control);` seam into a real FEMIC-controlled unattended
  Patchworks runner.
  - Immediate execution order:
    - extract and inspect the local `patchworks-201901` API docs, with first
      focus on `Control`, `Patchworks`, `ScenarioDescription`, `ClassicGui`,
      and `AppChooser`;
    - confirm the smallest real no-GUI launch path from shipped BeanShell and
      sample PIN surfaces before adding any FEMIC API/CLI surface;
    - implement a minimal proving-ground unattended launch/run/report/exit
      helper first, then broaden into richer scenario-definition automation.
  - Success bar for the first slice:
    - FEMIC launches one real Patchworks scenario headlessly,
    - outputs are written to disk,
    - control returns without a human click loop.
- 2026-03-27 (Phase 43 kickoff): start Issue 36 on branch
  `feature/k3z-all-intensive-silviculture` to design and implement a new K3Z
  teaching variant that combines the currently separated intensive
  silviculture paths (`PCT`, `CT`, `F1`, `F2`, `F3`) into one launchable
  surface.
  - Tracking issue:
    - GitHub issue #36 ("Add K3Z variant with combined PCT, CT, and F1/F2/F3
      treatment chain")
  - Immediate planning questions to answer before implementation:
    - which existing AU coverage should the combined variant inherit from the
      current `pct_*` and `ctfert_*` families;
    - what exact state chain should the combined surface use
      (`cc_pl -> cc_pl_pct -> cc_pl_pct_ct -> ...` or equivalent);
    - whether the combined family should ship as one canonical profile or as a
      small subvariant family mirroring the current SI-profile and/or PCT
      intensity choices;
    - how the combined surface should interact with the current QMD,
      stems-per-ha, harvested-QMD, and harvested-volume account contracts so it
      stays parallel with the rest of K3Z.
  - Immediate execution order:
    - compare the current `pct_*` and `ctfert_*` silviculture YAMLs and
      exported state naming so the combined contract reuses accepted behavior
      instead of inventing a parallel treatment model;
    - write the chosen combined treatment-path contract into this roadmap
      before touching exporter/runtime code;
    - only then implement the new variant family, rebuild artifacts, validate,
      and update the standalone K3Z docs.
  - Audit result so far:
    - the exporter already supports `PCT -> CT` composition via config using
      `ct_to_state` on the PCT side and `from_state`/`to_state` on the CT side;
    - fertilization can then continue from the CT state if
      `fertilization.first_application.from_state` matches that CT target
      state;
    - that means the lowest-risk rollout is likely a small combined subvariant
      family with one PCT intensity per surface layered onto one CT/fert
      profile per surface, rather than one giant surface carrying every PCT
      intensity and every fert profile simultaneously.
  - Developer-confirmed design choice:
    - use the full 8-AU union of the current `pct_*` and `ctfert_l15h5`
      families for the new combined rollout;
    - use the existing `ctfert_l15h5` SI-response profile as the CT/fert side
      of the combined family.
- 2026-03-27 (Phase 42 complete): Issue 33 on branch
  `feature/k3z-stems-per-ha-accounts` now exports AU-wise standing
  stems-per-ha surfaces across the active K3Z family.
  - Outcome:
    - added `feature.StemsPerHa.{managed,unmanaged}.<au_token>` surfaces to
      baseline, `ctfert_*`, `pct_*`, and the baseline-derived overlays;
    - rebuilt the K3Z ForestModel XML family and all shipped tracks/account
      surfaces so `main` will deliver the new rows directly;
    - normalized `feature.StemsPerHa.*` accounts downstream during
      `protoaccounts.csv -> accounts.csv` promotion so they read as standing
      stems per hectare instead of total stem counts.
  - Validation completed:
    - targeted exporter/runtime regression tests;
    - full repo gates (`ruff format`, `ruff check`, `mypy`, `pytest`,
      `pre-commit`);
    - parent and standalone K3Z Sphinx builds;
    - Matrix Builder reruns across baseline, CT/fert, PCT, and overlay
      runtime configs;
    - account-surface spot checks for baseline, `ctfert_l15h5`, and
      `pct_light`.
- 2026-03-27 (Phase 42 kickoff): start Issue 33 on branch
  `feature/k3z-stems-per-ha-accounts` to add standing stems-per-ha
  curves/attributes/accounts across the active K3Z launch surfaces.
  - Tracking issue:
    - GitHub issue #33 ("Add stems-per-ha curves, attributes, and accounts to
      active K3Z variants")
  - Working implementation focus:
    - audit the current managed/unmanaged stems-per-ha source support already
      available in `src/femic/fmg/adapters.py` and the K3Z handoff artifacts;
    - define the Patchworks-facing naming contract for
      `feature.StemsPerHa.{managed,unmanaged}.<au_token>`;
    - start with baseline `base`, CT/fert `ctfert_*`, and PCT `pct_*`, then
      carry the same standing-account contract through the overlay family if
      the exporter/runtime wiring is shared as expected;
    - regenerate the shipped K3Z tracks/account surfaces so downstream users
      pulling from `main` receive the new rows immediately after merge;
    - update docs and issue evidence before landing.
- 2026-03-26 (Phase 41 pivot): repurpose Issue 31 on branch
  `feature/k3z-harvest-utilization-factor` to add downstream harvested-volume
  utilization factors instead of changing fragment-level baseline retention.
  - Tracking issue:
    - GitHub issue #31 ("Add K3Z harvest utilization factor for recovered
      merchantable volume")
  - Working implementation focus:
    - keep fragment-level `RETENTION` unchanged;
    - apply a downstream utilization assumption only to harvested-volume
      accounts so standing growing-stock curves stay untouched;
    - use treatment-specific factors:
      - `CC = 0.85`
      - `CT = 0.75`
  - Immediate execution order:
    - add treatment-specific harvested-volume `SUM` multipliers during
      `protoaccounts.csv -> accounts.csv` promotion instead of changing XML or
      fragment inputs;
    - wire the utilization-factor config into the active K3Z runtime surfaces;
    - validate that the base and optional K3Z variants launch cleanly and that
      `product.HarvestedVolume.*.(CC|CT)` accounts reflect the intended
      recovered-volume assumption;
    - update docs / issue closeout evidence before landing.
- 2026-03-26 (Phase 40 widened rollout complete locally): the harvested-stem
  QMD ratio-account contract now extends across all active K3Z launch surfaces
  on branch `feature/k3z-qmd-product-accounts`.
  - Current shipped surface coverage on this branch:
    - baseline `base`
    - overlay subvariants `basecase_riparian`, `basecase_sum`,
      `scenario1_sum`, and `scenario2_sum`
    - CT/fert subvariants `ctfert_l15h5` and `ctfert_l20h0`
    - PCT-only subvariants `pct_light`, `pct_moderate`, and `pct_heavy`
  - Account-contract summary:
    - baseline and overlay surfaces now expose AU-wise harvested-QMD `CC`
      numerator / denominator attributes plus live `product.QMD.*.CC`
      Patchworks ratio accounts;
    - the `pct_*` family now exposes AU-wise harvested-QMD `PCT` and `CC`
      numerator / denominator attributes plus live
      `product.QMD.*.(PCT|CC)` Patchworks ratio accounts;
    - `ctfert_*` keeps the same AU-wise live ratio-account contract already
      accepted during the pilot.
  - Validation snapshot:
    - parent gates passed:
      - `python -m ruff format src tests`
      - `python -m ruff check src tests`
      - `python -m mypy src`
      - `python -m pytest`
      - `python -m pre_commit run --all-files`
      - `python -m sphinx -b html docs _build/html -W`
    - standalone K3Z docs build passed:
      - `python -m sphinx -b html external/femic-k3z-instance/docs external/femic-k3z-instance/docs/_build/html -W`
    - targeted account-surface checks passed:
      - baseline: `accounts=284 species=7 complete_species=7 au=14`
      - overlay `basecase_sum`: `accounts=261 species=6 complete_species=6 au=14`
      - `pct_light`: `accounts=291 species=7 complete_species=7 au=14`
      - `pct_moderate`: `accounts=291 species=7 complete_species=7 au=14`
      - `pct_heavy`: `accounts=291 species=7 complete_species=7 au=14`
  - Immediate next move:
    - update GitHub issue `#27` with the widened rollout evidence, then
      checkpoint parent + submodule commits before opening PRs or closing the
      issue.
- 2026-03-26 (Phase 40 kickoff): start Issue 27 on branch
  `feature/k3z-qmd-product-accounts` in the parent repo and K3Z submodule to
  add harvested-stem QMD `product` accounts to the active K3Z `ctfert_*`
  family, then port the same logic across the remaining active K3Z variants.
  - Tracking issue:
    - GitHub issue #27 ("Add harvested-stem QMD product accounts to K3Z
      CT/fert and port across variants")
  - Working implementation focus:
    - treat the active `ctfert_l15h5` and `ctfert_l20h0` surfaces as the pilot
      family;
    - add AU-wise harvested-stem mean-diameter `product` accounts that sit
      alongside, but remain clearly distinct from, the existing standing-stock
      `feature.QMD.*` surfaces;
    - keep the first pass limited to the CT/fert family until the account
      contract, normalization semantics, and runtime promotion behavior are
      proven out cleanly.
  - Immediate execution order:
    - audit the current product-account export path in
      `src/femic/fmg/patchworks.py` and the runtime
      `protoaccounts.csv -> accounts.csv` promotion logic in
      `src/femic/patchworks_runtime.py`;
    - define the new harvested-stem QMD account naming contract so the account
      surface makes the distinction between standing QMD and harvested-stem QMD
      obvious;
    - implement and validate the `ctfert_l15h5` / `ctfert_l20h0` pilot slice
      end-to-end, including refreshed shipped `tracks_ctfert_* / accounts.csv`
      surfaces;
    - only after the CT/fert pilot is stable, plan the port of the same
      product-QMD logic to the other active K3Z variants.
- 2026-03-26 (Phase 40 correction): convert the first-pass harvested-stem QMD
  pilot from raw numerator surfaces to live Patchworks `RatioAccount`
  registration so the launched `product.QMD.*` values resolve directly to mean
  harvested diameter in `cm`.
  - Immediate execution order:
    - rename the shipped AU/treatment harvested-QMD rows to an internal
      numerator namespace;
    - add BeanShell startup logic on the active `ctfert_*` `.pin` surfaces to
      call `control.addRatioAccount(...)` with scale `1` for the user-facing
      `product.QMD.*` accounts;
    - rebuild the `ctfert_*` tracks and update tests/docs so they describe
      `product.QMD.*` as runtime ratio accounts, not direct checked-in
      `accounts.csv` rows;
    - keep the current random-subset CT harvested-stem assumption for now, then
      revisit it later when `nemora` stem-diameter distributions are available.
- 2026-03-25 (Phase 36 kickoff): start Issue 21 on branch
  `feature/k3z-ctfert-si-subvariants` in the parent repo and K3Z submodule to
  expand the K3Z CT/fert teaching surface from the current medium-SI-only
  `FDC+HW` / `CW+HW` cohort to the full low/medium/high-SI cohort and compile
  two new SI-specific fert-response subvariants.
  - Tracking issue:
    - GitHub issue #21 ("Expand K3Z CT/fert to L/M/H SI classes and add two
      SI-specific fert-response subvariants")
  - Working implementation focus:
    - keep the current single CT treatment unchanged (30% BA removal from
      below);
    - keep the three-step fert chain (`F1` / `F2` / `F3`) wherever fert remains
      enabled;
    - expand eligible AUs from 2 to 6 across the `L/M/H` SI classes of the
      `FDC+HW` and `CW+HW` strata;
    - add two new subvariants with these SI-specific fert boosts:
      - profile A: `L=15%`, `M=10%`, `H=5%`
      - profile B: `L=20%`, `M=10%`, `H=0%` interpreted as "do not enable fert
        at all on H-class AUs" rather than compiling null-effect fert paths.
  - Immediate execution order:
    - audit the current `ctfert` silviculture/runtime/variant surface and
      enumerate the six eligible AUs explicitly;
    - decide whether the existing `ctfert` variant remains as-is while the two
      new response-profile subvariants are added alongside it;
    - overlay the `RETENTION` values from
      `tmp/CTFert Fragments/fragments_updated3_Usedinbasecase.shp` onto both
      new CT/fert subvariants so they replace the current placeholder `0.05`
      retention values;
    - teach the silviculture/export logic to express SI-specific fert boosts
      without compiling explicit 0%-effect fert paths;
    - regenerate the K3Z ForestModel/tracks/runtime/docs surfaces and validate
      both new subvariants with Matrix Builder before closeout.
- 2026-03-25 (Phase 36 complete locally): the two new CT/fert SI-profile
  subvariants are implemented and validated on
  `feature/k3z-ctfert-si-subvariants`.
  - New runtime surfaces:
    - `ctfert_l15h5`
    - `ctfert_l20h0`
  - Final semantics:
    - CT is now eligible on six `L/M/H` AUs:
      `985501001`, `985502001`, `985503001`, `985501002`, `985502002`,
      `985503002`;
    - `ctfert_l15h5` applies fert boosts `L=15%`, `M=10%`, `H=5%` and keeps
      the full `CT -> F1 -> F2 -> F3` chain on that eligible cohort;
    - `ctfert_l20h0` applies fert boosts `L=20%`, `M=10%`, and disables fert
      entirely on the `H` cohort while still compiling CT there.
  - RETENTION overlay provenance:
    - both validated fragment surfaces now match
      `tmp/CTFert Fragments/fragments_updated3_Usedinbasecase.shp` exactly
      across the accepted 218-fragment geometry footprint.
  - Runtime bug fix:
    - the CT / `F1` / `F2` / `F3` age-reset bug was fixed by emitting the
      Patchworks-schema-legal treatment attribute `adjust="R"` after first
      confirming that the earlier `adjusts="'R'"` form was invalid against
      `ForestModel.xsd`.
  - Validation:
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l15h5.windows.yaml --run-id k3z_ctfert_l15h5`
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l20h0.windows.yaml --run-id k3z_ctfert_l20h0`
    - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l15h5.windows.yaml`
    - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l20h0.windows.yaml`
- 2026-03-26 (Phase 36 follow-up): add a configurable CT post-thinning
  final-felling gap control after confirming the current implementation
  subtracts a flat CT-removed volume from all later final-felling yields.
  Next steps:
    - patch the commercial-thinning exporter so the final-felling gap ramps
      linearly from `1.0 x CT harvest volume` at CT age to a configurable
      target factor at `cmai_argmax`;
    - expose that target factor on the K3Z `ctfert_*` silviculture YAML
      surface with a default of `1.0` to preserve existing behavior;
    - rebuild `ctfert_l15h5` and `ctfert_l20h0` with the new target factor
      set to `0.0`, then rerun Matrix Builder and the usual validation gates.
- 2026-03-26 (Phase 36 follow-up complete locally): added a configurable
  commercial-thinning `final_felling_gap_factor` knob and rebuilt the two K3Z
  CT/fert SI-profile subvariants with that target set to `0.0`.
  - Exporter change:
    - the old CT residual-yield logic lived in
      `src/femic/fmg/patchworks.py` and subtracted a flat
      `ct_removed_volume` constant from all post-CT final-felling yields;
    - the new logic ramps the post-CT final-felling gap linearly from
      `1.0 x CT harvest volume` at CT age to the configured
      `final_felling_gap_factor` at `cmai_argmax`, then holds that target
      factor afterward.
  - K3Z config/doc updates:
    - `config/silviculture.k3z.ctfert_l15h5.yaml` and
      `config/silviculture.k3z.ctfert_l20h0.yaml` now set
      `commercial_thinning.final_felling_gap_factor: 0.0`;
    - standalone docs now explain the new knob and the zero-gap setting in
      `docs/silviculture-logic.rst` and
      `docs/variants-and-subvariants.rst`.
  - Runtime rebuild + QA:
    - regenerated
      `models/k3z_patchworks_model/yield/forestmodel_ctfert_l15h5.xml` and
      `models/k3z_patchworks_model/yield/forestmodel_ctfert_l20h0.xml`
      directly from the current bundle tables plus the updated silviculture
      YAMLs because checkpoint-based export remains blocked by the missing
      `data/ria_vri_vclr1p_checkpoint7.feather` / `au` handoff in this clone;
    - recopied the curated fragments overlay from
      `tmp/CTFert Fragments/fragments_updated3_Usedinbasecase.shp` onto both
      validated CT/fert subvariant surfaces;
    - reran Matrix Builder successfully for
      `ctfert_l15h5_gap0_20260326` and `ctfert_l20h0_gap0_20260326`;
    - confirmed from the rebuilt tracks that the post-CT final-felling gap now
      tapers to zero by later ages instead of remaining equal to the CT
      harvest volume indefinitely.
- 2026-03-26 (Phase 36 XML cleanup follow-up): thin the K3Z VDYP-derived XML
  yield curves to decadal knots so unmanaged curves no longer carry annual
  point density into the shipped ForestModel XMLs while managed TIPSY curves
  remain unchanged.
  Completed locally:
    - patched the exporter so unmanaged/VDYP total-yield curves now keep the
      first point, every 10-year knot, and the final point;
    - regenerated the shipped K3Z XML family from the updated exporter,
      including the active baseline, `pct_*`, and `ctfert_*` surfaces;
    - reran Matrix Builder successfully for the baseline, `ctfert_l15h5`, and
      `ctfert_l20h0` runtime configs after the curve thinning change;
    - retired the legacy single-surface `ctfert` launch surface so the active
      K3Z CT/fert family is now only `ctfert_l15h5` and `ctfert_l20h0`;
    - updated the standalone K3Z docs to explicitly record that the validated
      CT/fert fragment surfaces use curated `RETENTION` values overlaid from
      `tmp/CTFert Fragments/fragments_updated3_Usedinbasecase.shp`;
    - validation passed with:
      - `pytest tests/test_docs_contract.py tests/test_fmg_adapters.py tests/test_fmg_patchworks.py`
      - `ruff check src tests`
      - `mypy src`
      - `sphinx-build -b html docs _build/html -W`
      - standalone K3Z `python -m sphinx -b html docs docs/_build/html -W`
- 2026-03-26 (Phase 37 kickoff / Issue #22): replace the placeholder K3Z QMD
  curves with a reverse-engineered approximation derived from accepted stand
  yield, site-index height assumptions, and trees-per-hectare inputs rather
  than the current hand-tuned age heuristic.
  Completed locally:
    - audited the current QMD export path and confirmed the shipped curves were
      still coming from a hand-tuned age heuristic in
      `src/femic/fmg/patchworks.py`;
    - added per-AU QMD support loading in `src/femic/fmg/adapters.py`, using
      accepted K3Z inputs from:
      - `data/tipsy_curves_tsak3z.csv`
      - `data/tipsy_params_tsak3z.xlsx`
      - `data/ria_vri_vclr1p_checkpoint1-tsak3z.feather`
      - `data/vdyp_lyr-tsak3z.feather`
    - rebuilt the QMD exporter so managed curves use accepted BatchTIPSY
      height/TPH support when available and unmanaged curves fall back to a
      reverse-engineered approximation using stand yield, linear site-index
      height, and VDYP-side stems-per-hectare proxies;
    - preserved the existing CT/fert response multipliers on top of the
      rebuilt base QMD curves instead of the older placeholder age formula;
    - regenerated `forestmodel_ctfert_l15h5.xml` and
      `forestmodel_ctfert_l20h0.xml`, then reran Matrix Builder successfully
      for both CT/fert SI-profile subvariants;
    - updated the standalone K3Z docs to describe the new approximate QMD
      contract instead of the older placeholder wording;
    - validation passed with:
      - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l15h5.windows.yaml --run-id k3z_ctfert_l15h5_qmd_upgrade_retry_20260326`
      - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l20h0.windows.yaml --run-id k3z_ctfert_l20h0_qmd_upgrade_retry_20260326`
      - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l15h5.windows.yaml`
      - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert_l20h0.windows.yaml`
      - `ruff format src tests`
      - `ruff check src tests`
      - `mypy src`
      - `pytest`
      - `pre-commit run --all-files`
      - `sphinx-build -b html docs _build/html -W`
      - standalone K3Z `python -m sphinx -b html docs docs/_build/html -W`
- 2026-03-26 (Phase 37 cleanup): remove stale/dead QMD metadata knobs from the
  active `ctfert_*` silviculture YAMLs now that the exporter no longer uses
  the older `synthetic` / placeholder QMD path.
  Completed locally:
    - removed `qmd.source` and `qmd.notes` from:
      - `external/femic-k3z-instance/config/silviculture.k3z.ctfert_l15h5.yaml`
      - `external/femic-k3z-instance/config/silviculture.k3z.ctfert_l20h0.yaml`
    - verified the active user-facing docs already describe the current
      approximate QMD contract and no longer claim the shipped CT/fert QMD
      surfaces are placeholder outputs.
      open the parent + K3Z PRs from `feature/k3z-ctfert-si-subvariants`.
- 2026-03-25 (Phase 35 kickoff): correct the human-readable AU naming rollout
  so the shipped K3Z runtime artifacts actually expose the readable labels in
  launched Patchworks sessions.
  - Tracking issue:
    - GitHub issue #2 (reopened because the exported generator/tests were
      updated but the tracked K3Z runtime ForestModel XML family was not
      regenerated before merge).
  - Immediate repair scope:
    - regenerate the tracked K3Z ForestModel XML family from the updated
      exporter so `forestmodel.xml`, `forestmodel_ctfert.xml`, and the
      `forestmodel_pct_*` variants use the new AU labels;
    - verify the active launch surfaces (`analysis/base.pin` and related
      variants) resolve those readable labels at runtime rather than the old
      numeric AU ids;
    - rerun Matrix Builder across the active K3Z runtime family to ensure the
      regenerated XMLs are valid and actually ship through the runtime path;
    - update docs/changelog/issue status with the correction and do not close
      the issue again until the tracked runtime artifacts are verified.
- 2026-03-25 (Phase 35 complete): shipped K3Z runtime artifacts now expose
  syntax-safe readable AU tokens rather than numeric AU ids or illegal
  operator-bearing labels.
  - Root cause:
    - Patchworks parses attribute ``label=`` values as expressions, so the
      initial human-readable format using ``-`` and ``+`` (for example
      ``CWHvm-HW+FDC-H``) was not legal and caused XML-load failure even
      though the exported XML structure itself was otherwise valid.
  - Corrective implementation:
    - rebuilt the human-readable naming logic to use Patchworks-safe AU tokens
      derived from the same metadata, for example ``CWHvm_HW_FDC_H``;
    - regenerated the tracked K3Z ForestModel XML family
      (baseline, ``ctfert``, ``pct_light``, ``pct_moderate``, ``pct_heavy``);
    - reran Matrix Builder for baseline, ``ctfert``, all ``pct_*`` variants,
      and all four overlay track families so the shipped ``tracks*/`` account
      surfaces now match the syntax-safe naming contract.
  - Validation:
    - focused tests for Patchworks/account-surface/docs contracts;
    - `ruff format src tests`
    - `ruff check src tests`
    - `mypy src`
    - `pytest`
    - `pre-commit run --all-files`
    - `sphinx-build -b html docs _build/html -W`
    - standalone K3Z `sphinx-build -b html docs docs\\_build\\html -W`
    - Matrix Builder runs for baseline, ``ctfert``, ``pct_light``,
      ``pct_moderate``, ``pct_heavy``, ``overlay.basecase_riparian``,
      ``overlay.basecase_sum``, ``overlay.scenario1_sum``, and
      ``overlay.scenario2_sum`` all completed successfully with syntax-safe AU
      account names visible in the synced ``tracks*/accounts.csv`` surfaces.
- 2026-03-24 (Phase 34 kickoff): start Issue 2 on branch
  `feature/human-readable-au-names` to replace opaque numeric AU codes in the
  primary Patchworks-facing naming surfaces.
  - Tracking issue:
    - GitHub issue #2 ("Use human-readable AU names in Patchworks account
      names and related ForestModel surfaces")
  - Working implementation focus:
    - the immediate pain point is Patchworks account naming, where account
      labels like `feature.Seral.985501000.mature` are hard to interpret
      without an AU lookup table;
    - the same ForestModel generation seam also controls related readable XML
      ids/labels, so the change should be applied consistently where it
      improves human readability without breaking join semantics.
  - Immediate execution order:
    - add one deterministic AU display-label helper from `stratum_code` +
      `si_level`;
    - replace raw numeric AU tokens in the Patchworks account-producing labels
      (`feature.Area.og*`, `feature.QMD.*`, `feature.Seral.*`,
      `product.Seral.area.*`) with that readable AU label;
    - extend the same helper to adjacent readable XML curve/id surfaces where
      practical, while leaving numeric `AU eq ...` select semantics intact;
    - update account-surface parsing/tests/docs to accept and describe the new
      label format.
- 2026-03-24 (Phase 34 complete): human-readable AU labels now replace raw
  numeric AU ids across the Patchworks-facing account names and adjacent
  readable ForestModel ids generated by `src/femic/fmg/patchworks.py`.
  - Implemented behavior:
    - labels are derived from `stratum_code` + `si_level`, yielding values such
      as `CWHvm-HW+FDC-H`;
    - a TSA-prefix fallback is applied automatically only when the readable
      labels would otherwise collide across TSAs;
    - numeric AU ids remain in internal `AU eq ...` select clauses and similar
      join semantics where they are still required.
  - Validation:
    - `ruff format src tests`
    - `ruff check src tests`
    - `mypy src`
    - `pytest`
    - `pre-commit run --all-files`
    - `sphinx-build -b html docs _build/html -W`
    - standalone K3Z `sphinx-build -b html docs docs\\_build\\html -W`
  - Next workflow step:
    - update GitHub issue #2 with implementation status and validation before
      opening PRs / closing the issue on merge.
  - Success criterion:
    - primary user-facing Patchworks account names no longer require reading a
      long numeric AU code to understand what AU they refer to, and regression
      coverage prevents the numeric-only labels from quietly returning.
- 2026-03-24 (Phase 33 closeout): the K3Z true-TIPSY provenance correction
  now reaches all the way through the tracked managed-curve artifacts, not just
  the docs plot surface.
  - Tracking issue:
    - GitHub issue #17 ("Regenerate K3Z true-TIPSY comparison plots and remove
      stale scaled-VDYP docs artifacts")
  - Result:
    - proved that `data/tipsy_curves_tsak3z.csv` and the treated managed rows
      in `data/model_input_bundle/curve_points_table.csv` were still carrying
      the old scaled-VDYP lineage instead of raw BatchTIPSY output;
    - regenerated both tracked artifacts directly from
      `data/04_output-tsak3z.out`, restoring exact agreement between the
      treated bundle curves and the raw BatchTIPSY output for all 14 treated
      AUs;
    - rebuilt the baseline, `ctfert`, and `pct_*` ForestModel XMLs from the
      corrected bundle tables and synchronized the matching
      `output/patchworks_k3z*_validated/forestmodel.xml` copies;
    - reran Matrix Builder successfully for baseline, `ctfert`, the three
      `pct_*` subvariants, and all four overlay runtime configs.
  - Validation evidence:
    - bundle-vs-raw comparison now reports `{'both': 504, 'left_only': 0,
      'right_only': 0}` with `maxdiff=0.0` for the treated managed curves;
    - treated managed yield curves in
      `forestmodel.xml`, `forestmodel_ctfert.xml`,
      `forestmodel_pct_light.xml`, `forestmodel_pct_moderate.xml`, and
      `forestmodel_pct_heavy.xml` now all validate as raw-TIPSY-style decadal
      point series for the treated AUs;
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.windows.yaml --run-id k3z_true_tipsy_baseline_20260324`
      completed successfully with `returncode=0`;
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert.windows.yaml --run-id k3z_true_tipsy_ctfert_20260324`
      completed successfully with `returncode=0`;
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_light.windows.yaml --run-id k3z_true_tipsy_pct_light_20260324`
      completed successfully with `returncode=0`;
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_moderate.windows.yaml --run-id k3z_true_tipsy_pct_moderate_20260324`
      completed successfully with `returncode=0`;
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_heavy.windows.yaml --run-id k3z_true_tipsy_pct_heavy_20260324`
      completed successfully with `returncode=0`;
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.overlay.basecase_riparian.windows.yaml --run-id k3z_true_tipsy_overlay_basecase_riparian_20260324`
      completed successfully with `returncode=0`;
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.overlay.basecase_sum.windows.yaml --run-id k3z_true_tipsy_overlay_basecase_sum_20260324`
      completed successfully with `returncode=0`;
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.overlay.scenario1_sum.windows.yaml --run-id k3z_true_tipsy_overlay_scenario1_sum_20260324`
      completed successfully with `returncode=0`;
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.overlay.scenario2_sum.windows.yaml --run-id k3z_true_tipsy_overlay_scenario2_sum_20260324`
      completed successfully with `returncode=0`;
    - `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
      and `pre-commit run --all-files` all pass.
- 2026-03-24 (Phase 31 kickoff): retarget the K3Z student silviculture
  surface from `pctct_*` to PCT-only `pct_*` subvariants on branch
  `feature/k3z-pctct-expand-treatment-aus`.
  - Tracking issue:
    - GitHub issue #14 ("PCT-only requests: change eligible AUs, change AU
      regen assumptions, remove CT, add knob for changing PCT intensity")
  - Immediate execution order:
    - rename the K3Z PCT subvariant files/artifacts from `pctct_*` to
      `pct_*`;
    - remove `commercial_thinning` from the three active PCT subvariant YAMLs
      so the managed treatment path ends at `cc_pl_pct`;
    - regenerate `forestmodel_pct_*.xml`, `tracks_pct_*`, and
      `output/patchworks_k3z_pct_*_validated` from the PCT-only configs;
    - update parent/K3Z docs and regression tests so the supported launch
      matrix is `pct_light`, `pct_moderate`, and `pct_heavy`, with no `CT`
      products or `cc_pl_pct_ct` state in that family.
  - Success criterion:
    - the checked-in K3Z PCT-only surfaces launch via `pct_*` config + PIN
      pairs, materialize `PCT` without `CT`, preserve the accepted baseline
      fragment geometry, and the docs/contracts no longer describe the family
      as `PCT -> CT`.
- 2026-03-24 (Phase 31 closeout): the K3Z student treatment family is now
  PCT-only under `pct_light`, `pct_moderate`, and `pct_heavy`.
  - Result:
    - renamed the active K3Z runtime/spec/PIN/silviculture/build surfaces from
      `pctct_*` to `pct_*`;
    - removed `commercial_thinning`, `CT`, and the `cc_pl_pct_ct` leg from the
      three active PCT subvariant YAMLs so the treatment path now ends at
      `cc_pl_pct`;
    - regenerated `forestmodel_pct_*.xml`, rebuilt `tracks_pct_*`, and
      refreshed `output/patchworks_k3z_pct_*_validated` against copies of the
      accepted baseline fragments surface;
    - updated parent/K3Z docs and regression tests so the supported launch
      matrix, artifact names, and troubleshooting guidance all describe the
      new PCT-only family and explicitly reject retired `pctct_*` paths.
    - posted a final GitHub issue closeout comment naming the primary doc
      locations (`external/femic-k3z-instance/docs/` and
      `docs/sample-models/k3z.rst`), explaining why the delivered scope
      satisfies Issue 14, and then closed the issue.
  - Validation evidence:
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_light.windows.yaml --run-id k3z_pct_light_20260324_rebuild`
      completed successfully with `returncode=0`;
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_moderate.windows.yaml --run-id k3z_pct_moderate_20260324_rebuild`
      completed successfully with `returncode=0`;
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_heavy.windows.yaml --run-id k3z_pct_heavy_20260324_rebuild`
      completed successfully with `returncode=0`;
    - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_light.windows.yaml`
      reports `accounts=232`, `species=8`, `complete_species=8`, `au=14`;
    - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_moderate.windows.yaml`
      reports `accounts=232`, `species=8`, `complete_species=8`, `au=14`;
    - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pct_heavy.windows.yaml`
      reports `accounts=232`, `species=8`, `complete_species=8`, `au=14`;
    - active `tracks_pct_*` and `forestmodel_pct_*.xml` surfaces no longer
      materialize `CT` or `cc_pl_pct_ct`;
    - `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
      `sphinx-build -b html docs _build/html -W`,
      `..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`,
      and `pre-commit run --all-files` all pass.
- 2026-03-24 (Phase 32 kickoff): start Issue 13 on a fresh feature branch to
  integrate TIPSY-vs-VDYP yield-curve plots into the user-facing K3Z Sphinx
  docs.
  - Tracking issue:
    - GitHub issue #13 ("Upload new tipsy yield curves into guide")
  - Working interpretation:
    - the sparse issue title/body plus operator request mean the student-facing
      standalone K3Z docs should expose the existing TIPSY-vs-VDYP comparison
      plots more directly, rather than leaving them discoverable only as raw
      generated files.
  - Immediate execution order:
    - audit the current K3Z docs and the checked-in plot inventory to find the
      best student-facing landing page(s);
    - decide whether the right surface is an existing guide page, a new figure
      gallery page, or both;
    - update the standalone K3Z docs and any parent pointer docs as needed so
      students can find and interpret the comparison plots easily.
  - Success criterion:
    - a student using only the published K3Z docs can find the TIPSY-vs-VDYP
      comparison figures, understand what they show, and reach them from the
      normal getting-started / model-navigation flow.
- 2026-03-24 (Phase 32 implementation): the K3Z standalone docs now expose the
  treated TIPSY-vs-VDYP curve overlays through a dedicated student-facing guide
  page instead of leaving them discoverable only through the figure appendix.
  - Result:
    - added `external/femic-k3z-instance/docs/yield-curve-comparisons.rst` as
      a direct guide entry point with plain-language interpretation notes, a
      full treated-curve gallery, and an explanation of why AUs `22006` and
      `22008` are absent from the current comparison set;
    - linked that page into `index.rst`, `getting-started.rst`,
      `base-case-analysis.rst`, `model-anatomy.rst`, and
      `data-package-crosswalk.rst` so students can reach it through the normal
      navigation flow;
    - kept `figure-appendix.rst` as the filename-traceability/catalog surface,
      while adding an explicit cross-link back to the new student-facing page.
  - Validation evidence:
    - standalone K3Z docs build passes with
      `sphinx-build -b html docs docs\_build\html -W` from the
      `external/femic-k3z-instance` root;
    - parent quality gates pass with `ruff format src tests`,
      `ruff check src tests`, `mypy src`, `pytest`, and
      `pre-commit run --all-files`.
  - Issue tracking:
    - GitHub issue #13 now carries an explicit implementation/closeout note
      naming the new docs page and validation results, and the issue is closed
      as implemented.
- 2026-03-24 (Phase 23 `P23.11` kickoff): start the VDYP fit-policy YAML
  migration on branch `feature/vdyp-fit-policy-yaml`.
  - Tracking issue:
    - GitHub feature request `#9`:
      `Move VDYP fit overrides from code to a YAML-backed policy surface`
  - Immediate execution order:
    - record the active design/tradeoffs in a dedicated issue artifact before
      code changes so the planned YAML surface and fallback boundaries are
      traceable outside chat;
    - replace the hard-coded TSA/K3Z map in
      `src/femic/pipeline/vdyp_overrides.py` with a repo-tracked human-readable
      YAML policy surface for FEMIC defaults;
    - add optional per-instance YAML overlay support so case-specific rules can
      extend or override the defaults without editing Python;
    - preserve only a narrow code-level fallback seam for malformed/missing
      config or exceptional cases that cannot be expressed cleanly in YAML;
    - update docs/tests so override precedence, expected file locations, and
      operator usage are explicit and regression-covered.
  - Success criterion:
    - the current TSA and K3Z smoothing overrides can be reproduced from
      tracked YAML artifacts, and operators no longer need to edit
      `src/femic/pipeline/vdyp_overrides.py` for normal case-specific tuning.
- 2026-03-24 (Phase 23 `P23.11` closeout): YAML-backed VDYP fit policy is now
  the primary override surface in both parent FEMIC and the standalone K3Z
  instance.
  - Landed behavior:
    - shared per-TSA defaults now live in `config/vdyp_fit_policy.yaml`;
    - instance-local overlays now auto-resolve from
      `<instance_root>/config/vdyp_fit_policy.yaml`;
    - explicit runtime `kwarg_overrides_for_tsa` remains the highest-precedence
      escape hatch;
    - a narrow code fallback remains only for missing/malformed shared default
      YAML.
  - Validation and release evidence:
    - GitHub issue `#9` was opened before implementation and linked above;
    - parent docs build passes with
      `.\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W`;
    - standalone K3Z docs build passes with
      `..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`;
    - `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
      and `pre-commit run --all-files` all pass.
- 2026-03-23 (Phase 26 kickoff): the next K3Z milestone is a coordinated docs
  and CI repair pass, with the standalone K3Z docs treated as canonical and the
  parent FEMIC docs kept intentionally lightweight.
  - Immediate execution order:
    - update the standalone K3Z docs so they fully explain the three top-level
      variants (`base`, `ctfert`, `pctct`), the four baseline-derived overlay
      subvariants, the real treatment-parameter/state-machine logic, and the
      implemented `og1` / `og2` semantics;
    - repair the parent `docs-pages` GitHub Actions failure by landing the
      missing tracked `docs/reference/api/generated/*.rst` pages that the Phase
      24 curated API docs now reference from a clean checkout;
    - add docs-contract coverage for clean-checkout generated-doc references so
      future parent docs builds fail earlier and more explicitly.
  - High-priority urgent follow-up immediately after this docs issue is closed:
    - investigate and fix the `pctct` variant regression where species-wise
      growing-stock / harvest-volume surfaces appear to have disappeared;
    - current diagnosis already points upstream of live Patchworks launch:
      `models/k3z_patchworks_model/yield/forestmodel_pctct.xml` and
      `models/k3z_patchworks_model/tracks_pctct/` currently materialize only
      `product.Yield.managed.Total` / `feature.Yield.managed.Total`, rather than
      the expected species-wise managed surfaces;
    - follow-up success criterion: restore species-wise managed yield and
      harvested-volume accounts in `pctct` without regressing the intended
      `PCT -> CT` treatment chain.
- 2026-03-23 (Phase 26 closeout): the K3Z docs push and parent docs CI repair
  are complete on `feature/k3z-docs-upgrade`.
  - Closeout polish landed:
    - a practical launch-selector layer across the standalone K3Z docs;
    - corrected CT/fert config-path wording and tighter operator QA wording;
    - explicit documentation that the current `pctct` species-wise managed
      growing-stock / harvest-volume disappearance is a known bug, not
      intended variant behavior.
  - Validation and release evidence:
    - parent docs build passes with `.\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W`;
    - standalone K3Z docs build passes with `..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`;
    - parent clean-checkout Sphinx simulation passes;
    - `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
      and `pre-commit run --all-files` all pass.
  - Next task should start on a distinct bug-fix branch focused on restoring
    species-wise managed yield / harvested-volume accounts for `pctct`.
- 2026-03-24 (Phase 27 kickoff): start the `pctct` species-account regression
  fix on branch `bugfix/k3z-pctct-species-accounts`.
  - Immediate execution order:
    - compare baseline / `ctfert` / `pctct` from exported ForestModel XML into
      `tracks_*.csv` artifacts so the collapse point is proven rather than
      guessed;
    - repair the upstream export/build seam in parent FEMIC, not just the
      checked-in instance outputs, so regenerated `pctct` artifacts stay
      correct;
    - refresh the K3Z `pctct` checked-in artifact surface and rerun validation,
      including live-launch expectations, before closing the branch.
  - Success criterion:
    - `pctct` once again materializes species-wise managed yield /
      harvested-volume accounts alongside the intended `PCT -> CT` treatment
      path, matching baseline / `ctfert` account granularity where appropriate.
- 2026-03-24 (Phase 27 closeout): the `pctct` species-account regression is
  repaired on `bugfix/k3z-pctct-species-accounts`.
  - Diagnosis result:
    - current parent export logic can still generate species-wise `pctct`
      managed yield / harvested-volume surfaces;
    - the checked-in K3Z `pctct` ForestModel/tracks surface had gone stale and
      was the layer that had collapsed back to `Total`-only managed accounts.
  - Repair delivered:
    - refreshed `models/k3z_patchworks_model/yield/forestmodel_pctct.xml` from
      a current good species-wise export probe;
    - reran Patchworks Matrix Builder for `config/patchworks.runtime.pctct.windows.yaml`
      so `tracks_pctct` once again carries species-wise managed yield /
      harvested-volume accounts alongside `PCT` and `CT`;
    - removed the now-stale docs caveats that described the missing
      species-wise `pctct` surfaces as a current limitation;
    - added a parent repo contract test that fails if the checked-in `pctct`
      ForestModel/tracks surface ever regresses back to `Total`-only managed
      accounts.
  - Validation evidence:
    - standalone K3Z docs build passes with `..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`;
    - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct.windows.yaml`
      reports `species=8` and `complete_species=8`;
    - `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
      and `pre-commit run --all-files` all pass.
- 2026-03-24 (Phase 28 kickoff): start the broader `pctct` treatment-footprint
  expansion on branch `feature/k3z-pctct-expand-treatment-aus`.
  - Immediate execution order:
    - retarget the `pctct` eligible AU set to the medium/high SI `HW+FDC` and
      `FDC+HW` AUs only (`985502000`, `985503000`, `985502001`,
      `985503001`), removing all other prior `pctct` eligibles;
    - align the Issue 14 regen assumption for that AU cohort to
      `900 CW + 3100 HW`;
    - refresh the checked-in K3Z `pctct` ForestModel/tracks/docs surface so the
      broader AU set is visible in canonical artifacts rather than only in YAML;
    - run focused validation to prove the expanded AU list appears in the
      compiled `PCT`/`CT` surface and then append the same closeout summary to
      `CHANGE_LOG.md`.
  - Updated issue-14 target:
    - the active `pctct` cohort is now the medium/high SI `HW+FDC` and
      `FDC+HW` AUs only (`985502000`, `985503000`, `985502001`,
      `985503001`), with all other prior `pctct` eligibles removed.
  - Tracking issue:
    - GitHub feature request `#14`:
      `PCT requests: change eligible AUs, change AU regen assumptions, add knob for changing PCT intensity`
  - Known boundary to document during execution:
    - Issue 14's requested light/moderate/heavy PCT intensity options are not
      currently expressible as simple config-only variants because the current
      `pctct` surface compiles one post-PCT path (`cc_pl_pct`) rather than
      multiple intensity-specific treatment states/curve families.
- 2026-03-24 (Phase 28 closeout): the K3Z `pctct` variant now matches the
  updated Issue 14 AU cohort and regen assumption on branch
  `feature/k3z-pctct-expand-treatment-aus`.
  - Result:
    - retargeted `config/silviculture.k3z.pctct.yaml` so `PCT` and `CT`
      eligibility now applies only to `985502000`, `985503000`, `985502001`,
      and `985503001`;
    - updated `config/tipsy/tsak3z.yaml` so those four Issue 14 AUs now use
      the requested `900 CW + 3100 HW` planted regeneration mix;
    - refreshed the standalone K3Z docs so the `pctct` variant now documents
      the correct four-AU footprint, the matching regen assumption, and the
      current rebuild/validation contract;
    - regenerated
      `models/k3z_patchworks_model/yield/forestmodel_pctct.xml`,
      `output/patchworks_k3z_pctct_validated/forestmodel.xml`, and
      `models/k3z_patchworks_model/tracks_pctct/` from the updated config;
    - verified that `PCT` / `CT` treatment states now materialize only for the
      four Issue 14 AUs, while non-target AUs such as `985502002` remain only
      in the baseline/CC land-base surface as expected.
  - Validation evidence:
    - standalone K3Z docs build passes with
      `..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`;
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct.windows.yaml --run-id k3z_pctct_issue14_20260324`
      completed successfully with `returncode=0`;
    - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct.windows.yaml`
      reports `accounts=264`, `species=8`, `complete_species=8`, `au=14`;
    - `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
      and `pre-commit run --all-files` all pass in the current `.venv` after
      installing the previously missing local dev dependencies
      `openpyxl` and `pandas-stubs`.
  - Remaining boundary:
    - Issue 14's requested light/moderate/heavy PCT intensity options still
      require a deeper design change to the `pctct` model surface, because the
      current implementation only compiles one post-PCT managed state
      (`cc_pl_pct`) rather than multiple intensity-specific treatment paths.
- 2026-03-24 (Phase 29 kickoff): start the `pctct` multi-intensity PCT
  expansion on the existing branch `feature/k3z-pctct-expand-treatment-aus`.
  - Tracking issue:
    - GitHub feature request `#14`:
      `PCT requests: change eligible AUs, change AU regen assumptions, add knob for changing PCT intensity`
  - Immediate execution order:
    - extend parent Patchworks export logic so one `pctct` variant can compile
      multiple labeled PCT treatments from the same planted starting state;
    - model the three requested K3Z options as explicit post-PCT states:
      light (`900 CW + 2100 HW`), moderate (`900 CW + 1100 HW`), and heavy
      (`900 CW + 100 HW`), all available at age `10`;
    - route `CT` forward from each post-PCT state into its own matching
      post-CT state so all three paths coexist cleanly in the same
      `forestmodel_pctct.xml` / `tracks_pctct` surface;
    - refresh the K3Z PIN/docs/runtime artifacts and rerun matrix-build so the
      resulting instance is immediately testable in Patchworks.
  - Success criterion:
    - the checked-in K3Z `pctct` variant exposes three distinct age-10 PCT
      treatments for the Issue 14 AU cohort, each produces the intended
      residual HW mix, each can still flow into `CT`, and the rebuilt instance
      loads cleanly for live testing.
- 2026-03-24 (Phase 29 closeout): the K3Z `pctct` variant now exposes three
  coexisting age-10 PCT treatment choices on branch
  `feature/k3z-pctct-expand-treatment-aus`.
  - Result:
    - extended parent Patchworks export logic so `pre_commercial_thinning`
      can compile multiple labeled PCT treatments from one planted starting
      state, each with its own post-PCT state and per-species stem-removal
      target;
    - added parent regression coverage proving one variant can materialize
      `PCT_LIGHT`, `PCT_MODERATE`, and `PCT_HEAVY` in parallel while still
      routing `CT` from each resulting PCT state;
    - updated `config/silviculture.k3z.pctct.yaml` so the four Issue 14 AUs
      now expose three age-10 PCT choices:
      `PCT_LIGHT` (`900 CW + 2100 HW`), `PCT_MODERATE` (`900 CW + 1100 HW`),
      and `PCT_HEAVY` (`900 CW + 100 HW`);
    - refreshed the standalone K3Z docs and `analysis/pctct.pin` so the three
      PCT flavors are explicit and visually distinguishable in Patchworks;
    - regenerated
      `models/k3z_patchworks_model/yield/forestmodel_pctct.xml`,
      `output/patchworks_k3z_pctct_validated/forestmodel.xml`, and
      `models/k3z_patchworks_model/tracks_pctct/` from the updated multi-PCT
      config.
  - Validation evidence:
    - standalone K3Z docs build passes with
      `..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`;
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct.windows.yaml --run-id k3z_pctct_multi_pct_20260324`
      completed successfully with `returncode=0`;
    - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct.windows.yaml`
      reports `accounts=267`, `species=8`, `complete_species=8`, `au=14`;
    - `ruff check src tests`, `mypy src`, `pytest`, and
      `pre-commit run --all-files` all pass in the current `.venv`.
- 2026-03-24 (Phase 30 kickoff): pivot the Issue 14 PCT-intensity delivery
  from one stacked `pctct` surface to three simpler single-intensity
  subvariants on branch `feature/k3z-pctct-expand-treatment-aus`.
  - Tracking issue:
    - GitHub feature request `#14`:
      `PCT requests: change eligible AUs, change AU regen assumptions, add knob for changing PCT intensity`
  - Reason for pivot:
    - the user reported that the last stacked-treatment Matrix Builder attempt
      behaved like a runaway/hanging compile, so the immediate priority is a
      simpler testable delivery shape rather than preserving the one-variant
      multi-intensity experiment.
  - Immediate execution order:
    - define three explicit K3Z subvariants:
      `pctct_light`, `pctct_moderate`, and `pctct_heavy`;
    - give each subvariant a single age-10 `PCT` treatment labeled `PCT`
      followed by the existing age-40 `CT` step, while keeping the same four
      Issue 14 eligible AUs and the same `900 CW + 3100 HW` planted regen mix;
    - set the three `HW` removal levels to `1000`, `2000`, and `3000`
      stems/ha respectively, yielding post-PCT managed mixes of
      `900 CW + 2100 HW`, `900 CW + 1100 HW`, and `900 CW + 100 HW`;
    - rebuild the standalone K3Z docs/contracts and checked-in
      ForestModel/tracks/output artifacts so users launch the three new
      subvariants directly instead of the stacked `pctct` surface.
  - Success criterion:
    - all three single-intensity `pctct_*` subvariants compile and launch via
      their own runtime config + PIN pairs, and each remains geometry-aligned
      to the accepted baseline fragments footprint.
- 2026-03-24 (Phase 30 closeout): replaced the stacked multi-PCT K3Z surface
  with three single-intensity PCT->CT subvariants on branch
  `feature/k3z-pctct-expand-treatment-aus`.
  - Result:
    - added explicit K3Z config/runtime/PIN/build surfaces for
      `pctct_light`, `pctct_moderate`, and `pctct_heavy`;
    - each subvariant now carries one age-10 `PCT` treatment followed by the
      existing age-40 `CT` step on the same four Issue 14 AUs
      (`985502000`, `985503000`, `985502001`, `985503001`);
    - the planted regen assumption remains `900 CW + 3100 HW`, while the three
      subvariants remove `1000`, `2000`, and `3000` `HW` stems/ha respectively;
    - standalone K3Z docs/contracts now describe the new `pctct_*` launch
      matrix, state machine (`cc_pl -> cc_pl_pct -> cc_pl_pct_ct`), and
      expected `PCT`/`CT` account surface;
    - regenerated `forestmodel_pctct_light.xml`,
      `forestmodel_pctct_moderate.xml`, and `forestmodel_pctct_heavy.xml`
      directly from the checked-in bundle tables, then rebuilt
      `tracks_pctct_light/`, `tracks_pctct_moderate/`, and
      `tracks_pctct_heavy/` against copies of the accepted baseline fragments
      surface so all three subvariants preserve the 218-fragment teaching
      footprint exactly.
  - Validation evidence:
    - standalone K3Z docs build passes with
      `..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`;
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct_light.windows.yaml --run-id k3z_pctct_light_20260324`
      completed successfully with `returncode=0`;
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct_moderate.windows.yaml --run-id k3z_pctct_moderate_20260324`
      completed successfully with `returncode=0`;
    - `python -m femic patchworks matrix-build --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct_heavy.windows.yaml --run-id k3z_pctct_heavy_20260324`
      completed successfully with `returncode=0`;
    - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct_light.windows.yaml`
      reports `accounts=265`, `species=8`, `complete_species=8`, `au=14`;
    - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct_moderate.windows.yaml`
      reports `accounts=265`, `species=8`, `complete_species=8`, `au=14`;
    - `python -m femic instance account-surface --instance-root external/femic-k3z-instance --config config/patchworks.runtime.pctct_heavy.windows.yaml`
      reports `accounts=264`, `species=8`, `complete_species=8`, `au=14`;
    - `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
      and `pre-commit run --all-files` all pass in the current `.venv`.
- 2026-03-24 (Phase 30 legacy-surface cleanup): removed the now-redundant
  single-surface `pctct` alias after the three `pctct_*` subvariants passed
  live Patchworks smoke.
  - Result:
    - removed the orphaned legacy launch/config/build surface:
      `config/patchworks.variant.pctct.yaml`,
      `config/patchworks.runtime.pctct.windows.yaml`,
      `config/silviculture.k3z.pctct.yaml`,
      `models/k3z_patchworks_model/analysis/pctct.pin`,
      `models/k3z_patchworks_model/yield/forestmodel_pctct.xml`,
      `models/k3z_patchworks_model/tracks_pctct/`, and
      `output/patchworks_k3z_pctct_validated/`;
    - tightened the remaining parent/K3Z docs so they only point at the
      supported `pctct_light`, `pctct_moderate`, and `pctct_heavy`
      subvariants;
    - added a parent contract test that fails if the retired single-surface
      `pctct` files reappear beside the supported `pctct_*` surfaces.
- 2026-03-24 (Phase 25 P25.4b kickoff): close the overlay docs gap on branch
  `feature/k3z-overlay-guidance-closeout`.
  - Immediate execution order:
    - consolidate the existing overlay references into one explicit
      student/operator workflow page in the standalone K3Z docs;
    - document the source workbook provenance, `FEATURE_ID1` key quirk,
      `blocks.shp` bridge, subvariant meanings, launch pairings, and QA checks
      in one place;
    - update the surrounding K3Z guide pages so the overlay workflow is easy
      to find from getting-started, runbook, rebuild/QA, and scenario pages.
  - Success criterion:
    - `P25.4b` is complete when a student/operator can identify the four
      overlay subvariants, understand what each one means, reproduce the
      launch workflow, and audit the source/join contract without needing the
      earlier planning note or chat history.
- 2026-03-24 (Phase 25 P25.4b closeout): the K3Z overlay workflow is now
  documented as a repeatable student/operator procedure rather than being
  scattered across planning notes and variant docs.
  - Result:
    - added standalone K3Z page
      `external/femic-k3z-instance/docs/overlay-subvariants-workflow.rst`
      covering workbook provenance, the `FEATURE_ID1` key quirk, the
      `blocks.shp` bridge, the four retention fields, subvariant meaning map,
      repeatable launch pairings, validation totals, and an audit checklist;
    - updated the surrounding standalone K3Z guide set so getting-started,
      variants, operator-runbook, rebuild/QA, and scenario guidance all route
      readers to the overlay workflow page from the places students/operators
      already look first;
    - extended `tests/test_docs_contract.py` so the overlay workflow page and
      its critical sections cannot disappear silently in a future docs refactor.
  - Validation evidence:
    - standalone K3Z docs build passes with
      `..\..\.venv\Scripts\python.exe -m sphinx -b html docs docs\_build\html -W`;
    - parent docs build passes with
      `.\.venv\Scripts\python.exe -m sphinx -b html docs _build\html -W`;
    - `pytest tests/test_docs_contract.py -k "k3z_instance_standalone_docs"`
      passes;
    - full milestone validation (`ruff format src tests`, `ruff check src tests`,
      `mypy src`, `pytest`, `pre-commit run --all-files`) now passes.
  - Leading edge after this closeout:
    - Phase 25 is complete; the next K3Z backlog items remain the CT/fert
      canonical rebuild follow-up (`P22.9e`) and the VDYP override policy
      surface cleanup (`P23.11`) unless reprioritized.
- 2026-03-24 (Phase 22 P22.9e kickoff): start the CT/fert canonical-rebuild
  closeout on branch `feature/k3z-ctfert-canonical-rebuild`.
  - Immediate execution order:
    - inspect the current K3Z baseline + CT/fert artifact families to separate
      what is already accepted/teaching-authoritative from what is still a
      stale copied CT/fert surface;
    - determine the latest downstream canonical handoff we can safely resume
      from after `checkpoint1`, given that all K3Z variants share the same AU
      assignment and base VDYP/TIPSY yield surfaces and only diverge through
      added treatment/retention logic;
    - rebuild `forestmodel_ctfert.xml` / `tracks_ctfert` from canonical K3Z
      inputs while preserving the accepted baseline footprint (`THLB=1`,
      218 fragments, 14 AUs), then compare the rebuilt CT/fert accounts and
      treatments against the current checked-in surface to prove it is additive
      rather than a stale copied artifact.
  - Starting assumption to verify:
    - we should be able to resume downstream of `checkpoint1` if the accepted
      baseline feature/AU mask and current baseline yield surfaces are already
      canonical for all K3Z variants, with CT/fert differing only in added
      treatment-response logic on top of that shared baseline.
  - Success criterion:
    - `P22.9e` is complete when the checked-in CT/fert surface is rebuilt from
      canonical K3Z upstream inputs, still launches cleanly beside baseline and
      pctct, and no longer depends on artifact recovery from historical K3Z
      commits.
- 2026-03-24 (Phase 22 P22.9e closeout): confirmed that the checked-in K3Z
  CT/fert surface is already reproducible from the current canonical CT/fert
  export logic once it is paired with the accepted teaching-footprint fragments
  surface.
  - Result:
    - a fresh canonical CT/fert export from the current K3Z bundle/checkpoint
      inputs (`femic export patchworks --tsa k3z ... --silviculture-config
      config/silviculture.k3z.ctfert.yaml`) still emits the broad raw export
      surface (`au=27`, `fragments=219`), so raw export fragments remain
      unsuitable as the teaching-authoritative CT/fert landbase;
    - the checked-in accepted CT/fert fragments surface is deterministic and
      policy-explainable: it preserves the baseline 218-fragment geometry
      footprint exactly and differs only on 9 fragments in low-yield AUs
      `985502006` and `985502008`, where `RETENTION` is forced from `0.05` to
      `1.0`;
    - pairing the fresh canonical CT/fert ForestModel with that accepted
      checked-in CT/fert fragments surface reproduced the live CT/fert tracks
      surface cleanly in probe run `k3z_ctfert_p229e_probe`, with matching
      account/treatment coverage and no Patchworks launch errors;
    - the fresh canonical probe ForestModel hash matched the checked-in
      `models/k3z_patchworks_model/yield/forestmodel_ctfert.xml`, proving the
      current CT/fert ForestModel already reflects canonical upstream inputs
      rather than a stale historical artifact.
  - Contract changes recorded in repo:
    - `config/patchworks.variant.ctfert.yaml` now documents the real rebuild
      contract: refresh the CT/fert ForestModel from canonical inputs, but keep
      the accepted 218-fragment CT/fert footprint unless the raw export
      fragments satisfy the baseline-footprint invariants;
    - standalone K3Z rebuild/QA docs now state the accepted CT/fert fragment
      contract explicitly;
    - parent regression coverage now checks that the checked-in CT/fert surface
      preserves the baseline geometry footprint and only applies the 9 expected
      full-retention overrides.
  - Validation evidence:
    - `femic export patchworks --tsa k3z --instance-root external/femic-k3z-instance --output-dir output/patchworks_k3z_ctfert_probe_p229e --seral-stage-config config/seral.k3z.yaml --silviculture-config config/silviculture.k3z.ctfert.yaml`
      completed successfully (`au=27`, `fragments=219`, `curves=976`);
    - `femic patchworks matrix-build --instance-root external/femic-k3z-instance --config tmp_p229e_runtime_ctfert_probe.yaml --run-id k3z_ctfert_p229e_probe`
      completed successfully against the accepted CT/fert fragments surface
      (`218` fragment records; `CT/F1/F2/F3` tracks materialized).
- 2026-03-24 (Phase 22 variant-contract symmetry pass): aligned `pctct` docs
  and rebuild contract wording with the explicit `ctfert` contract so the two
  intensive-silviculture variants now diverge only in treatment-path logic.
  - Result:
    - `config/patchworks.variant.pctct.yaml` now states the accepted `pctct`
      fragments surface must preserve the baseline 218-fragment teaching
      footprint exactly, mirroring the explicit contract style already used for
      `ctfert`;
    - standalone K3Z runbook/QA docs now say `pctct` rebuilds should refresh
      the canonical ForestModel from current inputs but keep the checked-in
      fragments surface unless the baseline-footprint invariants still hold;
    - parent regression coverage now checks that baseline and `pctct`
      fragments surfaces remain geometry-identical with no
      `AU`/`IFM`/`RETENTION`/`ORIGIN`/`SILV_STATE` drift.
- 2026-03-23 (Phase 25 execution checkpoint): the K3Z student overlay import,
  join, and baseline-derived Patchworks subvariant compile path is now working
  end to end.
  - Result:
    - installed `xlrd` into the repo venv and verified the uploaded workbook
      `tmp/Fragments_Retention_HSmith.xls`;
    - confirmed the real workbook field names are `FEATURE_ID1`,
      `Basecase_Riparian`, `BaseCase_Sum`, `Scenario1_Sum`, and
      `Scenario2_Sum`, then normalized them into repo-local artifacts at
      `tmp/k3z_student_overlay_retention_join.csv` and `.feather`;
    - proved full 218/218 join coverage through the actual K3Z bridge
      `student FEATURE_ID1 -> models/k3z_patchworks_model/blocks/blocks.shp FEATURE_ID -> BLOCK -> output/patchworks_k3z_validated/fragments/fragments.shp`;
    - generated four overlay-specific fragments datasets and compiled four
      coexisting baseline-derived tracks surfaces:
      `tracks_overlay_basecase_riparian`,
      `tracks_overlay_basecase_sum`,
      `tracks_overlay_scenario1_sum`,
      and `tracks_overlay_scenario2_sum`;
    - added explicit runtime config, variant spec, and PIN wrapper surfaces for
      all four overlay subvariants;
    - completed four successful Patchworks matrix-builder runs with run IDs
      `k3z_overlay_basecase_riparian_20260323`,
      `k3z_overlay_basecase_sum_20260323`,
      `k3z_overlay_scenario1_sum_20260323`, and
      `k3z_overlay_scenario2_sum_20260323`.
  - Validation snapshot:
    - all five fragments surfaces (baseline + 4 overlays) remain at 218 rows and
      `1781.313237 ha` total area;
    - retained-area deltas versus baseline are now quantified in
      `tmp/k3z_overlay_retention_summary.csv`:
      `+75.239794 ha` (`basecase_riparian`),
      `+290.832868 ha` (`basecase_sum`),
      `+457.776048 ha` (`scenario1_sum`),
      and `+533.754032 ha` (`scenario2_sum`).
  - Remaining next step:
    - close `P25.4b` by updating the standalone K3Z student/operator docs so
      the new overlay subvariants, source-table naming quirks, launch workflow,
      and the species-account dropout behavior under high-retention overlays are
      explicit.
- 2026-03-23 (Phase 25 scenario2 rerun): the last overlay launch warning was
  resolved by re-running `scenario2_sum` from the user-edited workbook.
  - Result:
    - live Patchworks launches are now green for `basecase_riparian`,
      `basecase_sum`, `scenario1_sum`, and `scenario2_sum`;
    - the earlier `scenario2_sum` warning came from block `59`, where
      `RETENTION = 0.9999` left a managed remainder of only
      `0.0001427842 ha`, below Patchworks' internal `0.001 ha` precision limit;
    - after the workbook edit, block `59` now carries `Scenario2_Sum = 1.0`,
      so rerun `k3z_overlay_scenario2_sum_20260323_b` leaves no managed
      remainder on that block and should eliminate the warning on launch.
  - Updated validation snapshot:
    - refreshed `scenario2_sum` retained area is `622.819837 ha`
      (`+533.754175 ha` vs baseline).
- 2026-03-23 (Phase 25 / K3Z variant regression recovery): CT/fert launch
  failure after the overlay flow-target fix traced back to a missing CT/fert
  artifact family, not a bad overlay compile.
  - Result:
    - live `ctfert.pin` launch failed because `tracks_ctfert/accounts.csv` and
      the rest of the CT/fert runtime surface were absent from the current K3Z
      submodule checkout;
    - the stricter active-tracks flow-target fix made that absence fail early
      and explicitly, which is why the regression became visible now;
    - restored the CT/fert artifact family from historical K3Z submodule commit
      `5e11bfb` (`Recover K3Z ctfert variant with additive retention behavior`),
      including runtime config, variant spec, silviculture config,
      `tracks_ctfert/`, `forestmodel_ctfert.xml`, and
      `output/patchworks_k3z_ctfert_validated/`.
  - Recovery check:
    - `femic patchworks preflight --instance-root external/femic-k3z-instance --config config/patchworks.runtime.ctfert.windows.yaml`
      passes again after the restore.
- 2026-03-23 (Phase 25 overlay launch bugfix): live Patchworks launch exposed a
  baseline-account leakage bug in the shared K3Z flow-target script.
  - Result:
    - `overlay_basecase_riparian.pin` launches cleanly and matches the expected
      block-level and landscape-level retained-area checks;
    - `overlay_basecase_sum.pin` failed on launch because Patchworks tried to
      define `flow.even.product.Yield.managed.PLC` even though that managed PLC
      account no longer exists in the `basecase_sum` tracks surface;
    - comparison of the compiled overlay account tables confirmed this is
      legitimate surface variation, not a bad compile:
      `basecase_riparian` still includes managed `PLC`, while
      `basecase_sum`, `scenario1_sum`, and `scenario2_sum` do not.
  - Fix:
    - updated
      `external/femic-k3z-instance/models/k3z_patchworks_model/scripts/targets/flowTargets.bsh`
      so it accepts an explicit active tracks prefix for account discovery;
    - updated the baseline/overlay wrapper flow plus `ctfert.pin` and
      `pctct.pin` so they pass their own `tracks_path_prefix` directly into
      `setupYieldFlowTargets(...)` instead of relying on BeanShell interpreter
      state.
  - Expected outcome:
    - baseline and `basecase_riparian` behavior should stay unchanged;
    - `basecase_sum`, `scenario1_sum`, and `scenario2_sum` should now launch
      without trying to define flow targets for managed species accounts that
      are absent from their own overlay tracks.
- 2026-03-23 (Phase 25, P25.1 plan): start a new K3Z student-overlay planning
  pass in `planning/msfm-rec2group-k3z-overlay.md`.
  - Motivation:
    - the next K3Z task is a focused overlay workflow for teaching, not a return
      to TSA29 or the broader K3Z variant backlog;
    - we need to import a student GIS inventory from an abandoned fork, join it
      to the canonical K3Z fragments on `FEATURE_ID`, and turn four alternative
      RETENTION columns into four baseline-derived Patchworks subvariants;
    - the uploaded workbook `tmp/Fragments_Retention_HSmith.xls` gives us a
      first local artifact to validate the key/field contract before we wire the
      full overlay import.
  - Planned execution:
    - inspect the uploaded student export and confirm `FEATURE_ID` plus the
      target RETENTION columns are present;
    - define the repo-local `tmp/` import pattern and provenance notes for the
      abandoned student source;
    - join the student overlay to the current K3Z fragments shapefile and
      isolate the four alternative RETENTION fields;
    - compile four baseline-derived K3Z subvariants whose only intended change
      is the RETENTION-driven managed/unmanaged split;
    - add validation and operator/student notes only after the import/join
      contract is proven against the real K3Z fragments surface.
- 2026-03-22 (Phase 19 closeout note): `P19.17` is now complete in the TSA29 instance repo after a Sphinx deep-dive pass across the standalone docs set.
  - Result:
    - expanded the thin TSA29 pages (`getting-started`, `data-and-provenance`, `land-base-and-assumptions`, `rebuild-and-qa`, `troubleshooting`, and `docs-ownership-and-release`) with clearer workflow guidance, artifact references, evidence interpretation, and release/ownership notes;
    - hardened the TSA29 docs build config so it falls back cleanly when `sphinx_rtd_theme` is absent, then rebuilt the standalone docs successfully with `-W`.
- 2026-03-22 (Phase 19, P19.17 plan): execute the TSA29 instance Sphinx docs deep-dive and close the remaining documentation-gap pass in the linked instance repo.
  - Motivation: after closing Phase 24 in the parent FEMIC docs, the oldest still-open docs milestone is `P19.17`. The TSA29 instance already has canonical student/docs structure, but the roadmap still calls out one unfinished pass to deepen thin sections, tighten workflow guidance, and make evidence/artifact references easier to follow.
  - Planned execution:
    - audit the TSA29 instance Sphinx pages for weak sections, missing assumptions, thin workflow steps, and poor evidence cross-linking;
    - expand the weak spots with concrete procedural guidance and explicit references to current TSA29 compile/smoke evidence artifacts;
    - rebuild the TSA29 docs with warnings-as-errors if the submodule toolchain allows it, then record the closure summary in `ROADMAP.md` and `CHANGE_LOG.md`.
- 2026-03-22 (Phase 24 closeout): benchmark validation for the remaining docs work is now recorded in `planning/phase24_docs_benchmark_validation.md`, and the residual non-blocking docs polish is captured in `planning/phase24_docs_followup_issue.md`.
  - Result:
    - `P24.4a` passes: the docs are now sufficient for Patchworks runtime setup, bundled K3Z rebuild/amend loops, SiteProd default/fallback orientation, and DataLad/public-data bootstrap without relying on undocumented tribal knowledge.
    - `P24.4c` is satisfied by the issue draft covering the remaining quality-of-life improvements (native Windows Patchworks quickstart polish and a more compact SiteProd default-resolution summary).
- 2026-03-22 (Phase 24, P24.4a/P24.4c plan): use the new contract layer and acceptance checks against real benchmark tasks, then record any residual gaps as explicit follow-up work instead of leaving them implicit.
  - Motivation: `P24.2`, `P24.3`, and `P24.4b` are now in place, so the remaining work is no longer structure-building. The next question is whether the docs are actually sufficient for real maintenance tasks such as Patchworks runtime setup, K3Z rebuild/amend loops, SiteProd defaults, and DataLad bootstrap without relying on tribal memory.
  - Planned execution:
    - walk the benchmark tasks named in `P24.4a` against the current Guides, API pages, and technical-contract pages;
    - note where the current docs are now sufficient and where maintainers still have to infer missing details;
    - record any remaining gaps as a bounded follow-up issue/documented backlog item under `P24.4c`;
    - keep `ROADMAP.md` and `CHANGE_LOG.md` aligned with the benchmark results rather than leaving completion criteria only in chat.
- 2026-03-22 (Phase 24, P24.4b plan): extend the existing docs-contract test suite so the new compact contract layer cannot silently disappear or lose its required sections.
  - Motivation: `P24.2` adds the new technical-contract section, but it will drift unless the repo enforces both navigation and minimum content the same way it already does for guide and API-doc surfaces.
  - Planned execution:
    - extend `tests/test_docs_contract.py` with required-page coverage for `docs/reference/contracts/`;
    - assert docs-home, README, API reference, and `AGENTS.md` navigation all keep pointing at the compact contract section;
    - enforce the core headings/markers that make the contract pages useful for fast technical lookup;
    - run Sphinx plus the standard validation suite and record the milestone in `CHANGE_LOG.md`.
- 2026-03-22 (Phase 24, P24.2 plan): add a compact technical-contract section inside the main docs tree so contributors and coding agents can answer common repo/runtime questions without reverse-engineering multiple guides.
  - Motivation: `P24.1` fixed the high-value API pages, but the most repeated maintenance confusion still lives across several workflow guides and `AGENTS.md`: which repo root is canonical, how instance-root resolution works, when `FEMIC_EXTERNAL_DATA_ROOT` matters, which artifacts are authoritative at each stage, and where FEMIC stops at external runtime boundaries.
  - Planned execution:
    - create one compact reference-contract section under `docs/reference/` rather than a parallel agent-only doc set;
    - add concise source-of-truth pages for repo/runtime invariants, instance and external-data roots, stage boundaries/canonical artifacts, and recovery/runtime assumptions;
    - express those pages as checklists, tables, and bounded contract notes that link back to the deeper guides instead of duplicating them wholesale;
    - cross-link the new contract pages from top-level docs navigation plus contributor entrypoints such as `README.md` and `AGENTS.md`;
    - rebuild docs with warnings-as-errors, run the full validation suite, and record the milestone in `CHANGE_LOG.md`.
- 2026-03-22 (Phase 24, P24.1d.3/P24.1d.4 plan): finish the API-doc closure sweep by classifying the remaining generated-only pages and promoting the rebuild/release cluster that still blocks real maintenance work.
  - Motivation: after the operational and support-contract rewrites, the remaining generated-only set is mostly acceptable helper/package surface area. The main cluster that still benefits from curated orientation is the rebuild/release path (`rebuild_spec`, `rebuild_baseline`, `rebuild_invariants`, `rebuild_runner`, `release_packaging`), because it underpins reproducible instance maintenance.
  - Planned execution:
    - write an explicit closure-sweep artifact that classifies every remaining generated-only API page as either acceptable generated-only or promoted for a final curated pass;
    - add curated API pages for the rebuild/release cluster that still blocks comprehension of instance rebuild and release-maintenance tasks;
    - update the API index/modules pages so the bounded curated set is explicit rather than implied;
    - if the closure sweep leaves no unjustified generated-only pages, mark `P24.1d.3`, `P24.1d.4`, `P24.1d.5`, and top-level `P24.1d` complete.
- 2026-03-22 (Phase 24, P24.1d.2 plan): execute the support-module rewrite bundle needed to close the remaining contract-heavy autosummary stubs.
  - Motivation: the first-wave operational pages are done, but maintainers still have to reverse-engineer several smaller modules that carry core runtime contracts around instance resolution, bootstrap, preflight, bundle tables, runtime payload typing, and manifest capture.
  - Planned execution:
    - add curated API pages for ``femic.instance_context``, ``femic.instance_bootstrap``, ``femic.geospatial_preflight``, ``femic.pipeline.bundle``, ``femic.pipeline.legacy_runtime``, and ``femic.pipeline.manifest``;
    - group those pages under a curated support-modules section in ``docs/reference/api/modules.rst`` while keeping generated autodoc pages reachable through hidden toctrees;
    - document the contracts these modules own rather than leaving them implied: instance-root precedence, template/bootstrap payloads, geospatial readiness checks, canonical bundle-table surfaces, typed legacy runtime payloads, and run-manifest provenance;
    - rebuild Sphinx with warnings-as-errors, run the full validation suite, and record the milestone in ``CHANGE_LOG.md``.
- 2026-03-22 (Phase 24, P24.1d closure plan): convert `P24.1d` from an open-ended "rewrite docs forever" task into a bounded closure queue that can actually be checked off.
  - Motivation: the original first-wave rewrite targets are now done, but the roadmap still treats `P24.1d` as one undifferentiated open item. We need an explicit finish line so the remaining support-module rewrites and closure sweep are trackable.
  - Planned execution:
    - treat the first-wave operational module rewrites as completed scope inside `P24.1d`;
    - queue one support-module rewrite bundle covering `femic.instance_context`, `femic.instance_bootstrap`, `femic.geospatial_preflight`, `femic.pipeline.bundle`, `femic.pipeline.legacy_runtime`, and `femic.pipeline.manifest`;
    - run one explicit classification sweep for the remaining autosummary-only pages so "acceptable generated-only" modules are documented as an intentional choice rather than forgotten work;
    - only mark `P24.1d` complete after that queue is closed and the remaining generated pages are explicitly justified.
- 2026-03-22 (Phase 24, P24.1d/P24.1e plan): continue the curated API-doc rewrite by replacing the ``femic.pipeline.siteprod`` autosummary stub with a hand-authored narrative page.
  - Motivation: ``femic.pipeline.siteprod`` owns one of FEMIC's most environment-sensitive geospatial seams, but the generated page does not explain the preferred canonical ``siteprod.tif`` + ``siteprod.bandmap.json`` path, the ArcRasterRescue/ArcGIS Pro fallback behavior, or the stand-level raster assignment contract clearly enough.
  - Planned execution:
    - document the module's role in SiteProd species mapping, band-map loading, fallback layer discovery/export, and per-stand mean site productivity assignment;
    - explain the platform-sensitive runtime split between ArcRasterRescue and Windows ArcGIS Pro fallback, including executable resolution and timeout behavior;
    - surface the main contract surfaces and failure seams around species-code normalization, missing band maps, FileGDB layer enumeration, and temporary export stacking;
    - keep the generated autodoc page reachable through a curated page and rebuild Sphinx with warnings-as-errors.
- 2026-03-22 (Phase 24, P24.1d/P24.1e plan): continue the curated API-doc rewrite by replacing the ``femic.workflows.legacy`` autosummary stub with a hand-authored narrative page.
  - Motivation: ``femic.workflows.legacy`` is the bridge between FEMIC's newer CLI/path-resolution layer and the still-active legacy stage scripts, but the generated page does not explain the two distinct orchestration paths it owns: Stage 00 data-prep subprocess execution and the cached 01b-plus-bundle post-TIPSY assembly flow.
  - Planned execution:
    - document the module's role as the orchestration seam that resolves the legacy script bundle, manages temporary env/cwd overrides, and writes manifests around legacy execution;
    - explain the main public entry surfaces for ``run_data_prep`` and ``run_post_tipsy_bundle(_with_manifest)`` including their cached-artifact expectations and downstream bundle outputs;
    - surface the main failure seams around missing 01a checkpoints, mis-resolved legacy script roots, manifest/log expectations, and managed-curve override drift;
    - keep the generated autodoc page reachable through a curated page and rebuild Sphinx with warnings-as-errors.
- 2026-03-22 (Phase 24, P24.1d/P24.1e plan): continue the curated API-doc rewrite by replacing the ``femic.patchworks_runtime`` autosummary stub with a hand-authored narrative page.
  - Motivation: ``femic.patchworks_runtime`` owns the operational seam after export synthesis: config loading, preflight, launcher selection, Matrix Builder/log manifest capture, and blocks/topology preparation. The current generated page does not explain that runtime contract clearly enough.
  - Planned execution:
    - document the main runtime flow from config file to preflight to command launch and manifest capture;
    - explain the host-mode split between native Windows and Wine/Linux execution, including license/env expectations and `xvfb` behavior;
    - surface the main artifacts and failure seams for matrix-build, beanshell, and block/topology preparation;
    - keep the generated autodoc page reachable through a curated page and rebuild Sphinx with warnings-as-errors.
- 2026-03-22 (Phase 24, P24.1d/P24.1e plan): continue the curated API-doc rewrite by replacing the ``femic.fmg.patchworks`` autosummary stub with a hand-authored narrative page.
  - Motivation: ``femic.fmg.patchworks`` is the central export synthesis seam for Patchworks package generation, but its generated page still does not explain the ForestModel/fragments contract, IFM/origin/silviculture state wiring, retention handling, or the distinction between export-time validation and later runtime execution.
  - Planned execution:
    - document the main export flow from bundle/checkpoint tables into ForestModel XML and fragments shapefile outputs;
    - explain the most important contract surfaces: curve derivation, fragment field requirements, seral/retention wiring, and export result payloads;
    - call out the main failure seams around invalid fragments geometry, XML structure drift, IFM assignment, and silviculture/seral config misuse;
    - keep the generated autodoc page reachable through a curated page and rebuild Sphinx with warnings-as-errors.
- 2026-03-22 (Phase 24, P24.1d/P24.1e plan): continue the curated API-doc rewrite by replacing the ``femic.pipeline.tipsy`` autosummary stub with a hand-authored narrative page.
  - Motivation: ``femic.pipeline.tipsy`` owns one of FEMIC's most brittle operator-facing seams: fixed-width BatchTIPSY handoff generation, candidate filtering, canonical DAT/output freshness validation, and the coherence-based stale-output policy.
  - Planned execution:
    - document the Stage 01a/01b boundary this module owns and clarify why ``02_input-*.dat`` is canonical while XLSX is only a mirror;
    - explain the main functional surfaces for DAT export, candidate evaluation, fingerprinting, and coherence-based freshness checks;
    - surface the main failure seams around fixed-width overflow, stale ``04_output`` reuse, and managed-curve mode differences;
    - keep the generated autodoc page reachable through a curated page and rebuild Sphinx with warnings-as-errors.
- 2026-03-22 (Phase 24, P24.1d/P24.1e plan): continue the curated API-doc rewrite by replacing the ``femic.pipeline.io`` autosummary stub with a hand-authored narrative page.
  - Motivation: ``femic.pipeline.io`` is the main source-of-truth seam for run-profile normalization, instance-root resolution, external-data fallback, canonical SiteProd/THLB artifact selection, and legacy subprocess execution planning.
  - Planned execution:
    - document the main dataclass payloads and how CLI/profile inputs become effective run options and execution plans;
    - explain the artifact/path resolution order for instance-local data, ``FEMIC_EXTERNAL_DATA_ROOT``, and published canonical SiteProd/THLB assets;
    - call out the main environment variables and failure seams that matter when debugging path/instance/bootstrap issues;
    - keep the generated autodoc page reachable through a curated page and rebuild Sphinx with warnings-as-errors.
- 2026-03-22 (Phase 24, P24.2b/P24.2d plan): add one explicit source-of-truth docs pass for the bundled example instances under ``external/`` plus the full scripted developer bootstrap path on both Linux and Windows.
  - Motivation: the current docs mention ``external/femic-k3z-instance`` and ``external/femic-tsa29-instance``, but they still make contributors assemble too much of the extend/amend/rebuild workflow from scattered pages and tribal knowledge.
  - Planned execution:
    - document the complete fresh-clone bootstrap ritual as copy-paste command blocks for Linux/macOS and Windows PowerShell, including `.venv`, editable dev install, submodule/DataLad materialization, `FEMIC_EXTERNAL_DATA_ROOT`, and preflight checks;
    - explain how maintainers should work with the bundled ``external/*`` example instances in this checkout versus the standalone upstream instance repositories;
    - add a clear amend/rebuild loop for bundled example instances covering config edits, validation, rebuild/spec checks, and the boundary between local experimentation and submodule updates;
    - cross-link those instructions from both the guides and the README so humans and coding agents hit the same source-of-truth path.
- 2026-03-22 (Phase 24, P24.1d/P24.1e plan): continue the curated API-doc rewrite by replacing the ``femic.pipeline.vdyp_stage`` autosummary stub with a hand-authored narrative page.
  - Motivation: ``femic.pipeline.vdyp_stage`` is one of the largest and most failure-prone runtime seams in FEMIC, but its generated API page still provides almost no operational guidance for maintainers or coding agents.
  - Planned execution:
    - document module purpose, pipeline role, and the main sub-flows from input-table loading through batch execution, bootstrap orchestration, and curve smoothing;
    - surface the most important contracts and artifacts (``vdyp_io/`` runtime assets, per-run logs, sampling/cache expectations, and common failure seams);
    - keep the generated autodoc page reachable through the curated page with the same hidden-toctree + ``:noindex:`` pattern used for ``femic.cli.main``;
    - rebuild Sphinx with warnings-as-errors and record the milestone in ``CHANGE_LOG.md``.
- 2026-03-22 (Phase 23 follow-up, P23.10 plan): publish SiteProd band-map sidecar metadata alongside canonical stacked TIFF.
  - Motivation: default runtime use of pre-stacked `siteprod.tif` requires canonical species-to-band mapping without ArcRasterRescue/ArcPy discovery at runtime.
  - Planned execution:
    - derive canonical species order matching stacked TIFF generation workflow for current published artifact;
    - write `siteprod.bandmap.json` under `external/femic-public-data/data/bc/siteprod/` with `bands_1_based`, `bands_0_based`, and `ordered_species`;
    - save/push dataset to GitHub and confirm distribution semantics (Git-tracked vs annexed) explicitly for downstream Windows agents.
- 2026-03-22 (Phase 23 follow-up, P23.10 complete): published canonical SiteProd band-map sidecar for pre-stacked TIFF default runtime usage.
- 2026-03-22 (Phase 23 follow-up, P23.10 runtime default complete): the real Windows K3Z clean-start path now defaults to the published canonical SiteProd artifacts and no longer requires ArcRasterRescue/ArcPy when siteprod.tif + siteprod.bandmap.json are present.
  - Runtime behavior updates:
    - Stage 00 resolves SiteProd artifacts from instance-local or FEMIC_EXTERNAL_DATA_ROOT canonical paths before considering ArcRasterRescue/ArcPy export.
    - src/femic/resources/legacy/00_data-prep.py now logs the selected SiteProd raster path, band-map path, and whether export fallback was used.
    - src/femic/pipeline/siteprod.py now loads canonical species-to-band mapping from siteprod.bandmap.json so per-stand SiteProd assignment works without runtime layer discovery.
  - Windows validation evidence:
    - clean-start run k3z_p2310_siteprod_default_20260322_b selected external/femic-public-data/data/bc/siteprod/siteprod.tif, logged siteprod export fallback used: no, completed native VDYP successfully, regenerated 02_input-tsak3z.dat, and resumed through femic tsa post-tipsy after a refreshed BatchTIPSY handoff.
  - Acceptance result:
    - P23.10a through P23.10e are now satisfied for the current K3Z Windows path.
  - Dataset artifact:
    - path: `external/femic-public-data/data/bc/siteprod/siteprod.bandmap.json`
    - dataset commit: `b23ce8290862915b518322cbf59f6c92f2d46654`
  - Mapping derivation notes:
    - species universe derived from `list_siteprod_layers(...)` against `Site_Prod_BC.gdb`;
    - order set to lexicographic species-code order, matching stacked TIFF band assembly semantics (`enumerate_siteprod_layer_tif_paths(...)` sorted `site_prod_bc_<SPECIES>.tif` filenames);
    - validated against published `siteprod.tif` band count (`22`).
  - Distribution semantics:
    - sidecar JSON is Git-tracked text (not annexed), so availability comes from Git branch sync (`main` on GitHub), not `arbutus-s3` annex object transfer.
- 2026-03-22 (Phase 23 follow-up, P23.9 plan): publish canonical stacked SiteProd TIFF into the DataLad public-data mirror for cross-host reuse.
  - Motivation: reduce repeated Stage 00 SiteProd export friction when ArcRasterRescue/ArcPy runtime surfaces are unavailable on a host, while preserving annex-backed distribution semantics.
  - Planned execution:
    - select a known-good Linux-generated `siteprod.tif` artifact from parity runs;
    - copy to `external/femic-public-data/data/bc/siteprod/siteprod.tif`;
    - `datalad save` + push `femic-public-data` to GitHub + git-annex metadata branch;
    - upload annex payload to `arbutus-s3` and verify no missing copies for this artifact.
- 2026-03-22 (Phase 23 follow-up, P23.9 complete): published canonical stacked SiteProd TIFF to `femic-public-data` and verified cloud availability.
  - Artifact + provenance:
    - source artifact copied from Linux parity run output:
      `/tmp/femic_p23a_finalrun_rC45UW/data/siteprod.tif`
    - destination in DataLad dataset:
      `external/femic-public-data/data/bc/siteprod/siteprod.tif`
    - SHA256 (source + destination match):
      `307c177608a93b57b8df6d743256651fc8e50399753cbbcf34f97b876b6f926d`
  - Dataset sync evidence:
    - `datalad save` commit in `femic-public-data`: `b73dba7290e28ae893cc13e9a1ecbacd15b39904`
    - pushed dataset history to GitHub `main` and `git-annex` metadata branch.
    - uploaded annex payload to `arbutus-s3` with `git annex copy --to arbutus-s3 data/bc/siteprod/siteprod.tif`
    - verification: `MISSING_ON_ARBUTUS_SITEPROD=0` and `git annex whereis data/bc/siteprod/siteprod.tif` includes `arbutus-s3`.
- 2026-03-22 (Phase 23 follow-up, P23.8 plan): fix THLB raster path resolution for tmp-clone Linux parity runs.
  - Problem observed from full run `k3z_linux_p233a_20260322_live_session1`: pipeline progressed through Stage 00/01a + post-TIPSY resume but failed in bundle-stage THLB assignment with
    `rasterio.errors.RasterioIOError: .../data/misc.thlb.tif: No such file or directory`.
  - Root cause hypothesis: instance clone lacks `data/misc.thlb.tif`, while canonical payload exists under `external/femic-public-data/data/misc.thlb.tif`.
  - Planned implementation:
    - add fallback path resolution from external data root when instance-local THLB raster is absent;
    - emit selected-path diagnostics for easier runtime triage;
    - add focused regression tests for fallback + precedence behavior;
    - rerun Linux parity command to confirm this seam no longer aborts progress.
- 2026-03-22 (Phase 23 follow-up, P23.8 complete): fixed THLB raster path seam that caused late-stage Linux tmp-clone failures.
  - Runtime behavior updates:
    - added `resolve_legacy_thlb_raster_path(...)` in `src/femic/pipeline/io.py` to prefer instance-local `data/misc.thlb.tif`, then fall back to `FEMIC_EXTERNAL_DATA_ROOT/misc.thlb.tif`.
    - `00_data-prep.py` now logs the selected THLB raster path and explicit fallback context when instance-local raster is absent.
    - post-01b THLB assignment now uses the resolved path rather than assuming instance-local `data/misc.thlb.tif` is always present.
  - Verification evidence:
    - `pytest -q tests/test_pipeline_io.py` passed (`3 passed`) covering precedence + fallback behavior.
    - replayed `femic tsa post-tipsy` on previously failing tmp instance (`/tmp/femic_p23a_live_session_ax08cp`) now succeeds (`RC=0`, `post-tipsy completed`).
    - bounded full-run replay logs now show `using THLB raster source (fallback): .../external/femic-public-data/data/misc.thlb.tif` and no longer fail at `misc.thlb.tif` missing-path boundary before timeout.
- 2026-03-22 (Phase 23 follow-up, P23.7 plan): implement coherence-based stale-TIPSY behavior for development ergonomics.
  - Problem: timestamp-only stale checks still halt runs in cases where input/output look structurally coherent and the run goal is unrelated to regenerating BatchTIPSY.
  - Planned implementation:
    - extend `validate_tipsy_output_is_fresh(...)` to perform structural coherence checks (AU/table coverage) when DAT is newer than output and no DAT fingerprint sidecar is present;
    - default to warning-and-continue on coherent in/out pairs;
    - add a strict override env switch to restore hard-error behavior for coherent timestamp mismatches;
    - add tests + docs notes so behavior is explicit and reproducible.
- 2026-03-22 (Phase 23 follow-up, P23.7 complete): implemented coherence-based timestamp mismatch handling for BatchTIPSY freshness.
  - Code behavior updates:
    - `validate_tipsy_output_is_fresh(...)` now supports structural coherence checks when DAT is newer than output and no DAT hash sidecar exists.
    - Coherence is assessed via AU/table coverage parsed from `TIPSY_inputTBL` (`AU`, `TBLno`, `SI>0`) and output table IDs from `04_output-tsaXX.out`.
    - Coherent timestamp mismatches now warn-and-continue by default (`RuntimeWarning`) instead of hard failing.
    - Non-default strict mode added: `FEMIC_STRICT_TIPSY_TIMESTAMP_MISMATCH=1` escalates coherent timestamp mismatch back to `RuntimeError`.
  - Wiring updates:
    - `src/femic/resources/legacy/01b_run-tsa.py` now reads `FEMIC_STRICT_TIPSY_TIMESTAMP_MISMATCH` and passes it into freshness validation.
  - Regression/docs updates:
    - added tests in `tests/test_tipsy.py` for warn-and-continue, strict override error, and incoherent coverage handling.
    - updated `docs/guides/stage-01b-post-tipsy.rst` freshness guard guidance to document coherence default + strict override.

- 2026-03-21 (Phase 23 Linux parity full clean-start convergence): obtained the first uninterrupted Linux `P23.3a` terminal outcome and closed parity sign-off items.
  - Run details:
    - tmp instance: `/tmp/femic_p23a_finalrun_rC45UW`
    - run id: `k3z_linux_p233a_20260321_r16_full`
    - log: `/tmp/femic_p23a_r16_full.log`
    - manifest: `/tmp/femic_p23a_finalrun_rC45UW/vdyp_io/logs/run_manifest-k3z_linux_p233a_20260321_r16_full.json`
  - Observed terminal behavior:
    - ArcRasterRescue exported all 22 species layers with per-layer completion timings,
    - Stage 00 completed through stacked `siteprod.tif` and regenerated checkpoints (`checkpoint2`, `checkpoint3`, `checkpoint4`, `vdyp_prep-tsak3z.pkl`),
    - VDYP bootstrap ran across all strata/SI bins and two-pass SI rebin completed (`mapped VDYP SI for 38/46 rows`, rebuilt bins with `missing=0 of 114`),
    - run then stopped at expected Stage 01a->BatchTIPSY freshness boundary:
      `RuntimeError: Stale BatchTIPSY output detected: data/04_output-tsak3z.out is older than data/02_input-tsak3z.dat`.
  - Outcome:
    - this is the expected Linux Stage 01a handoff boundary behavior, not a runtime crash regression;
    - with `P23.3b` already passing on Linux, parity sign-off (`P23.3c`) is now complete.

- 2026-03-21 (Phase 23 Linux parity fail-fast diagnostic plan for Stage 00): convert the ArcRasterRescue export seam from silent long-running behavior to explicit bounded failures.
  - Add per-layer ArcRasterRescue instrumentation in `src/femic/pipeline/siteprod.py`:
    - emit start/completion timing messages for each species/layer export,
    - enforce timeout-bounded subprocess behavior (configurable),
    - raise explicit `RuntimeError` on timeout/non-zero return with layer/species context and stderr summary.
  - Add regression coverage in `tests/test_siteprod.py` for:
    - timeout path emits a deterministic failure instead of indefinite wait,
    - non-zero returncode path includes diagnostics.
  - Re-run a Linux `P23.3a` clean-start check after instrumentation to capture the first concrete failing ArcRasterRescue layer or prove progression beyond Stage 00.
- 2026-03-21 (Phase 23 Linux parity diagnostic outcome after Stage 00 instrumentation): prior "species SW stall" interpretation was corrected.
  - Implemented fail-fast diagnostics in `src/femic/pipeline/siteprod.py`:
    - per-layer ArcRasterRescue launch/completion messages with timing,
    - timeout-bound execution via `FEMIC_ARC_RASTER_RESCUE_TIMEOUT_SEC` (default 900s),
    - explicit `RuntimeError` on timeout/non-zero returncode with species/layer context and stderr summary.
  - Added execution-stream visibility hardening:
    - `build_legacy_execution_plan(...)` now sets `PYTHONUNBUFFERED=1` by default so long Stage 00 progress is not hidden by Python buffering.
  - Added regression coverage:
    - `tests/test_siteprod.py`: timeout and non-zero returncode diagnostics.
    - `tests/test_pipeline_helpers.py`: asserts `PYTHONUNBUFFERED=1` in legacy execution env.
  - Linux rerun evidence (`run-id: k3z_linux_p233a_20260321_r15_diag_unbuffered`, tmp `/tmp/femic_p23a_diag2_P0qEiG`):
    - Stage 00 progressed beyond ArcRasterRescue export despite sparse streamed output:
      - temp `site_prod_bc_*.tif` count dropped to zero,
      - stacked `data/siteprod.tif` grew to full-size write,
      - `data/ria_vri_vclr1p_checkpoint2.feather` and `data/ria_vri_vclr1p_checkpoint3.feather` were created.
    - Run was manually interrupted before reaching VDYP/TIPSY boundary to keep iteration time bounded, so `P23.3a` remains open.

- 2026-03-21 (Phase 23 Linux parity clean-start rerun, post runtime-asset staging): `P23.3a` remains open after a reproducible Stage 00 stall before VDYP boundary.
  - Clean rerun context:
    - tmp instance: `/tmp/femic_p23a_final_bF2EN4`
    - run id: `k3z_linux_p233a_20260321_r13_final`
    - shell log: `/tmp/femic_p23a_r13_final.log`
    - manifest: `/tmp/femic_p23a_final_bF2EN4/vdyp_io/logs/run_manifest-k3z_linux_p233a_20260321_r13_final.json`
  - Observed behavior:
    - preflight passed (`validate-case`, `geospatial-preflight`);
    - run advanced through ArcRasterRescue species extraction logs up to `... processing species SW`;
    - after that point, no new log lines were emitted for multiple minutes, no `vdyp_runs-...jsonl`/`vdyp_stderr-...log` files were created, and no active ArcRasterRescue child process remained;
    - process was interrupted manually to avoid indefinite execution, leaving the run manifest in `status=started`.
  - Interpretation:
    - the prior missing-VDYP-runtime-asset seam is fixed in code, but this run did not reach the VDYP boundary, so `P23.3a` still lacks final Linux handoff confirmation.

- 2026-03-21 (Phase 23 Linux parity root-cause + runtime-asset staging): identified why Linux `P23.3a` reported missing VDYP output even though bootstrap dispatch calls were emitted.
  - Root cause evidence:
    - failing runs reached bootstrap dispatch, but each call logged `FATAL: VDYP7 Configuration Folder ('-c') has not been supplied.` in `vdyp_stderr-*.log`;
    - all generated `vdyp_out_*.out` files were empty (`0` bytes), so two-pass SI rebin mapped `0/46` and downstream strata reported missing VDYP curves;
    - direct replay of a captured VDYP command from `/tmp` instance root failed the same way, while replay from repo source root succeeded and produced non-empty `vdyp_out` output.
  - Root cause interpretation:
    - `vdyp_params-landp` still points to relative legacy paths (`./vdyp_io/VDYP_CFG`, `./vdyp_io/VDYP.INI`);
    - clean `/tmp` instance clones did not carry those runtime assets, so Wine VDYP dispatch executed but produced no usable output.
  - Corrective implementation:
    - added `ensure_local_vdyp_runtime_assets(...)` in `src/femic/pipeline/vdyp_stage.py` and wired it into `run_vdyp_for_stratum(...)` so missing `vdyp_io/VDYP_CFG` and `vdyp_io/VDYP.INI` are staged from `FEMIC_SOURCE_ROOT` runtime assets before VDYP calls.
    - added regression coverage in `tests/test_vdyp_stage.py` (`test_ensure_local_vdyp_runtime_assets_stages_cfg_and_ini`).
  - Current status:
    - targeted regression tests pass for the new staging seam;
    - full clean-start Linux `P23.3a` confirmation to the Stage 01a BatchTIPSY boundary still pending (long Stage 00 extraction runs were interrupted in-session before the VDYP boundary was reached).

- 2026-03-21 (Phase 23 Linux parity corrective rerun after ArcRasterRescue + TIPSY freshness fixes): advanced past prior blockers, but Linux parity is still not fully closed.
  - Implemented and validated in-repo fixes:
    - ArcRasterRescue executable path resolution now supports `FEMIC_ARC_RASTER_RESCUE_EXE` and source-root/instance-root fallback resolution.
    - ArcRasterRescue FileGDB invocation now normalizes `.gdb/` command-path form expected by the patched tool workflow.
    - Stage 01b freshness now treats DAT as canonical and supports DAT-hash sidecars (`04_output-tsaXX.out.input_sha256`) so unchanged DAT content does not repeatedly force manual BatchTIPSY reruns.
    - Stage 01b skips BatchTIPSY freshness gating when `managed_curve_mode != tipsy` (`vdyp_transform` path).
    - `run_vdyp_for_stratum(...)` now resolves relative VDYP executable paths via `FEMIC_SOURCE_ROOT` fallback (matching existing params-path fallback semantics).
  - Linux runtime verification evidence:
    - `P23.3a` rerun (`run-id: k3z_linux_p233a_20260321_r4`) progressed through SiteProd extraction/stacking and pre-VDYP checkpoint generation, then failed at VDYP runtime boundary with:
      `RuntimeError: VDYP executable not found: /tmp/femic_p23a_r4_Ch5Y9R/VDYP7/VDYP7/VDYP7Console.exe`
      (manifest: `/tmp/femic_p23a_r4_Ch5Y9R/vdyp_io/logs/run_manifest-k3z_linux_p233a_20260321_r4.json`, `status=failed`, `exit_code=1`).
    - After adding source-root fallback for VDYP executable resolution, resumed Linux rerun continued past this explicit error but did not yet complete to a clean BatchTIPSY handoff sign-off within this session.
  - `P23.3b` rerun evidence:
    - command:
      `femic tsa post-tipsy --instance-root /tmp/femic_p23b_r5_dC7Rio --run-config config/run_profile.k3z.yaml --tsa k3z --run-id k3z_linux_p233b_20260321_r5_only`
    - freshness guard no longer blocked on DAT/XLSX timestamp mismatch; run advanced into plotting and then failed with:
      `KeyError: 'L'` (from `vdyp_curves_by_scsi.loc[sc, si_level]` in `01b_run-tsa.py`).
    - manifest:
      `/tmp/femic_p23b_r5_dC7Rio/vdyp_io/logs/run_manifest-k3z_linux_p233b_20260321_r5_only.json` (`status=failed`, `exit_code=1`).
  - Phase 23 remains open pending:
    - final Linux run confirmation that Stage 01a reaches the expected BatchTIPSY handoff boundary with the corrected runtime fallbacks, and
    - resolution/characterization of the `KeyError: 'L'` post-TIPSY plotting/indexing failure during Linux resume validation.
- 2026-03-21 (Phase 23 Linux parity follow-up): patch 01b post-TIPSY plotting to tolerate missing `(stratum_code, si_level)` VDYP overlays during resume validation.
  - Scope:
    - keep bundle/table generation behavior unchanged,
    - when a VDYP comparison key is missing, emit a warning and continue plotting TIPSY-managed trajectory rather than raising and aborting.
  - Validation target:
    - rerun `femic tsa post-tipsy` on Linux tmp clone and confirm stale-output guard remains resolved and the previous `KeyError: 'L'` no longer aborts the run.
- 2026-03-21 (Phase 23 Linux parity follow-up outcome): `P23.3b` now passes on Linux; `P23.3a` still pending final clean-start boundary confirmation.
  - Implemented additional 01b resilience fixes after rerun evidence:
    - missing `(stratum_code, si_level)` VDYP comparison keys now emit warnings and continue,
    - missing AU->(stratum, SI) map entries now emit warnings and continue (no hard crash in plotting loop).
  - Linux verification evidence:
    - `P23.3b` pass:
      - command:
        `femic tsa post-tipsy --instance-root /tmp/femic_p23b_r5_dC7Rio --run-config config/run_profile.k3z.yaml --tsa k3z --run-id k3z_linux_p233b_20260321_r8`
      - result:
        downstream bundle tables + plots regenerated; command completed with `status=ok`.
      - manifest:
        `/tmp/femic_p23b_r5_dC7Rio/vdyp_io/logs/run_manifest-k3z_linux_p233b_20260321_r8.json`.
    - `P23.3a` remains open:
      - attempted clean-start rerun (`run-id: k3z_linux_p233a_20260321_r6`) entered full Stage 00 extraction path and was still long-running at session cutoff, so final Stage 01a boundary sign-off remains pending.
  - additional bounded rerun attempt:
    - command:
      `timeout 900 femic run --instance-root /tmp/femic_p23a_r6_KpHxKg --run-config config/run_profile.k3z.yaml --run-id k3z_linux_p233a_20260321_r6_resume --resume`
    - observed behavior:
      entered legacy Stage 00 path (`00_data-prep.py`) and remained long-running without reaching a terminal success/failure boundary within the allotted window; process was terminated to avoid indefinite resource consumption.
- 2026-03-21 (Phase 23 Linux parity corrective implementation scope): execute a targeted parity fix pass before any additional Linux reruns.
  - ArcRasterRescue boundary:
    - Do not treat this as a new runtime design problem.
    - Reuse and codify the existing documented workflow for the patched ArcRasterRescue fork/build used to extract SiteProd rasters from ESRI FileGDB sources.
    - Update runtime path resolution/docs so Linux parity runs point at that existing executable workflow rather than assuming only a local `../ArcRasterRescue/build/arc_raster_rescue.exe` adjacency.
  - BatchTIPSY freshness boundary:
    - Treat `02_input-tsaXX.dat` as the canonical freshness input, not `tipsy_params_tsaXX.xlsx` (human-readable companion only).
    - Replace timestamp-only stale detection with content-aware behavior so unchanged DAT content does not force repeated manual BatchTIPSY reruns.
    - Ensure Stage 01b/post-TIPSY freshness blocking is mode-aware: when managed curves are not `tipsy` (for example `vdyp_transform`), do not require BatchTIPSY output freshness to proceed.
  - Required outputs for this corrective pass:
    - code + tests for ArcRasterRescue executable resolution aligned with documented workflow,
    - code + tests for DAT-authoritative, mode-aware TIPSY freshness behavior,
    - user-facing and agent-facing docs updated to match actual expected operator workflow on Linux and Windows.
- 2026-03-21 (Phase 23 Linux parity rerun after bootstrap hardening): verified Linux runtime bootstrap improvements and re-ran the remaining `P23.3` commands from a Linux host with real annex payload materialization; parity remains blocked by two concrete runtime boundaries.
  - Linux runtime bootstrap recovery completed in-session:
    - installed OS-level `git-annex` (`sudo apt-get install -y git-annex`),
    - enabled DataLad special remote (`git -C external/femic-public-data annex enableremote arbutus-s3`),
    - materialized annex-backed payloads (`datalad get -r external/femic-public-data/data`), including VRI/SiteProd/TSA GDB table files that were missing previously.
  - `P23.3a` rerun evidence:
    - command:
      `femic run --instance-root <tmp_k3z_clone> --run-config config/run_profile.k3z.yaml --run-id k3z_linux_p233a_20260321_r2`
    - preflight passed, but run failed before VDYP execution with:
      `FileNotFoundError: ArcRasterRescue executable not found: ../ArcRasterRescue/build/arc_raster_rescue.exe`
    - manifest:
      `<tmp_k3z_clone>/vdyp_io/logs/run_manifest-k3z_linux_p233a_20260321_r2.json` (`status=failed`, `exit_code=1`).
  - `P23.3b` rerun evidence:
    - command:
      `femic tsa post-tipsy --instance-root <tmp_k3z_clone> --run-config config/run_profile.k3z.yaml --tsa k3z --run-id k3z_linux_p233b_20260321_r2`
    - failed with expected freshness guard:
      `Stale BatchTIPSY output detected: .../04_output-tsak3z.out is older than .../tipsy_params_tsak3z.xlsx`
    - manifest:
      `<tmp_k3z_clone>/vdyp_io/logs/run_manifest-k3z_linux_p233b_20260321_r2.json` (`status=failed`, `exit_code=1`).
  - Phase 23 remains open pending:
    - Linux-accessible SiteProd/ArcRasterRescue path resolution for clean Stage 00->01a execution,
    - fresh BatchTIPSY `04_output-tsak3z.out` regenerated from current handoff before Linux post-TIPSY resume sign-off.
- 2026-03-21 (Phase 23 `P23.6` complete): hardened fresh-clone developer bootstrap and DataLad materialization rituals across agent-facing and user-facing docs.
  - Added explicit agent startup checklist in `AGENTS.md` covering:
    - local `.venv` activation + editable dev install,
    - required runtime smoke commands,
    - DataLad/git-annex + `arbutus-s3` enable + recursive `datalad get`,
    - mandatory `FEMIC_EXTERNAL_DATA_ROOT` export before case preflight/runs.
  - Added a dedicated user-facing guide:
    `docs/guides/developer-environment-bootstrap.rst` and linked it in the guides index.
  - Updated bootstrap/runbook guides to require explicit annex payload materialization:
    - `docs/guides/geospatial-runtime-bootstrap.rst`
    - `docs/guides/public-data-mirror-runbook.rst`
    - `docs/guides/deployment-instances.rst`
    - `docs/guides/cross-platform-runtime-smoke.rst`
    - `docs/guides/stage-01a-vdyp-tipsy-input.rst`
    - `docs/guides/stage-01b-post-tipsy.rst`
    - `docs/guides/pipeline-overview.rst`
  - Added packaging affordances for repeatable setup:
    - new `requirements-dev.txt` (`-e .[dev]`)
    - new `[project.optional-dependencies].dev` in `pyproject.toml`
    - `requirements.txt` now includes `datalad[full]`.
  - Validation passed in local `.venv`:
    - `ruff format src tests`
    - `ruff check src tests`
    - `mypy src`
    - `pytest`
    - `pre-commit run --all-files`
    - `sphinx-build -b html docs _build/html -W`
- 2026-03-20 (Phase 22 kickoff): queued a new optional K3Z treatment-variant workstream for commercial thinning plus 1-3 fertilization treatments.
  - Branches created:
    - parent repo: `feature/k3z-ct-fert-treatment-scaffold`
    - K3Z instance repo: `feature/k3z-ct-fert-treatment-option`
  - Locked planning decision: do not overload `ORIGIN` with CT/fert gating
    states; introduce a separate treatment-path state variable so natural vs
    planted origin semantics remain intact.
  - Initial scope:
    CT only in `FDC+HW-M` and `CW+HW-M` AUs, planted-only eligibility,
    provisional QMD curves, one CT plus optional `fert1`/`fert2`/`fert3`
    treatment chain, all parameterized through K3Z YAML scaffolding.
  - Immediate execution order for this phase:
    YAML contract -> treatment-path state design -> QMD scaffold -> CT curves ->
    fert curves -> K3Z variant rebuild/smoke.
- 2026-03-20 (Phase 21 complete): added generalized K3Z old-growth feature
  attributes and regenerated the tracked instance ForestModel XML.
  - Implemented OG curve generation in `femic.fmg.patchworks`:
    - `og1`: unmanaged-curve-driven linear ramp from CMAI age (`0.0`) to
      peak-yield age (`1.0`).
    - `og2`: fixed policy step at ages `249 -> 0.0`, `250 -> 1.0`.
  - Added per-AU + total feature attributes on both IFM selects:
    `feature.Area.og1.<au_id>`, `feature.Area.og1.total`,
    `feature.Area.og2.<au_id>`, `feature.Area.og2.total`.
  - Added regression test coverage and refreshed XML fixtures to include new
    OG curves/attributes.
  - Rewrote K3Z instance
    `models/k3z_patchworks_model/yield/forestmodel.xml` from current bundle
    tables and confirmed OG labels/curves are present.
- 2026-03-16 (Phase 19 toe-shift correction follow-up): removed the accidental
  second right-shift on toe `c` and confirmed no extended left plateau from
  double-shifting.
  - `fill_curve_left(...)` now treats `toe_shift_years` as inapplicable when
    the toe model already has an explicit location parameter (`popt.size >= 3`,
    as in legacy `fit_func1`); no `c += toe_shift` mutation is performed.
  - Blend-window sizing now keys off the effective shift (zero when location
    already exists), so `toe_shift_years` no longer distorts splice behavior in
    legacy toe fits.
  - Targeted TSA29 `MS_PLI L` rerun still detects the long tail segment and
    selects `tail_blend`, with no `candidate_rejected_non_finite` or
    `non_finite_curve` events.
- 2026-03-16 (Phase 19 toe-shift correction): replaced clamp-based toe shift
  with a location-parameter toe transform so the toe stage no longer injects
  `NaN/Inf` values when `toe_shift_years > 0`.
  - Root cause was `legacy_fit_func2` evaluation on `x=0` values created by
    global age clamping (`x -> max(x-shift, 0)`), yielding `0**(-a)` in toe
    evaluation for early ages.
  - Updated `fill_curve_left(...)` to apply a toe-only location transform
    (softplus shift) before toe fit/eval, and removed global body-age clamping
    from `process_vdyp_out(...)`.
  - Targeted TSA29 `MS_PLI L` rerun now shows no
    `candidate_rejected_non_finite` events; layered candidates are valid and
    fallback selection resolves to `reparameterized_nlls` after fit-gate rescue
    (tail candidate rejected for overshoot, not non-finite values).
- 2026-03-15 (Phase 19 follow-up checkpoint): validated the new 5-year-bin
  substrate + layered tail/toe logic with full QA gates and refreshed the
  TSA29 `MS_PLI L` fit diagnostic artifact.
  - Ran required validation suite successfully:
    `ruff format src tests`, `ruff check src tests`,
    `PYTHONPATH=src python -m mypy src`,
    `PYTHONPATH=src python -m pytest`,
    `python -m pre_commit run --all-files`,
    `sphinx-build -b html docs _build/html -W`.
  - Regenerated `plots/vdyp_fitdiag_tsa29-01-MS_PLI-L.png` from cached
    `vdyp_prep-tsa29.pkl` / `vdyp_results-tsa29.pkl` with current logic.
  - Current rerun telemetry confirms long-tail detection is active
    (`anchor_age=180`, `tail_span_years=120`) but also shows candidate
    validation rejecting tail-blend and left-toe-censor curves for non-finite
    values in this case, leaving `selected_path=primary_nlls`.
  - Next tightening target (without per-case overrides): stabilize toe/candidate
    non-finite handling so layered candidates remain selectable when their
    fitted shapes are structurally valid.
- 2026-03-15 (Phase 19 follow-up complete): switched VDYP fit substrate to
  5-year binned medians and tightened layered censor+tail behavior.
  - Updated `process_vdyp_out(...)` to consume 5-year binned medians for
    body NLLS and tail detection inputs (annual-age medians no longer drive
    fit substrate).
  - Added `build_observed_bins_for_fit(...)` and updated tail detection to
    right-to-left contiguous break scanning with composite straight-ish gate:
    low normalized residual + (high R2 or near-flat slope), plus minimum tail
    span guard.
  - Added new tail defaults/env knobs in stage runtime:
    `FEMIC_TAIL_LINEAR_FLAT_SLOPE_ABS` and
    `FEMIC_TAIL_LINEAR_MIN_SPAN_YEARS`.
  - Updated stage layering policy so structural left-toe discontinuities
    (`skip_delta >= 4`) are accepted and tail blending is selected when a
    valid right-tail segment is detected.
  - Targeted TSA29 `MS_PLI L` rerun now shows:
    `left_toe_censor_selected (skip1_after=6)` and
    `tail_blend_selected` with detected tail anchor near age `180`
    (span `120` years), rather than tiny terminal segments near age `294+`.
- 2026-03-15 (Phase 19 follow-up complete): generalized left-toe discontinuity
  censoring so early low-shoulder/kink failures are handled by fit logic rather
  than per-case smoothing overrides.
  - Updated `_infer_left_toe_censor_skip(...)` in
    `execute_curve_smoothing_runs(...)` to detect:
    - existing early high-spike / sharp-drop outliers, plus
    - symmetric early low-discontinuity outliers (`next_median/current` and
      absolute gap), and
    - local slope-kink discontinuities (initial slope vs following-slope scale).
  - Added a strict non-harm structural acceptance path for left-toe censor
    candidates when inferred censor depth is substantial (default
    `skip_delta >= 4`) and RMSE/tail-RMSE/MAPE remain within tight ratio
    guardrails.
  - Removed the temporary TSA29 `("MS_PLI","L")` tail-shape override so this
    case now relies on generalized fit logic.
  - Targeted rerun for `MS_PLI L` now emits
    `left_toe_censor_selected` (`skip1_after=6`) and selects
    `selected_path=censored_refit` in curve-fit telemetry.
- 2026-03-15 (Phase 19 follow-up complete): corrected TSA29 `MS_PLI L` right-tail
  behavior to enforce a near-linear post-200 shape (not zero-slope clamping).
  - Added TSA29 per-case smoothing override in `vdyp_overrides` for
    `("MS_PLI", "L")`:
    `tail_linear_min_points=20`, `tail_linear_min_r2=0.6`,
    `tail_linear_max_nrmse=0.25`, quantile fallback enabled,
    `tail_anchor_quantile=0.70`, `tail_blend_years=10.0`.
  - Targeted rerun for only `MS_PLI L` confirms `selected_path=tail_blend` with
    effectively linear post-200 tail (very small quadratic term) and refreshed
    fit diagnostic plot `plots/vdyp_fitdiag_tsa29-01-MS_PLI-L.png`.
  - Added regression coverage in `tests/test_vdyp_overrides.py` for the new
    TSA29 case override payload.
- 2026-03-15 (Phase 19 `P19.16` planned): address degenerative selection logic
  that currently preserves catastrophic primary curves in some strata/SI cases.
  - Observed failure pattern from `vdyp_curve_events-tsa29-rerun-20260315T213053Z.jsonl`:
    `MS_PLI H` and `IDF_FDI L` selected `primary_nlls` with catastrophic metrics
    (`MAPE ~= 1.0`, very high RMSE/tail RMSE) while rejecting left-toe-censor
    candidates that drastically improved RMSE/MAPE/tail RMSE.
  - Root-cause hypothesis to validate in code:
    selection applies strict guard-veto precedence (notably early-overshoot)
    without a catastrophic-baseline override, and selected-curve quality gates
    do not currently classify these cases as hard failures.
  - Planned implementation sequence:
    (1) add dominant-recovery override in selection scoring/order,
    (2) add selected-curve catastrophic hard-fail envelope with forced
    re-selection,
    (3) extend decision telemetry with explicit veto/override fields,
    (4) add regression fixtures for reported strata, and
    (5) rerun cached TSA29 + regenerate fit diagnostics + selection summaries.
  - Acceptance evidence for closure:
    reported failure strata must no longer finalize catastrophic primary curves,
    and reviewer-facing logs/summary must explicitly show why the selected path
    won in each case.
- 2026-03-15 (Phase 19 `P19.16a`-`P19.16d` complete): implemented dominant
  recovery selection + catastrophic gate hardening with deterministic telemetry
  and targeted regression coverage.
  - Added `early_underfit` fit metric and catastrophic/underfit gate reasons in
    `execute_curve_smoothing_runs(...)`, including new env knobs:
    `FEMIC_FIT_GATE_CATASTROPHIC_MAPE`,
    `FEMIC_FIT_GATE_MAX_EARLY_UNDERFIT`,
    `FEMIC_DOMINANT_RECOVERY_MAX_METRIC_RATIO`.
  - Added `dominant_recovery` decision logic used by both left-toe-censor and
    tail-blend selection so catastrophic baselines can be replaced when
    candidate RMSE/MAPE/tail-RMSE improvements are decisive.
  - Expanded fit-event telemetry with structured decision payloads and rescue
    audit fields (`rescue_trigger_gate_reasons`, `rescue_order`, `gate_by_path`)
    so veto/override causes are explicit in JSONL logs.
  - Added regression tests:
    - `test_execute_curve_smoothing_runs_selects_dominant_recovery_tail_blend_candidate`
    - `test_summarize_curve_selection_rows_flags_selected_curve_gate_rescue`
  - Targeted TSA29 cached rerun evidence from
    `vdyp_curve_events-tsa29-p1916_rerun_20260315T2212Z.jsonl` shows:
    `MS_PLI H` and `IDF_FDI L` left-toe-censor now selected via
    `dominant_recovery.selected=true` instead of prior catastrophic
    `primary_nlls` retention.
- 2026-03-15 (Phase 19 follow-up complete): moved toe-shift behavior to the
  default fit path so all VDYP smoothing candidates use the same delayed-toe
  shape unless explicitly overridden.
  - `execute_curve_smoothing_runs(...)` now injects `toe_shift_years` into
    baseline/candidate fit kwargs by default (env-backed via
    `FEMIC_VDYP_TOE_SHIFT_YEARS`, default `20.0`).
  - Merchantable-floor candidate generation is now skipped when a positive
    toe-shift is already active, avoiding duplicate post-hoc flattening logic.
  - Added run-profile support for `modes.vdyp_toe_shift_years` so users can set
    per-run defaults in config files; value is exported to runtime env for
    legacy stage execution.
  - Added regression coverage in `tests/test_vdyp_stage.py`,
    `tests/test_vdyp_curves.py`, and `tests/test_pipeline_helpers.py` for
    default/env-config toe-shift behavior and config parsing/env wiring.
- 2026-03-15 (Phase 19 `P19.13c` follow-up complete): corrected merchantable
  floor behavior to preserve smooth toe-ramp shape by shifting the fitted curve
  right (age-delay) instead of hard-clamping the first 20 years to zero.
  - Updated `process_vdyp_out(...)` merchantable-floor path to apply a
    right-shift transform (`x -> x - floor_age`) with floor fill only for
    `x <= floor_age`, preserving the fitted toe curvature after age 20.
  - Added `mode=right_shift` and `shift_years` fields to
    `stage=merchantable_floor` events for explicit audit visibility.
  - Expanded regression coverage in `tests/test_vdyp_curves.py` to assert
    post-floor ages follow the shifted baseline curve rather than flattened
    clamping behavior.
- 2026-03-15 (Phase 19 `P19.15d` complete): tightened curve-path branching and
  selected-curve quality gate behavior.
  - Left-toe censoring now composes with downstream candidates (including
    tail-blend runs) instead of behaving as an exclusive final-path override.
  - Added selected-curve gate rescue logic: if the initial selected curve fails
    fit-quality gate checks, FEMIC now attempts ordered rescue candidates
    (`tail_blend`, `merchantable_floor`, `reparameterized_nlls`,
    `censored_refit`, `primary_nlls`) and emits explicit gate-rescue/unresolved
    warning events.
  - Tail-blend selection thresholds are now env-tunable (`FEMIC_TAIL_SELECT_*`)
    with relaxed defaults so tail blends are admitted more often when primary
    curves are weak but still near non-harm bounds.
  - Added regression coverage in `tests/test_vdyp_stage.py` for composable
    censor+tail behavior and selected-curve gate rescue selection.
- 2026-03-15 (Phase 19 `P19.15` complete): reran TSA29 curve QA with
  updated plotting/fitting policy stack and published curve-stability evidence.
  - Regenerated TSA29 diagnostics with `FEMIC_STRAT_TOP_AREA_COVERAGE=0.80`
    (18 strata; coverage `0.8061826878755755`), including `plots/strata-tsa29.png`
    and all `54` AU overlays (`plots/tipsy_vdyp_tsa29-*.png`).
  - Produced reviewer CSV via `femic vdyp report --selection-summary-out`:
    `vdyp_io/logs/curve_selection_summary-tsa29-20260315T184955Z.csv`
    (`primary_nlls=12`, `tail_blend=19`, `merchantable_floor=22`,
    `censored_refit=1`).
  - Finalized post-TIPSY bundle via
    `vdyp_io/logs/run_manifest-post_tipsy_20260315T190051Z.json`
    and refreshed `data/model_input_bundle/{au_table,curve_table,curve_points_table}.csv`.
  - Published instance evidence in submodule:
    `external/femic-tsa29-instance/evidence/curve_stability_report.20260315.md`
    and
    `external/femic-tsa29-instance/evidence/curve_selection_summary-tsa29-20260315T184955Z.csv`.
- 2026-03-15 (Phase 19 `P19.15a.1` complete): patched THLB raster sampling to
  return fallback values when masked geometries have no valid cells.
  - Updated `mean_thlb_for_geometry(...)` to avoid `np.mean` on empty slices
    and to guard non-finite outputs.
  - Added regression coverage in `tests/test_pipeline_helpers.py` for the
    empty-valid-cell fallback path.
- 2026-03-15 (Phase 19 `P19.15b` complete): added reviewer-facing curve
  selection summary output from VDYP curve-event logs.
  - Added `summarize_curve_selection_rows(...)` in `femic.vdyp.reporting` to
    generate per-stratum/SI rows with selected path plus key fit-path flags
    (fit-quality warning, left-toe, merchantable-floor, tail-blend).
  - Extended `femic vdyp report` with `--selection-summary-out` to emit the
    summary as CSV for reviewer handoff and audit trails.
- 2026-03-15 (Phase 19 `P19.14c` complete): upgraded VDYP fit diagnostics to
  expose selected fit path, blend window context, and residual behavior.
  - Fit diagnostic plot now renders the selected output curve explicitly
    alongside current/candidate curves and prints the selected path in-figure.
  - Added residual subplot (`selected - observed median`) over age bins for
    per-stratum/SI visual QA of systematic fit bias.
  - Added tail-blend window annotation support (anchor/end age estimates) so
    reviewers can see where tail blending is expected to act.
- 2026-03-15 (Phase 19 `P19.14b` complete): added explicit objective selection
  logic for tail-blend vs straight NLLS with deterministic tie-breaks.
  - Added metric-driven tail selection policy requiring strong tail-RMSE
    improvement under non-harm guardrails, with deterministic tie-break when
    tails are near-equal.
  - Added `vdyp_curve_fit` decision events at `stage=tail_blend_selection`
    (selected/rejected) including baseline/candidate metrics and decision
    predicates.
  - Integrated tail selection into fallback output path as `selected_path=tail_blend`
    for non-K3Z when criteria are met; K3Z override behavior remains intact.
- 2026-03-15 (Phase 19 `P19.14a` complete): relaxed tail-linearity defaults and
  moved threshold control to config/env + per-stratum overrides.
  - Tail candidate no longer hard-overwrites threshold values in stage logic;
    it now uses configurable defaults and preserves `kwarg_overrides_for_tsa`
    when provided.
  - Added env-backed defaults for tail thresholds (`FEMIC_TAIL_*`) to enable
    runtime tuning without source edits.
  - Added regression tests verifying both per-stratum override precedence and
    env-default application for tail-blend candidate settings.
- 2026-03-15 (Phase 19 `P19.13d` complete): wired explicit ordered fallback
  selection policy with per-stratum/SI selection events.
  - Selection order now executes as `primary_nlls -> reparameterized_nlls
    (auto-skip) -> censored_refit -> merchantable_floor`, with K3Z-specific
    tail-blend override preserved.
  - Added `vdyp_curve_fit` event `stage=fallback_policy`/`reason=curve_selected`
    for each stratum/SI with selected path, available candidates, and selected
    metrics to make fit-path decisions auditable.
  - Added regression test to verify reparameterized candidate selection and
    fallback-policy event emission.
- 2026-03-15 (Phase 19 `P19.13c` complete): added optional merchantable-volume
  floor candidate (default zero through age 20) with selection diagnostics.
  - `process_vdyp_out(...)` now supports
    `merchantable_floor_enabled/age/value` and logs `merchantable_floor` stage
    events when applied.
  - Stage-level smoothing now evaluates a merchantable-floor candidate when
    baseline pre-merchantable volume is non-trivial, then selects/rejects it
    using pre-age-20 plausibility plus RMSE guardrails.
  - Added regression tests covering both direct floor application in
    `vdyp_curves` and stage-level candidate selection behavior.
- 2026-03-15 (Phase 19 `P19.13b` complete): added left-toe outlier censor
  candidate fit path with deterministic selection logging.
  - Added observed-bin based left-toe outlier detection that proposes
    `skip1` censoring for incoherent early-age points.
  - Added a re-fit candidate using censored vectors and acceptance logic based
    on early-overshoot reduction plus RMSE/MAPE improvement.
  - Added structured `vdyp_curve_fit` events at stage `left_toe_censor`
    indicating selected/rejected decisions with baseline vs candidate metrics.
- 2026-03-15 (Phase 19 `P19.13a` complete): added fit-quality gate warnings for
  implausible VDYP NLLS outputs before downstream acceptance.
  - Added gate checks in curve smoothing for non-finite/negative outputs plus
    metric thresholds (`mape`, `early_overshoot`) and emits structured
    `vdyp_curve_fit` warning events (`stage=fit_quality_gate`) when violated.
  - Added regression coverage that forces an implausible fit and verifies
    `fit_quality_gate_failed` diagnostics are recorded.
- 2026-03-15 (Phase 19 `P19.12` follow-up): fixed strata SI diagnostic x-axis
  floor to `0` so left violin tails are not visually clipped by quantile-based
  windowing.
  - Lower SI bound is now fixed at `site_index_xlim[0]` (default `0`) while
    upper bound remains quantile-focused.
  - Regenerated TSA29 strata diagnostics to confirm rendered SI axis starts at
    `0`.
- 2026-03-15 (Phase 19 `P19.12` follow-up): switched strata diagnostic output
  to PNG-only by default to reduce plot-folder noise.
  - `render_strata_distribution_plot(...)` now writes PDF only when explicitly
    enabled in plot config (`write_pdf=True`).
- 2026-03-15 (Phase 19 `P19.12` complete): improved stratum SI diagnostic
  plotting readability and added auditable clipping metadata.
  - Point overlays now use deterministic thinning and lower default opacity to
    keep violin density visible under heavy sample counts.
  - Plot SI axis now uses quantile-centered windowing with configurable cap and
    padding instead of expanding to extreme outliers.
  - Plot helper now returns clipping/point-count metadata; legacy 01a run logs
    report SI window, total/window/overlay point counts, and low/high clipped
    counts for audit traceability.
- 2026-03-15 (Phase 19 planning note): incorporated TSA29 curve-review feedback
  as new actionable tasks `P19.12`-`P19.15`.
  - Plot readability work (`P19.12`): reduce overplot darkness, thin point
    overlays, and add quantile-focused SI zoom with auditable outlier clipping.
  - NLLS robustness work (`P19.13`): detect failed fits and apply ordered
    auto-reparameterization fallbacks, including left-toe point censoring and
    merchantable-volume floor through age 20.
  - Tail policy work (`P19.14`): relax/redefine tail-linearity and revise
    tail-blend selection criteria against straight NLLS.
  - Validation/evidence work (`P19.15`): rerun TSA29 diagnostics and publish
    fit-path evidence for sign-off before phase closure.
- 2026-03-15 (Phase 19 `P19.11` complete): fixed resume behavior so
  `vdyp_prep-tsaXX.pkl` cannot be reused when pre-VDYP stratification settings
  change (for example `FEMIC_STRAT_TOP_AREA_COVERAGE`).
  - Added signature-aware pre-VDYP checkpoint persistence/validation.
  - Resume now rebuilds pre-VDYP fit payload on signature mismatch instead of
    silently loading stale strata payloads.
- 2026-03-15 (Phase 19 runtime tuning): removed default explicit feature-id
  chunked GDB reads in VDYP source loading to reduce per-query overhead on
  high-memory hosts.
  - New default for explicit feature-id mode is full-layer read + in-memory
    `FEATURE_ID` filter.
  - Chunked `FEATURE_ID IN (...)` reads remain available only when an explicit
    `source_feature_id_chunk_size` is provided.
  - Also removed explicit `driver=\"FileGDB\"` kwargs from these calls to avoid
    `OpenFileGDB ... open option DRIVER` warning spam.
- 2026-03-15 (Phase 19 in-flight run note): current clean TSA29 run is showing
  stratum coverage around `0.656` with ~10 strata (current cutoff), which is
  below preferred operating target.
  - Queue for next run only: tune stratum inclusion/cutoff to target coverage
    near `0.8`.
  - Do not interrupt/restart the currently monitored run; first observe whether
    this run completes with sane output.
  - Keep Phase 20 deferred to a separate feature branch after TSA29 handoff
    readiness is achieved.
- 2026-03-15 (Phase 20 `P20.1` drafted): added execution-ready acceptance
  checklist in `planning/TSA29_dataset_compile_plan.md` covering:
  - scope boundary (VDYP-only),
  - serial/parallel parity invariants + numeric tolerance policy,
  - determinism/hash-repeatability requirements,
  - worker-failure/fallback behavior,
  - observability heartbeat minimums,
  - performance and rollout gates (opt-in first).
- 2026-03-15 (Phase 20 planning note): added a separate, explicitly
  non-blocking phase for VDYP parallelization and long-run observability so
  TSA29 Phase 19 delivery can proceed without waiting on concurrency work.
  - Execution rule: do not block `P19.5`/instance delivery on Phase 20.
  - Phase 20 focuses on opt-in first, with parity checks before any default
    behavior change.
- 2026-03-15 (Phase 19 planning note): added explicit TSA29 investigation task
  on siteprod dependency in compile paths (strata/AU/VDYP/TIPSY/other) with
  decision gate:
  - if not required, disable siteprod in default path and keep it opt-in.
  - if required, harden no-data handling so sparse no-data stands cannot crash
    clean runs.
- 2026-03-14 (Phase 19 `P19.10` complete): executed real TSA29 Woodstock export
  and ws3 smoke gate, then published evidence in the TSA29 instance repo.
  - Generated complete Woodstock package under
    `external/femic-tsa29-instance/output/woodstock_tsa29_validated/`
    (yields/areas/actions/transitions + ws3 bridge `.lan/.are/.yld/.act/.trn`).
  - Executed command:
    `femic instance ws3-smoke --instance-root external/femic-tsa29-instance --woodstock-dir output/woodstock_tsa29_validated --output evidence/ws3_smoke_report.latest.json --ws3-repo-path /home/gep/projects/ws3`.
  - Result: `status=ok`, rows `(y/a/ac/t)=(10050/147959/30/30)`,
    `actions=1`, `inventory_area=2172195.127`.
  - Published TSA29 instance commit with evidence/artifacts:
    `UBC-FRESH/femic-tsa29-instance@afc5f8b`.
- 2026-03-14 (Phase 19 `P19.10` progress): added builtin ws3 model smoke path
  that converts FEMIC Woodstock CSV exports into ws3-ingestible Woodstock
  section files and runs a minimal `ForestModel` compile/schedule check.
  - Added bridge module:
    `src/femic/ws3_bridge.py` with
    `build_ws3_sections_from_femic_woodstock(...)` to generate
    `.lan/.are/.yld/.act/.trn`.
  - Extended ws3 smoke runtime:
    `src/femic/ws3_smoke.py` now supports builtin smoke execution, optional
    `--ws3-repo-path` PYTHONPATH injection, and report fields for bridge output
    location/model name.
  - Extended CLI wiring:
    `femic export dual` now supports
    `--ws3-repo-path`, `--ws3-builtin-smoke`, `--ws3-bridge-dir`;
    `femic instance ws3-smoke` now supports
    `--ws3-repo-path`, `--builtin-model-smoke`, `--ws3-bridge-dir`.
  - Added tests/docs coverage:
    `tests/test_ws3_bridge.py`, updates to
    `tests/test_ws3_smoke.py`, `tests/test_cli_main.py`,
    `tests/test_docs_contract.py`,
    `docs/reference/cli.rst`,
    `docs/reference/api/modules.rst`.
  - Remaining for `P19.10`:
    run this against a real TSA29 Woodstock output + ws3 model workflow and
    publish green ws3 smoke evidence in the TSA29 instance repo.
- 2026-03-14 (Phase 19 `P19.9` complete, `P19.10` in progress):
  implemented dual-output orchestration and ws3 smoke-test command support in
  FEMIC CLI/runtime.
  - Added new export command:
    `femic export dual` to generate Patchworks and Woodstock outputs from the
    same bundle/checkpoint inputs, with optional ws3 smoke execution.
  - Added new instance command:
    `femic instance ws3-smoke` to validate Woodstock datasets and optionally
    execute a ws3 simulation command, emitting JSON evidence.
  - Added `src/femic/ws3_smoke.py` with machine-readable smoke results and
    sanity checks (file presence, row counts, nonzero aggregate volume/area,
    optional command return code and captured logs).
  - Updated docs:
    `docs/reference/cli.rst`,
    `docs/guides/model-input-bundle-and-export.rst`,
    `docs/guides/pipeline-overview.rst`.
  - Added tests:
    `tests/test_ws3_smoke.py` and new CLI wiring checks in
    `tests/test_cli_main.py`.
  - Remaining for `P19.10`:
    execute ws3 smoke against an actual ws3 model instance path and capture
    green evidence in TSA29 instance repository workflows.
- 2026-03-14 (Phase 19 extension - dual-output + ws3 integration):
  extended TSA29 planning so the pipeline must fork to both Patchworks and
  Woodstock outputs, with ws3 simulation smoke tests as required validation.
  - Created feature branch for this workstream firewall:
    `feature/compile-tsa29-instance-ws3-fork`.
  - Rewrote plan doc:
    `planning/TSA29_dataset_compile_plan.md` with explicit:
    - fork-stage contract (`Patchworks` and `Woodstock` outputs),
    - ws3 ingestion and simulation smoke-test workflow,
    - ws3 evidence artifacts and sanity gates.
  - Added new open Phase 19 tasks:
    `P19.9` (dual-output contract) and
    `P19.10` (ws3 smoke-test gate).
- 2026-03-14 (Phase 19 kickoff + initial delivery):
  published initial standalone TSA29 instance repository and linked it back into
  FEMIC.
  - Published repo/tag:
    `https://github.com/UBC-FRESH/femic-tsa29-instance` @ `v0.1.0`.
  - Completed deliverables:
    - authored instance contract in
      `planning/tsa29-instance-contract.md`,
    - bootstrapped TSA29 repo structure/config/rebuild runbook/docs,
    - assembled thin snapshot payload with curated TSA29 artifacts + checksums,
    - added evidence baseline artifact
      `evidence/reference_rebuild_report.latest.json`,
    - added FEMIC submodule link at `external/femic-tsa29-instance`,
    - added FEMIC TSA29 pointer docs and docs-contract tests.
  - Intentional thin-instance policy:
    very large artifacts were externalized and referenced via
    `metadata/large_artifacts.sha256` and output manifest docs.
  - Remaining step for full phase closure (`P19.5`):
    run full Patchworks-enabled rebuild in a validated runtime host and publish
    a green evidence update replacing the current warning-state baseline.
- 2026-03-12 (Phase 18 `P18.3` + `P18.4` complete): published
  `femic==0.1.1a1` to production PyPI via trusted publisher and validated
  post-release smoke install in workflow.
  - Green production run:
    `https://github.com/UBC-FRESH/femic/actions/runs/23024083304`
  - Published artifacts (from PyPI API):
    - `femic-0.1.1a1-py3-none-any.whl`
      `sha256=09c8dfca3539815b149dee77145ba525eae33f239e88a3e3e63879d6fcc0d699`
    - `femic-0.1.1a1.tar.gz`
      `sha256=10fb2e43abdecb0dcee5c40096230462aca9cab5e2cc7c28687a7bd8258154d7`
  - Release summary:
    Phase 18 checklist is now fully complete (`P18.1`-`P18.4`).
- 2026-03-12 (Phase 18 `P18.2` complete): published pre-release
  `femic==0.1.1a1` to TestPyPI with successful end-to-end smoke install in
  GitHub Actions.
  - Version bump:
    `pyproject.toml` from `0.1.0` -> `0.1.1a1` (PEP 440 pre-release).
  - Workflow hardening:
    - aligned `.github/workflows/publish-pypi.yml` with TestPyPI safety
      behavior (`skip-existing: true` + smoke install step),
    - added index-propagation retry loops to both publish workflows to handle
      TestPyPI/PyPI indexing lag after upload.
  - Green TestPyPI run:
    `https://github.com/UBC-FRESH/femic/actions/runs/23023751656`.
  - Prior failed attempt (diagnosed and fixed):
    publish succeeded, smoke install failed due immediate index lag:
    `https://github.com/UBC-FRESH/femic/actions/runs/23023687076`.
  - Next:
    execute `P18.3` production PyPI publish using the now-matched workflow and
    then complete `P18.4` traceability recording.
- 2026-03-12 (Phase 18 `P18.3` execution attempt): production publish workflow
  is blocked by PyPI trusted-publisher configuration (not by workflow/build
  logic).
  - Failing run:
    `https://github.com/UBC-FRESH/femic/actions/runs/23023862800`
  - Failure:
    `invalid-publisher` during OIDC exchange in `Publish to PyPI`.
  - Emitted claims:
    - `sub`: `repo:UBC-FRESH/femic:environment:pypi`
    - `repository`: `UBC-FRESH/femic`
    - `workflow_ref`:
      `UBC-FRESH/femic/.github/workflows/publish-pypi.yml@refs/heads/main`
    - `ref`: `refs/heads/main`
    - `environment`: `pypi`
  - Next unblock action:
    create/update matching trusted publisher on production PyPI, then rerun
    `publish-pypi`; smoke step is already wired and will verify install.
- 2026-03-12 (Phase 18 workflow bugfix): fixed TestPyPI smoke step shell
  parsing error after successful publish.
  - Root cause:
    `publish-testpypi.yml` used brittle nested quoting in the version-detection
    command, producing shell parse error near `tomllib.loads(...)`.
  - Fix:
    simplified version extraction command to a single robust Python `-c`
    invocation in `.github/workflows/publish-testpypi.yml`.
  - Validation gates passed locally:
    `ruff format`, `ruff check`, `mypy`, `pytest`, `pre-commit --all-files`,
    `sphinx-build -W`.
- 2026-03-12 (Phase 18 docs clarification): added validated TestPyPI
  token-free bootstrap path to release runbook to remove ambiguity when no
  project-level "Add project" button is visible.
  - Updated `docs/guides/pypi-release-runbook.rst` with account-level
    TestPyPI pending-publisher flow:
    `https://test.pypi.org/manage/account/publishing/`.
  - Added explicit notes that first successful OIDC publish creates the
    TestPyPI project automatically and attaches the publisher.
  - Kept token upload documented only as fallback, not primary path.
- 2026-03-12 (Phase 18 `P18.2` execution attempt): triggered
  `publish-testpypi` workflow and confirmed current blocker is trusted
  publisher configuration, not packaging artifacts.
  - Workflow run:
    `https://github.com/UBC-FRESH/femic/actions/runs/23022440859`
    failed at `Publish to TestPyPI` with `invalid-publisher`.
  - Claims emitted by GitHub for debugging:
    - `repository`: `UBC-FRESH/femic`
    - `workflow_ref`:
      `UBC-FRESH/femic/.github/workflows/publish-testpypi.yml@refs/heads/main`
    - `environment`: `testpypi`
  - Updated `docs/guides/pypi-release-runbook.rst` with explicit trusted
    publisher setup requirements for TestPyPI/PyPI and troubleshooting steps.
  - Next action for `P18.2`:
    configure matching trusted publisher entries on TestPyPI, then re-run
    `publish-testpypi` and perform install smoke.
- 2026-03-12 (Phase 17 docs refinement): switched K3Z appendix from
  filename-only inventory to inline-rendered figures in the standalone
  instance docs.
  - Updated `external/femic-k3z-instance/docs/figure-appendix.rst` to embed:
    analysis-area map, strata figure, all VDYP LMH envelopes, all VDYP fit
    diagnostics, and all TIPSY-vs-natural overlay plots.
  - Retained filename references in captions for traceability/QA.
  - Updated docs contract checks in `tests/test_docs_contract.py` to require
    new appendix section headings and figure directives.
  - Validation checks passed:
    `pytest tests/test_docs_contract.py`,
    `sphinx-build -b html external/femic-k3z-instance/docs ... -W`,
    `sphinx-build -b html docs _build/html -W`.
- 2026-03-12 (Phase 18 `P18.1` completion + `P18.2/P18.3` automation prep):
  added deterministic packaging runbook + CI/workflow scaffolding for staged
  TestPyPI -> PyPI publication.
  - Added release runbook:
    `docs/guides/pypi-release-runbook.rst` and wired it in
    `docs/guides/index.rst`.
  - Added local helper:
    `scripts/release_package_checks.sh` to run
    `python -m build`, `twine check`, wheel install smoke, and a wheel
    reproducibility check under fixed `SOURCE_DATE_EPOCH`.
  - Updated CI packaging workflow:
    `.github/workflows/package-release-checks.yml` now sets deterministic build
    epoch and enforces wheel reproducibility across consecutive builds.
  - Added staged publish workflows:
    `.github/workflows/publish-testpypi.yml` and
    `.github/workflows/publish-pypi.yml` (OIDC/trusted-publisher ready).
  - Updated user-facing release instructions in `README.md` to point to the
    runbook and helper script.
  - Validation gates passed:
    `ruff format`, `ruff check`, `mypy`, `pytest (491 passed)`,
    `pre-commit --all-files`, `sphinx-build -W`, and
    `scripts/release_package_checks.sh`.
  - Remaining for Phase 18 completion:
    run actual TestPyPI and PyPI publish executions (`P18.2`/`P18.3`) once
    publisher credentials/trust bindings are active; then record final
    artifact/version traceability (`P18.4`).
- 2026-03-12 (Phase 17 `P17.4` completion): converted FEMIC K3Z page to
  pointer/overview model and aligned docs contracts to submodule-first
  ownership.
  - Replaced `docs/sample-models/k3z.rst` with a concise pointer page linking:
    - canonical repo/docs:
      `https://github.com/UBC-FRESH/femic-k3z-instance`,
      `https://ubc-fresh.github.io/femic-k3z-instance/`,
    - submodule sync commands and FEMIC-local integration paths.
  - Updated `tests/test_docs_contract.py` K3Z sample-model assertions to
    enforce pointer-page contract (required sections + canonical links +
    submodule commands), replacing old deep narrative heading checks.
  - Phase 17 checklist now fully complete (`P17.0`-`P17.5`).
  - Validation gates passed:
    `ruff format`, `ruff check`, `mypy`, `pytest (490 passed)`,
    `pre-commit --all-files`,
    `sphinx-build -W` for parent docs and standalone
    `external/femic-k3z-instance/docs`.
- 2026-03-12 (Phase 17 `P17.1/P17.2/P17.3/P17.5` completion): expanded
  standalone K3Z student docs to TSR-style structure with area accounting, map,
  and full figure appendix coverage.
  - Updated standalone guide IA in
    `external/femic-k3z-instance/docs/index.rst` to include
    `figure-appendix.rst` and keep K3Z docs rooted in submodule Sphinx.
  - Extended
    `external/femic-k3z-instance/docs/land-base-and-netdown.rst` with:
    - analysis-area map section using generated
      `docs/_static/k3z_analysis_area_map.png`,
    - total analysis area/THLB summary table,
    - AU-level area accounting table (14 AUs),
    - explicit THLB netdown placeholder table with zeroed reductions.
  - Extended
    `external/femic-k3z-instance/docs/base-case-analysis.rst` with appendix
    linkage so interpretation sections reference canonical figures.
  - Added new
    `external/femic-k3z-instance/docs/figure-appendix.rst` containing:
    - core teaching figure catalog with captions,
    - full inventory list of all current `plots/*tsak3z*` artifacts.
  - Updated
    `external/femic-k3z-instance/docs/data-package-crosswalk.rst` to map TSR
    figure/map exhibits to the new appendix and linked pages.
  - Added/expanded docs contract checks in `tests/test_docs_contract.py` for:
    - required `figure-appendix` navigation entry,
    - required new land-base section headings,
    - required appendix anchor/content and base-case appendix references.
  - Validation gates passed:
    `ruff format`, `ruff check`, `mypy`, `pytest (490 passed)`,
    `pre-commit --all-files`,
    `sphinx-build -W` for both parent docs and standalone
    `external/femic-k3z-instance/docs`.
- 2026-03-12 (Phase 16 `P16.2` completion): finished public-surface docstring
  coverage for FEMIC Python modules and normalized command/helper docstrings.
  - Added/normalized missing public docstrings in:
    `src/femic/__main__.py`,
    `src/femic/cli/main.py`,
    `src/femic/patchworks_runtime.py`,
    `src/femic/pipeline/io.py`,
    `src/femic/pipeline/plots.py`,
    `src/femic/pipeline/tipsy_legacy.py`,
    `src/femic/rebuild_runner.py`,
    `src/femic/vdyp/reporting.py`.
  - Verified public-surface docstring completeness with a static AST scan
    (`missing count: 0` for non-private defs in `src/femic`, excluding
    resources payload modules).
  - Kept behavior unchanged (documentation-only updates in code paths).
- 2026-03-12 (Phase 16/17 execution kick-off): synced K3Z submodule baseline
  and landed initial FEMIC API reference scaffolding with guardrails.
  - Completed `P17.0` by fast-forwarding
    `external/femic-k3z-instance` from `e3285ad` to `9748707`, restoring
    standalone docs scaffold and `config/rebuild.spec.yaml` expected by
    contract tests.
  - Completed `P16.1` by adding API contract policy page:
    `docs/reference/api/index.rst` (public module scope, exclusions, and
    private-member policy).
  - Completed `P16.3` by wiring API docs into Sphinx:
    `docs/index.rst` now links `reference/api/index`;
    `docs/reference/api/modules.rst` enumerates public modules for generated
    API stubs.
  - Completed `P16.4` by extending docs contract tests in
    `tests/test_docs_contract.py` to require API reference pages and expected
    module entries.
  - Updated Sphinx config in `docs/conf.py` to add `src/` import path so
    autodoc/autosummary can resolve `femic` modules during docs build.
  - Validation gates (this checkpoint): `ruff format`, `ruff check`, `mypy`,
    `pytest` (`490 passed`), `pre-commit --all-files`, and
    `sphinx-build -W` all passed.
- 2026-03-12 (Phase 16-18 roadmap extension lock-in): added the
  decision-complete implementation plan for API docs coverage, submodule-first
  K3Z student docs, and staged package publication.
  - Added new roadmap phase checklists:
    - `Phase 16: Full Developer API Documentation Coverage (FEMIC Package)`
    - `Phase 17: K3Z TSR-Style Student Documentation (Submodule-First)`
    - `Phase 18: Packaging and Publication to PyPI`
  - Locked documentation model:
    `external/femic-k3z-instance/docs/` is canonical for student-facing K3Z
    content, while FEMIC docs keep a short pointer/overview page.
  - Locked API docs policy defaults:
    Google-style docstrings, public-surface API publication, and
    autosummary/autodoc Sphinx coverage for `src/femic` public modules.
  - Locked release flow:
    package publication executes via TestPyPI validation first, then PyPI.
  - Implementation reminder:
    current local submodule checkout is behind upstream and lacks a local docs
    tree; `P17.0` must sync `external/femic-k3z-instance` before docs work.
- 2026-03-11 (repo-root cleanup: legacy notebook archive move):
  moved legacy notebook artifacts out of repository root into a dedicated
  archive location.
  - Moved notebook files:
    `00_data-prep.ipynb`, `01a_run-tsa.ipynb`, `01b_run-tsa.ipynb` ->
    `reference/legacy_notebooks/`.
  - Updated docs/test references to the new notebook location:
    `docs/guides/legacy-traceability.rst`,
    `docs/guides/index.rst`,
    `tests/test_docs_contract.py`.
  - Verified contract/tests/docs build remain green after relocation.
- 2026-03-11 (K3Z species-account bugfix: TIPSY `FD` alias to canonical `FDC`):
  fixed treated species-proportion mapping so species-wise accounts no longer
  drop `FDC` to zero when TIPSY outputs `FD`.
  - Updated bundle assembly in `src/femic/pipeline/bundle.py` to normalize
    TIPSY species aliases (`FD -> FDC`) before writing treated species-prop
    curves.
  - Added regression test
    `tests/test_bundle.py::test_build_bundle_tables_from_curves_maps_tipsy_fd_to_fdc`.
  - Re-ran K3Z post-TIPSY bundle + Patchworks export and verified
    `managed_prop_FDC_985521000004` now exports with `y=0.1`, and
    `au_985501000_managed_yield_FDC` is no longer a flat zero curve.
- 2026-03-10 (P8.7 docs QA + acceptance checks): added automated docs
  contract coverage for Sample Models navigation and required K3Z sections,
  and added a release-readiness checklist for student distribution.
  - Extended `tests/test_docs_contract.py` with:
    - Sample Models toctree/page existence checks (`k3z`, `k3z-metadata-lineage`),
    - required heading checks for `docs/sample-models/k3z.rst`,
    - required heading checks for
      `docs/sample-models/k3z-metadata-lineage.rst`.
  - Added `Release Readiness Checklist` section to
    `docs/sample-models/k3z.rst`.
  - Marked `P8.7a/P8.7b/P8.7c` complete.
- 2026-03-11 (Phase 8 `P8.6d` complete: regenerated strata/AU plot rollout):
  integrated regenerated K3Z strata/AU QA plot artifacts into user-facing
  Sample Models documentation.
  - Added new section `Regenerated Strata/AU Build Plots` to
    `docs/sample-models/k3z.rst` with explicit artifact families:
    `plots/strata-tsak3z.png`, `plots/vdyp_lmh_tsak3z-*.png`,
    `plots/tipsy_vdyp_tsak3z-*.png`.
  - Updated K3Z release checklist to require regenerated plot presence prior to
    student distribution.
  - Extended `tests/test_docs_contract.py` K3Z section contract to require the
    new plot section and artifact-pattern references.
  - Marked `P8.6d` complete; with `P8.6a/P8.6b/P8.6c` already complete, parent
    `P8.6` is now complete.
- 2026-03-11 (Phase 8 status normalization): parent `P8.3` marked complete
  because all child items (`P8.3a/P8.3b/P8.3c`) were already completed.
- 2026-03-11 (Phase 10 status normalization): parent `P10.1`, `P10.2`, and
  `P10.3` marked complete because all child items were already completed.
- 2026-03-10 (P8.5 scenario interpretation guidance): completed trajectory
  interpretation guidance for classroom scenario analysis in K3Z docs.
  - Added `Scenario Comparison Guidance` to `docs/sample-models/k3z.rst`
    covering within-scenario and cross-scenario comparison workflow.
  - Added explicit treatment-shift interpretation guidance using
    `product.Seral.area.<stage>.<au_id>.CC` trajectories.
  - Added a minimum report-template matrix mapping analytical questions to
    account sources and aggregation patterns for student exercises.
  - Marked `P8.5a/P8.5b/P8.5c` complete.
- 2026-03-10 (P8.2c + P8.4c completion): expanded K3Z guide with explicit
  student-facing parameter risk ranges and backup/recovery conventions.
  - Added `Parameter Risk and Suggested Ranges` section to
    `docs/sample-models/k3z.rst` covering IFM share/threshold tuning,
    topology radius, seral boundaries, CC min-age behavior, and horizon risk.
  - Added `Backup and Recovery Conventions` section to document run-log
    retention, automatic `accounts.csv` timestamp backups, and regeneration-
    first recovery practices.
  - Marked `P8.2c` and `P8.4c` complete; with this, `P8.2` and `P8.4` are
    now fully complete.
- 2026-03-10 (P8.1 metadata + lineage baseline): completed initial K3Z
  metadata lineage capture for student-facing use and future rebuild governance.
  - Added docs page `docs/sample-models/k3z-metadata-lineage.rst` with:
    source inventory for `data/`, `yield/`, `blocks/`, explicit lineage chain,
    and a provenance versioning policy/checklist.
  - Added machine-readable registry
    `models/k3z_patchworks_model/metadata/lineage_registry.yaml` encoding
    artifact-to-source mappings, builder commands, and provenance rules.
  - Wired metadata page into Sample Models docs navigation
    (`docs/sample-models/index.rst`) and linked from K3Z guide.
  - Marked `P8.1a/P8.1b/P8.1c` complete.
- 2026-03-10 (P6.4 onboarding regression scenarios): completed the queued
  onboarding regression test slice by adding template-driven case preflight and
  docs-linkage contract coverage.
  - Added `tests/test_case_preflight_cli.py` scenarios for:
    - smoke instantiation from `config/run_profile.case_template.yaml` +
      `config/tipsy/template.case.yaml` (new TSA code) passing
      `femic prep validate-case`;
    - boundary-mode compatibility using template-derived profile
      (`selection.boundary_path`/`selection.boundary_code`) with matching
      `tsa<boundary_code>.yaml` config.
  - Added docs contract check in `tests/test_docs_contract.py` requiring
    `docs/guides/case-onboarding.rst` to keep links to both onboarding
    templates plus the `femic prep validate-case` command.
  - Marked `P6.4a/P6.4b/P6.4c` complete.
- 2026-03-10 (Sample Models docs + K3Z deep-dive launch): added a new
  top-level Sphinx "Sample Models" section and published a detailed K3Z guide at
  `docs/sample-models/k3z.rst`, anchored to the in-repo authoritative model
  state at `models/k3z_patchworks_model/`.
  - Documented purpose/scope, provenance, full component mapping, rebuild
    commands, runtime pathing, and matrix-builder artifact expectations.
  - Explicitly documented post-build accounts promotion behavior:
    `tracks/protoaccounts.csv -> tracks/accounts.csv` with timestamped backup.
  - Added user guidance for assumptions/parameters, edit policy, seral account
    semantics, and common troubleshooting signatures.
  - Added new planning phase `Phase 8` to drive full student-facing K3Z
    metadata/how-to documentation to completion.
  - Marked completed Phase 8 starter tasks in checklist form (`P8.2a/P8.2b`,
    `P8.3a/P8.3b/P8.3c`, `P8.4a/P8.4b`, `P8.6a/P8.6b/P8.6c`) so roadmap
    progress reflects delivered docs work.
- 2026-03-09 (THLB/IFM tuning for Patchworks export): confirmed legacy 00 THLB
  assignment logic is still in effect (`assign_thlb_area_and_flag` with fixed
  thresholds 93/69/50 and `thlb_raw` expected on percent-like scale), and added
  explicit export-time IFM tuning controls to avoid guesswork when checkpoints
  carry continuous THLB values (for example `[0,1]`).
  - New `femic export patchworks` options:
    - `--ifm-source-col` (explicit THLB signal column, e.g. `thlb_raw`)
    - `--ifm-threshold` (managed when signal > threshold)
    - `--ifm-target-managed-share` (top-N stands managed by signal rank)
  - `--ifm-threshold` and `--ifm-target-managed-share` are mutually exclusive.
  - This keeps legacy defaults unchanged unless an operator opts into tuning.
- 2026-03-09 (1:1 blocks + topology pipeline step): added
  `femic patchworks build-blocks` to compile a sample-aligned blocks package
  from `data/fragments.shp` with strict stand:block identity (`BLOCK` copied
  from `FEATURE_ID`/`FRAGS_ID`) and optional topology generation.
  - Output contract:
    - `<model>/blocks/blocks.shp`
    - `<model>/blocks/topology_blocks_<radius>r.csv` (default radius `200`)
  - Topology CSV schema matches Patchworks sample usage:
    `BLOCK1,BLOCK2,DISTANCE,LENGTH`, including exterior `-9999` rows for PIN
    `control.inputTopology(...)` wiring.
  - Live validation completed on
    `C:\Users\gep\Documents\msfm\msfm2025\k3z_patchworks_model` with
    `blocks=218` and `edges=928` at `200m` radius.
- 2026-03-09 (Windows runtime config path correction): updated
  `config/patchworks.runtime.windows.yaml` paths from stale Desktop location to
  active model root under
  `C:\Users\gep\Documents\msfm\msfm2025\k3z_patchworks_model`.
- 2026-03-09 (K3Z script adaptation): replaced
  `C:\Users\gep\Desktop\msfm2025\k3z_patchworks_model\scripts\dataPrep\prepareBlocks.bsh`
  with a FEMIC-aligned variant that:
  - targets `data/fragments.*`, `yield/forestmodel.xml`, and `tracks/`,
  - requires `yield/forestmodel.xml` explicitly (no C5 fallback filename),
  - runs Matrix Builder through `new ca.spatial.tracks.builder.Process(...).execute(false)`,
    then waits on the process object for completion,
  - keeps C5-style dissolve/join steps as optional toggles and skips safely when
    lookup inputs are missing.
- 2026-03-09 (K3Z Patchworks model layout reorg): created
  `C:\Users\gep\Desktop\msfm2025\k3z_patchworks_model` with top-level folders
  mirroring Patchworks `sample_2024` structure (`analysis`, `blocks`, `data`,
  `imagery`, `misc`, `roads`, `scenarios`, `scripts`, `tracks`, `yield`).
- Copied K3Z runtime artifacts into sample-aligned locations:
  - fragments shapefile set -> `...\k3z_patchworks_model\data\fragments.*`
  - ForestModel XML -> `...\k3z_patchworks_model\yield\forestmodel.xml`
  - seeded scripts from `reference/Patchworks-202502/sample_2024/scripts/`.
- Updated `config/patchworks.runtime.windows.yaml` matrix builder paths to use
  the new K3Z model root and verified a successful matrix build run
  (`run_id=win_native_k3z_reorg_20260309`, `returncode=0`) writing tracks to
  `...\k3z_patchworks_model\tracks`.
- 2026-03-09 (Windows-first Patchworks runtime): updated
  `femic patchworks` to support native Windows launch (`java -jar ...`) in
  addition to Linux/Wine, instead of hard-requiring Wine on all hosts.
- 2026-03-09 (matrix-build completion semantics): aligned with Patchworks
  `Process.main(argv)` behavior by treating non-interactive run success as
  artifact-driven (tracks output present + no fatal signatures), recording both
  raw JVM return code and effective FEMIC return code in run manifests.
- 2026-03-09 (matrix output precondition): matrix output directory is now
  created automatically before non-interactive launch to satisfy Patchworks
  constructor requirements (`outName` must exist).
- Completed `P6.3`: added `femic export release` for versioned student-facing
  bundle packaging with strict required-artifact checks, release manifest
  (`release_manifest.json`), and operator handoff notes (`HANDOFF.md`).
- Added release packaging tests and CLI/docs wiring; next queued work starts at
  `P6.4` (onboarding regression scenario tests + docs linkage checks).
- Started Phase 7 runtime integration for proprietary Patchworks tooling:
  added `femic patchworks preflight` and `femic patchworks matrix-build` command
  skeletons with config-driven Wine invocation, Matrix Builder command assembly,
  run log capture, and execution manifest output.
- Added a baseline Patchworks runtime config (`config/patchworks.runtime.yaml`)
  for local editing, and gitignored `reference/Patchworks/` to avoid publishing
  proprietary binaries/API docs.
- Added Phase 7 docs/test wiring for Patchworks runtime and VPN diagnostics;
  verified `reference/Patchworks/` is now ignored and not tracked in git index;
  remaining queued Phase 7 work is first live VPN+Wine validation against the
  real license server environment.
- Updated Patchworks runtime licensing behavior to match real Patchworks
  ownership: `femic patchworks preflight` now validates env/config only
  (`SPS_LICENSE_SERVER`, `SPSHOME`, Wine/Java/jar/input paths) and no longer
  performs direct DNS/TCP checks against inferred license ports/hosts.
- Added required `patchworks.spshome` runtime config support and propagated
  `SPSHOME` injection into Wine subprocess env for `matrix-build` runs.
- Live validation (2026-03-09): `patchworks preflight` now passes in-container
  with `SPSHOME` set to the Wine-visible local Patchworks path, but
  `patchworks matrix-build` still fails internally despite shell return code 0.
  Current blockers from stderr are:
  `no mrsidget2_64 in java.library.path`, GUI/X11 peer creation failures
  (`$DISPLAY` missing), and final license message
  `Not licensed or no connection to license server`; no `tracks/` output
  directory is produced.
- Next queued Phase 7 work: harden matrix-build success detection beyond process
  return code (stderr signature + required output artifact checks), then resolve
  runtime prerequisites (headless/GUI mode compatibility and Patchworks native
  library path) before re-testing VPN/license pass-through.
- Completed matrix-build hardening pass:
  - `patchworks.use_xvfb` config support (wraps launch with `xvfb-run -a`);
  - Windows-side `SPSHOME`/`PATH` injection plus `-Djava.library.path` in
    java launch command;
  - deterministic failure promotion when fatal runtime signatures are found in
    process output or when matrix output directory is missing/empty.
- Live rerun now fails deterministically with explicit blockers:
  `Not licensed or no connection to license server`,
  `IP Helper Library GetAdaptersAddresses function failed`, and missing
  matrix output artifacts.
- Matrix Builder validation from user Windows workstation identified a
  ForestModel schema-order issue (`<input>` unexpectedly encountered near top of
  document). Exporter now emits ForestModel child elements in schema-compatible
  order aligned with current Patchworks samples:
  curves -> define -> input/output -> select.
- Regenerated Patchworks fixtures and re-exported
  `output/patchworks_k3z_validated/forestmodel.xml` with corrected ordering for
  external Matrix Builder retest.
- Follow-up Windows Matrix Builder parse error identified select expression type
  mismatch (`AU` integer column compared to string literal). Exporter now emits
  numeric AU predicates (`AU eq 985501000`) while keeping quoted string
  predicates for `IFM`/`treatment`.
- Re-exported K3Z ForestModel XML with numeric AU expressions for immediate
  external retest.
- Additional Windows Matrix Builder validation shows schema engine mismatch with
  legacy DTD header expectations. Exporter now emits Patchworks XSD model hint
  header (`<?xml-model href="https://www.spatial.ca/ForestModel.xsd"?>`) in
  place of the old DOCTYPE line to align with 2024/2025 sample model format.
- Live preflight now resolves local file paths and Java-in-Wine checks in this
  container; remaining blockers are matrix runtime dependencies and effective
  Patchworks licensing at launch time.
- Phase 6 kickoff complete: added reusable onboarding assets for new cases:
  `config/run_profile.case_template.yaml`, `config/tipsy/template.case.yaml`,
  and `docs/guides/case-onboarding.rst`.
- Guides navigation now includes a dedicated onboarding page so new-case setup
  is discoverable in published docs.
- Next queued work starts at `P6.2` (single-command case preflight validation).
- Completed `P6.2`: added `femic prep validate-case` to run profile-aware
  prerequisite checks (boundary/path integrity, TIPSY config presence/validity,
  external dataset presence, log-dir warnings) with remediation messages and
  optional `--strict-warnings` failure mode.
- Added regression coverage in `tests/test_case_preflight_cli.py` for preflight
  success and key failure paths (missing TIPSY config, missing boundary code,
  strict warnings), and extended docs drift checks for the new CLI options.
- Next queued work starts at `P6.3` (student-facing release packaging workflow).
- Phase 5 docs recovery milestone completed locally: added a new Guides section
  (`docs/guides/*`), a notebook-to-guides coverage matrix
  (`docs/guides/legacy_notebook_coverage.csv`), and a legacy traceability page
  (`docs/guides/legacy-traceability.rst`) so notebook narrative knowledge is now
  explicitly preserved in published docs.
- Added docs contract tests in `tests/test_docs_contract.py` to enforce guide
  page presence, toctree wiring, notebook markdown coverage completeness, and
  high-value CLI docs drift checks.
- Completed GitHub Pages deployment validation (`P5.7`) after push to `main`:
  verified Guides nav renders and direct guide URLs return HTTP 200.
- Updated docs workflow deploy guard in `.github/workflows/docs-pages.yml` to
  allow deployment for both push and manual `workflow_dispatch` runs on `main`
  (still excludes pull requests).
- `PYTHONPATH=src python -m femic --help` now works in the venv.
- `pyproject.toml` defines the `femic` console script; install with `pip install -e .` when ready.
- Added a legacy workflow wrapper that runs `00_data-prep.py` and honors `--tsa`/`--resume`.
- `femic run` now performs preflight checks (use `--skip-checks` to bypass).
- Legacy bundle handling now targets `data/model_input_bundle` only (no legacy auto-copy).
- Removed legacy `data/spadescbm_bundle` directory.
- Normalized `tsa_code`/`tsa` to zero-padded strings to prevent resume-time index mismatches.
- Added a guard that fails fast with a summary when AU assignment yields zero rows.
- Rebuilds `scsi_au` from `au_table` when resuming so curve assignment can proceed.
- Added a `--debug-rows` CLI option to downsample VRI rows for faster iteration.
- Debug row limiting now re-applies after checkpoint reloads to avoid full-size fallbacks.
- Fixed debug row helper ordering so checkpoint loads can call it safely.
- Skips strata lacking VDYP curves to avoid debug-run crashes.
- Debug runs now disable cached checkpoint and output reuse.
- External dataset paths now resolve relative to repo root (`../data`).
- Added external data root override via `FEMIC_EXTERNAL_DATA_ROOT`.
- Fixed raster masking calls to wrap geometries in lists (rasterio expects iterables).
- AU/curve assignment now tolerates missing stratum+SI mappings and logs a warning summary before
  dropping unmapped rows.
- Added `planning/VDYP_debug_notes.md` and queued a VDYP diagnostics + metadata
  hardening focus.
- Added VDYP run and curve-fit diagnostics logs plus toe-fit auto-trimming with warnings to keep
  the pipeline moving while recording failures.
- Updated curve anchoring to quasi-origin `(1, 1e-6)` so zero-value filtering can stay strict.
- Added pre-VDYP TSA checkpointing (`data/vdyp_prep-tsa{tsa}.pkl`) for faster warm-starts.
- Pre-VDYP checkpoint payloads now strip non-picklable fit callables for reliable resume loads.
- Added minimal validation scaffolding: `tests/`, `docs/`, and `.pre-commit-config.yaml`.
- Verified TSA 08 rerun writes `vdyp_io/logs/vdyp_curve_events.jsonl` entries with
  `first_age=1.0` and `first_volume=1e-06`.
- Added `femic vdyp report` to summarize `vdyp_runs.jsonl` + `vdyp_curve_events.jsonl`
  (status/stage/phase counts, parse errors, first-point conformance, mismatch samples).
- Added fallback handling for `nsamples="auto"` with small strata so VDYP runs all available
  records instead of raising `AssertionError`.
- Added explicit warnings + JSONL metadata when curve build/tipsy-input stages encounter
  missing VDYP outputs for specific stratum+SI combinations.
- Forced a fresh TSA 08 debug rerun (`--debug-rows 500`) and confirmed non-empty logs:
  `vdyp_runs.jsonl` (77 events) and `vdyp_curve_events.jsonl` (26 events).
- Hardened sparse-curve handling in `process_vdyp_out`: if smoothed body-fit inputs are empty or
  too short, emit a warning event and return a quasi-origin-anchored fallback curve instead of
  crashing on `idxmax()`.
- Moved `scsi_au`/`au_scsi` registration to only occur for stratum+SI combos that pass all
  operability/species filters and have usable VDYP output.
- Hardened AU-table build in `00_data-prep.py` to skip VDYP curve combos that have no AU mapping,
  with a top-10 warning summary instead of raising `KeyError`.
- Re-ran forced TSA 08 debug (`--debug-rows 500`) from fresh VDYP and reached end-to-end completion
  (process exit code `0`) with populated logs:
  `vdyp_runs.jsonl` (77 events) and `vdyp_curve_events.jsonl` (27 events, including 1
  `body_input` sparse-data warning fallback).
- Defaulted row-wise apply paths back to pandas `.apply(...)` (with optional
  `FEMIC_USE_SWIFTER=1` opt-in) to reduce swifter-related instability/noise during debug runs.
- Added `FEMIC_DISABLE_IPP` handling (default `1`) so debug runs use serial execution without
  ipyparallel controller dependencies.
- Added `FEMIC_SKIP_STANDS_SHP` handling (defaults to skip in debug mode) to bypass final
  shapefile export when iterating rapidly.
- The non-fatal shutdown message (`Error in sys.excepthook` / `Original exception was`) still
  appears even on exit code `0`; root cause remains unresolved, but pipeline outputs and VDYP
  diagnostics are now completing reliably in forced TSA08 debug reruns.
- Updated citation metadata repository URL to match the active remote:
  `https://github.com/UBC-FRESH/wbi_ria_yield`.
- Fixed singleton-stratum handling in `fit_stratum` by forcing `f_.loc[[sc]]` DataFrame access
  (avoids accidental Series coercion and `KeyError: np.False_` during boolean filtering).
- Added guards for empty species mixes in TIPSY-input assembly: if a stratum+SI has no species
  candidates after filtering, emit `no_species_candidates` warning metadata and skip that combo
  instead of raising `IndexError`.
- Stopped importing `swifter` unless `FEMIC_USE_SWIFTER=1` is explicitly enabled, removing
  default monkeypatch side effects during normal debug runs.
- Reworked `run_data_prep` to execute `00_data-prep.py` in a subprocess and stream filtered
  output; this removes persistent non-fatal legacy shutdown noise
  (`Error in sys.excepthook` / `Original exception was`) from `femic run` logs.
- Roadmap review checkpoint (2026-03-01): completed the runtime hardening/diagnostics tranche that
  started this refactor; roadmap focus is now Phase 2 extraction and global-state reduction.
- `femic run` now accepts `--run-id` and `--log-dir`; these are passed to the legacy runner and
  exported as `FEMIC_RUN_ID` / `FEMIC_LOG_DIR`.
- Added per-run manifest output (`run_manifest-<run_id>.json`) with command/options, env flags,
  TSA list, checkpoint presence, and resolved run-scoped log paths.
- VDYP logs are now emitted per TSA + run id
  (`vdyp_runs-tsa{tsa}-{run_id}.jsonl`, `vdyp_curve_events-tsa{tsa}-{run_id}.jsonl`).
- Added deterministic TSA08 regression fixtures under `tests/fixtures/vdyp/tsa08_debug/` and
  tests that assert stable `summarize_vdyp_logs` counts.
- Added warning-budget evaluation (`evaluate_warning_budget`) and CLI threshold flags on
  `femic vdyp report` so CI can fail when warnings/parse-errors grow beyond expected bounds.
- Added per-TSA raw VDYP stream artifacts:
  `vdyp_stdout-tsa{tsa}-{run_id}.log` and `vdyp_stderr-tsa{tsa}-{run_id}.log`.
- Expanded run manifest payloads with runtime/package versions, resolved key paths, and per-TSA
  artifact existence inventory for `vdyp_runs`, `vdyp_curve_events`, `vdyp_stdout`, and
  `vdyp_stderr`.
- Phase 1 checklist reconciled with completed runtime hardening deliverables; remaining work now starts at
  Phase 2 modularization tasks (P2.1+).
- Started Phase 2 module extraction with new reusable helpers under `src/femic/pipeline/`:
  `io.py`, `vdyp.py`, `tsa.py`, and `plots.py`.
- Legacy workflow manifest/log path logic now consumes `femic.pipeline` helpers, reducing
  duplicated logic and defining a stable seam for future migration out of notebook-generated code.
- Removed hardcoded multi-TSA defaults from new pipeline helpers; default TSA selection now reads
  from dev config (`config/dev.toml`, `[run].default_tsa_list`) with `["08"]` fallback for local
  testing.
- Introduced explicit `PipelineRunConfig` handoff from CLI to workflow wrapper so run settings
  (`tsa_list`, `resume`, `debug_rows`, `run_id`, `log_dir`) are passed as typed config instead of
  loose parameters; this is the first concrete step toward `P2.1b` global-state reduction.
- Added `LegacyExecutionPlan` builder in pipeline I/O helpers; legacy runner now consumes a fully
  resolved execution plan (command, env, run IDs, paths, checkpoints) instead of constructing this
  state inline.
- `P2.1b` is now partially complete at the CLI/workflow boundary (typed run config + execution
  plan); remaining `P2.1b` work is to eliminate notebook-script globals inside `00_data-prep.py`
  and `01a_run-tsa.py`.
- Extracted subprocess execution into `femic.pipeline.stages.run_legacy_subprocess(...)`, giving a
  reusable stage executor and reducing orchestration logic inside the legacy workflow wrapper.
- Extracted run-manifest assembly into `femic.pipeline.manifest` (`build_run_manifest_payload`,
  `collect_runtime_versions`, `write_manifest`) so workflow wrapper orchestration now calls reusable
  stage + manifest builders instead of maintaining these internals inline.
- Extracted pre-VDYP checkpoint serialization/load/save into `femic.pipeline.pre_vdyp` and wired
  `01a_run-tsa.py` to use these helpers (`load_vdyp_prep_checkpoint`,
  `save_vdyp_prep_checkpoint`), creating the first notebook-derived data-stage seam for `P2.2a`.
- Removed the old `Next Focus` section after merging non-redundant items into phase checklists to
  keep a single source of planning truth.
- Extracted VDYP input/output table I/O helpers into `femic.pipeline.vdyp_io` and refactored
  `01a_run-tsa.py` to call these shared functions (`write_vdyp_infiles_plylyr`,
  `import_vdyp_tables`), extending `P2.2a` modularization with explicit helper seams.
- Extracted VDYP sample-size estimator into `femic.pipeline.vdyp_sampling.nsamples_from_curves`
  and refactored the auto-sampling loop in `01a_run-tsa.py` to consume this helper.
- Extracted run-id/log-path resolution and append helpers into
  `femic.pipeline.vdyp_logging` (`resolve_run_id`, `build_tsa_vdyp_log_paths`,
  `append_jsonl`, `append_text`) and refactored `01a_run-tsa.py` to consume them.
- Rewired manifest-facing VDYP artifact path builder (`femic.pipeline.vdyp.build_vdyp_log_paths`)
  to reuse `build_tsa_vdyp_log_paths`, removing duplicated filename logic between modules.
- Extracted VDYP curve-building helpers into `femic.pipeline.vdyp_curves` and refactored
  `01a_run-tsa.py` to call shared `process_vdyp_out(...)` logic (including toe-fit retry/fallback
  and quasi-origin anchor behavior) through a reusable module seam.
- Extracted shared VDYP-to-TIPSY scalar derivations into `femic.pipeline.tipsy`
  (`compute_vdyp_site_index`, `compute_vdyp_oaf1`) and refactored all TSA-specific TIPSY parameter
  builders in `01a_run-tsa.py` to consume these helpers instead of duplicating inline parsing logic.
- Added reusable TIPSY candidate evaluation + warning payload helpers in `femic.pipeline.tipsy`
  (`evaluate_tipsy_candidate`, `build_tipsy_warning_event`) and rewired the AU-selection loop in
  `01a_run-tsa.py` to use centralized eligibility reasoning + standardized warning metadata.
- Added initial manual-handoff TIPSY config scaffolding under `config/tipsy/` with a draft template
  (`template.tsa.yaml`) and notes capturing cross-TSA variability from the five legacy TSA rule
  dicts (08/16/24/40/41), to guide migration from hard-coded logic to expert-authored config.
- Added `femic.pipeline.tipsy_config` with TSA YAML loader/validator and config-rule evaluation
  (`load_tipsy_tsa_config`, `validate_tipsy_tsa_config`, `build_tipsy_params_from_config`), and
  wired `01a_run-tsa.py` to prefer `config/tipsy/tsa{tsa}.yaml` (or `.yml`) when present, with
  legacy dict-based dispatch as fallback.
- Added first concrete migrated TSA config `config/tipsy/tsa08.yaml` plus tokenized assignment
  support (e.g., `$leading_species_tipsy`) so config rules can preserve legacy species normalization
  behavior (notably `SX -> SW`) while keeping per-TSA rule logic out of Python code.
- Added second migrated TSA config `config/tipsy/tsa16.yaml` (high-variability case with full
  species-mix/GW field coverage), plus tests that load the repo config and verify expected
  config-driven rule selection output.
- Added third migrated TSA config `config/tipsy/tsa24.yaml` capturing BEC-dependent branching
  (`SBS` vs `ESSF`) and species-group-specific assignment blocks; expanded config tests to verify
  both SBS and ESSF rule-path selection from repo-backed YAML.
- Added `config/tipsy/tsa40.yaml` and `config/tipsy/tsa41.yaml`, completing migration of all five
  legacy TSA rule dict examples into YAML. Extended token support for ranked species placeholders
  (`$species_rank_<n>_tipsy`, `$species_pct_<n>`) and added tests covering dynamic species token
  expansion and forest-type-conditioned rule selection.
- Switched legacy runner default to require config-driven TIPSY rules for TSA processing; missing
  config now fails fast with explicit guidance, while `FEMIC_TIPSY_USE_LEGACY=1` preserves an
  opt-in escape hatch to legacy in-code rule dispatch during transition.
- Added `femic tipsy validate` CLI command for preflight validation of TSA YAML handoff files
  (all discovered configs, or explicit `--tsa` subset), including missing-file detection and schema
  checks via shared `tipsy_config` loader/validator helpers.
- Reduced notebook-script global coupling at the 00/01a/01b stage boundary:
  `01a_run-tsa.run_tsa(...)` and `01b_run-tsa.run_tsa(...)` now take explicit runtime arguments
  (`tsa`, and for 01a also `stratum_col`, `f`, `si_levels`, `vdyp_out_cache`, fit/wrap hooks),
  and `00_data-prep.py` now passes these values directly instead of setting module globals.
- Replaced broad `module.__dict__.update(globals())` handoff with explicit, validated context
  binding via `femic.pipeline.legacy_context.bind_legacy_module_context(...)` and scoped symbol
  lists (`RUN_01A_CONTEXT_SYMBOLS`, `RUN_01B_CONTEXT_SYMBOLS`) so 01a/01b receive only required
  shared notebook-state dependencies.
- Extracted VDYP batch prep/run/import orchestration into
  `femic.pipeline.vdyp_stage.execute_vdyp_batch(...)` (input CSV staging, subprocess execution,
  stdout/stderr artifact appends, parse/error/status event logging), and rewired `01a_run-tsa.py`
  `run_vdyp` internals to call this shared stage helper.
- Added focused unit tests for the VDYP stage helper (`tests/test_vdyp_stage.py`) covering success,
  parse-error, and timeout paths with deterministic fake runner/importer hooks.
- Extracted bootstrap-dispatch orchestration from `01a_run-tsa.py` into
  `femic.pipeline.vdyp_stage.execute_bootstrap_vdyp_runs(...)` (per stratum+SI context assembly,
  dispatch/dispatch_error logging, and nested result-table accumulation), and rewired the
  `force_run_vdyp` branch to consume this helper.
- Expanded `tests/test_vdyp_stage.py` with bootstrap orchestration coverage for success and
  dispatch-error logging behavior.
- Extracted curve-smoothing dispatch orchestration from `01a_run-tsa.py` into
  `femic.pipeline.vdyp_stage.execute_curve_smoothing_runs(...)`, centralizing per stratum+SI
  missing-output warnings, `process_vdyp_out(...)` invocation, and curve-context event emission.
- Rewired `01a_run-tsa.py` to consume `execute_curve_smoothing_runs(...)` and build
  `vdyp_smoothxy` tables from returned smoothed-curve records before writing
  `vdyp_curves_smooth-tsa{tsa}.feather`.
- Expanded `tests/test_vdyp_stage.py` with curve-smoothing orchestration coverage, including
  missing-VDYP warning logging and kwarg-override forwarding into `process_vdyp_out(...)`.
- Extracted legacy VDYP overlay plotting into
  `femic.pipeline.vdyp_stage.plot_curve_overlays(...)`, so `01a_run-tsa.py` now delegates the
  per-stratum plotting loop to a shared stage helper while preserving existing plot output shape.
- Reduced required 01a legacy context symbols by removing no-longer-used globals
  (`Path`, `curve_fit`, `shlex`, `subprocess`) from `RUN_01A_CONTEXT_SYMBOLS`.
- Added `tests/test_vdyp_stage.py` coverage for overlay plotting orchestration
  (`plot_curve_overlays`) to assert expected plotting calls and axis/legend handling.
- Extracted the remaining smooth-curve table assembly/write path into
  `femic.pipeline.vdyp_stage.build_smoothed_curve_table(...)`, so `01a_run-tsa.py` now delegates
  smoothed-curve DataFrame construction + optional feather persistence through a shared stage helper.
- Removed additional stale 01a legacy context symbols after extraction (`_curve_fit`, `wraps`)
  from `RUN_01A_CONTEXT_SYMBOLS`.
- Expanded `tests/test_vdyp_stage.py` with `build_smoothed_curve_table(...)` coverage to verify
  row assembly and output-path write invocation behavior.
- Extracted VDYP result-resolution branching (`force_run`, per-TSA cache load, combined-cache
  fallback, bootstrap-and-persist) into
  `femic.pipeline.vdyp_stage.load_or_build_vdyp_results_tsa(...)`, and rewired `01a_run-tsa.py`
  to delegate this cache/bootstrap decision path through the shared stage helper.
- Reduced required 01a legacy context symbols again by removing stale `pickle` dependency from
  `RUN_01A_CONTEXT_SYMBOLS`.
- Expanded `tests/test_vdyp_stage.py` with coverage for `load_or_build_vdyp_results_tsa(...)`
  across force-run, TSA-cache, combined-cache, and compat-loader fallback branches.
- Extracted VDYP polygon/layer table loading into
  `femic.pipeline.vdyp_stage.load_vdyp_input_tables(...)` and rewired `01a_run-tsa.py` to use this
  helper instead of inline source/feather branch code.
- Reduced required 01a legacy context symbols again by removing stale `gpd` dependency from
  `RUN_01A_CONTEXT_SYMBOLS`.
- Expanded `tests/test_vdyp_stage.py` with `load_vdyp_input_tables(...)` coverage for both feather
  cache loads and source-geodatabase load+persist behavior.
- Added `femic.pipeline.vdyp_stage.build_curve_fit_adapter(...)` and rewired `01a_run-tsa.py` to
  construct a local `curve_fit` wrapper from `curve_fit_impl` so legacy `maxfev` kwargs map to
  modern SciPy `max_nfev` without per-call inline wrapper logic.
- Removed obsolete `wraps_impl` plumbing from `01a_run-tsa.run_tsa(...)` and the
  `00_data-prep.py` caller now that curve-fit adaptation is centralized in the stage helper.
- Expanded `tests/test_vdyp_stage.py` with `build_curve_fit_adapter(...)` coverage for both
  `maxfev -> max_nfev` conversion and passthrough when `max_nfev` is already supplied.
- Reduced additional 01a global-state coupling by extending `01a_run-tsa.run_tsa(...)` with
  explicit path/export inputs (`vdyp_results_*`, `vdyp_input_pandl_path`,
  `vdyp_{ply,lyr}_feather_path`, `tipsy_params_columns`, `tipsy_params_path_prefix`) and wiring
  `00_data-prep.py` to pass them directly.
- Trimmed `RUN_01A_CONTEXT_SYMBOLS` after this signature change by removing no-longer-needed path
  and TIPSY-export globals (`vdyp_input_pandl_path`, `vdyp_{ply,lyr}_feather_path`,
  `vdyp_results_*`, `tipsy_params_columns`, `tipsy_params_path_prefix`).
- Extended `01a_run-tsa.run_tsa(...)` again to take the mutable per-run data structures
  (`results`, `vdyp_results`, `vdyp_curves_smooth`, `scsi_au`, `au_scsi`, `tipsy_params`) and
  lookup inputs (`si_levelquants`, `species_list`,
  `vdyp_curves_smooth_tsa_feather_path_prefix`) explicitly from `00_data-prep.py`.
- Trimmed `RUN_01A_CONTEXT_SYMBOLS` further after this handoff update, leaving only baseline
  runtime/module helpers (`np`, `pd`, `plt`, `sns`, `os`, `operator`, `itertools`, `distance`,
  `kwarg_overrides`, `_femic_resume_effective`) instead of dataset/state payload globals.
- Converted `01b_run-tsa.run_tsa(...)` to explicit runtime inputs
  (`results`, `au_scsi`, `tipsy_curves`, `vdyp_curves_smooth`) and updated `00_data-prep.py` to
  pass these directly instead of relying on injected module globals.
- Removed all remaining 01b context injection requirements by setting
  `RUN_01B_CONTEXT_SYMBOLS` to an empty tuple and localizing 01b plotting imports
  (`matplotlib.pyplot`, `seaborn`) inside the function.
- Extracted TIPSY export assembly/writes from `01a_run-tsa.py` into reusable
  `femic.pipeline.tipsy` helpers (`build_tipsy_input_table`, `write_tipsy_input_exports`) and
  rewired the legacy script to delegate xlsx/dat output generation through these helpers.
- Expanded `tests/test_tipsy.py` with coverage for new TIPSY export helpers: row/column assembly,
  empty-input failure behavior, and xlsx/dat artifact writes.
- Extracted config-vs-legacy TIPSY rule-selection into
  `femic.pipeline.tipsy_config.resolve_tipsy_param_builder(...)` and rewired `01a_run-tsa.py` to
  call this helper for builder/message resolution.
- Expanded `tests/test_tipsy_config.py` with resolver coverage for config-preferred, forced-legacy,
  and missing-config error paths.
- Localized remaining non-numeric helper imports used by `01a_run-tsa.py` (`distance`,
  `itertools`, `operator`, `os`) inside `run_tsa(...)`, removing these dependencies on injected
  legacy module globals.
- Trimmed `RUN_01A_CONTEXT_SYMBOLS` again after import localization; 01a context binding now
  requires only `_femic_resume_effective`, `kwarg_overrides`, and plotting/dataframe modules
  (`np`, `pd`, `plt`, `sns`).
- Extracted the TIPSY candidate-selection and AU-assignment loop from `01a_run-tsa.py` into
  `femic.pipeline.tipsy.build_tipsy_params_for_tsa(...)`, including eligibility filtering, warning
  event emission, and final `scsi_au`/`au_scsi`/`tipsy_params` map construction.
- Rewired `01a_run-tsa.run_tsa(...)` to consume `build_tipsy_params_for_tsa(...)` and pass
  explicit runtime flags (`resume_effective`, `force_run_vdyp`, `kwarg_overrides_for_tsa`) from
  `00_data-prep.py` instead of reading injected globals.
- Localized `numpy`/`pandas`/`matplotlib`/`seaborn` imports inside `01a_run-tsa.run_tsa(...)` and
  trimmed `RUN_01A_CONTEXT_SYMBOLS` to an empty tuple; both 01a and 01b now run without required
  legacy context payload injection.
- Expanded `tests/test_tipsy.py` with orchestration coverage for
  `build_tipsy_params_for_tsa(...)` (success mapping, missing-VDYP warning, no-species warning).
- Extracted inline legacy TSA rule builders/exclusion setup from `01a_run-tsa.py` into new
  `femic.pipeline.tipsy_legacy` module (`build_tipsy_exclusion`,
  `get_legacy_tipsy_builders`, `tipsy_params_tsa08/16/24/40/41`) and rewired 01a to consume this
  shared seam.
- Added `tests/test_tipsy_legacy.py` coverage for legacy builder-dispatch keys, exclusion-map keys,
  and baseline TSA08 output fields.
- Added runtime-wiring regression tests in `tests/test_legacy_context.py` asserting
  `RUN_01A_CONTEXT_SYMBOLS == ()` and `RUN_01B_CONTEXT_SYMBOLS == ()`, plus empty-required-symbol
  binding behavior.
- Removed no-op legacy context binding calls from `00_data-prep.py` now that both
  `RUN_01A_CONTEXT_SYMBOLS` and `RUN_01B_CONTEXT_SYMBOLS` are empty; 01a/01b module loading now
  proceeds directly to explicit `run_tsa(...)` invocation.
- Removed the inactive `if 0:` legacy TIPSY export branch from `01a_run-tsa.py` (unused duplicate
  xlsx assembly path) to keep only the active helper-driven export flow.
- Pruned deprecated legacy-context re-exports from `femic.pipeline.__init__` now that context
  injection is no longer part of the runtime orchestration surface.
- Removed additional low-risk inactive `if 0:` debug/reload blocks from `00_data-prep.py`
  (checkpoint rollbacks/manual cache toggles/legacy shp export snippets) to reduce notebook-era
  dead-code noise without altering active runtime branches.
- Added `tests/test_legacy_orchestration_wiring.py` AST regression checks to lock explicit
  `_run01a_module.run_tsa(...)` and `_run01b_module.run_tsa(...)` keyword handoff surfaces and
  assert no `bind_legacy_module_context(...)` call remains in `00_data-prep.py`.
- Removed the final inactive `if 0:` notebook-era debug blocks from `00_data-prep.py` (dormant
  legacy `process_vdyp_out(...)` sandbox and manual TSA smoothing loop), leaving only active
  orchestration code paths.
- Expanded `tests/test_tipsy_legacy.py` with a TSA24 regression case that verifies BEC-dependent
  legacy rule branching (`SBS` vs `ESSF`) for a fir-leading stand.
- Extracted default VDYP curve-smoothing kwarg overrides into
  `femic.pipeline.vdyp_overrides` (`DEFAULT_VDYP_KWARG_OVERRIDES`,
  `vdyp_kwarg_overrides_for_tsa(...)`) to remove hardcoded override dicts from
  `00_data-prep.py` and centralize override defaults in a reusable pipeline seam.
- Updated `01a_run-tsa.run_tsa(...)` to resolve override defaults internally when
  `kwarg_overrides_for_tsa` is not provided; `00_data-prep.py` now passes `None` explicitly.
- Added regression coverage for the new override helper (`tests/test_vdyp_overrides.py`) plus AST
  wiring coverage asserting the 00->01a handoff uses internal defaults
  (`kwarg_overrides_for_tsa=None`).
- Rewired `01a_run-tsa.py` to consume `femic.pipeline.tsa.target_nstrata_for(...)` instead of an
  inline TSA->target-strata dict, reducing notebook-era duplicated constants.
- Added shared `femic.pipeline.tsa.MIN_STANDCOUNT` and updated 01a strata filtering/tests to consume
  this constant instead of hardcoded local values.
- Removed additional inline bootstrap tuning constants from `01a_run-tsa.py` by relying on
  `execute_bootstrap_vdyp_runs(...)` defaults for `half_rel_ci`, `nsamples_c1`, and `ipp_mode`.
- Added `tests/test_legacy_01a_structure.py` AST guardrails that lock 01a structural cleanup:
  `run_tsa(...)` must call `target_nstrata_for(...)`, must not reintroduce an inline
  `target_nstrata` dict assignment, and must not locally reassign `si_levels`.
- Extracted 01a strata summarization logic into `femic.pipeline.tsa.build_strata_summary(...)`
  (target-strata selection, site-index/crown-closure/coverage aggregates, stand-count filtering,
  and `median_si` enrichment), reducing notebook-era inline grouping logic in `run_tsa(...)`.
- Rewired `01a_run-tsa.py` to consume `build_strata_summary(...)` for stratum candidate table
  assembly and IQR reporting.
- Expanded `tests/test_pipeline_helpers.py` with deterministic `build_strata_summary(...)` coverage
  (aggregate outputs + validation error path), and updated `tests/test_legacy_01a_structure.py`
  guardrails to assert `run_tsa(...)` calls the extracted helper seam.
- Extracted 01a lexmatch alias resolution into
  `femic.pipeline.tsa.build_stratum_lexmatch_alias_map(...)`, moving Levenshtein tie-break
  selection logic (distance + relative-area tiebreak) out of inline notebook-era code.
- Rewired `01a_run-tsa.py` to consume `build_stratum_lexmatch_alias_map(...)` when mapping
  non-selected strata onto selected strata for downstream fitting.
- Expanded tests with deterministic alias-map coverage in `tests/test_pipeline_helpers.py`, and
  added AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls the new
  lexmatch helper seam.
- Extracted the inline 01a stratum-fitting block into
  `femic.pipeline.vdyp_stage.fit_stratum_curves(...)`, centralizing per-SI quantile filtering,
  species-share derivation, curve-fit execution/error handling, and optional plot emission in a
  reusable stage seam.
- Rewired `01a_run-tsa.py` to call `fit_stratum_curves(...)` during pre-VDYP stratum compilation,
  removing the nested `fit_stratum(...)` function definition from `run_tsa(...)`.
- Expanded `tests/test_vdyp_stage.py` with focused `fit_stratum_curves(...)` coverage (successful
  species payload output and curve-fit error skip/log behavior), and extended
  `tests/test_legacy_01a_structure.py` guardrails to assert 01a calls the stage helper and no
  longer defines a nested `fit_stratum`.
- Extracted stratum-compilation loop orchestration into
  `femic.pipeline.vdyp_stage.compile_strata_fit_results(...)`, so 01a now delegates per-stratum
  iteration/message/result assembly through a reusable stage helper.
- Rewired `01a_run-tsa.py` pre-VDYP compilation path to call
  `compile_strata_fit_results(...)` with the extracted `fit_stratum_curves(...)` seam.
- Expanded `tests/test_vdyp_stage.py` with deterministic compile-loop helper coverage, and extended
  `tests/test_legacy_01a_structure.py` guardrails to assert 01a calls
  `compile_strata_fit_results(...)`.
- Extracted VDYP sampling-mode orchestration into
  `femic.pipeline.vdyp_stage.run_vdyp_sampling(...)`, centralizing the `auto`/`all`/fixed sample
  flow, cache-hit handling, and gap-fill loop decision logic previously embedded in 01a.
- Rewired `01a_run-tsa.py` `run_vdyp(...)` to delegate sampling decisions through
  `run_vdyp_sampling(...)` while keeping batch execution/logging in its existing `_run_vdyp(...)`
  closure.
- Expanded `tests/test_vdyp_stage.py` with focused `run_vdyp_sampling(...)` coverage
  (auto-small-sample path, auto gap-fill phase path, and invalid-mode assertion), and extended
  `tests/test_legacy_01a_structure.py` guardrails to assert 01a calls
  `run_vdyp_sampling(...)`.
- Extracted the nested 01a `run_vdyp(...)` wrapper into
  `femic.pipeline.vdyp_stage.run_vdyp_for_stratum(...)`, centralizing per-stratum VDYP runtime
  preflight checks (wine/bin/params), default log-path resolution, run-event logging, batch
  execution dispatch, and sampling orchestration handoff.
- Rewired `01a_run-tsa.py` bootstrap execution to call `run_vdyp_for_stratum(...)` directly and
  removed the nested `run_vdyp` and `_tsa_log_path` definitions from `run_tsa(...)`.
- Expanded `tests/test_vdyp_stage.py` with `run_vdyp_for_stratum(...)` coverage and updated
  `tests/test_legacy_01a_structure.py` guardrails to assert 01a no longer calls
  `run_vdyp_sampling(...)` directly and no longer defines a nested `run_vdyp`.
- Queued next extraction slice: move the remaining 01a bootstrap-callable wiring lambda into a
  dedicated stage helper so `run_tsa(...)` only passes explicit orchestration inputs without
  inline closure assembly.
- Added `femic.pipeline.vdyp_stage.build_run_vdyp_for_stratum_runner(...)`, a reusable helper that
  binds per-TSA runtime context (`tsa`, `run_id`, VDYP tables, fit hooks, and run-log paths) into
  a `run_vdyp_fn(sample_table, **kwargs)` callable compatible with
  `execute_bootstrap_vdyp_runs(...)`.
- Rewired `01a_run-tsa.py` bootstrap flow to build `run_vdyp_fn` via
  `build_run_vdyp_for_stratum_runner(...)`, removing the remaining inline lambda that assembled
  `run_vdyp_for_stratum(...)` kwargs inside `run_tsa(...)`.
- Expanded `tests/test_vdyp_stage.py` with binding/forwarding coverage for
  `build_run_vdyp_for_stratum_runner(...)`, and updated
  `tests/test_legacy_01a_structure.py` guardrails to assert 01a calls the builder helper and no
  longer calls `run_vdyp_for_stratum(...)` directly.
- Queued next extraction slice: remove the remaining inline `run_bootstrap_fn=lambda: ...`
  assembly in `01a_run-tsa.py` by introducing a dedicated stage helper for per-TSA bootstrap
  callback construction.
- Added `femic.pipeline.vdyp_stage.build_bootstrap_vdyp_results_runner(...)`, a reusable helper
  that binds per-TSA bootstrap dispatch inputs (`tsa`, `run_id`, results payload, SI levels, log
  sink, `run_vdyp_fn`, and cache map) into a zero-arg callback compatible with
  `load_or_build_vdyp_results_tsa(...)`.
- Rewired `01a_run-tsa.py` to pass `run_bootstrap_fn` built by
  `build_bootstrap_vdyp_results_runner(...)`, removing the remaining inline
  `run_bootstrap_fn=lambda: execute_bootstrap_vdyp_runs(...)` closure assembly.
- Expanded `tests/test_vdyp_stage.py` with binding/forwarding coverage for
  `build_bootstrap_vdyp_results_runner(...)`, and updated
  `tests/test_legacy_01a_structure.py` guardrails to assert 01a calls the builder helper and does
  not pass an inline lambda to `run_bootstrap_fn`.
- Queued next extraction slice: move the remaining inline `compile_one_fn=lambda: ...` assembly in
  pre-VDYP stratum compilation into a dedicated stage helper so 01a no longer builds fit-call
  closures inline.
- Added `femic.pipeline.vdyp_stage.build_fit_stratum_curves_runner(...)`, a reusable helper that
  binds per-TSA stratum-fit context into `compile_one_fn(stratumi, sc)` callbacks for
  `compile_strata_fit_results(...)`.
- Rewired `01a_run-tsa.py` to build and pass `compile_one_fn` via
  `build_fit_stratum_curves_runner(...)`, removing inline fit-call closure assembly in the pre-VDYP
  compilation path.
- Expanded `tests/test_vdyp_stage.py` with fit-runner binding coverage and updated
  `tests/test_legacy_01a_structure.py` guardrails so 01a must call the builder helper and must not
  pass inline lambdas to `compile_one_fn`.
- Extracted legacy notebook fit functions (`fit_func1`, `fit_func1_bounds_func`, `fit_func2`,
  `fit_func2_bounds_func`) from `01a_run-tsa.py` into `femic.pipeline.vdyp_curves`
  (`legacy_fit_func1`, `legacy_fit_func1_bounds_func`, `legacy_fit_func2`,
  `legacy_fit_func2_bounds_func`), and rewired 01a to consume these shared helpers.
- Expanded `tests/test_vdyp_curves.py` with deterministic coverage for legacy fit-function outputs
  and bounds, and added AST guardrails asserting 01a no longer defines nested legacy fit functions.
- Queued next extraction slice: remove the final nested `match_stratum(...)` function definition in
  `01a_run-tsa.py` by moving alias-application logic into a reusable TSA helper.
- Added `femic.pipeline.tsa.apply_stratum_alias_map(...)` to encapsulate selected-strata retention
  plus alias fallback assignment for `*_matched` stratum columns.
- Rewired `01a_run-tsa.py` to call `apply_stratum_alias_map(...)` for stratum matching, removing
  the final nested helper definition (`match_stratum`) from `run_tsa(...)`.
- Expanded `tests/test_pipeline_helpers.py` with deterministic alias-application coverage and added
  AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls the helper and has no
  nested `match_stratum`.
- `01a_run-tsa.run_tsa(...)` now has zero nested function definitions; remaining extraction focus is
  reducing inline notebook-style constant/plot configuration blocks into reusable stage helpers.
- Queued next extraction slice: move curve-smoothing plot setup constants
  (`palette_flavours`/palette/alpha defaults) from `01a_run-tsa.py` into a shared stage helper.
- Added `femic.pipeline.vdyp_stage.CurveSmoothingPlotConfig` and
  `build_curve_smoothing_plot_config(...)` to centralize legacy curve-smoothing plot defaults
  (plot toggle, `figsize`, palette setup, `palette_flavours`, `alphas`) behind a shared stage seam.
- Rewired `01a_run-tsa.py` curve-smoothing overlay path to call
  `build_curve_smoothing_plot_config(...)` and consume the returned config instead of defining
  inline plot/palette constants.
- Expanded `tests/test_vdyp_stage.py` with deterministic defaults coverage for
  `build_curve_smoothing_plot_config(...)`, and added AST guardrails in
  `tests/test_legacy_01a_structure.py` asserting 01a calls this helper and no longer assigns
  inline smoothing `palette_flavours`/`alphas` constants.
- Queued next extraction slice: remove dead legacy `fit_func2`/`fit_func2_bounds_func` local
  bindings from `01a_run-tsa.py` now that these values are no longer consumed by any active stage.
- Removed dead `legacy_fit_func2`/`legacy_fit_func2_bounds_func` imports and local
  `fit_func2`/`fit_func2_bounds_func` assignments from `01a_run-tsa.py`; these values were no
  longer used by any active stage path after prior smoothing-stage extraction.
- Added `tests/test_legacy_01a_structure.py` guardrails asserting `run_tsa(...)` no longer assigns
  local legacy fit2 bindings.
- Queued next extraction slice: move inline TIPSY staging defaults
  (`min_operable_years`, `si_iqrlo_quantile`, local `verbose`) into a shared helper seam so 01a no
  longer embeds these constants directly.
- Removed inline TIPSY staging constant assignments from `01a_run-tsa.py`
  (`min_operable_years`, `si_iqrlo_quantile`, local `verbose`) and now rely on
  `build_tipsy_params_for_tsa(...)` shared default thresholds.
- Expanded `tests/test_legacy_01a_structure.py` with guardrails asserting 01a no longer assigns
  these constants inline and no longer overrides corresponding
  `build_tipsy_params_for_tsa(...)` keyword defaults.
- Queued next extraction slice: move overlay axis-bound constants (`xlim`, `ylim`) passed to
  `plot_curve_overlays(...)` out of `01a_run-tsa.py` into a shared stage/default helper.
- Extended `CurveSmoothingPlotConfig` / `build_curve_smoothing_plot_config(...)` to include overlay
  axis defaults (`xlim`, `ylim`) so smoothing overlay bounds are configured in one shared stage
  seam.
- Rewired `01a_run-tsa.py` `plot_curve_overlays(...)` call to consume
  `smooth_plot_cfg.xlim`/`smooth_plot_cfg.ylim` instead of inline tuple literals.
- Expanded `tests/test_vdyp_stage.py` defaults coverage for new axis config fields and added
  `tests/test_legacy_01a_structure.py` AST guardrails asserting overlay axes are sourced from
  `smooth_plot_cfg`.
- Queued next extraction slice: move stratum-distribution plot constants (`bw`, `linewidth`,
  `inner`, `width`, `cut`, `alpha`) from `01a_run-tsa.py` into a shared plotting helper/config
  seam.
- Added `StrataDistributionPlotConfig` and `build_strata_distribution_plot_config(...)` in
  `femic.pipeline.plots` to centralize default plotting constants for 01a stratum-distribution
  diagnostics.
- Rewired the 01a stratum-distribution plotting block to consume
  `build_strata_distribution_plot_config(...)` values instead of inline constants.
- Expanded `tests/test_pipeline_helpers.py` with defaults coverage for the new plot-config helper,
  and added AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls the helper
  and no longer assigns inline strata-plot constants.
- Queued next extraction slice: replace inline strata plot output path literals in `01a_run-tsa.py`
  with `femic.pipeline.plots.strata_plot_paths(...)` helper output.
- Rewired `01a_run-tsa.py` strata diagnostic plot output writes to call
  `femic.pipeline.plots.strata_plot_paths(...)` and save to returned PDF/PNG paths instead of
  inline `"plots/strata-tsa%s.*"` string literals.
- Added AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls
  `strata_plot_paths(...)` and no longer embeds inline strata plot output path literals.
- Queued next extraction slice: move inline stratum-label ordering toggle (`sort_lex` branch) from
  `01a_run-tsa.py` into a reusable TSA/plot helper seam.
- Added `femic.pipeline.plots.resolve_strata_plot_ordering(...)` to centralize abundance-vs-lexic
  ordering for stratum distribution plots.
- Rewired `01a_run-tsa.py` to call `resolve_strata_plot_ordering(...)` and removed the inline
  `sort_lex` branch and local ordering assembly.
- Expanded `tests/test_pipeline_helpers.py` with deterministic ordering coverage for default
  (abundance) and lexical modes, and added AST guardrails in
  `tests/test_legacy_01a_structure.py` asserting 01a calls the helper and no longer assigns local
  `sort_lex`.
- Queued next extraction slice: remove residual inline notebook-style diagnostic plot calls in early
  01a flow (`site_index_median` histogram + scatter) into a reusable plotting helper.
- Added `femic.pipeline.plots.plot_strata_site_index_diagnostics(...)` to encapsulate early 01a
  stratum diagnostics plotting (`site_index_median` histogram + abundance-vs-SI scatter).
- Rewired `01a_run-tsa.py` to call `plot_strata_site_index_diagnostics(...)` and removed direct
  inline histogram/scatter plotting calls from `run_tsa(...)`.
- Expanded `tests/test_pipeline_helpers.py` with deterministic behavior coverage for the new
  diagnostics helper and added AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a
  calls the helper and no longer invokes direct `plt.scatter(...)` for this stage.
- Queued next extraction slice: centralize stratum-distribution/ordering plotting orchestration
  (bar+violin block) into a dedicated shared helper to further shrink inline plotting in 01a.
- Added `femic.pipeline.plots.render_strata_distribution_plot(...)` to encapsulate the stratum
  distribution diagnostics rendering workflow (barplot + violinplot + labels + xlim + PDF/PNG
  writes via helper-managed paths).
- Rewired `01a_run-tsa.py` to call `render_strata_distribution_plot(...)`, removing direct inline
  seaborn bar/violin calls and save-path plumbing from `run_tsa(...)`.
- Expanded `tests/test_pipeline_helpers.py` with deterministic rendering-helper coverage and added
  AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls the rendering helper
  and no longer performs direct `sns.barplot(...)`/`sns.violinplot(...)` calls in this stage.
- Queued next extraction slice: trim now-unused local imports from `01a_run-tsa.py` (notably early
  `seaborn` direct plotting dependencies that have moved behind helper seams) and lock with
  guardrails.
- Added `femic.pipeline.tipsy_config.resolve_tipsy_runtime_options(...)` to centralize
  `FEMIC_TIPSY_CONFIG_DIR`/`FEMIC_TIPSY_USE_LEGACY` environment resolution for TIPSY runtime
  behavior.
- Rewired `01a_run-tsa.py` to call `resolve_tipsy_runtime_options(...)` instead of reading
  `os.environ` directly for TIPSY config/legacy flags.
- Expanded `tests/test_tipsy_config.py` with defaults/override coverage for
  `resolve_tipsy_runtime_options(...)` and added AST guardrails in
  `tests/test_legacy_01a_structure.py` asserting 01a no longer reads `os.environ` directly for this
  stage.
- Queued next extraction slice: begin consolidating remaining inline 01a run-stage constants
  (`fit_rawdata`, `min_age`, `agg_type`, `verbose`, `plot`) into dedicated stage/config helpers.
- Added `StratumFitRunConfig` and `build_stratum_fit_run_config(...)` in
  `femic.pipeline.vdyp_stage` to centralize pre-VDYP stratum fit-stage defaults
  (`fit_rawdata`, `min_age`, `agg_type`, `plot`, `verbose`, `figsize`, `xlim`, `ylim`).
- Rewired `01a_run-tsa.py` pre-VDYP fit compilation path to consume
  `build_stratum_fit_run_config(...)` instead of assigning these constants inline.
- Expanded `tests/test_vdyp_stage.py` with defaults coverage for the new fit-stage config helper
  and added AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls the helper
  and no longer assigns inline stratum fit-stage constants.
- Queued next extraction slice: centralize pre-VDYP checkpoint filename construction
  (`"./data/vdyp_prep-tsa%s.pkl"`) into a shared path helper seam.
- Added `femic.pipeline.pre_vdyp.pre_vdyp_checkpoint_path(...)` to centralize per-TSA pre-VDYP
  checkpoint path construction.
- Rewired `01a_run-tsa.py` to call `pre_vdyp_checkpoint_path(...)` instead of constructing
  `"./data/vdyp_prep-tsa%s.pkl"` inline.
- Expanded `tests/test_pre_vdyp.py` with path-helper coverage (default dir + TSA zero-padding) and
  added AST guardrails in `tests/test_legacy_01a_structure.py` asserting 01a calls the helper and
  no longer embeds `vdyp_prep-tsa` literals.
- Queued next extraction slice: centralize remaining inline 01a path templates
  (`vdyp_results_tsa_pickle_path`, `vdyp_curves_smooth_tsa_feather_path`) into dedicated shared
  path helpers.
- Transcript review checkpoint (2026-03-02): the legacy notebook-to-script debugging tranche is
  complete (00/01a/01b script entrypoints, VDYP/Wine diagnostics hardening, config-driven TIPSY
  handoff, and broad 01a helper extraction); active work remains in Phase 2 (`P2.1b`/`P2.2`) to
  remove residual inline globals/path templates and tighten stage orchestration seams.
- Planned execution sequence after transcript review:
  1) extract remaining 01a inline path templates into shared helpers, 2) trim stale 01a imports and
  dependency injection leftovers, 3) finish converting any residual inline stage logic to helper
  calls with AST guardrails, 4) run full validation gate and capture a new end-to-end TSA debug run
  summary in changelog notes.
- Added `femic.pipeline.vdyp.build_vdyp_cache_paths(...)` to centralize per-TSA cache artifact path
  templates for `vdyp_results-tsa*.pkl` and `vdyp_curves_smooth-tsa*.feather`.
- Rewired `01a_run-tsa.py` to call `build_vdyp_cache_paths(...)` instead of constructing per-TSA
  cache paths inline via string templates.
- Expanded tests with helper and guardrail coverage:
  `tests/test_pipeline_helpers.py` now checks `build_vdyp_cache_paths(...)`, and
  `tests/test_legacy_01a_structure.py` now asserts 01a calls the helper and no longer assigns
  inline `%`-formatted cache-path templates.
- Full validation gate passes after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (154 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: trim now-stale local imports and remaining dependency handoff
  plumbing in `01a_run-tsa.py` after path-template helper extraction.
- Removed local `os` dependency from `01a_run-tsa.py` path checks by switching to
  `Path(...).is_file()` for pre-VDYP checkpoint and smoothed-curve cache detection.
- Added AST guardrail coverage in `tests/test_legacy_01a_structure.py` asserting `run_tsa(...)`
  does not import `os` locally for this path-check stage.
- Queued next extraction slice: reduce remaining 00->01a path handoff plumbing by passing a single
  resolved VDYP cache-path payload instead of separate path-prefix arguments.
- Queued execution batch (post-checklist refresh):
  1) implement a `vdyp_cache_paths` payload handoff from `00_data-prep.py` to `01a_run-tsa.py`,
  2) reduce `run_tsa(...)` argument surface by grouping remaining path/runtime plumbing into a
  typed config payload,
  3) extract 00_data-prep 01a/01b module-loader/caller loops into shared orchestration helper(s).
- Added `Legacy01ARuntimeConfig` (`femic.pipeline.legacy_runtime`) and rewired
  `01a_run-tsa.run_tsa(...)` to consume this typed runtime payload instead of discrete
  path/runtime args (`resume_effective`, `force_run_vdyp`, cache path prefixes, tipsy export paths,
  and optional fit/cache hooks).
- Collapsed 00->01a cache-path handoff to one resolved payload (`vdyp_cache_paths`) built in
  `00_data-prep.py` and passed through `Legacy01ARuntimeConfig`.
- Added shared orchestration helpers in `femic.pipeline.stages`:
  `load_legacy_module(...)` and `run_legacy_tsa_loop(...)`.
- Rewired 00_data-prep 01a/01b execution loops to use shared loader/loop helpers (instead of
  inline `importlib.util` plumbing and duplicated loop scaffolding).
- Added script-run fallback in `00_data-prep.py` to prepend `src/` on `ModuleNotFoundError` so
  direct `python 00_data-prep.py` execution can still import `femic.pipeline` helpers.
- Expanded guardrails/tests:
  `tests/test_legacy_orchestration_wiring.py` now validates runtime-config handoff plus shared
  loader/loop helper usage, `tests/test_pipeline_stages.py` now covers
  `load_legacy_module(...)`/`run_legacy_tsa_loop(...)`, and
  `tests/test_legacy_01a_structure.py` asserts 01a reads cache paths from `runtime_config`.
- Queued next extraction slice: continue `P2.2` by moving remaining 00_data-prep orchestration
  logic around stage setup/checkpoints into reusable stage helpers so the top-level script becomes a
  thin workflow shell.
- Added stage setup helpers in `femic.pipeline.stages`:
  `initialize_legacy_tsa_stage_state(...)`, `prepare_tsa_index(...)`, and
  `should_skip_if_outputs_exist(...)`.
- Added `femic.pipeline.legacy_runtime.build_legacy_01a_runtime_config(...)` so 00_data-prep no
  longer assembles the 01a runtime payload inline.
- Rewired `00_data-prep.py` to consume these helpers for state-map initialization, TSA-index
  preparation, resume-skip checks, and 01a runtime-config assembly.
- Expanded tests to cover new setup/runtime helpers and wiring:
  `tests/test_pipeline_stages.py` now covers helper behavior and runtime-config cache path build,
  and `tests/test_legacy_orchestration_wiring.py` asserts 00_data-prep calls the new setup/runtime
  helper seams.
- Queued next extraction slice: continue thinning 00_data-prep by extracting remaining post-01b
  bundle/table orchestration and path wiring into shared helpers under `femic.pipeline`.
- Added new bundle orchestration helpers in `femic.pipeline.bundle`:
  `resolve_bundle_paths(...)`, `bundle_tables_ready(...)`, `load_bundle_tables(...)`,
  `write_bundle_tables(...)`, and `ensure_scsi_au_from_table(...)`.
- Rewired 00_data-prep post-01b bundle block to use shared bundle helpers for path wiring,
  resume-time table loading, CSV persistence, and `scsi_au` backfill.
- Added focused bundle helper tests in `tests/test_bundle.py` and expanded orchestration AST
  guardrails in `tests/test_legacy_orchestration_wiring.py` to assert 00_data-prep calls bundle
  helper seams.
- Queued next extraction slice: move the heavy AU/curve table assembly loop (currently inline in
  00_data-prep) into a reusable pipeline helper with deterministic unit coverage.
- Added `build_bundle_tables_from_curves(...)` and `BundleAssemblyResult` in
  `femic.pipeline.bundle` to extract the heavy AU/curve table assembly loop from 00_data-prep.
- Rewired 00_data-prep to consume `build_bundle_tables_from_curves(...)` and retain warning summary
  behavior for missing AU mappings using returned diagnostics.
- Expanded `tests/test_bundle.py` with deterministic coverage for managed/unmanaged curve assembly
  and missing-mapping diagnostics, and extended orchestration guardrails to assert
  `build_bundle_tables_from_curves(...)` usage.
- Queued next extraction slice: continue P2.2 by moving residual stratum-matching + SI-level
  assignment orchestration (post-bundle stage) into reusable helper seams.
- Added residual post-bundle strata helpers in `femic.pipeline.tsa`:
  `assign_stratum_matches_from_au_table(...)` and
  `assign_si_levels_from_stratum_quantiles(...)`.
- Rewired `00_data-prep.py` post-bundle stage to call these helpers instead of maintaining inline
  stratum-matching and SI-level assignment loops.
- Expanded helper/wiring tests:
  `tests/test_pipeline_helpers.py` now covers both new TSA helpers, and
  `tests/test_legacy_orchestration_wiring.py` guardrails now assert
  `assign_stratum_matches_from_au_table(...)` and
  `assign_si_levels_from_stratum_quantiles(...)` seam usage.
- Queued next extraction slice: continue thinning 00_data-prep by extracting AU assignment + null
  diagnostics (`_lookup_scsi_au`, `au_from_scsi`, missing/null summaries) into reusable helper(s).
- Added AU-assignment helper seams in `femic.pipeline.tsa`:
  `lookup_scsi_au_base(...)`, `assign_au_ids_from_scsi(...)`,
  `summarize_missing_au_mappings(...)`, `build_au_assignment_null_summary(...)`, and
  `validate_nonempty_au_assignment(...)`.
- Rewired 00_data-prep AU assignment + null-diagnostics block to consume these helpers instead of
  inline `_lookup_scsi_au`/`au_from_scsi`/missing-summary logic.
- Expanded tests with deterministic helper coverage in `tests/test_pipeline_helpers.py` and updated
  orchestration guardrails in `tests/test_legacy_orchestration_wiring.py` to assert new AU helper
  seam usage.
- Queued next extraction slice: continue P2.2 by extracting the post-AU curve-ID assignment block
  (`assign_curve1`, `assign_curve2`) into reusable helper(s), then wire through tests/guardrails.
- Added `assign_curve_ids_from_au_table(...)` in `femic.pipeline.bundle` to centralize post-AU
  curve ID assignment logic (managed/unmanaged switch and fallback handling).
- Rewired 00_data-prep to call `assign_curve_ids_from_au_table(...)` in place of inline
  `assign_curve1`/`assign_curve2` functions and row-wise assignment calls.
- Expanded `tests/test_bundle.py` with deterministic coverage for managed/unmanaged curve assignment
  behavior, and updated orchestration guardrails to assert
  `assign_curve_ids_from_au_table(...)` seam usage.
- Queued next extraction slice: continue P2.2 by extracting the remaining post-curve assignment
  THLB/theme orchestration blocks into reusable helper seams.
- Added `assign_thlb_area_and_flag(...)` in `femic.pipeline.tsa` to centralize THLB area + THLB
  flag assignment rules previously embedded in 00_data-prep.
- Rewired 00_data-prep to call `assign_thlb_area_and_flag(...)` instead of inline `thlb_area(...)`
  and `assign_thlb(...)` functions.
- Expanded `tests/test_pipeline_helpers.py` with deterministic THLB helper coverage and updated
  orchestration guardrails to assert `assign_thlb_area_and_flag(...)` seam usage.
- Queued next extraction slice: continue P2.2 by extracting remaining theme/shapefile post-processing
  orchestration (`has_managed_curve`, `extract_features`, per-TSA stand export transforms) into
  reusable helper seams.
- Added `src/femic/pipeline/stands.py` to centralize stand-export post-processing helpers:
  `should_skip_stands_export(...)`, `clean_stand_geometry(...)`,
  `extract_stand_features_for_tsa(...)`, `build_stands_column_map(...)`,
  `prepare_stands_export_frame(...)`, and `export_stands_shapefiles(...)`.
- Rewired 00_data-prep stand-export orchestration to consume the new stands helpers (skip-flag
  resolution, column-map construction, per-TSA feature extraction/transform, and shapefile write
  loop) instead of inline local function definitions.
- Exported stands helpers from `femic.pipeline.__init__` and added deterministic coverage in
  `tests/test_stands.py`; updated orchestration guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `build_stands_column_map(...)`, `should_skip_stands_export(...)`, and
  `export_stands_shapefiles(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (178 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline post-01b orchestration
  prints/warnings and path literals in `00_data-prep.py` into reusable logging/path helper seams so
  the script body approaches a pure stage-composition shell.
- Added `tipsy_stage_output_paths(...)` in `src/femic/pipeline/tipsy.py` to centralize legacy 01b
  per-TSA output CSV path construction.
- Added `emit_missing_au_mapping_warning(...)` in `src/femic/pipeline/tsa.py` to centralize the
  two-line warning emission for missing AU mapping diagnostics.
- Rewired 00_data-prep post-01b orchestration to consume the new helpers:
  `_should_skip_01b(...)` now uses `tipsy_stage_output_paths(...)`, and AU null-handling now uses
  `emit_missing_au_mapping_warning(...)` instead of inline `print(...)` statements.
- Exported new helpers via `femic.pipeline.__init__`, added deterministic helper tests in
  `tests/test_tipsy.py` and `tests/test_pipeline_helpers.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (180 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by centralizing remaining `00_data-prep.py` hardcoded
  `./data/...` artifact path literals (checkpoints, intermediates, and exports) behind reusable path
  builders so stage orchestration uses structured path payloads instead of inline strings.
- Added `build_ria_vri_checkpoint_paths(...)` in `src/femic/pipeline/io.py` to centralize legacy
  VRI checkpoint artifact path construction (`ria_vri_vclr1p_checkpoint{1..8}.feather`).
- Rewired `00_data-prep.py` to call `build_ria_vri_checkpoint_paths(...)` and source checkpoint path
  variables from the returned path payload instead of embedding eight inline `./data/...` literals.
- Exported the new path helper via `femic.pipeline.__init__`, added deterministic helper coverage in
  `tests/test_pipeline_helpers.py`, and extended AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (181 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by centralizing remaining non-checkpoint
  `00_data-prep.py` `./data/...` path literals (VDYP input/output, TIPSY exports, and siteprod
  artifact prefixes) into reusable path builders so stage configuration is fully payload-driven.
- Added `LegacyDataArtifactPaths` and `build_legacy_data_artifact_paths(...)` in
  `src/femic/pipeline/io.py` to centralize non-checkpoint legacy `data/` artifact paths under a
  single reusable payload.
- Rewired `00_data-prep.py` to source non-checkpoint data artifact paths from
  `build_legacy_data_artifact_paths(...)`, including VDYP input/output paths, TIPSY input-column
  file path and prefix, siteprod artifacts, bundle root, THLB raster, and stands shapefile output
  directory.
- Exported new I/O path payload helpers via `femic.pipeline.__init__`, added deterministic coverage
  in `tests/test_pipeline_helpers.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `build_legacy_data_artifact_paths(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (182 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by removing residual duplicated path-to-string
  coercion and remaining ad-hoc path joins in `00_data-prep.py` (favor passing `Path` objects
  through helper boundaries directly) so orchestration has a consistent typed path surface.
- Reworked `00_data-prep.py` path handling to keep legacy artifact paths as `Path` objects through
  helper boundaries (removed residual `str(...)` coercions for non-external artifact paths).
- Replaced remaining ad-hoc path joins in 00_data-prep with helper/path-native composition:
  `build_vdyp_cache_paths(...)` + `tipsy_params_excel_path(...)` now drive 01a resume-skip output
  checks; siteprod layer temp paths now use `Path` joins/globs instead of `%s` string templates.
- Replaced residual string-shell path checks/builds in this stage:
  `Path.is_file()` for local executable/artifact presence, list-based `subprocess.run(...)` calls
  with pathlike args, and `Path.read_text().splitlines()` for TIPSY column loading.
- Added `tipsy_params_excel_path(...)` in `src/femic/pipeline/tipsy.py`, exported it in
  `femic.pipeline.__init__`, added deterministic coverage in `tests/test_tipsy.py`, and updated AST
  guardrails in `tests/test_legacy_orchestration_wiring.py` to assert
  `build_vdyp_cache_paths(...)` + `tipsy_params_excel_path(...)` seam usage in 00_data-prep.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (183 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by centralizing remaining inline external-data root
  resolution and path selection logic in `00_data-prep.py` (`_select_external_data_root`,
  candidate list assembly, VRI/TSA source roots) into reusable I/O helper seams.
- Added `LegacyExternalDataPaths` + `resolve_legacy_external_data_paths(...)` in
  `src/femic/pipeline/io.py` to centralize external data-root candidate resolution and canonical
  VRI/TSA source path construction.
- Rewired `00_data-prep.py` to consume `resolve_legacy_external_data_paths(...)`, removing inline
  `_select_external_data_root` and candidate-list assembly logic from the script body.
- Exported external-path helpers in `femic.pipeline.__init__`, added deterministic helper coverage
  in `tests/test_pipeline_helpers.py`, and updated AST orchestration guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `resolve_legacy_external_data_paths(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (184 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline siteprod raster
  export/stack orchestration in `00_data-prep.py` (ArcRasterRescue command assembly, temporary
  layer path enumeration, cleanup loop) into dedicated stage/helper seams.
- Added `src/femic/pipeline/siteprod.py` with reusable siteprod orchestration helpers:
  `parse_arc_raster_rescue_layer_mappings(...)`, `list_siteprod_layers(...)`,
  `build_siteprod_layer_tif_path(...)`, `enumerate_siteprod_layer_tif_paths(...)`, and
  `export_and_stack_siteprod_layers(...)`.
- Rewired `00_data-prep.py` siteprod stage to consume `list_siteprod_layers(...)` and
  `export_and_stack_siteprod_layers(...)`, removing inline ArcRasterRescue command assembly,
  temporary-layer path enumeration, and temp cleanup loop logic.
- Exported siteprod helpers via `femic.pipeline.__init__`, added deterministic coverage in
  `tests/test_siteprod.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `list_siteprod_layers(...)` + `export_and_stack_siteprod_layers(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (188 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline siteprod sampling
  orchestration in `00_data-prep.py` (`siteprod_species_lookup`, `mean_siteprod` closure, and row
  apply wiring) into reusable helper seams under `femic.pipeline.siteprod`.
- Expanded `src/femic/pipeline/siteprod.py` with reusable siteprod sampling helpers:
  `DEFAULT_SITEPROD_SPECIES_LOOKUP`, `siteprod_species_lookup(...)`,
  `mean_siteprod_for_row(...)`, and `assign_siteprod_from_raster(...)`.
- Rewired `00_data-prep.py` checkpoint2 siteprod assignment to call
  `assign_siteprod_from_raster(...)`, removing inline `siteprod_species_lookup` and nested
  `mean_siteprod(...)` closure logic from the script.
- Exported new sampling helpers via `femic.pipeline.__init__`, extended
  `tests/test_siteprod.py` with lookup + row-mean + assignment coverage, and updated AST guardrails
  in `tests/test_legacy_orchestration_wiring.py` to assert
  `assign_siteprod_from_raster(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (190 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline species-volume
  compilation orchestration in checkpoint3 (`compile_species_vol` local function, map dispatch, and
  per-species assignment loop) into reusable helper seams.
- Added `src/femic/pipeline/species_volume.py` with reusable checkpoint3 species-volume helpers:
  `species_volume_input_columns(...)`, `compile_species_volume_series(...)`, and
  `compile_species_volume_columns(...)`.
- Rewired checkpoint3 species-volume compilation in `00_data-prep.py` to call
  `compile_species_volume_columns(...)`, removing inline `compile_species_vol(...)`, manual column
  assembly, map dispatch, and per-species assignment loop.
- Exported species-volume helpers via `femic.pipeline.__init__`, added deterministic coverage in
  `tests/test_species_volume.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `compile_species_volume_columns(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (193 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline checkpoint2
  pre-filter/fillna normalization block (species/soil/BCLCS/LIVE_VOL defaults and filters) into a
  dedicated reusable helper seam.
- Added `src/femic/pipeline/vri.py` with
  `normalize_and_filter_checkpoint2_records(...)` to centralize checkpoint2 fill-defaults and
  row-filter rules (species slots, soil/BCLCS defaults, operability filters).
- Rewired `00_data-prep.py` checkpoint2 normalization stage to call
  `normalize_and_filter_checkpoint2_records(...)`, removing the large inline fillna/filter block.
- Exported VRI helper seams via `femic.pipeline.__init__`, added deterministic unit coverage in
  `tests/test_vri.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `normalize_and_filter_checkpoint2_records(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (195 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline conifer/deciduous
  classification helpers (`is_conif`, `is_decid`, `pconif`, `pdecid`, stand-type classifiers) from
  `00_data-prep.py` into reusable helper seams.
- Expanded `src/femic/pipeline/vri.py` with reusable stand-classification helpers:
  `is_conifer_species_code(...)`, `is_deciduous_species_code(...)`, `pconif(...)`, `pdecid(...)`,
  `classify_stand_cdm(...)`, `classify_stand_forest_type(...)`, and
  `assign_forest_type_from_species_pct(...)`.
- Rewired `00_data-prep.py` to remove inline conifer/deciduous classifier function definitions and
  call `assign_forest_type_from_species_pct(...)` for forest-type assignment.
- Exported new VRI classification helpers via `femic.pipeline.__init__`, expanded
  `tests/test_vri.py` coverage for all classification helpers, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `assign_forest_type_from_species_pct(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (198 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline stratum-code assembly
  logic (`stratify_stand` + `stratify_stand_lexmatch` partial wiring) from `00_data-prep.py` into
  reusable helper seams.
- Expanded `src/femic/pipeline/vri.py` with reusable stratum-code helpers:
  `stratify_stand(...)` and `assign_stratum_codes_with_lexmatch(...)`.
- Rewired `00_data-prep.py` to remove inline `stratify_stand`/`stratify_stand_lexmatch` wiring and
  call `assign_stratum_codes_with_lexmatch(...)` at both stratum derivation stages.
- Exported new VRI stratum helpers via `femic.pipeline.__init__`, expanded
  `tests/test_vri.py` with deterministic stratification coverage, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `assign_stratum_codes_with_lexmatch(...)` seam usage count.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (200 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting the remaining inline THLB sampling
  closure (`mean_thlb`) into a reusable helper seam so raster masking logic is no longer defined
  inline in `00_data-prep.py`.
- Added reusable THLB raster sampling helpers in `src/femic/pipeline/tsa.py`:
  `mean_thlb_for_geometry(...)` and `assign_thlb_raw_from_raster(...)`.
- Rewired `00_data-prep.py` THLB sampling stage to call
  `assign_thlb_raw_from_raster(...)`, removing inline `with rio.open(...): mean_thlb(...)` closure
  logic.
- Exported new THLB raster helpers via `femic.pipeline.__init__`, expanded deterministic coverage in
  `tests/test_pipeline_helpers.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `assign_thlb_raw_from_raster(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (201 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting the remaining inline checkpoint83
  post-THLB stand-filter block (`BCLCS_LEVEL_2`, management base, BEC, species/site-index null
  filters) into a reusable helper seam in `femic.pipeline.vri`.
- Expanded `src/femic/pipeline/vri.py` with
  `filter_post_thlb_stands(...)` to centralize checkpoint83 post-THLB stand filtering rules.
- Rewired `00_data-prep.py` checkpoint83 post-THLB filtering stage to call
  `filter_post_thlb_stands(...)`, removing the remaining inline filter chain.
- Exported the new VRI filter helper via `femic.pipeline.__init__`, expanded deterministic coverage
  in `tests/test_vri.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `filter_post_thlb_stands(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (202 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline species-list
  derivation (`set().union(...)` over `SPECIES_CD_1..6`) into a reusable helper seam so derived
  species universes are no longer assembled ad hoc inside `00_data-prep.py`.
- Expanded `src/femic/pipeline/vri.py` with
  `derive_species_list_from_slots(...)` to centralize species-universe derivation from
  `SPECIES_CD_1..6` slot columns.
- Rewired `00_data-prep.py` to call `derive_species_list_from_slots(...)` instead of inline
  `set().union(...)` species-list assembly.
- Exported the new species-list helper via `femic.pipeline.__init__`, expanded deterministic
  coverage in `tests/test_vri.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `derive_species_list_from_slots(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (203 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting remaining inline post-bundle warning
  formatting for missing AU/curve mappings into a reusable diagnostics helper seam so 00_data-prep
  no longer assembles this warning text block inline.
- Added `emit_missing_au_curve_mapping_warning(...)` in `src/femic/pipeline/bundle.py` to
  centralize post-bundle missing AU/curve warning formatting and emission.
- Rewired `00_data-prep.py` post-bundle diagnostics to call
  `emit_missing_au_curve_mapping_warning(...)` instead of assembling warning text inline.
- Exported the new bundle diagnostics helper via `femic.pipeline.__init__`, expanded deterministic
  coverage in `tests/test_bundle.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `emit_missing_au_curve_mapping_warning(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (204 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by extracting residual inline `f.shape` diagnostic
  notebook artifacts from `00_data-prep.py` into optional helper/log seams (or remove where dead)
  so the script body remains pure orchestration.
- Removed residual dead inline `f.shape` notebook diagnostic expressions from
  `00_data-prep.py` where they had no runtime effect.
- Verified this cleanup does not alter pipeline behavior; all required gates passed:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (204 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by removing remaining dead notebook preview artifacts
  (`au_table.head()`, `curve_table.head()`, `curve_points_table.head()`) so `00_data-prep.py`
  remains a pure orchestration script.
- Removed remaining dead notebook preview artifacts
  (`au_table.head()`, `curve_table.head()`, `curve_points_table.head()`) from `00_data-prep.py`.
- Verified no behavior change and full validation gate success:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (204 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by trimming residual notebook-only `if 1:` wrappers
  in `00_data-prep.py` where they no longer control branching, so orchestration flow is explicit.
- Removed residual notebook-only `if 1:` wrappers in `00_data-prep.py` that no longer controlled
  branching (01a stage block and checkpoint83 post-THLB block), leaving explicit orchestration
  flow.
- Verified behavior parity and full validation gate success:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (204 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by removing or gating remaining notebook-only plot
  diagnostics (`f.thlb_raw.describe()` / `f.thlb_raw.hist()`) so headless/script runs stay focused
  on pipeline outputs.
- Gated remaining notebook-only THLB diagnostics in `00_data-prep.py` behind
  `FEMIC_THLB_DIAGNOSTICS` (`0` default; enable with `1`/`true`/`yes`) so headless/script runs do
  not emit notebook-style plotting/stat calls unless explicitly requested.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (204 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by removing remaining dead inline aggregate preview
  expressions (`f.query(...).groupby(...).sum()` and `f.groupby(...).sum()`) from
  `00_data-prep.py` so script-mode orchestration contains only side-effecting pipeline steps.
- Removed remaining dead inline aggregate preview expressions from `00_data-prep.py`
  (`f.query("thlb == 1").groupby(...).sum()` and `f.groupby("tsa_code").thlb_area.sum()`), leaving
  only side-effecting pipeline steps in this stage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (204 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by removing notebook carry-over no-op aliases like
  `stratify_stand = stratify_stand` if any remain, or mark completion of this cleanup tranche if
  none remain.
- Confirmed no residual notebook no-op alias assignments remained; removed adjacent dead empty cell
  marker artifacts in `00_data-prep.py` (`# --- cell 85 ---`, `# --- cell 101 ---`,
  `# --- cell 105 ---`) as part of the same cleanup tranche.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (204 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by reducing residual generic exception handling in
  `00_data-prep.py` (e.g., broad `except:` blocks around helperable operations) into explicit helper
  seams or narrowed exception paths.
- Added `ensure_au_table_index(...)` in `src/femic/pipeline/bundle.py` and rewired
  `00_data-prep.py` to call it in place of the broad `try/except:` around
  `au_table.set_index("au_id", inplace=True)`.
- Exported the helper via `femic.pipeline.__init__`, expanded deterministic coverage in
  `tests/test_bundle.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert `ensure_au_table_index(...)` seam usage.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (206 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by narrowing broad `except Exception` around
  ipyparallel client initialization into explicit import/runtime exception paths (or helper seam)
  while preserving serial fallback behavior.
- Added `ParallelExecutionBackend` and `initialize_parallel_execution_backend(...)` in
  `src/femic/pipeline/stages.py` to centralize ipyparallel bootstrap + serial fallback behavior with
  explicit fallback exception classes (instead of broad `except Exception`), and rewired
  `00_data-prep.py` to consume that helper seam.
- Exported the new parallel backend seam via `femic.pipeline.__init__`, expanded deterministic
  coverage in `tests/test_pipeline_stages.py`, and updated AST guardrails in
  `tests/test_legacy_orchestration_wiring.py` to assert
  `initialize_parallel_execution_backend(...)` seam usage.
- Narrowed `stratify_stand(...)` row lookup fallback handling in `src/femic/pipeline/vri.py` from
  broad `except Exception` to explicit lookup errors (`KeyError`, `TypeError`, `IndexError`) and
  expanded coverage in `tests/test_vri.py` for attribute-style row objects.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (209 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by narrowing remaining broad exception fallbacks in
  THLB helper seams (`mean_thlb_for_geometry(...)` / `assign_thlb_raw_from_raster(...)` in
  `src/femic/pipeline/tsa.py`) into explicit raster/row-lookup exception paths while preserving
  legacy default-on-error behavior.
- Narrowed broad THLB helper fallback scopes in `src/femic/pipeline/tsa.py`:
  `mean_thlb_for_geometry(...)` now catches explicit raster/mask runtime classes
  (`ValueError`, `TypeError`, `RuntimeError`, `OSError`) and
  `assign_thlb_raw_from_raster(...)` row geometry fallback now catches explicit lookup errors
  (`KeyError`, `TypeError`, `IndexError`).
- Expanded deterministic coverage in `tests/test_pipeline_helpers.py` to assert
  `mean_thlb_for_geometry(...)` still returns `default_on_error` for expected runtime failures while
  unexpected exceptions propagate.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (211 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing remaining broad `except Exception`
  handlers in pipeline helper modules that support legacy orchestration (next target:
  `src/femic/pipeline/vdyp_curves.py`) and narrow them to explicit operational fallback classes
  without changing emitted diagnostics.
- Narrowed remaining broad curve-smoothing exception handling in
  `src/femic/pipeline/vdyp_curves.py` by introducing an explicit
  `_curve_fit_fallback_exception_types()` tuple and applying it to both body-fit and toe-fit retry
  fallback paths in `process_vdyp_out(...)`.
- Preserved legacy fallback behavior for expected operational fit failures while allowing unexpected
  exceptions to propagate for visibility/debuggability.
- Expanded deterministic coverage in `tests/test_vdyp_curves.py` to assert:
  runtime body-fit failures still fallback to quasi-origin outputs, and unexpected body/toe failures
  (`ZeroDivisionError`) now propagate.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (214 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing broad fallback handlers in
  `src/femic/pipeline/vdyp_stage.py` and narrowing them to explicit subprocess/IO/parsing exception
  classes while preserving current logging semantics.
- Narrowed a first safe subset of broad exception handlers in `src/femic/pipeline/vdyp_stage.py`:
  `fit_stratum_curves(...)` now catches explicit curve-fit operational failures, and
  `execute_vdyp_batch(...)` now catches explicit subprocess execution and parse/import failure
  classes for `status=error` / `status=parse_error` logging paths.
- Preserved existing logging semantics for expected operational failures while allowing unexpected
  exceptions to propagate.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` to assert:
  `RuntimeError` curve-fit failures still skip species with `fit error` messages, and unexpected
  `ZeroDivisionError` failures in curve-fit, subprocess execution, and parse stages propagate.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (217 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by narrowing the remaining broad exception handler in
  `execute_bootstrap_vdyp_runs(...)` (`dispatch_error` logging wrapper around `run_vdyp_fn`) into
  explicit run-stage exception classes while preserving JSONL diagnostics.
- Narrowed the remaining broad dispatch wrapper in
  `execute_bootstrap_vdyp_runs(...)` (`src/femic/pipeline/vdyp_stage.py`) to explicit
  `_bootstrap_dispatch_exception_types()` while preserving `dispatch_error` JSONL emission for known
  operational failures.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` to assert unexpected bootstrap
  dispatch failures (`ZeroDivisionError`) now propagate without being converted into
  `dispatch_error` records.
- Verified `src/femic/pipeline/vdyp_stage.py` now contains no `except Exception` handlers.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (218 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing remaining broad exception handlers in
  legacy-adapter modules (`src/femic/pipeline/tipsy.py`, `tipsy_config.py`, `tipsy_legacy.py`) and
  narrowing first safe operational fallback paths with explicit exception classes.
- Narrowed a first safe subset of broad exception fallbacks in tipsy adapter modules:
  `compute_vdyp_site_index(...)` and `compute_vdyp_oaf1(...)` in `src/femic/pipeline/tipsy.py`,
  forest-type mode fallback in `src/femic/pipeline/tipsy_config.py`, and species-slot unpack
  fallback in `tipsy_params_tsa40(...)` (`src/femic/pipeline/tipsy_legacy.py`).
- Preserved malformed-input fallback behavior for expected data-shape/key issues while allowing
  unexpected exceptions to propagate.
- Expanded deterministic coverage in `tests/test_tipsy.py`, `tests/test_tipsy_config.py`, and
  `tests/test_tipsy_legacy.py` to assert both expected fallback behavior and unexpected-error
  propagation.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (222 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by narrowing the remaining broad exception wrapper in
  `build_tipsy_params_for_tsa(...)` (`src/femic/pipeline/tipsy.py`, around
  `evaluate_tipsy_candidate(...)`) to explicit candidate-evaluation data/runtime exception classes
  while preserving current debug message emission and re-raise behavior.
- Narrowed the remaining broad candidate-evaluation wrapper in
  `build_tipsy_params_for_tsa(...)` (`src/femic/pipeline/tipsy.py`) to explicit
  `_tipsy_candidate_exception_types()` while preserving legacy debug message emission and re-raise
  behavior for expected candidate-evaluation failures.
- Expanded deterministic coverage in `tests/test_tipsy.py` to assert:
  candidate `ValueError` paths still emit debug context then re-raise, and unexpected
  candidate-evaluation failures (`ZeroDivisionError`) propagate.
- Verified no `except Exception` handlers remain in tipsy adapter modules
  (`src/femic/pipeline/tipsy.py`, `tipsy_config.py`, `tipsy_legacy.py`).
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (224 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing remaining broad exception handlers
  outside tipsy/vdyp modules (current highest-priority target: `src/femic/pipeline/tsa.py`) and
  narrowing operational fallback paths with explicit exception classes plus propagation tests.
- Narrowed the broad pre-VDYP resume checkpoint load handler in `01a_run-tsa.py` from
  `except Exception` to explicit pickle/IO/runtime classes
  (`OSError`, `EOFError`, `pickle.UnpicklingError`, `TypeError`, `AttributeError`,
  `ModuleNotFoundError`) while preserving existing failure message + non-fatal resume fallback
  behavior.
- Expanded AST guardrails in `tests/test_legacy_01a_structure.py` with
  `test_run01a_no_broad_exception_handlers` to prevent reintroduction of bare/broad exception
  handlers in `run_tsa(...)`.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (225 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by narrowing the remaining broad exception handler in
  CLI entry wiring (`src/femic/cli/main.py`) with explicit command/runtime exception classes and
  targeted CLI regression coverage.
- Narrowed the remaining broad CLI debug-traceback handler in `src/femic/cli/main.py`
  (`_enable_rich_tracebacks`) to explicit optional-import failures
  (`ModuleNotFoundError`, `ImportError`) so unexpected import-time/runtime failures are no longer
  silently swallowed.
- Added targeted CLI coverage in `tests/test_cli_main.py` to assert missing optional `rich`
  dependency is ignored while unexpected import failures propagate.
- Completed broad-exception hardening audit for active orchestration/code paths:
  no `except Exception` or bare `except:` handlers remain in `src/`, `tests/`,
  `00_data-prep.py`, or `01a_run-tsa.py`.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (227 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by replacing remaining sentinel `assert False`
  branches in legacy orchestration/helper modules with explicit typed errors carrying actionable
  context (start with legacy TIPSY builders in `src/femic/pipeline/tipsy_legacy.py`).
- Replaced sentinel `assert False` branches in legacy TIPSY builders
  (`src/femic/pipeline/tipsy_legacy.py`) with explicit typed errors carrying actionable context:
  `ValueError` for invalid unsupported species/BEC rule selections and `NotImplementedError` for
  explicitly unimplemented legacy forest-type branches.
- Added reusable error helpers (`_raise_invalid_legacy_tipsy_rule(...)`,
  `_raise_unimplemented_legacy_tipsy_rule(...)`) so failure paths are explicit and consistent.
- Expanded deterministic coverage in `tests/test_tipsy_legacy.py` to assert unsupported inputs raise
  typed/contextual errors and added an AST guardrail ensuring `tipsy_legacy.py` contains no
  `assert False` sentinels.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (231 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by replacing remaining `assert False` sentinels in
  `src/femic/pipeline/vdyp_stage.py` (unreachable load-balanced branch and invalid `nsamples`
  guard) with explicit typed errors plus regression tests.
- Replaced remaining `assert False` sentinels in `src/femic/pipeline/vdyp_stage.py` with explicit
  typed errors:
  `NotImplementedError` for unsupported `ipp_mode='load_balanced'` branch in
  `run_vdyp_sampling(...)`, and `ValueError` for invalid `nsamples` mode values.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` to assert these branches now raise
  typed errors with informative messages.
- Verified no `assert False` sentinels remain in production orchestration/pipeline modules
  (`src/`, `00_data-prep.py`, `01a_run-tsa.py`).
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (232 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing remaining broad `assert`-style runtime
  sentinels in production helper/orchestration paths (non-test) and replacing inappropriate
  runtime assertions with explicit typed errors where behavior is user/input dependent.
- Replaced remaining non-test runtime assertion control-flow checks with explicit typed errors in
  production modules:
  `resolve_tipsy_param_builder(...)` (`src/femic/pipeline/tipsy_config.py`),
  `run_legacy_subprocess(...)` (`src/femic/pipeline/stages.py`),
  `clean_stand_geometry(...)` (`src/femic/pipeline/stands.py`), and runtime config validation in
  `run_tsa(...)` (`01a_run-tsa.py`).
- Expanded deterministic coverage with new regression/guardrail tests in
  `tests/test_tipsy_config.py`, `tests/test_pipeline_stages.py`, `tests/test_stands.py`, and
  `tests/test_legacy_01a_structure.py` for new typed error branches and assertion-removal guards.
- Completed runtime assertion hardening audit:
  no `assert` statements remain in production orchestration/pipeline code
  (`src/`, `00_data-prep.py`, `01a_run-tsa.py`).
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (237 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by consolidating repeated legacy rule-error
  construction patterns (currently duplicated across TIPSY/VDYP helper seams) into shared diagnostic
  helpers where practical, while preserving existing external behavior and messages.
- Added shared diagnostics formatting helpers in `src/femic/pipeline/diagnostics.py`
  (`format_context_kv(...)`, `build_contextual_error_message(...)`) to centralize contextual
  error-string construction.
- Rewired legacy TIPSY and VDYP typed-error branches to use shared diagnostics formatting:
  `src/femic/pipeline/tipsy_legacy.py` and `src/femic/pipeline/vdyp_stage.py`, preserving existing
  behavior while reducing duplicated message assembly logic.
- Added deterministic coverage in `tests/test_diagnostics.py` and verified existing regression
  coverage still exercises the rewired TIPSY/VDYP error branches.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (240 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by consolidating repeated structured event payload
  assembly in VDYP/TIPSY warning/error logging paths into shared builders where this can be done
  without changing emitted field sets.
- Extended shared diagnostics utilities in `src/femic/pipeline/diagnostics.py` with
  `build_timestamped_event(...)` to centralize structured event payload construction.
- Rewired duplicated VDYP/TIPSY event payload assembly to use shared helpers without changing
  emitted field sets:
  `build_tipsy_warning_event(...)` (`src/femic/pipeline/tipsy.py`) and bootstrap/batch
  VDYP run event logging paths in `src/femic/pipeline/vdyp_stage.py`
  (`dispatch`, `dispatch_error`, `timeout`, `error`, `parse_error`, `ok|empty_output`).
- Added deterministic unit coverage in `tests/test_diagnostics.py` for the shared event helper and
  validated existing TIPSY/VDYP regression suites against the rewired event construction paths.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (240 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing remaining ad hoc timestamped event/log
  payload builders outside VDYP/TIPSY (if any) and consolidating them into shared diagnostics
  helpers where this can be done with zero field-shape drift.
- Continued event-payload consolidation by rewiring remaining ad hoc VDYP run-event builders in
  `src/femic/pipeline/vdyp_stage.py` (`cache_only`, `start`, and curve-input missing-output
  warning) to use shared `build_timestamped_event(...)` helper.
- Preserved emitted field shapes/status semantics for existing log consumers and regression tests.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (240 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by evaluating whether `process_vdyp_out(...)`
  (`src/femic/pipeline/vdyp_curves.py`) can adopt shared timestamped event builder without
  changing its intentional single-base-event timestamp semantics; if not, explicitly document that
  rationale and mark this consolidation sub-track complete.
- Completed the queued `vdyp_curves.py` evaluation and successfully adopted shared event helpers
  without changing its single-base-event timestamp semantics: `process_vdyp_out(...)` now builds its
  base event via shared `build_timestamped_event(...)` exactly once per run and reuses that payload
  across emitted events.
- Extended `build_timestamped_event(...)` (`src/femic/pipeline/diagnostics.py`) to support optional
  `status` and explicit `timestamp` override so both per-event and base-event patterns are supported
  through one helper.
- Expanded deterministic coverage in `tests/test_diagnostics.py` for status-optional event payloads
  and validated `tests/test_vdyp_curves.py` against the rewired base-event construction path.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (241 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by closing the event-consolidation sub-track with a
  quick repo-wide audit for remaining ad hoc `event` + `timestamp` payload construction in
  production code and either (a) rewire to shared diagnostics helpers or (b) document explicit
  exceptions where intentional.
- Closed the queued event-consolidation audit by rewiring the final ad hoc structured event path in
  `src/femic/pipeline/vdyp_curves.py` (`vdyp_curve_anchor`) to shared
  `build_timestamped_event(...)` while preserving one-timestamp-per-run semantics.
- Extended `build_timestamped_event(...)` (`src/femic/pipeline/diagnostics.py`) to support optional
  `status` and explicit timestamp override, enabling both per-event and base-event reuse patterns.
- Added `build_vdyp_stream_header(...)` in `src/femic/pipeline/vdyp_logging.py` and rewired
  `execute_vdyp_batch(...)` (`src/femic/pipeline/vdyp_stage.py`) to consume it, removing the last
  inline timestamped stream-header string assembly from execution flow.
- Expanded deterministic coverage in `tests/test_diagnostics.py`, `tests/test_vdyp_curves.py`, and
  `tests/test_vdyp_logging.py` for the rewired helpers and timestamp-semantics guard.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (242 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by reducing duplicated fallback-event assembly inside
  `process_vdyp_out(...)` (`src/femic/pipeline/vdyp_curves.py`) via a small internal event-builder
  seam that reuses shared diagnostics helpers without changing emitted fields.
- Reduced duplicated fallback-event assembly in `process_vdyp_out(...)`
  (`src/femic/pipeline/vdyp_curves.py`) by adding a small internal `emit_curve_event(...)` seam that
  reuses shared diagnostics event helpers while preserving emitted field sets and timestamp/context
  semantics.
- Rewired all `process_vdyp_out(...)` event emissions (fallback, body-fit error, toe-fit success,
  toe-fit warning, quasi-origin anchor) through the new internal seam; behavior remains unchanged.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (242 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing duplicate formatting/serialization logic in
  logging helpers (`append_jsonl`, stream-header and related callers) for additional safe
  centralization seams now that event payload assembly is consolidated.
- Consolidated duplicate logging-format/serialization logic in `src/femic/pipeline/vdyp_logging.py`
  by introducing `serialize_jsonl_payload(...)` and `append_line(...)`, then rewiring
  `append_jsonl(...)` to use these shared seams.
- Preserved existing external behavior (`default=str` JSON serialization and newline-terminated line
  append semantics) while removing repeated parent-dir + line-write patterns.
- Expanded deterministic coverage in `tests/test_vdyp_logging.py` for payload serialization and
  generic line-appending helpers.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (244 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing whether remaining specialized appenders
  (plain-text stream append and JSONL append callsites) can share a single file-append primitive
  end-to-end without reducing clarity or changing output contract.
- Completed the queued append-primitive audit in `src/femic/pipeline/vdyp_logging.py` by adding a
  shared internal file-append helper (`_append_text_fragment(...)`) and rewiring both
  `append_line(...)` and `append_text(...)` to consume it.
- Preserved output contracts: `append_line(...)` still appends newline-terminated records and
  `append_text(...)` still appends exact text fragments.
- Expanded deterministic coverage in `tests/test_vdyp_logging.py` with
  `test_append_text_appends_without_overwriting` to guard append-vs-overwrite behavior.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (245 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing remaining direct append-file writes
  outside `vdyp_logging`/`append_line` callsites and centralizing them only where behavior can
  remain byte-for-byte unchanged.
- Completed the queued direct-append audit across production Python paths (`src/`,
  `00_data-prep.py`, `01a_run-tsa.py`, `01b_run-tsa.py`): no remaining direct file-append writes
  exist outside `src/femic/pipeline/vdyp_logging.py`.
- Confirmed the only append-file primitive in production code is now
  `_append_text_fragment(...)` via `append_line(...)`/`append_text(...)`; no behavior-preserving
  rewires were needed in this slice.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (245 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing duplicated newline/stream framing usage
  around legacy subprocess output (`run_legacy_subprocess` and VDYP batch stream capture) and
  centralizing safe formatting seams without altering emitted log text.
- Completed the queued subprocess/stream-format audit by adding explicit formatting seams for both
  line-forwarded legacy subprocess output and VDYP stream artifact capture.
- Added `stream_filtered_subprocess_output(...)` in `src/femic/pipeline/stages.py` and rewired
  `run_legacy_subprocess(...)` to consume this helper, preserving line text/newline behavior while
  centralizing known-noise filtering.
- Added `build_vdyp_stream_log_block(...)` in `src/femic/pipeline/vdyp_logging.py` and rewired
  `execute_vdyp_batch(...)` (`src/femic/pipeline/vdyp_stage.py`) to use it for both stdout/stderr
  stream block assembly (`header + stream + trailing newline`), removing duplicated inline framing.
- Expanded deterministic coverage in `tests/test_pipeline_stages.py` and
  `tests/test_vdyp_logging.py` for these new stream-formatting helper seams.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (247 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing duplicated VDYP subprocess command-string
  assembly/metadata capture in `execute_vdyp_batch(...)` and centralizing it behind a helper seam
  without changing emitted command text or event fields.
- Completed the queued `execute_vdyp_batch(...)` command/metadata consolidation slice with two
  shared helper seams in `src/femic/pipeline/vdyp_stage.py`:
  `build_vdyp_batch_command(...)` (legacy command-string assembly) and
  `collect_vdyp_batch_run_metadata(...)` (shared returncode/duration/file-size/head capture).
- Rewired `execute_vdyp_batch(...)` to consume these helpers for timeout/error/parse-error/ok
  logging paths while preserving emitted command text and event field shape.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` for both new helpers, including
  legacy command-string shape and metadata-field extraction behavior.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (249 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing duplicated base-context enrichment in
  VDYP run orchestration (`run_vdyp_for_stratum`, `execute_vdyp_batch`) and centralizing it via a
  helper seam without changing emitted context keys/values.
- Completed the queued VDYP base-context consolidation by adding
  `build_vdyp_run_context(...)` in `src/femic/pipeline/vdyp_stage.py`.
- Rewired both `run_vdyp_for_stratum(...)` and `execute_vdyp_batch(...)` to consume the shared
  context helper so run-id/log-path/bin/params context defaults are centralized while preserving
  existing `setdefault(...)` semantics and emitted context fields.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` for
  `build_vdyp_run_context(...)`, including default-key population and preservation of
  caller-provided context values.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (251 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing repeated VDYP run-event payload fields
  in `execute_vdyp_batch(...)` (timeout/error/parse_error/ok) and centralizing shared payload
  assembly without changing emitted event keys/values.
- Completed the queued VDYP run-event payload consolidation in
  `src/femic/pipeline/vdyp_stage.py` by adding `build_vdyp_run_event(...)` for shared base field
  assembly (`event/status/phase/feature_count/cache_hits/ply_rows/lyr_rows/cmd/context`).
- Rewired `execute_vdyp_batch(...)` timeout/error/parse_error/ok|empty_output paths to consume
  `build_vdyp_run_event(...)`, preserving emitted event keys/values while removing duplicated
  inline payload assembly.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` for
  `build_vdyp_run_event(...)`, including int normalization of count fields and passthrough extra
  event fields.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (252 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing duplicated event-emission callsites in
  `execute_vdyp_batch(...)` (`append_jsonl_(vdyp_log_path, ...)`) and centralizing them via a
  local helper seam without changing write order or payload content.
- Completed the queued VDYP event-emission callsite consolidation in
  `src/femic/pipeline/vdyp_stage.py` by adding a local `_emit_run_event(...)` seam inside
  `execute_vdyp_batch(...)`.
- Rewired timeout/error/parse_error/ok|empty_output paths to call `_emit_run_event(...)`, removing
  duplicated `append_jsonl_(vdyp_log_path, ...)` callsites while preserving event payload content
  and emission order.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (252 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing duplicated temporary-file basename/path
  extraction in `execute_vdyp_batch(...)` and centralizing it behind a helper seam without changing
  runtime filenames or downstream parse behavior.
- Completed the queued temporary-file extraction consolidation in
  `src/femic/pipeline/vdyp_stage.py` by adding `VdypBatchTempArtifacts` and
  `resolve_vdyp_batch_temp_artifacts(...)` to centralize basename/path derivation from temp files.
- Rewired `execute_vdyp_batch(...)` to consume resolved temp artifacts for infile writing, command
  assembly, output-table import path resolution, and run-metadata file stats while preserving
  runtime filename behavior.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` for
  `resolve_vdyp_batch_temp_artifacts(...)` (basename + full-path expectations).
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (253 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing duplicated numeric coercion (`int(...)`)
  across VDYP batch run-event payload construction and consolidating this coercion at one seam
  without changing emitted values.
- Completed the queued VDYP numeric-coercion consolidation by adding
  `VdypRunEventCounts` + `normalize_vdyp_run_event_counts(...)` in
  `src/femic/pipeline/vdyp_stage.py` and routing shared count coercion through this seam.
- Rewired `build_vdyp_run_event(...)` to consume normalized count payloads and updated
  `execute_vdyp_batch(...)` to reuse the same normalized counts for both run-event emission and
  stream-header construction.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` for
  `normalize_vdyp_run_event_counts(...)` and updated `build_vdyp_run_event(...)` tests to assert
  unchanged emitted values under the new count wrapper.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (254 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing repeated `Path(...)` coercions in VDYP
  helpers (`build_vdyp_batch_command`, `resolve_vdyp_batch_temp_artifacts`,
  `collect_vdyp_batch_run_metadata`) and centralizing only where behavior remains unchanged.
- Completed the queued VDYP path-coercion consolidation by adding `_as_path(...)` in
  `src/femic/pipeline/vdyp_stage.py` and reusing it in:
  `build_vdyp_batch_command(...)`, `resolve_vdyp_batch_temp_artifacts(...)`, and
  `collect_vdyp_batch_run_metadata(...)`.
- Preserved behavior while reducing repeated inline `Path(...)` casts and broadened
  `collect_vdyp_batch_run_metadata(...)` to accept either `str` or `Path` path-like inputs.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` with a string-path metadata test
  to confirm unchanged size/head extraction behavior across path input types.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (255 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing repeated callable-cast setup in
  `execute_vdyp_batch(...)` and centralizing safe dependency-resolution/cast seams without changing
  runtime defaults or injection points.
- Completed the queued callable-resolution/cast consolidation in
  `src/femic/pipeline/vdyp_stage.py` by adding `VdypBatchExecutionDependencies` and
  `resolve_vdyp_batch_execution_dependencies(...)`.
- Rewired `execute_vdyp_batch(...)` to consume resolved dependency fields
  (`write_vdyp_infiles`, `import_vdyp_tables`, `append_jsonl`, `append_text`,
  `build_stream_header`, `build_stream_log_block`, `subprocess_run`) while preserving default
  runtime imports and explicit injection override behavior.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` with an injection-preservation test
  for `resolve_vdyp_batch_execution_dependencies(...)`.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (256 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing repeated ephemeral helper closures inside
  `execute_vdyp_batch(...)` (`_emit_run_event`) and promoting reusable pieces where this improves
  clarity without changing event emission semantics or order.
- Completed the queued closure-promotion slice in `src/femic/pipeline/vdyp_stage.py` by replacing
  the local `_emit_run_event` closure with reusable module helper `emit_vdyp_run_event(...)`.
- Rewired `execute_vdyp_batch(...)` timeout/error/parse_error/ok|empty_output branches to call
  `emit_vdyp_run_event(...)`, preserving event payload shape, write order, and log sink behavior.
- Expanded deterministic coverage in `tests/test_vdyp_stage.py` with
  `test_emit_vdyp_run_event_appends_payload` to assert helper emission semantics.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (257 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice: continue P2.2 by auditing repeated `dict(...)` defensive copies in
  VDYP helper seams (`build_vdyp_run_context`, `build_vdyp_run_event`) and centralizing copy policy
  where clarity improves without mutability regressions.
- Closed P2.2c by adding shared stage executor `execute_legacy_tsa_stage(...)` in
  `src/femic/pipeline/stages.py` and rewiring `00_data-prep.py` 01a/01b orchestration to use
  explicit kwargs builders (`_build_01a_run_kwargs`, `_build_01b_run_kwargs`) instead of inline
  module-load + per-TSA run-loop plumbing.
- Updated orchestration wiring guardrails in `tests/test_legacy_orchestration_wiring.py` to assert
  helper-driven 01a/01b dispatch and preserved explicit keyword handoff payloads.
- Added stage-helper regression coverage in `tests/test_pipeline_stages.py` for
  `execute_legacy_tsa_stage(...)` success and missing-symbol failure behavior.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (259 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): finish `P2.1b` by eliminating remaining
  implicit/global state handoff at 00->01a/01b boundaries, then close `P2.2a`/`P2.2b` with
  explicit major-step wrappers and thin orchestration sequencing.
- Reduced remaining `P2.1b` implicit-state handoff by removing `globals().get(...)` runtime
  injection in `00_data-prep.py` for 01a runtime config (`vdyp_out_cache`, `curve_fit_impl`) and
  replacing it with explicit stage-level variables passed through `_build_01a_run_kwargs(...)`.
- Added AST guardrail coverage in `tests/test_legacy_orchestration_wiring.py` to assert no
  `globals().get(...)` orchestration handoff remains.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (260 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): continue `P2.1b` by auditing remaining 01b
  hard-coded runtime paths and introducing explicit runtime config handoff (mirroring 01a-style
  typed runtime payload) to eliminate residual implicit file-path globals at stage boundaries.
- Closed remaining `P2.1b` boundary implicitness by introducing `Legacy01BRuntimeConfig` +
  `build_legacy_01b_runtime_config(...)` in `src/femic/pipeline/legacy_runtime.py` and wiring
  explicit runtime handoff from `00_data-prep.py` into `01b_run-tsa.py`.
- Refactored `01b_run-tsa.py` to require typed `runtime_config` and consume shared TIPSY path
  helpers (`tipsy_params_excel_path`, `tipsy_stage_output_paths`) plus runtime output-root/template
  settings instead of hard-coded stage-path literals.
- Extended orchestration/runtime guardrails in `tests/test_legacy_orchestration_wiring.py` and
  `tests/test_pipeline_stages.py` for 01b runtime config builder usage and explicit handoff.
- Marked `P2.1b` complete: 00->01a/01b stage boundaries now pass typed runtime payloads and no
  longer rely on implicit `globals().get(...)` runtime injection.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (261 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): close `P2.2a` by wrapping the largest remaining
  major orchestration block in `00_data-prep.py` (post-01b bundle + AU/curve assignment segment)
  behind a shared helper with explicit inputs/outputs, then sequence it under `P2.2b`.
- Closed `P2.2a` by wrapping the largest remaining post-01b orchestration block in
  `00_data-prep.py` behind explicit input/output helper
  `_run_post_01b_bundle_and_curve_assignment_stage(...)`, including bundle load/build,
  stratum/AU assignment, curve-id mapping, and checkpoint writes.
- Stage output handoff is now explicit (`f`, `au_table`, `curve_table`, `curve_points_table`),
  removing the last large inline notebook-style block from top-level execution flow.
- Completed validation gate after this slice:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest` (261 passed),
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W`.
- Queued next extraction slice (ASAP closure path): close `P2.2b` by adding one thin
  top-level orchestration function in `00_data-prep.py` that sequences the extracted stage calls
  with explicit intermediate payload handoff and minimal side effects.
- Closed `P2.2b` by adding `_run_legacy_tsa_orchestration_stage(...)` in `00_data-prep.py` to
  sequence 01a stage execution, 01b stage execution, and post-01b bundle/AU/curve assignment under
  one explicit handoff seam.
- Removed remaining inline top-level sequencing calls for 01a/01b and bundle-path stage dispatch;
  stage outputs now flow through the orchestration helper return payload.
- Queued next extraction slice (ASAP closure path): start `P2.3a` with smoke tests for extracted
  core helpers (path/validation and key deterministic transforms) to lock in current behavior before
  Phase 3 workflow hardening.
- Started and closed `P2.3a` by extending smoke coverage with CLI preflight file-validation tests
  (`tests/test_cli_main.py`) and lightweight transform smoke checks for TSA normalization/checkpoint
  path building (`tests/test_smoke.py`).
- Queued next extraction slice (ASAP closure path): start `P2.3b` by adding deterministic,
  small-sample assertions for one or two extracted core helpers where behavior contracts are
  currently implicit (without expanding runtime-heavy legacy integration scope).
- Closed `P2.3b` with deterministic, small-sample CLI preflight assertions in
  `tests/test_cli_main.py`, including exact missing-required-file failure behavior and stable error
  classification under controlled repo layouts.
- Marked `P2.3` complete now that both `P2.3a` and `P2.3b` are closed.
- Queued next extraction slice (ASAP closure path): begin Phase 3 (`P3.1a`) by validating and
  tightening Sphinx config/package surface (theme/extensions/autosummary defaults) now that Phase 2
  modularization + minimal helper test coverage are complete.
- Closed `P3.1a` by upgrading `docs/conf.py` with explicit extension defaults
  (`sphinx.ext.autodoc`, `sphinx.ext.autosummary`, `sphinx.ext.napoleon`,
  `sphinx.ext.viewcode`) plus optional enablement for `nbsphinx` and
  `sphinx_rtd_theme` when installed in the environment.
- Added `autosummary_generate = True`, notebook-checkpoint exclusions, and resilient theme/static
  settings so docs builds stay warning-clean under `-W` even when optional packages are absent.
- Queued next extraction slice (ASAP closure path): continue `P3.1` with `P3.1b` by adding
  `docs/reference/cli.rst` and wiring `docs/index.rst` to mirror current CLI help surface.
- Closed `P3.1b` by replacing the docs placeholder index with a real reference toctree and adding
  `docs/reference/cli.rst` containing the current `python -m femic --help` command/option surface
  (top-level plus `run`, `prep`, `vdyp`, `tsa`, and `tipsy` subcommand entries).
- Queued next extraction slice (ASAP closure path): close `P3.1c` with a GitHub Pages docs build
  workflow that runs Sphinx in CI and publishes `_build/html`.
- Closed `P3.1c` by adding `.github/workflows/docs-pages.yml` with PR/push docs build, strict
  `sphinx-build -W` gating, artifact upload, and deploy-to-Pages on pushes to `main`.
- Marked `P3.1` complete now that docs config, reference content, and Pages CI publishing are all
  in place.
- Queued next extraction slice (ASAP closure path): start `P3.2a` by mapping current `femic` CLI
  commands/subcommands to a draft Nemora task taxonomy table in docs.
- Closed `P3.2a` by adding `docs/reference/nemora-task-map.rst` and wiring it into docs index
  to map current CLI entries (`run`, `prep run`, `vdyp run/report`, `tsa run`,
  `tipsy validate`) to draft Nemora task keys.
- Queued next extraction slice (ASAP closure path): close `P3.2b` by inventorying extracted shared
  utilities and tagging top upstream candidates (diagnostics/logging/path/runtime helpers).
- Closed `P3.2b` by adding `docs/reference/nemora-upstream-candidates.rst` and wiring it into docs
  index with a prioritized inventory of extracted helper modules suitable for Nemora upstreaming.
- Marked `P3.2` complete now that CLI taxonomy mapping and upstream-candidate inventory are both in
  place.
- Queued next extraction slice (ASAP closure path): start `P3.3a` by adding a first config file
  schema for selecting TSA/mode flags and mapping it into existing run option parsing.
- Closed `P3.3a` by adding YAML/JSON run-profile loading
  (`load_pipeline_run_profile(...)`) and explicit CLI/profile merge logic
  (`resolve_effective_run_options(...)`) for `femic run` TSA/strata/mode selection.
- Added `--run-config` support in `femic run`, a template profile at
  `config/run_profile.example.yaml`, and reference docs for schema/precedence in
  `docs/reference/run-config.rst`.
- Added deterministic coverage for run-profile loading/validation and CLI integration in
  `tests/test_pipeline_helpers.py` and `tests/test_cli_main.py`.
- Queued next extraction slice (ASAP closure path): close `P3.3b` by extending run manifest payload
  metadata with profile/config provenance and versioned output-root annotations.
- Closed `P3.3b` by extending run metadata through `PipelineRunConfig`/`LegacyExecutionPlan` with
  output-root + config provenance fields and surfacing them in manifest payload sections
  (`config_provenance`, `outputs`, and output-root option/path annotations).
- Added manifest/run-config coverage updates in `tests/test_pipeline_helpers.py` and
  `tests/test_legacy_manifest.py` plus SHA256 helper coverage for profile provenance digests.
- Marked `P3.3` complete now that config selection/mode wiring and manifest/version metadata are
  both in place.
- Queued next extraction slice (ASAP closure path): start `P3.4a` by auditing bootstrap/sample
  randomness seams and introducing explicit seed controls where stochastic behavior still exists.
- Closed `P3.4a` by adding explicit deterministic seed controls across VDYP sampling helpers:
  `run_vdyp_sampling(...)`, `run_vdyp_for_stratum(...)`, and bootstrap dispatch sequencing with
  per-stratum/SI derived seeds.
- Added `FEMIC_SAMPLING_SEED` env support for deterministic bootstrap/sample draws and coverage in
  `tests/test_vdyp_stage.py` for fixed-seed sampling stability and per-dispatch seed derivation.
- Queued next extraction slice (ASAP closure path): close `P3.4b` by ensuring run manifests capture
  full runtime/tool version metadata consistently for config-driven and non-config runs.
- Closed `P3.4b` by extending manifest payload runtime metadata capture with an explicit
  `runtime_parameters` block and seed/config provenance fields (`FEMIC_SAMPLING_SEED`,
  `FEMIC_RUN_CONFIG_*`, output-root metadata).
- Added regression assertions in `tests/test_legacy_manifest.py` for runtime-parameter sections and
  seed/config provenance values.
- Marked `P3.4` complete now that deterministic seed control and runtime parameter/version metadata
  capture are both implemented.
- Queued next extraction slice (ASAP closure path): start `P3.5a` by updating README workflow docs
  to reflect run-config profiles, manifest provenance fields, and deterministic sampling controls.
- Closed `P3.5a` by updating `README.md` workflow documentation for config-driven runs
  (`--run-config`), deterministic sampling control (`FEMIC_SAMPLING_SEED`), and manifest metadata
  sections used for reproducibility/audit.
- Closed `P3.5b` by adding a concise end-to-end quickstart flow in `README.md` covering
  CLI help check, TIPSY config validation, single-TSA run, and VDYP diagnostics reporting.
- Marked `P3.5` complete now that workflow handoff docs and quickstart are both in place.
- Queued next extraction slice (ASAP closure path): run a final roadmap consistency pass and
  prepare branch for merge/deployment handoff.
- Completed final roadmap consistency pass: all Phase 1/2/3 checklist items are now checked,
  including parent closeout for `P2.1` (its sub-items were already complete).
- Branch is ready for merge/deployment handoff.
- Added `planning/TSA29_dataset_compile_plan.md` with an explicit runbook for compiling TSA 29,
  including the required `config/tipsy/tsa29.yaml` gate, config-driven run steps, diagnostics, and
  completion criteria.
- Debugged TSA29 TIPSY config bring-up blocker: replaced species-whitelist rule with a catch-all
  rule (`when: {}`) and added null defaults for optional schema columns (`SPP_2..5`, `PCT_2..5`,
  `GW_*`, `GW_age_*`) so `tipsy_params_columns` projection succeeds.
- Re-ran TIPSY stage directly from cached TSA29 artifacts (`vdyp_prep-tsa29.pkl`,
  `vdyp_results-tsa29.pkl`, `vdyp_curves_smooth-tsa29.feather`) and regenerated
  `data/tipsy_params_tsa29.xlsx` + `data/02_input-tsa29.dat` with 30 AU rows (10 strata x 3 SI).
- Immediate next queue: have user run BatchTIPSY against `data/02_input-tsa29.dat`, upload
  `data/04_output-tsa29.out`, then execute 01b/post-01b assembly to validate full end-to-end TSA29
  compile.
- Added a dedicated downstream CLI recovery path for manual BatchTIPSY handoff:
  `python -m femic tsa post-tipsy --tsa <code> [-v]`.
- Implemented `run_post_tipsy_bundle(...)` in `src/femic/workflows/legacy.py` to run 01b from
  cached TSA artifacts (`vdyp_prep-tsaXX.pkl`, `vdyp_curves_smooth-tsaXX.feather`) and rebuild
  `data/model_input_bundle/{au_table,curve_table,curve_points_table}.csv` without re-running the
  full 00/01a front-half.
- Added regression coverage for command wiring and downstream assembly in
  `tests/test_cli_main.py` and `tests/test_workflows_post_tipsy.py`.
- Immediate next queue: polish 01b runtime warnings (deprecated
  `delim_whitespace`, figure-close loop, lexsort warnings) and add a run manifest entry for the
  new `tsa post-tipsy` command.
- Added targeted `vdyp_io` ignore rules in `.gitignore` for generated scratch artifacts
  (`vdyp_err_*`, `vdyp_out_*`, `vdyp_ply_*`, `vdyp_lyr_*`, and tmp dirs/files) so `git status`
  stays clean while retaining tracked `vdyp_io/VDYP_CFG` assets.
- Updated ignore strategy to also exclude volatile local `vdyp_io/VDYP_CFG` runtime files
  (`VDYP7_BACK.ctl`, `VDYP7_VDYP.ctl`, `vdyp7.log`) and untracked them from git index so repeated
  model runs no longer generate persistent dirty-state churn.
- Closed queued runtime-noise cleanup for 01b:
  replaced deprecated `delim_whitespace` parsing with `sep="\\s+"`, pre-sorted the VDYP curve
  MultiIndex once before per-AU plotting, and added explicit `plt.close(fig)` in the loop to
  prevent figure accumulation warnings during `tsa post-tipsy` runs.
- Closed queued run-manifest/audit logging for `femic tsa post-tipsy`:
  added workflow-level manifest emission (`started`/`ok`/`failed`) with runtime metadata + output
  artifact checks, and wired CLI `--run-id`/`--log-dir` through the command.
- Started TSA29 TIPSY rule quality tuning: replaced single-species catch-all behavior with ordered
  provisional BEC/species-group rules (pine, fir, spruce, balsam pathways) including species mixes,
  adjusted density/utilization, and modest GW settings while preserving final catch-all coverage.
- Added regression coverage in `tests/test_tipsy_config.py` for key TSA29 rule matches
  (MS pine pathway and IDF fir pathway).
- Regenerated `data/tipsy_params_tsa29.xlsx` + `data/02_input-tsa29.dat` from cached TSA29
  artifacts using the tuned ruleset so next BatchTIPSY run can proceed immediately.
- Remaining immediate queue: run BatchTIPSY with the new TSA29 input, re-run
  `femic tsa post-tipsy --tsa 29`, then add managed-vs-unmanaged curve-dominance regression
  assertions from the refreshed outputs.
- Upgraded TSA29 TIPSY parameter rules to TSR-anchored assumptions using Williams Lake data
  package references:
  `reference/29ts_dpkg_2024-2.pdf` (Section 8.5) and
  `reference/williams_lake_tsa_data_package-2.pdf` (Section 6.3 Tables 23-25).
- Updated `config/tipsy/tsa29.yaml` from provisional heuristics to ordered BEC/species pathways
  with explicit treated/untreated proportions, regeneration delays, species mixes, densities, and
  genetic-worth values aligned to TSR assumptions, while preserving catch-all coverage.
- Synced TSA29 config tests in `tests/test_tipsy_config.py` to the new rule expectations.
- Fixed a TSA29 resume-path loader defect in `src/femic/pipeline/vdyp_stage.py` by adding
  fallback reads for plain Feather caches lacking GeoPandas metadata.
- Forced 01a rerun for TSA29 and regenerated `data/02_input-tsa29.dat` from cached artifacts
  under the new ruleset (30 AU rows retained; values changed materially).
- Immediate next queue:
  user runs BatchTIPSY with regenerated `data/02_input-tsa29.dat`, uploads refreshed
  `data/04_output-tsa29.out`, then we run
  `python -m femic tsa post-tipsy --tsa 29 --run-id <id> -v`
  and validate refreshed `tipsy_vdyp_tsa29-*.png` behavior.
- Added custom management-unit boundary mode for `femic run` profiles:
  `selection.boundary_path`, `selection.boundary_layer`, and `selection.boundary_code`
  now flow from run profile to legacy execution env (`FEMIC_BOUNDARY_*`).
- Implemented boundary-mode extraction in `00_data-prep.py`:
  when `FEMIC_BOUNDARY_PATH` is set, FEMIC unions that layer geometry and uses it as the
  VRI mask for the selected run code (e.g., `k3z`), forcing no-cache execution.
- Added a complete K3Z test-case scaffold:
  `config/run_profile.k3z.yaml`, `config/tipsy/tsak3z.yaml`, and
  `planning/K3Z_dataset_compile_plan.md`.
- Extended TIPSY config discovery/validation to support non-numeric case codes
  (`tsak3z.yaml`) in addition to numeric TSA configs.
- Removed numeric-TSA assumptions in downstream ID assembly by introducing a deterministic
  named-code AU prefix path in `src/femic/pipeline/bundle.py` and `src/femic/pipeline/tsa.py`.
- Ran smoke execution for K3Z (`--debug-rows 20`, no BatchTIPSY output yet):
  run completed and emitted manifest
  `vdyp_io/logs/run_manifest-k3z_smoke5_20260304_221317.json`,
  generating `data/02_input-tsak3z.dat` and `data/tipsy_params_tsak3z.xlsx`.
- Immediate next queue:
  run full K3Z step 1a without debug-row truncation, then user runs BatchTIPSY on
  `data/02_input-tsak3z.dat`, uploads `data/04_output-tsak3z.out`, and we execute
  `python -m femic tsa post-tipsy --tsa k3z --run-id <id> -v`.
- Hardened config-driven TIPSY mix output (`src/femic/pipeline/tipsy_config.py`) to eliminate
  known BatchTIPSY failure patterns in treated rows:
  normalize `SX -> SW`, drop treated broadleaf species from `f` mixes, enforce descending
  species order (dominant species in `SPP_1`), and force exact integer composition sums to 100.
- Added regression coverage in `tests/test_tipsy_config.py` for mix normalization and TSA29 rule
  behavior (`AT`/`SX` removed from treated `f` rows, dominant species promoted to `SPP_1`,
  `% composition == 100`).
- Validation gate completed for this slice:
  `.venv/bin/ruff format src tests`, `.venv/bin/ruff check src tests`,
  `.venv/bin/mypy src`, `.venv/bin/pytest`, `.venv/bin/pre-commit run --all-files`.
- Immediate next queue:
  regenerate TSA29 step 1a artifacts (`data/tipsy_params_tsa29.xlsx`, `data/02_input-tsa29.dat`)
  from a clean non-stalled run path, then rerun BatchTIPSY and post-tipsy downstream assembly.
- Added config-driven SI tuning support in `src/femic/pipeline/tipsy_config.py`:
  per-side `SI_offset` (or `si_offset`) can now be set in either `defaults.{e,f}` or any
  rule `assign.{e,f}` block; final per-side SI is computed as
  `round(computed_vdyp_si + SI_offset, 1)`.
- Updated TSA29 config defaults to apply a +2.0 managed-side SI bump directly in config:
  `config/tipsy/tsa29.yaml -> defaults.f.SI_offset: 2.0`.
- Added/updated tests in `tests/test_tipsy_config.py` for side-specific SI offset handling
  and TSA29 +2 SI expectations.
- Regenerated TSA29 step-1a artifacts from cached TSA29 prep outputs with the new config:
  `data/tipsy_params_tsa29.xlsx` and `data/02_input-tsa29.dat` now embed the +2 managed SI
  adjustment without manual dat editing.
- Extended TIPSY SI tuning from additive-only to linear transform support in
  `src/femic/pipeline/tipsy_config.py`:
  per-side config can now define `SI_c1` and `SI_c2` (plus lowercase aliases), applied as
  `SI_final = SI_c1 * SI_baseline + SI_c2` (with legacy `SI_offset` still honored).
- Updated TSA29 managed defaults to explicit linear form in `config/tipsy/tsa29.yaml`:
  `defaults.f.SI_c1: 1.0`, `defaults.f.SI_c2: 2.0` (equivalent to fixed +2 SI).
- Added regression tests in `tests/test_tipsy_config.py` for linear SI transform behavior and
  retained backward-compatible SI offset coverage.
- Updated TIPSY config docs/templates:
  `config/tipsy/README.md` and `config/tipsy/template.tsa.yaml` now describe SI linear tuning
  fields and usage.
- Added TSA29 VDYP smoothing override for pathological curve AU 21005 (`SBPS_PL`, `L`) in
  `src/femic/pipeline/vdyp_overrides.py`: `skip1=50`.
- Added default per-curve VDYP fit diagnostic plot generation in
  `src/femic/pipeline/vdyp_stage.py` during smoothing runs:
  each stratum/SI now emits `plots/vdyp_fitdiag_tsaXX-<stratumi>-<stratum>-<si>.png` showing
  observed 5-year binned median/IQR vs fitted curve.
- Re-ran TSA29 01a/01b and post-tipsy stages to validate integration:
  AU 21005 unmanaged curve corrected from early spike (peak 943.9 @ age 19) to a coherent shape
  (peak 96.3 @ age 223), and fresh overlays/diagnostics were written.
- Extended VDYP smoothing diagnostics in `src/femic/pipeline/vdyp_stage.py` to compare
  three fit flavours per stratum/SI on each default fitdiag PNG:
  baseline/current, sigma-asymmetric candidate, tail-blend candidate, plus conditional
  auto-skip candidate when heuristically detected and validation-approved.
- Extended `src/femic/pipeline/vdyp_curves.py` with two candidate-fit controls used by the new
  diagnostics:
  right-tail sigma reweighting (`sigma_right_scale`/`sigma_right_offset`) and optional
  right-tail linear blend (`tail_blend_enabled`, anchor/blend/slope controls).
- Added first-pass auto left-tail anomaly detection in `execute_curve_smoothing_runs(...)`:
  infer suggested `skip1` from early-age overshoot, rerun, and only accept candidate when it
  clears all validation gates (`rmse`, `tail_rmse`, `early_overshoot` vs baseline).
- Ran TSA29 targeted smoothing from cached prep/results artifacts (no full rerun required) and
  regenerated:
  `data/vdyp_curves_smooth-tsa29.feather`,
  `plots/vdyp_fitdiag_tsa29-*.png` (30 files),
  and comparison summary `plots/vdyp_fitdiag_tsa29_metrics_compare.csv`.
- Quick quantitative readout from `vdyp_fitdiag_tsa29_metrics_compare.csv`:
  best-overall-RMSE counts across 30 curves were `tail_blend=18`, `sigma_asym=9`, `current=3`;
  best-tail-RMSE counts were `sigma_asym=18`, `tail_blend=9`, `current=3`.
  Auto-skip was suggested in 18 curves but validated in 0 under current strict acceptance gates.
- Follow-up fit-logic revision based on visual QA feedback:
  removed `sigma_asym` candidate from default diagnostics and switched focus to a stronger
  tail-blend approach.
- Updated `src/femic/pipeline/vdyp_curves.py` tail blend algorithm to detect a rightmost linear
  binned segment automatically (maximal contiguous tail from the right that meets
  `R^2 >= tail_linear_min_r2` and `NRMSE <= tail_linear_max_nrmse`), then blend the current NLLS
  curve into that linear tail. If no credible linear tail exists, it naturally falls back to
  raw/current behavior (no tail override).
- New tail controls in `process_vdyp_out(...)`:
  `tail_linear_min_points`, `tail_linear_min_r2`, `tail_linear_max_nrmse`
  (with existing `tail_blend_years` and slope bounds still applied).
- Updated default fitdiag plotting in `src/femic/pipeline/vdyp_stage.py` to show:
  `current`, `tail_blend`, and validated `auto_skip` only.
- Re-ran TSA29 smoothing from cached artifacts and regenerated:
  `data/vdyp_curves_smooth-tsa29.feather`,
  30 plots at `plots/vdyp_fitdiag_tsa29-*.png`,
  and tail-only comparison summary at
  `plots/vdyp_fitdiag_tsa29_metrics_tail_only.csv`.
- Tail-only readout on TSA29 (30 curves):
  `tail_blend` improved overall RMSE on 17 curves and improved tail RMSE on 17 curves;
  auto-skip remained suggested in 18 curves.
- Tail-blend failure diagnosis + heuristic correction (2026-03-05 follow-up):
  identified that quantile fallback and non-age-constrained tail selection were still allowing
  early-age pseudo-linear segments to be blended (for example ESSF_SE-L anchoring near age 65),
  causing severe regressions.
- Updated right-tail detection in `src/femic/pipeline/vdyp_curves.py` to require
  preferred-age tail candidates (`tail_linear_prefer_min_age`, default 200) and skip blending
  entirely when no preferred candidate passes thresholds.
- Kept quantile fallback disabled for TSA29 diagnostic runs
  (`tail_linear_allow_quantile_fallback=False`) so non-linear tails naturally retain
  the current/NLLS curve.
- Regenerated TSA29 fit diagnostics + metrics with the stricter age-aware logic:
  `plots/vdyp_fitdiag_tsa29-*.png` and
  `plots/vdyp_fitdiag_tsa29_metrics_tail_only.csv`.
- New outcome (TSA29, 30 curves):
  no catastrophic tail-blend failures remain; worst RMSE regression is now ~0.045
  (`IDF_FDI-L`) instead of multi-unit failures.
- Relaxed-tail detection calibration pass (to capture more long near-linear segments):
  in `src/femic/pipeline/vdyp_stage.py` updated candidate tail thresholds to
  `tail_linear_min_r2=0.82`, `tail_linear_max_nrmse=0.12`,
  `tail_linear_prefer_min_age=190.0`.
- Re-ran TSA29 smoothing + diagnostics with relaxed thresholds:
  tail-blend detection increased from 22/30 to 26/30 curve pairs (4 still intentionally skipped).
- Updated summary (`plots/vdyp_fitdiag_tsa29_metrics_tail_only.csv`) shows broader tail capture
  with controlled but non-zero tradeoff:
  `tail_better_rmse=15/30`, `tail_better_tail_rmse=15/30`;
  worst remaining regression is moderate (`IDF_PL-H`, delta RMSE ~ +0.67), with no catastrophic outliers.
- Added a detailed planning summary of this entire curve-fit enhancement stream at:
  `planning/VDYP_curve_fit_enhancements_2026-03-05.md`, including explicit TODO notes to
  continue tuning tail-fit hyperparameters later.
- Enhanced default fit diagnostic plotting for lecture/demo use:
  `src/femic/pipeline/vdyp_stage.py` now overlays raw per-sample VDYP curves
  (`Age` vs `Vdwb`) as fine low-alpha grey lines behind binned aggregates/fitted curves.
- Re-ran K3Z with updated fitting/plotting logic:
  `python -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_curvefit_enh_20260305`.
  Run completed and emitted manifest
  `vdyp_io/logs/run_manifest-k3z_curvefit_enh_20260305.json`.
- New K3Z fit diagnostics are available at `plots/vdyp_fitdiag_tsak3z-*.png` (9 plots for
  strata/SI combos with usable VDYP outputs: CWH_CW, CWH_FD, CWH_HW), with raw VDYP lines
  visible in the updated style.
- Ran full K3Z post-TIPSY integration using user-supplied BatchTIPSY output:
  copied `data/02_output-tsak3z.out` to expected runtime filename
  `data/04_output-tsak3z.out`, then executed
  `python -m femic run --run-config config/run_profile.k3z.yaml -v --resume --run-id k3z_posttipsy_20260306_062442`.
  Run completed successfully (manifest:
  `vdyp_io/logs/run_manifest-k3z_posttipsy_20260306_062442.json`) and regenerated K3Z artifacts,
  including `plots/strata-tsak3z.png`, `plots/tipsy_vdyp_tsak3z-*.png`,
  `data/tipsy_params_tsak3z.xlsx`, and `data/tipsy_curves_tsak3z.csv`.
- Debugged K3Z strata diagnostics regression and fixed summary/plot logic:
  `src/femic/pipeline/tsa.py::build_strata_summary(...)` now avoids reintroducing filtered strata
  as NaN rows, and falls back to unfiltered top strata when `min_standcount` removes everything
  (small custom boundaries).
- Improved strata plotting robustness in `src/femic/pipeline/plots.py`:
  relative-abundance ordering now tolerates missing `totalarea_p`,
  SI x-limits auto-expand to observed values (so high coastal SI is not clipped at 30),
  and sparse-strata `stripplot` points are overlaid on violins for visibility.
- Added K3Z-specific legacy TIPSY-vs-VDYP y-axis scaling helper
  `tipsy_vdyp_ylim_for_tsa(...)` (`0..1500` for `k3z`, default `0..600`) and wired
  `01b_run-tsa.py` to use it.
- Re-ran K3Z end-to-end with the fixes:
  `python -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_plotfix_20260306_063833`.
  Run completed (`status=ok`, manifest:
  `vdyp_io/logs/run_manifest-k3z_plotfix_20260306_063833.json`) with corrected
  01a diagnostics (`coverage 1.0`, `count 9`) and refreshed K3Z plot artifacts.
- Applied K3Z-focused scoping + comparison updates:
  set `TARGET_NSTRATA_BY_TSA["k3z"] = 4` in `src/femic/pipeline/tsa.py`
  to constrain the custom-boundary case to top-4 strata by area.
- Updated smoothing-output selection in `src/femic/pipeline/vdyp_stage.py` so K3Z
  exports tail-blend unmanaged curves (when available) to
  `vdyp_curves_smooth-tsak3z.feather` for downstream TIPSY-vs-VDYP comparison plots,
  while keeping fitdiag overlays unchanged (`current` + candidate curves).
- Added regression coverage:
  `tests/test_pipeline_helpers.py` now asserts `target_nstrata_for("k3z") == 4`,
  and `tests/test_vdyp_stage.py` now verifies K3Z smoothing output prefers tail-blend
  candidate curves when present.
- Deleted all stale K3Z plot artifacts (`plots/*tsak3z*`) and re-ran K3Z end-to-end:
  `python -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_n4_tailblend_20260306_064902`.
  Run completed (`status=ok`, manifest:
  `vdyp_io/logs/run_manifest-k3z_n4_tailblend_20260306_064902.json`) with
  01a diagnostics now reporting `count 4` and `coverage 0.9882` (top-4 strata only).
- Implemented adaptive SI split-count logic in `src/femic/pipeline/tsa.py` from per-stratum
  5th-95th percentile SI width:
  `< 5` -> `M` only, `5..10` -> `L/H`, `> 10` -> `L/M/H`.
- Wired the same adaptive SI quantile resolver into VDYP curve fitting
  (`src/femic/pipeline/vdyp_stage.py::fit_stratum_curves`) so fit outputs and AU definitions
  stay aligned for narrow-SI strata.
- Hardened SI assignment and AU mapping for variable split counts:
  `assign_si_levels_from_stratum_quantiles(...)` now supports optional
  `allowed_levels_by_stratum`, and `00_data-prep.py` passes allowed levels inferred from
  `au_table` so post-01b stand assignment cannot request non-existent SI bins.
- Updated TIPSY parameter assembly to tolerate missing per-stratum SI bins cleanly
  (`src/femic/pipeline/tipsy.py::build_tipsy_params_for_tsa` skips absent fit levels).
- Added regression coverage for adaptive split behavior and missing-level handling:
  `tests/test_pipeline_helpers.py`, `tests/test_tipsy.py`, `tests/test_vdyp_stage.py`.
- Re-validated K3Z end-to-end under the adaptive SI split logic:
  `FEMIC_NO_CACHE=1 PYTHONPATH=src .venv/bin/python -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_siwidth_verify_20260306_070055`.
  Run completed `status=ok` (manifest:
  `vdyp_io/logs/run_manifest-k3z_siwidth_verify_20260306_070055.json`), producing
  an 8-row K3Z TIPSY input table where `CWH_CW` is now correctly split into `L/H` only.
- Fixed K3Z comparison-plot scaling request:
  `src/femic/pipeline/plots.py::tipsy_vdyp_ylim_for_tsa(...)` now returns `0..2000`
  for `k3z` (was `0..1500`), with regression assertion updated in
  `tests/test_pipeline_helpers.py`.
- Fixed fitdiag regeneration behavior:
  1) `01a_run-tsa.py` now rebuilds smoothing outputs whenever `resume_effective=False`
     (so non-resume/no-cache runs do not silently reuse stale
     `vdyp_curves_smooth-tsa*.feather`), and
  2) `src/femic/pipeline/vdyp_stage.py` now emits fitdiag PNGs even when binned
     observations are missing (overlay is conditional, plot emission is unconditional).
- Fixed no-cache VDYP bootstrap cache reuse:
  `00_data-prep.py` now sets `force_run_vdyp = 1` whenever `_femic_no_cache` is active,
  preventing stale `data/vdyp_results-tsa*.pkl` reuse during no-cache/debug/custom-boundary runs.
- Fixed adaptive-SI bootstrap dispatch bug surfaced by forced reruns:
  `src/femic/pipeline/vdyp_stage.py::execute_bootstrap_vdyp_runs(...)` now skips missing/empty
  SI payloads per stratum (`status=skipped`, reason `missing_or_empty_si_sample`) instead of
  raising `KeyError` when a stratum has `L/H` only under adaptive split rules.
- Re-ran K3Z with forced fresh VDYP bootstraps:
  `FEMIC_NO_CACHE=1 PYTHONPATH=src .venv/bin/python -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_forcevdyp_fix_20260306_072037`.
  Run completed `status=ok` (manifest:
  `vdyp_io/logs/run_manifest-k3z_forcevdyp_fix_20260306_072037.json`) and regenerated
  current K3Z artifacts from fresh caches:
  `data/vdyp_results-tsak3z.pkl` (updated), 8 fitdiag plots (`plots/vdyp_fitdiag_tsak3z-*.png`)
  and 8 TIPSY-vs-VDYP comparison plots (`plots/tipsy_vdyp_tsak3z-*.png`).
- Extracted K3Z FSP stocking guidance from `data/bc/cfa/k3z/NICF-LP-Forest-Stewardship-Plan-Appendices-2020.pdf` (Appendix B, pp. 4-6) and replaced provisional K3Z TIPSY assumptions with FSP-informed mixed-species pathways in `config/tipsy/tsak3z.yaml`.
- Updated K3Z TIPSY rule set to use CWH-leading-species pathways (`CW/YC`, `HW/HM`, `FD/FDC`, `SS/SX`) with `Density=900`, `Regen_Delay=2`, and explicit mixed compositions summing to 100% instead of single-species 1400-sph defaults.
- Re-ran K3Z no-cache pipeline with new rules:
  `PYTHONPATH=src .venv/bin/python -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_fsp_rules_20260306_073524`.
  Run completed (`status=ok`, manifest `vdyp_io/logs/run_manifest-k3z_fsp_rules_20260306_073524.json`) and regenerated K3Z artifacts.
- Verified regenerated `data/02_input-tsak3z.dat` now reflects new FSP-informed parameters (8 rows; all rows `Density=900`, `Regen_Delay=2`, and mixed-species compositions such as `CW60/HW25/YC15`, `HW70/CW20/FD10`, `FD60/HW25/CW15`).
- Next: user runs BatchTIPSY with the refreshed K3Z DAT, uploads updated `data/04_output-tsak3z.out`, then we re-run post-TIPSY to evaluate whether TIPSY-vs-VDYP coherence improved under FSP-informed assumptions.
- Added a dedicated K3Z compile/iteration playbook at
  `planning/CFAK3Z_dataset_compile_plan.md`, adapted from TSA29 planning but
  rewritten for K3Z-specific constraints (small-area sparse strata, fixed BatchTIPSY
  field-map dependency, and iterative TIPSY-vs-VDYP tuning workflow).
- Documented next refinement queue for K3Z stratification:
  1) BEC subzone/variant/phase-based keys and
  2) top-N leading-species combination keys (start N=2, test N=3).
- Confirmed VRI attribute availability needed for this refinement from local 2019
  GDB (`BEC_SUBZONE`, `BEC_VARIANT`, `BEC_PHASE`, `SPECIES_CD_1..6`,
  `SPECIES_PCT_1..6`, SI fields).
- Confirmed `data/bc/vri/VEG_COMP_LYR_R1_POLY_2024.gdb.zip` currently fails unzip
  integrity checks (incomplete/corrupt), so K3Z refinement should proceed on
  existing readable VRI until a clean 2024 download is available.

- Added configurable stratum-key controls to the run-profile/env pipeline:
  `selection.stratification.bec_grouping` (`zone|subzone|variant|phase`),
  `selection.stratification.species_combo_count` (top-N species by `SPECIES_PCT_1..6`),
  and `selection.stratification.include_tm_species2_for_single`.
- Wired those controls from YAML -> effective run options -> legacy execution env
  (`FEMIC_STRAT_*`) -> `00_data-prep.py` -> `assign_stratum_codes_with_lexmatch(...)`,
  with backward-compatible defaults so existing TSA runs keep legacy behavior.
- Updated K3Z run profile to exercise finer strata by default:
  `config/run_profile.k3z.yaml` now sets `bec_grouping: subzone` and
  `species_combo_count: 2`.
- Confirmed local VRI schema supports this path (fields present in 2019 GDB):
  `BEC_SUBZONE`, `BEC_VARIANT`, `BEC_PHASE`, `SPECIES_CD_1..6`, `SPECIES_PCT_1..6`.
- Updated legacy external-data path resolution to prefer 2024 VRI when present, with
  automatic fallback to 2019:
  `bc/vri/2024/VEG_COMP_LYR_R1_POLY_2024.gdb` -> `bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb`.
- Added explicit source-path startup prints in `00_data-prep.py` so each run reports the
  exact VRI and TSA boundary datasets in use.
- Added regression coverage to lock 2024-first behavior:
  `tests/test_pipeline_helpers.py::test_resolve_legacy_external_data_paths_prefers_2024_vri_when_available`.
- Extended external-data resolver to also pick a paired VDYP input GDB (2024-first, then 2019)
  and wired `00_data-prep.py` to use that resolved path, with startup printout:
  `using VDYP input source: ...`.
- Verified 2024 K3Z runs now resolve both:
  `VEG_COMP_LYR_R1_POLY_2024.gdb` and
  `VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb`.
- Current blocker on 2024 K3Z compile quality:
  01a VDYP bootstrap events are all `empty_output`, resulting in
  `data/vdyp_curves_smooth-tsak3z.feather` with `0` rows and thus an empty
  `data/02_input-tsak3z.dat`. This points to a 2024 schema/field-mapping mismatch in
  VDYP input preparation rather than path resolution.
- Completed 2024 VDYP ID-domain fix for K3Z:
  in `run_vdyp_for_stratum(...)` (`src/femic/pipeline/vdyp_stage.py`), bootstrap dispatch now
  resolves sampled source `FEATURE_ID`s to the VDYP table key space using `MAP_ID` when direct
  `FEATURE_ID` overlap is absent, then maps returned VDYP outputs back to source IDs for cache
  compatibility.
- Added regression coverage for the map-join fallback:
  `tests/test_vdyp_stage.py::test_run_vdyp_for_stratum_maps_source_feature_ids_via_map_id`
  asserts that non-overlapping source IDs are bridged through `MAP_ID` and still return results
  keyed by original source `FEATURE_ID`.
- Re-ran full no-cache K3Z pipeline against 2024 VRI+VDYP inputs:
  `FEMIC_NO_CACHE=1 PYTHONPATH=src .venv/bin/python -u -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_vri2024_mapfix_20260307`.
  Run completed `status=ok` with non-empty outputs (`data/vdyp_curves_smooth-tsak3z.feather`
  rows `= 3588`, `data/02_input-tsak3z.dat` lines `= 13`) and VDYP report showing no empty-output
  failures (`status counts: dispatch=12, start=12, ok=12`).
- Consulted the local VRI metadata PDFs in `docs/reference` to avoid schema guessing while
  debugging (`vegcomp_poly_rank1_data_dictionaryv5_2019*.pdf`,
  `vegcomp_toc_data_dictionaryv5_2019.pdf`); practical takeaway for this run path remains:
  `MAP_ID` is the reliable bridge field across 2024 VRI rank1 samples and 2024 VDYP input layers
  when `FEATURE_ID` domains diverge.
- Added profile/env support for cumulative top-strata selection by area coverage:
  new config key `selection.stratification.top_area_coverage` (wired through CLI/profile/env as
  `FEMIC_STRAT_TOP_AREA_COVERAGE`) and 01a runtime (`target_area_coverage`) now drive
  `build_strata_summary(..., target_coverage=...)`.
- K3Z profile now sets `top_area_coverage: 0.95` in `config/run_profile.k3z.yaml`.
- Re-ran K3Z no-cache with 95% top-area cutoff:
  `FEMIC_NO_CACHE=1 PYTHONPATH=src .venv/bin/python -u -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_cov95_20260307`.
  Result: `coverage=0.95565930139286`, `count=13` strata in 01a (up from 4).
- BEC hierarchy check on selected strata: all selected strata are still identical at
  zone+subzone (`CWHvm`), and also at zone+subzone+variant (`CWHvm1`) and phase (all null),
  so deeper BEC hierarchy splitting cannot add signal for K3Z with current VRI attributes.
- SI split diagnostics for this 95% run show many sparse bins in the long-tail strata
  (`L/M/H` counts often 0-2 stands), with multiple `skipped` or `empty_output` VDYP events;
  this supports a likely next change to collapse SI splitting for sparse strata in K3Z.
- Implemented user-requested K3Z stratification reset and stabilization path:
  `top_area_coverage` lowered to `0.80`, adaptive SI-width split override removed,
  and SI bins restored to fixed quantile bands (`L=5..35`, `M=35..65`, `H=65..95`).
- Added post-fit adjacent SI-curve merge support in TIPSY AU assembly
  (`src/femic/pipeline/tipsy.py::build_tipsy_params_for_tsa`), with configurable
  relative-gap thresholds over a bounded age window; merged groups now map to a
  shared AU while preserving per-stratum diagnostics (`si-groups [...]`).
- Fixed merged-AU downstream regression failure in bundle assignment:
  `assign_curve_ids_from_au_table(...)` now handles duplicate `au_id` rows
  (introduced by SI merges) by collapsing to first non-null managed/unmanaged
  curve IDs before managed/unmanaged curve selection.
- Hardened stand-export AU lookup for merged AUs:
  `prepare_stands_export_frame(...)` now resolves `theme3` canfi species safely
  when `au_table` has duplicate `au_id` rows.
- Added regression tests for merged-AU duplicate-row behavior:
  `tests/test_bundle.py::test_assign_curve_ids_from_au_table_handles_duplicate_au_rows`
  and `tests/test_stands.py::test_prepare_stands_export_frame_handles_duplicate_au_rows`.
- Re-validated K3Z end-to-end with requested settings:
  `FEMIC_NO_CACHE=1 PYTHONPATH=src .venv/bin/python -u -m femic run --run-config config/run_profile.k3z.yaml -v --run-id k3z_cov80_fixedsi_merge_debug2_20260307`
  now completes `status=ok` (manifest:
  `vdyp_io/logs/run_manifest-k3z_cov80_fixedsi_merge_debug2_20260307.json`).
- Next tuning focus (as requested): keep fixed quantile SI bins, then adjust
  post-fit merge criteria to avoid over-fragmentation while preserving clearly
  distinct VDYP curve families.
- Implemented pre-fit SI-bin stabilization in `fit_stratum_curves(...)`:
  added `min_stands_per_si_bin` (default `25`) and automatic adjacent-bin collapse before
  NLLS fitting; collapse actions are now logged per stratum (for sparse K3Z bins this
  prevents fragile one- or two-stand regressions).
- Updated TIPSY SI-level merge logic in `build_tipsy_params_for_tsa(...)` to use a
  combined criterion instead of max-relative-gap alone:
  merge now requires both `max_relative_gap <= threshold` and
  `window_nrmse <= threshold` over a shared age window; merge diagnostics now print
  `gap/rmse/nrmse` values.
- Added deterministic config-driven species/siteprod overrides for weak mapping cases:
  `species_code_overrides` (for example `DR -> FD`) and
  `siteprod_si_fallback_by_species` are now supported by `tipsy_config` builders and
  consumed by candidate evaluation when siteprod SI is absent/invalid.
- Added requested stratum-level L/M/H overlay plot output:
  `execute_curve_smoothing_runs(...)` now emits
  `plots/vdyp_lmh_tsa<tsa>-<stratum>-<code>.png` so L/M/H best-fit curves are visible on
  one panel for ordering/material-difference QA.
- Wired legacy siteprod source resolution to prefer
  `data/bc/siteprod/Site_Prod_BC.gdb` (fallback to legacy root path), and surfaced the
  resolved path in 00-data-prep startup logging.
- Re-ran full no-cache K3Z with fresh 2024 VRI/VDYP + fresh siteprod source:
  `run_id=k3z_siteprod_refresh_20260307` completed `status=ok` with updated fitdiag,
  L/M/H overlay, and TIPSY-vs-VDYP plot outputs under `plots/`.
- Next tuning queue (explicitly requested): continue calibrating post-fit tail/merge
  hyperparameters and SI-bin collapse thresholds now that the new diagnostics are in place.
- Two-pass K3Z rebin regression root cause identified: stale TSA-specific VDYP feather caches
  (`data/vdyp_ply-tsak3z.feather`, `data/vdyp_lyr-tsak3z.feather`) were still being reused even
  under `FEMIC_NO_CACHE=1`, so first-pass VDYP key remap operated on mismatched IDs.
- Fixed loader precedence and cache refresh behavior:
  `load_vdyp_input_tables(...)` now prioritizes explicit `source_feature_ids` over `source_map_ids`,
  and 01a now forces VDYP source reload whenever `runtime_config.force_run_vdyp` is true.
- Fixed VDYP output remap robustness:
  `run_vdyp_for_stratum(...)` now maps per-table outputs back to resolved feature IDs via VDYP
  table attrs (`Map Name` + `Polygon`) before ID/order fallbacks, handling table-number keyed
  outputs and extra-table cases.
- Verified with fresh no-cache K3Z run
  (`run_id=k3z_twopass_fix5_20260307`): two-pass now reports
  `mapped VDYP SI for 194/251 rows` (was `0/251`), `missing=3 of 447` in cache-table rebuild
  (was `447/447`), and full downstream TIPSY/bundle stages complete without empty-curve failure.
- Added configurable SI-bin collapse threshold to run profiles:
  `modes.vdyp_min_stands_per_si_bin` now flows from YAML/CLI profile parsing into
  legacy env (`FEMIC_VDYP_MIN_STANDS_PER_SI_BIN`) and into 01a stratum fitting
  (`build_stratum_fit_run_config(min_stands_per_si_bin=...)`).
- Updated K3Z test profile for current iteration:
  `config/run_profile.k3z.yaml` now uses `top_area_coverage: 0.90` and
  `modes.vdyp_min_stands_per_si_bin: 10` (with `species_combo_count: 2`).
- Executed no-cache K3Z validation run with these settings:
  `tmp/k3z_sc2_restore.log` reports `coverage=0.90655`, `count=9` selected strata,
  and currently generated AU bundle has `27` AUs (`9 strata x 3 SI levels`), with
  Sitka spruce present (`CWHvm_HW+SS`).
- Executed comparison run for 3-species stratification under same thresholds:
  `tmp/k3z_sc3_run.log` reports `coverage=0.90153`, `count=25` selected strata;
  resulting AU bundle expanded to `66` AUs (`22 strata x 3 SI levels` after downstream
  consolidation), confirming species-combo=3 greatly increases fragmentation.
- Next suggested tuning step for teaching-case usability: keep species-combo=2 as
  default, then selectively carve SS-focused strata via explicit rule/override
  rather than globally increasing to species-combo=3.
- Added AU species-proportion curve export in post-TIPSY bundle assembly:
  for each AU, `curve_table/curve_points_table` now include
  `unmanaged_species_prop_<SPP>` and `managed_species_prop_<SPP>` curves (single-point at `x=1`).
- Species universe for these curves is pre-scanned from inventory checkpoint
  `data/ria_vri_vclr1p_checkpoint8.feather` using top-6 VRI slots (`SPECIES_CD_1..6` with
  positive `SPECIES_PCT_*`) scoped to selected TSA(s); this yields a full consistent per-AU
  species set (zero-valued curves emitted for absent species in a specific AU).
- Unmanaged species proportions are sourced from VDYP fit payload species shares per
  `(stratum_code, si_level)`; managed species proportions are sourced from
  `tipsy_sppcomp_tsa<tsa>.csv` proportions.
- Added regression coverage for species-proportion curve emission:
  `tests/test_bundle.py::test_build_bundle_tables_from_curves_adds_species_proportion_curves`.
- 2026-03-08 (TIPSY DAT hardening): finalized fixed-schema DAT rendering in `src/femic/pipeline/tipsy.py` using explicit row/header start maps, mandatory full schema columns (including blank GW/SPP slots), and fixed-length line emission so BatchTIPSY column mappings remain stable for sparse K3Z mixes.
- 2026-03-08 (verification): regenerated `data/02_input-tsak3z.dat` from `data/tipsy_params_tsak3z.xlsx`; row slices now cleanly parse expected values (`PCT_1=70`, `SI=23.9`, `SPP_2=CW`, `PCT_2=20`, `SPP_3=FD`, `PCT_3=10`) without `7023.` concatenation.
- 2026-03-08 (TIPSY DAT alignment fix #2): switched DAT row layout to exact 1-based BatchTIPSY wizard indices from the user screenshots (converted to 0-based in code), including sparse-field ranges like `PCT_1: 61-63`, `Regen_Method: 64`, `SI: 108-111`, `SPP_2: 129-131`, `PCT_2: 136-137`, etc.; line length now fixed at 231 chars to match GW_age_5 end column.
- 2026-03-08 (TIPSY DAT anti-regression hardening): introduced a single canonical `DEFAULT_TIPSY_BATCH_COLUMNS_1BASED` schema (directly mirroring BatchTIPSY wizard indices), derive 0-based starts/widths from it, and enforce per-row fixed-width slice validation before writing DAT output; generator now fails fast on any field overflow/misalignment.
- 2026-03-08: Per request, removed all prior plot files and ran a full fresh no-cache K3Z compile using current profile settings; produced a clean single set of regenerated K3Z plots for review (`run_id=k3z_fresh_20260308_032428`).
- 2026-03-08: Added a profile-driven managed-yield fallback mode for teaching/small-case stability (`modes.managed_curve_mode: vdyp_transform`) that synthesizes managed curves directly from VDYP unmanaged curves via configurable transforms (`x_scale`, `y_scale`, culmination-tail truncation, `max_age`).
- 2026-03-08: Applied this mode to K3Z profile (`x_scale=0.8`, `y_scale=1.2`, truncate tail, max age 300), cleared old plots, and reran a full fresh no-cache K3Z compile (`run_id=k3z_vdyp_managed_20260308_1`) producing a clean regenerated plot set.
- 2026-03-08: Added a new roadmap phase (`Phase 4`) to track `femic.fmg` delivery:
  Patchworks-first ForestModel XML + fragments shapefile generation from current FEMIC outputs,
  with Woodstock portability work carried in parallel but prioritized second.
- 2026-03-08: Added initial `femic.fmg` implementation in `src/femic/fmg/patchworks.py`:
  ForestModel XML writer, fragments shapefile builder, and high-level
  `export_patchworks_package(...)` orchestration wired from bundle/checkpoint artifacts.
- 2026-03-08: Added `femic export patchworks` CLI command in `src/femic/cli/main.py`
  with configurable TSA list, bundle/checkpoint paths, planning horizon, CC age window,
  output directory, and fragments CRS.
- 2026-03-08: Fixed Patchworks fragments export for feather checkpoints with WKB geometry payloads:
  exporter now normalizes bytes/memoryview/hex geometries before GeoDataFrame construction.
- 2026-03-08: Added regression coverage for Patchworks export in
  `tests/test_fmg_patchworks.py` and `tests/test_cli_main.py` (XML content, fragments fields,
  CLI wiring, WKB decode case).
- 2026-03-08: Updated user-facing docs for Patchworks export:
  `README.md` quickstart and `docs/reference/cli.rst` command reference.
- 2026-03-08: Ran full milestone validation gates after export implementation:
  `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
  `pre-commit run --all-files`, and `sphinx-build -b html docs _build/html -W` all passing.
- 2026-03-08: Added fail-fast Patchworks validation in `src/femic/fmg/patchworks.py`:
  `validate_forestmodel_xml_tree(...)` now checks required ForestModel nodes/attrs,
  required define fields, curve-idref integrity, and CC treatment presence; and
  `validate_fragments_geodataframe(...)` now checks required fragment schema,
  value domains (`IFM`), geometry validity/non-null, uniqueness of `BLOCK`,
  numeric coercion, and positive area.
- 2026-03-08: Hooked validations into export orchestration:
  `export_patchworks_package(...)` now validates XML tree and fragments data before writing.
- 2026-03-08: Added regression tests for validation rules in
  `tests/test_fmg_patchworks.py` (missing curve-idref detection and invalid IFM rejection).
- 2026-03-08: Validated Patchworks package builds for both active test cases:
  `k3z` via direct CLI export from current bundle/checkpoint, and `tsa29` via
  a reconstructed TSA29 validation bundle/checkpoint built from cached TSA29 prep artifacts
  (`vdyp_prep-tsa29.pkl`, `vdyp_curves_smooth-tsa29.feather`,
  `tipsy_curves_tsa29.csv`, `tipsy_sppcomp_tsa29.csv`).
- 2026-03-08: Documented the Patchworks export contract in docs:
  `docs/reference/patchworks-export.rst` now captures required ForestModel XML
  structure and required fragments schema fields enforced by exporter validators.
- 2026-03-08: Added initial Woodstock compatibility export module
  `src/femic/fmg/woodstock.py` with `export_woodstock_package(...)`
  (CSV outputs from current FEMIC bundle/checkpoint artifacts), wired to
  CLI as `femic export woodstock`.
- 2026-03-08: Added shared FMG core dataclasses in `src/femic/fmg/core.py`
  (`CurvePoint`, `CurveDefinition`, `AnalysisUnitDefinition`, `BundleModelContext`)
  and bundle adapters in `src/femic/fmg/adapters.py` so Patchworks/Woodstock exporters
  consume one normalized AU/curve context instead of duplicating parsing logic.
- 2026-03-08: Refactored `src/femic/fmg/patchworks.py` and
  `src/femic/fmg/woodstock.py` to use shared adapters/context; revalidated exports:
  - Patchworks `k3z` (`au=14`, `fragments=218`, `curves=54`)
  - Woodstock `k3z` (`yield_rows=16162`, `area_rows=218`)
  - Woodstock `tsa29` from reconstructed validation bundle/checkpoint
    (`yield_rows=10050`, `area_rows=147959`).
- 2026-03-08: Added initial deterministic Patchworks XML fixture parity coverage
  (`tests/fixtures/fmg/forestmodel_minimal.xml`,
  `tests/test_fmg_patchworks.py::test_write_forestmodel_xml_matches_fixture`)
  as the first concrete step toward `P4.2b`.
- 2026-03-08: Completed core class migration milestone for `P4.2a` by adding
  explicit ForestModel/Treatment-related dataclasses in `src/femic/fmg/core.py`
  (`ForestModelDefinition`, `SelectDefinition`, `TreatmentDefinition`,
  `AttributeBinding`, `DefineFieldDefinition`, `TreatmentAssignment`) and moving
  Patchworks XML construction to `build_patchworks_forestmodel_definition(...)`
  + `forestmodel_definition_to_xml_tree(...)`.
- 2026-03-08: Expanded deterministic XML parity coverage for `P4.2b` with a
  richer multi-AU/species fixture:
  `tests/fixtures/fmg/forestmodel_multi_au.xml` and
  `tests/test_fmg_patchworks.py::test_write_forestmodel_xml_matches_multi_au_fixture`.
- 2026-03-08 next queue: start treatment transition/action parity work beyond
  baseline CC assignment (legacy semantics), and extend Woodstock compatibility
  outputs toward direct model ingest conventions.
- 2026-03-08: Started treatment transition/action parity by extending the
  Patchworks treatment model/serializer to emit `<transition>` assignments;
  baseline CC tracks now include `IFM -> 'managed'` transition assignment
  (configurable via `--cc-transition-ifm`).
- 2026-03-08: Extended Woodstock compatibility export toward direct-ingest
  conventions by adding `woodstock_actions.csv` and
  `woodstock_transitions.csv` outputs (plus CLI support for `--cc-min-age` /
  `--cc-max-age`).
- 2026-03-08 next queue: add configurable per-AU transition target fields
  (beyond IFM only), and evaluate adding Woodstock `.yld` writer/import parity
  helpers for tighter legacy interoperability.
- 2026-03-08: Implemented species-wise yield curve derivation in Patchworks XML:
  for each AU/IFM species, emit `feature.Yield.*.<SPP>` (and managed product
  equivalents) as `TotalVolume(age) * SpeciesProp(age)` with piecewise-linear
  species-proportion interpolation at total-curve ages.
- 2026-03-08: Added coverage for derived species yields in
  `tests/test_fmg_patchworks.py::test_build_forestmodel_xml_tree_adds_species_yield_curves`
  and regenerated deterministic XML fixtures to lock serializer parity.
- 2026-03-08: Updated Patchworks XML serialization to drop redundant repeated
  y-values on both far-left and far-right tails for non-`unity` curves (keep
  the inner edge points of each terminal plateau), matching Patchworks behavior
  of extending terminal points horizontally.
- 2026-03-08: Hardened Patchworks XML point serialization for schema safety:
  sanitize non-finite point values (replace non-finite `y` with `0.0`, drop
  non-finite `x`), enforce monotonic/deduped `x` ordering, and fix all-flat
  curve trimming to retain earliest age point (avoids degenerate `(299,0)` tails).
- 2026-03-08: Switched Patchworks XML curve IDs from opaque numeric aliases to
  readable deterministic identifiers (`managed_total_*`, `unmanaged_prop_*`,
  `au_*_managed_yield_*`), while preserving unique idref linkage.
- 2026-03-08: Updated Patchworks XML point formatting to emit integer age `x`
  values when age is integral (default case), while preserving float formatting
  only for genuinely non-integral x values.
- 2026-03-08: Updated Patchworks XML `y` formatting by curve family:
  volume-yield curves now round to 1 decimal place; normalized/proportion
  curves round to at most 5 decimals (avoids excessive precision noise).
- 2026-03-08: Added CC harvested-volume product consequences in Patchworks XML:
  each select now includes `product.HarvestedVolume.managed.Total.CC` and
  species-wise `product.HarvestedVolume.managed.<SPP>.CC` attributes bound to
  managed total/species yield curves; validated via refreshed fixtures/tests
  and regenerated `output/patchworks_k3z_validated/forestmodel.xml`.
- 2026-03-08: Audited Patchworks managed/unmanaged semantics against
  vendor Patchworks documentation and corrected FMG export assumptions:
  fragments exporter now writes one stand-fragment row per block (`1 fragment = 1 block`)
  with binary IFM assignment (`managed`/`unmanaged`) using THLB signal precedence
  (`thlb` -> `thlb_fact` -> `thlb_area` -> `thlb_raw`), matching the simplified K3Z
  teaching model requirement.
- 2026-03-08: Removed redundant Patchworks CC transition IFM assignment:
  exporter no longer writes `assign IFM='managed'` within managed-only select
  statements by default; `--cc-transition-ifm` is now optional (unset by default),
  and only non-redundant transitions (e.g., `unmanaged`) are emitted.
- 2026-03-08: Renamed upstream bundle yield terminology from
  `managed/unmanaged` to `treated/untreated` to avoid semantic collision with
  Patchworks IFM keywords. Bundle assembly now emits:
  - `curve_type` values `treated` / `untreated`
  - species-proportion curve types `treated_species_prop_*` /
    `untreated_species_prop_*`
  while preserving back-compat aliases (`managed_curve_id` /
  `unmanaged_curve_id`) and adding canonical AU columns
  (`treated_curve_id` / `untreated_curve_id`).
- 2026-03-08: Split documentation source from development reference assets:
  moved non-Sphinx PDFs out of `docs/reference/` into top-level `reference/`
  (including `reference/vdyp/`), leaving `docs/` as Sphinx source only; updated
  path references in `config/tipsy/tsa29.yaml`, `ROADMAP.md`, and
  `CHANGE_LOG.md`, and added `reference/README.md` to document directory intent.
- 2026-03-09 (seral semantics correction; feature-only accounts):
  - Confirmed Patchworks model semantics issue: `product.Seral.*` attributes are
    conceptually invalid for inventory state and should not be exported.
  - Removed `product.Seral.*` emission from
    `build_patchworks_forestmodel_definition(...)`; seral output now remains
    `feature.Seral.*` only.
  - Updated tests/docs to enforce and document feature-only seral attributes.
  - Live K3Z model repair:
    - removed `product.Seral.*` attributes from
      `C:\Users\gep\Documents\msfm\msfm2025\k3z_patchworks_model\yield\forestmodel.xml`,
    - re-ran `femic patchworks matrix-build` and verified both
      `protoaccounts.csv` and `accounts.csv` now contain `feature.Seral.*` only.
- 2026-03-09 (seral treatment-area consequence accounts + map layer):
  - Added Patchworks exporter support for treatment-consequence seral area
    accounts in CC product tracks with labels:
    `product.Seral.area.<stage>.<au_id>.CC`.
  - Updated docs/tests to reflect this semantic split:
    - inventory/state: `feature.Seral.*`
    - treatment consequences: `product.Seral.area.*.*.CC`.
  - Live K3Z model update:
    - injected `product.Seral.area.*.*.CC` attributes in
      `yield/forestmodel.xml`,
    - re-ran `femic patchworks matrix-build` and verified accounts appear in
      `protoaccounts.csv` and `accounts.csv`.
  - Added Seral Stages map layer to
    `analysis/base.pin` using sample-style `DitherTheme` configuration
    (`feature.Seral.*`, caption `Dithered Seral Stage`, layer title
    `Seral Stages`).
- 2026-03-10 (Patchworks matrix-build account sync + seral wiring):
  - Added post-build `tracks/protoaccounts.csv -> tracks/accounts.csv` sync in
    `femic patchworks matrix-build`, with timestamped backup of existing
    `accounts.csv` before overwrite and manifest/CLI reporting of sync status.
  - Added optional `--seral-stage-config` YAML support to
    `femic export patchworks` to emit per-AU seral curves and
    `feature.Seral.*` / `product.Seral.*` attributes with default or per-AU
    override boundaries.
  - Added `config/seral.k3z.yaml` starter config for K3Z seral stage setup.
- 2026-03-10 (CC treatment min age logic update):
  - Updated Patchworks exporter so CC `minage` resolves to
    `CMAI(managed_total_curve) - 20` per AU (clamped to `0..cc_max_age`).
  - `cc_min_age` remains as a fallback only when managed yield curve metadata is
    unavailable for an AU.
- 2026-03-10 (tracked K3Z prototype model moved in-repo):
  - Moved/copy-synced the active K3Z Patchworks prototype model into the repo at
    `models/k3z_patchworks_model/` so it can be versioned and shared with
    students/collaborators.
  - Updated `config/patchworks.runtime.windows.yaml` matrix builder paths to
    point at `../models/k3z_patchworks_model/...` (config-relative paths).
  - Verified `femic patchworks preflight` and `femic patchworks matrix-build`
    run successfully against the in-repo model (`run_id=repo_model_move_verify_20260310`).
- 2026-03-10 (plot docs follow-up): queued a docs enhancement to include the
  regenerated K3Z strata/AU plots in the student-facing Sample Models guide
  after the next full pipeline rerun refreshes those artifacts.
  - Added pending roadmap item `P8.6d`:
    `Roll regenerated strata/AU build plots into user-facing K3Z docs`.
- 2026-03-10 (validation gate unblock for docs checkpoint): resolved
  cross-platform/runtime regressions so full repository quality gates pass in
  this Windows environment.
  - Normalized selected emitted path strings to POSIX form where tests and
    downstream interchange contracts require stable separators
    (`legacy env boundary path`, `release manifest paths`, VDYP context/command
    payload strings, stand export file target path string).
  - Added graceful no-op behavior for VDYP diagnostic plotting when
    `matplotlib` is unavailable.
  - Hardened species slot derivation to exclude NaN-like species tokens.
  - Re-ran required gates successfully:
    `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
    `pre-commit run --all-files`, `sphinx-build -b html docs _build/html -W`.
- 2026-03-10 (Phase 9 rebrand planning kickoff): added a dedicated rebrand
  phase to move repository/project naming from `wbi_ria_yield` to `femic`,
  covering metadata, URLs, runtime path cleanup, slug sweep policy, and cutover
  validation workflow.
  - Created branch `feature/rebrand-femic` and marked `P9.5a` complete.
- 2026-03-10 (Phase 9 implementation slice 1): completed the first rebrand
  implementation pass across canonical metadata and operator-facing config/docs.
  - Updated project naming/title surfaces to `femic` in:
    `README.md`, `docs/conf.py`, `docs/index.rst`, and `CITATION.cff`.
  - Added explicit transition note in `README.md`:
    formerly `wbi_ria_yield`.
  - Updated target URLs to new slug endpoints:
    `github.com/UBC-FRESH/femic` and `ubc-fresh.github.io/femic`.
  - Removed old hard-coded slug path from `config/patchworks.runtime.yaml`;
    runtime now relies on `SPSHOME` env for install-home resolution.
  - Marked complete: `P9.1`, `P9.2a`, `P9.2b`, `P9.3a`, `P9.5b`.
- 2026-03-10 (Phase 9 implementation slice 2): validated post-rename runtime
  smoke behavior and locked env-driven Patchworks install-home handling with
  regression coverage.
  - Runtime checks:
    - `python -m femic --help` succeeds (CLI smoke).
    - `sphinx-build -b html docs _build/html -W` succeeds (docs smoke).
    - `femic patchworks preflight --config config/patchworks.runtime.windows.yaml`
      succeeds on this host.
    - `femic patchworks preflight --config config/patchworks.runtime.yaml`
      now fails only on missing local artifacts (jar/fragments/xml), not
      `SPSHOME` lookup when env is provided.
  - Added regression test in `tests/test_patchworks_runtime.py`:
    `test_load_patchworks_runtime_config_uses_env_spshome_when_field_missing`.
  - Marked complete: `P9.3b`, `P9.3c`, `P9.5c`.
  - GitHub Actions observation: latest `docs-pages` deployment currently
    advertises `https://ubc-fresh.github.io/wbi_ria_yield/`; need a post-merge
    main-branch deploy to confirm transition to `.../femic/`.
  - `P9.2c` remains pending until a post-merge docs-pages deployment confirms
    the new published URL target after rename.
- 2026-03-10 (Patchworks install-registration heuristic): updated preflight to
  explicitly warn when `SPSHOME` is missing from the process environment,
  reflecting the operational assumption that a correct Patchworks install should
  set `SPSHOME`.
  - Added warning text in `run_patchworks_preflight(...)`:
    missing `SPSHOME` indicates install/registration may be incomplete.
  - Added regression test:
    `tests/test_patchworks_runtime.py::test_run_patchworks_preflight_warns_when_env_spshome_missing`.
- 2026-03-10 (Pages post-rename verification + Node 24 readiness): confirmed
  docs are live under the renamed repo/docs URL and updated workflow defaults
  to avoid pending Node 20 action deprecation risk.
  - Confirmed GitHub Pages publish target is now `https://ubc-fresh.github.io/femic/`.
  - Updated `.github/workflows/docs-pages.yml` to set:
    `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`.
  - Upgraded `actions/upload-pages-artifact` from `@v3` to `@v4`.
  - Marked `P9.2c` complete.
- 2026-03-10 (Phase 9 closure pass): completed legacy-slug sweep enforcement
  and notebook-output cleanup policy so rebrand phase can be closed.
  - Added `Notebook Output Cleanup Policy` section to
    `docs/guides/legacy-traceability.rst` with explicit output-clearing guidance
    and `nbconvert --clear-output` command.
  - Added docs contract checks in `tests/test_docs_contract.py` for:
    - required notebook cleanup policy section presence,
    - legacy slug reference restrictions (allowed in audit-trail files only).
  - Removed remaining transition slug mention from `README.md` to keep active
    user-facing docs/config free of historical slug references.
  - Marked complete: `P9.2`, `P9.4a`, `P9.4b`, `P9.4c`, and parent `P9.4`.
- 2026-03-10 (Phase 10 implementation slice 1: instance decoupling + bootstrap):
  implemented instance-rooted CLI path resolution and deployment workspace
  scaffolding as the first concrete Phase 10 delivery.
  - Added `src/femic/instance_context.py` with resolver precedence:
    `--instance-root` -> `FEMIC_INSTANCE_ROOT` -> CWD, plus legacy repo-root
    compatibility fallback warning.
  - Added shared `--instance-root` support across operational commands
    (`run`, `prep validate-case`, `tipsy validate`, `tsa post-tipsy`,
    export commands, and patchworks runtime commands), and rewired relative
    paths to resolve under instance root.
  - Added `femic instance init` (`instance` CLI namespace) with filesystem-first
    scaffold generation (`config/`, `config/tipsy/`, `data/`, `output/`,
    `vdyp_io/logs/`, `.gitignore`, `QUICKSTART.md`).
  - Added optional BC-wide VRI dataset bootstrap with built-in URLs and default
    yes/no prompt:
    `VEG_COMP_LYR_R1_POLY_2024.gdb.zip` and
    `VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb.zip`.
  - Added package-owned resources under `src/femic/resources/` for instance
    templates and legacy scripts (`00_data-prep.py`, `01a_run-tsa.py`,
    `01b_run-tsa.py`), and updated workflow runtime to execute packaged scripts
    by default (no hard dependency on repo-root script paths).
  - Added/updated tests for instance-context resolution, instance bootstrap,
    packaged legacy resource loading, and CLI wiring.
  - Marked complete: `P10.1a/P10.1b/P10.1c`, `P10.2a/P10.2b/P10.2c`,
    `P10.3a/P10.3b/P10.3c`.
- 2026-03-10 (Phase 10 scope extension: public-but-inaccessible dataset mirror):
  added a new Phase 10 workstream to publish missing FEMIC-required public
  datasets (including archived HectaresBC `misc*.tif` layers) through a
  DataLad-powered GitHub dataset repository with Arbutus special-remote object
  storage, then link that dataset back into FEMIC as a git submodule.
  - Added checklist `P10.6a/P10.6b/P10.6c/P10.6d` for inventory, publishing,
    submodule integration, and collaborator runbook coverage.
- 2026-03-10 (Phase 10 `P10.6a` complete: dataset inventory + provenance baseline):
  published the required dataset inventory for DataLad mirror planning, with
  explicit access mode and checksum status fields.
  - Added machine-readable registry:
    `metadata/required_datasets.yaml`
    covering VRI/VDYP provincial layers, TSA boundaries, Site_Prod_BC,
    HectaresBC `misc.thlb.tif`, support assets, and case-specific boundary
    geometry.
  - Added user-facing guide:
    `docs/guides/data-access-inventory.rst`
    and wired it into docs navigation.
  - Updated deployment-instance guide to reference the authoritative registry.
  - Marked `P10.6a` complete; next queued step is `P10.6b` (publish DataLad
    dataset repository and configure Arbutus special remote).
- 2026-03-10 (Phase 10 `P10.6d` complete: DataLad operator runbook + mirror seed):
  added maintainer/operator docs and seed artifacts so the mirror workflow can
  be executed deterministically once the dataset repo is created.
  - Added guide `docs/guides/public-data-mirror-runbook.rst` with
    create/publish steps plus collaborator clone/get/update commands.
  - Added `metadata/datalad_mirror_seed.csv` as the current
    `datalad_mirror.include=true` extraction from dataset registry.
  - Added maintainer bootstrap note:
    `planning/femic_public_data_datalad_bootstrap.md`.
  - Marked `P10.6d` complete; next queued implementation is
    `P10.6b` followed by `P10.6c`.
- 2026-03-11 (Phase 10 `P10.6c` complete + local `P10.6b` bootstrap):
  created a local DataLad dataset mirror repo and linked it back into FEMIC as
  a Git submodule at `external/femic-public-data`.
  - Created local dataset repo at `/home/gep/projects/femic-public-data` and
    mirrored current seed artifacts from this workspace:
    - `data/misc.thlb.tif`
    - `data/bc/tsa/FADM_TSA.gdb`
    - `data/bc/siteprod/Site_Prod_BC.gdb`
    - `data/bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb`
    - `data/bc/vri/2019/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2019.gdb`
  - Added submodule linkage in FEMIC:
    `external/femic-public-data`.
  - Marked `P10.6c` complete.
  - `P10.6b` remains open pending GitHub publish + Arbutus special-remote
    configuration + checksum backfill in `metadata/required_datasets.yaml`.
- 2026-03-11 (Phase 10 `P10.6b` execution hardening with lab KB template):
  aligned FEMIC DataLad mirror runbook/bootstrap docs to the known-good
  Arbutus S3 command sequence from the FRESH lab workflow workshop materials.
  - Updated `docs/guides/public-data-mirror-runbook.rst` to use explicit
    `git annex initremote arbutus-s3` setup, followed by
    `datalad create-sibling-github --publish-depends arbutus-s3`.
  - Added credential/export and recovery notes (`git annex enableremote`) to
    reduce clone/get failures caused by ordering/config mismatches.
  - Updated `planning/femic_public_data_datalad_bootstrap.md` with source links
    to the imported KB/workshop references in `tmp/`.
- 2026-03-11 (Phase 10 `P10.6b` creds bootstrap template standardization):
  added a repo-local Arbutus credentials template and ignore policy so
  maintainers can source AWS/S3 env vars consistently without risking secret
  commits.
  - Added template:
    `config/credentials/arbutus_env.template.sh`.
  - Updated `.gitignore` to ignore concrete credential scripts under
    `config/credentials/*.sh` while keeping `*.template.sh` tracked.
  - Updated `docs/guides/public-data-mirror-runbook.rst` and
    `planning/femic_public_data_datalad_bootstrap.md` to use the new template
    path in the `P10.6b` setup sequence.
- 2026-03-11 (Phase 10 `P10.6b` complete: published mirror repo + Arbutus upload):
  completed the publish phase for the FEMIC public-data mirror dataset.
  - Verified published dataset repository:
    `https://github.com/UBC-FRESH/femic-public-data`.
  - Verified `git-annex` object availability on `arbutus-s3` for mirrored
    seed artifacts, including:
    - `data/misc.thlb.tif`
    - `data/bc/vri/2019/VEG_COMP_LYR_R1_POLY.gdb/a00000009.gdbtable`
  - Backfilled checksum values in `metadata/required_datasets.yaml` for all
    current `datalad_mirror.include=true` artifacts and documented the
    deterministic directory-hash method for `*.gdb` datasets.
  - Marked `P10.6b` complete; with `P10.6a/P10.6c/P10.6d` already complete,
    parent `P10.6` is now complete.
- 2026-03-11 (Phase 10 `P10.4a` complete: canonical in-repo reference instance):
  established a maintainer reference deployment instance under
  `instances/reference/`, separate from package source templates.
  - Generated `instances/reference/` via `femic instance init` with
    `--no-download-bc-vri` for deterministic in-repo scaffolding.
  - Added docs section in `docs/guides/deployment-instances.rst` defining
    `instances/reference/` as the canonical maintainer reference location.
  - Added docs contract coverage in `tests/test_docs_contract.py` to require
    the reference instance path and key scaffold files.
  - Marked `P10.4a` complete; next execution step remains `P10.4b`.
- 2026-03-11 (Phase 10 `P10.4b` complete: docs/tests/examples repointed):
  repointed maintainer-facing workflow docs and template-instantiation tests to
  use the canonical in-repo reference instance layout.
  - Updated guides:
    `docs/guides/case-onboarding.rst`,
    `docs/guides/pipeline-overview.rst`,
    `docs/reference/run-config.rst`.
  - Updated README onboarding/run-config examples to reference
    `instances/reference/config/...` paths.
  - Updated tests to consume reference-instance templates:
    `tests/test_case_preflight_cli.py`,
    `tests/test_docs_contract.py`.
  - Marked `P10.4b` complete; next execution step is `P10.4c`.
- 2026-03-11 (Phase 10 `P10.4c` complete: repo-path coupling contract checks):
  enforced docs/config contract coverage against repo-root-coupled deployment
  wording and removed remaining active references.
  - Updated `README.md` external-data note to describe instance-root-relative
    behavior rather than repo-root assumptions.
  - Updated `docs/sample-models/k3z.rst` wording from "repository root" to
    workspace-root phrasing.
  - Added `tests/test_docs_contract.py` check to fail on forbidden active
    deployment wording (`repository root`, `repo root`, and host-specific
    `/home/gep/projects/` paths) across key docs/config files.
  - Marked `P10.4c` complete; with `P10.4a/P10.4b` already complete, parent
    `P10.4` is now complete.
- 2026-03-11 (Phase 10 `P10.5a` complete: package build/release checks):
  added automated and documented package-distribution checks and fixed runtime
  package metadata so wheel smoke installs are executable.
  - Added GitHub Actions workflow:
    `.github/workflows/package-release-checks.yml` running:
    `python -m build`, `twine check dist/*`, and wheel-install smoke
    (`femic --help`, `femic instance init ...`).
  - Added README maintainer section documenting equivalent local commands.
  - Expanded `pyproject.toml` runtime `dependencies` to include required
    import-time packages (for example `numpy`, `pandas`, `geopandas`, `scipy`,
    `rasterio`) discovered by wheel-smoke failure diagnostics.
  - Added docs contract test coverage requiring workflow presence and required
    packaging-check commands (`tests/test_docs_contract.py`).
  - Marked `P10.5a` complete; next execution step remains `P10.5b`.
- 2026-03-11 (Phase 10 `P10.5b` complete: clean-env installed-package preflight):
  extended publish-readiness verification to cover an installed-wheel case
  preflight run in a clean virtual environment.
  - Updated `.github/workflows/package-release-checks.yml` to run:
    installed `femic prep validate-case` after `femic instance init`.
  - Added CI fixture setup in workflow for minimal preflight prerequisites:
    required instance-local data/runtime placeholders, mock `wine` on `PATH`,
    and a minimal external-data tree via `FEMIC_EXTERNAL_DATA_ROOT`.
  - Extended `tests/test_docs_contract.py` package-workflow contract assertions
    to require installed-package preflight coverage.
  - Marked `P10.5b` complete; next execution step remains `P10.5c`.
- 2026-03-11 (Phase 10 `P10.5c` complete: install->instance->run docs finalization):
  finalized user-facing docs for installed-package execution flow.
  - Updated `README.md` quickstart to lead with:
    `python -m pip install femic` -> `femic instance init` -> `femic run ...`
    and switched primary command examples to installed CLI form.
  - Updated deployment/onboarding pipeline guides to use installed CLI commands
    as primary examples:
    `docs/guides/deployment-instances.rst`,
    `docs/guides/case-onboarding.rst`,
    `docs/guides/pipeline-overview.rst`.
  - Added docs contract checks in `tests/test_docs_contract.py` to require
    explicit installed-package workflow text.
  - Marked `P10.5c` complete; with `P10.5a/P10.5b` already complete, parent
    `P10.5` is now complete.
- 2026-03-11 (Phase 11 complete: K3Z standalone example instance + submodule):
  implemented and published the canonical full K3Z instance repository and
  linked it back into FEMIC for onboarding and reproducible case setup.
  - Defined contract note:
    `planning/femic_k3z_instance_repo_contract.md`.
  - Published public repo:
    `https://github.com/UBC-FRESH/femic-k3z-instance` with initial baseline
    tag `v0.1.0`.
  - Added submodule linkage:
    `external/femic-k3z-instance`.
  - Updated docs to reference the standalone K3Z repo + submodule workflow and
    added operator commands:
    `git submodule update --init --recursive`,
    `git submodule update --remote external/femic-k3z-instance`.
  - Added docs-contract assertions requiring K3Z repo and submodule references.
  - Marked `P11.1/P11.2/P11.3/P11.4/P11.5` complete.
- 2026-03-11 (Phase 12 planning kickoff): added a concrete execution phase for
  relocated K3Z rebuild validation and standalone K3Z documentation buildout,
  including explicit FHOPS-template alignment requirements for cross-project
  FRESH lab Sphinx consistency.
  - Added `P12.1/P12.2` for relocated Patchworks matrix-build execution,
    bugfix verification, and regression evidence capture.
  - Added `P12.3/P12.4` for standalone `femic-k3z-instance` Sphinx docs
    scaffolding and TSR-style user-guide expansion.
  - Added `P12.5` to formalize a shared FRESH lab Sphinx template baseline
    using FHOPS as canonical reference.
  - Added `P12.6` for documentation ownership, cadence, and release policy.
- 2026-03-11 (Phase 12 `P12.1a/P12.1b` execution on relocated K3Z instance):
  ran Windows native Patchworks preflight + blocks build + matrix build in
  `external/femic-k3z-instance`.
  - Added instance-local runtime config:
    `external/femic-k3z-instance/config/patchworks.runtime.windows.yaml`.
  - Executed successful runs with artifacts/logs under:
    `external/femic-k3z-instance/vdyp_io/logs/`
    (run ids: `k3z_relocated_20260311`, `k3z_relocated_20260311b`).
  - `accounts.csv` sync/backup behavior confirmed via manifest.
  - Noted structural drift from tracked baseline remains and requires follow-up
    under `P12.2` (for example lower account/treatment counts after rebuild).
- 2026-03-11 (Phase 12 scope extension: cross-platform geospatial bootstrap):
  added explicit `fiona`/`GDAL` hardening tasks for Linux/Windows local `.venv`
  bootstrap reliability.
  - Added `P12.7a` for OS-specific validated install rituals.
  - Added `P12.7b` for runtime/bootstrap environment detection.
  - Added `P12.7c` for geospatial dependency preflight checks.
  - Added `P12.7d` for Windows remediation runbook coverage.
- 2026-03-11 (Phase 13 planning kickoff): added a new cross-instance
  reproducibility phase that makes rebuild scripts/specs + invariant checks the
  default requirement for all new FEMIC deployment-instance projects.
  - Added `P13.1` contract definition tasks for required inputs, sequence, invariants, and failure taxonomy.
  - Added `P13.2` orchestration tasks for first-class CLI rebuild execution + manifest/report outputs.
  - Added `P13.3` per-instance rebuild spec/template tasks, including K3Z backfill as reference.
  - Added `P13.4` regression guardrail tasks (invariants, baseline diffs, allowlisted deltas, fail-fast behavior).
  - Added `P13.5` user-facing documentation/runbook tasks for authoring and interpreting rebuild reports.
  - Added `P13.6` enforcement tasks to make this mandatory in `instance init`, docs contracts, and release gates.
- 2026-03-11 (K3Z runtime validation feedback: species account completeness):
  user confirmed rebuilt K3Z launches in Patchworks without startup errors and
  now shows nonzero volume in species-wise accounts except `PL`.
  - Added follow-up task `P12.2d` to verify `PL` vs `PLC` semantics in this
    case and, if `PL` is not valid for current K3Z inputs, remove/trim `PL`
    from generated accounts/targets/docs to avoid student confusion.
- 2026-03-11 (Phase 12 `P12.1c` + `P12.2a/b/c` execution: reproducible K3Z rebuild checks):
  implemented and exercised a deterministic rebuild-and-validate script for the
  relocated K3Z instance.
  - Fixed and expanded `scripts/k3z/rebuild_k3z_instance.py` to:
    - execute full rebuild flow,
    - emit machine-readable report JSON,
    - record key artifact timestamps,
    - enforce species/seral/block-join invariants,
    - compare structural `tracks/*.csv` invariants against a baseline snapshot.
  - Added baseline snapshot: `scripts/k3z/k3z_tracks_baseline.json`.
  - Executed evidence runs:
    - `k3z_reprocheck_20260311_2` (baseline initialized with `--write-baseline`),
    - `k3z_reprocheck_20260311_3` (baseline regression check pass),
    - `k3z_reprocheck_20260311_4` (clean repeat pass after UTC warning fix).
  - Latest report confirms:
    `managed_area_ha=1781.3132360577583`, `passive_area_ha=0.0`,
    `block_join_csv_only=0`, `block_join_shp_only=0`,
    `seral_account_count=75`, `baseline_match=true`.
  - Marked complete: `P12.1c`, `P12.2a`, `P12.2b`, `P12.2c`.
  - Left open: `P12.2d` (`PL` vs `PLC` semantics cleanup for student-facing clarity).
- 2026-03-11 (Phase 12 terminology normalization complete): replaced
  legacy curve-source terminology across active FEMIC code/docs with
  `untreated/treated`, while preserving IFM terminology as
  `managed/unmanaged`.
  - Updated bundle/adapters/export logic and tests to use
    `untreated_curve_id`/`treated_curve_id` and
    `untreated_species_prop_*`/`treated_species_prop_*` naming.
  - Updated user-facing docs/metadata wording to remove legacy curve-source
    references and align with `untreated/treated`.
  - Completed `P12.8a/P12.8b/P12.8c`.
- 2026-03-11 (Phase 12 `P12.2d` completion): validated `PL` vs `PLC` behavior
  in K3Z and implemented zero-signal species trimming so `PL` no longer appears
  as an empty managed species account when no treated species-proportion signal
  exists for `PL`.
- 2026-03-11 (Phase 12 `P12.3a` complete: standalone K3Z Sphinx scaffold):
  created and published the baseline standalone docs scaffold in
  `external/femic-k3z-instance`.
  - Submodule commit pushed: `6c61c71` (`femic-k3z-instance/main`).
  - Added docs files: `docs/conf.py`, `docs/index.rst`,
    `docs/getting-started.rst`, `docs/model-anatomy.rst`,
    `docs/rebuild-and-qa.rst`, `docs/troubleshooting.rst`, and
    `docs/requirements.txt`.
  - Added publishing/build config: `.readthedocs.yaml` and
    `.github/workflows/docs-pages.yml`.
  - Added parent docs-contract check in `tests/test_docs_contract.py` requiring
    standalone K3Z docs scaffold presence and key toctree entries.
  - Verified standalone docs build:
    `python -m sphinx -b html docs docs/_build/html -W` in submodule root.
- 2026-03-11 (Phase 12 `P12.3b` complete + FEMIC RTD-theme alignment):
  published and validated standalone K3Z docs, then aligned FEMIC docs publish
  deps to the same Read the Docs theme baseline.
  - Verified `femic-k3z-instance` docs deployment run success and URL:
    `https://ubc-fresh.github.io/femic-k3z-instance/`.
  - Added FEMIC docs dependency file: `docs/requirements.txt`
    (`sphinx`, `sphinx-rtd-theme`).
  - Updated FEMIC docs workflow to install docs deps from
    `docs/requirements.txt` so GitHub Pages builds use RTD theme consistently.
- 2026-03-11 (Phase 12 `P12.3c` complete): added standalone K3Z docs acceptance
  checks for required navigation and section coverage.
  - Expanded docs contract tests in `tests/test_docs_contract.py` to require:
    - guide toctree structure in `external/femic-k3z-instance/docs/index.rst`,
    - required headings and command snippets in `getting-started.rst`,
    - required anatomy/edit-policy sections in `model-anatomy.rst`,
    - required reproducibility sections and script references in
      `rebuild-and-qa.rst`,
    - required troubleshooting topics in `troubleshooting.rst`.
- 2026-03-11 (Phase 12 roadmap amendment: TSR-grade K3Z data-package depth):
  refined Phase 12 docs scope to explicitly target BC small-unit data-package
  structure/depth expectations using three exemplar references.
  - Added `P12.4d/P12.4e/P12.4f/P12.4g/P12.4h` to enforce:
    exemplar section crosswalk, standalone K3Z data-package page set,
    evidence/provenance tables, student usability acceptance content, and
    publication acceptance criteria.
  - Added `P12.5e` to ensure FHOPS template alignment does not dilute
    BC data-package depth expectations.
  - Exemplar references for structure baseline:
    `reference/TFL26_Information_Package_Sept-2018_v1.1.pdf`,
    `reference/CFA_Analysis_Report.pdf`,
    `reference/FNWL_Analysis_Report.pdf`.
  - Next execution sequence locked:
    `P12.4d -> P12.4e -> P12.4f -> P12.4g -> P12.4h`.
- 2026-03-11 (Phase 12 `P12.4d/P12.4e/P12.4f/P12.4g` execution):
  added TSR-grade K3Z standalone data-package docs and acceptance checks using
  the TFL26/CFA/FNWL exemplar structure as the baseline.
  - Added standalone docs pages:
    `data-package-crosswalk.rst`, `land-base-and-netdown.rst`,
    `assumptions-registry.rst`, `base-case-analysis.rst`.
  - Wired new pages into standalone docs navigation in
    `external/femic-k3z-instance/docs/index.rst`.
  - Added docs-contract coverage in `tests/test_docs_contract.py` requiring:
    crosswalk sections, exemplar references, TSR-style required headings, and
    provenance-table columns plus operator usability sections.
  - Marked complete: `P12.4d`, `P12.4e`, `P12.4f`, `P12.4g`.
  - Remaining for `P12.4`: `P12.4h` (publish acceptance verification).
- 2026-03-11 (Phase 12 `P12.4h` completion): publication acceptance criteria
  verified for standalone K3Z TSR-style docs update.
  - Verified standalone docs warnings-as-errors build succeeds:
    `python -m sphinx -b html docs docs/_build/html -W` (submodule).
  - Verified parent docs-contract coverage includes required TSR headings and
    provenance/usability sections (`tests/test_docs_contract.py`).
  - Verified GitHub Pages deployment/run and live navigation for new pages:
    run `22981643203` (`success`) and URL
    `https://ubc-fresh.github.io/femic-k3z-instance/`.
- 2026-03-11 (Phase 12 `P12.4a/P12.4b/P12.4c` execution): expanded standalone
  K3Z docs to complete the core TSR-style data-package scope.
  - Added metadata/lineage page:
    `external/femic-k3z-instance/docs/metadata-and-lineage.rst`
    (artifact inventory, lineage chain, validation evidence, provenance policy).
  - Added operator runbook page:
    `external/femic-k3z-instance/docs/operator-runbook.rst`
    (fresh setup, rebuild, diagnostics, troubleshooting, release/publication
    checklists).
  - Added edit-policy/scenario guidance page:
    `external/femic-k3z-instance/docs/edit-policy-and-scenarios.rst`
    (editable/regenerate matrix and classroom scenario interpretation workflow).
  - Wired pages into standalone docs navigation in
    `external/femic-k3z-instance/docs/index.rst`.
  - Extended parent docs-contract checks to enforce required headings for the
    three new pages (`tests/test_docs_contract.py`).
  - Marked complete: `P12.4a`, `P12.4b`, `P12.4c`.
- 2026-03-11 (standalone-docs decoupling hardening): removed parent-repo path
  assumptions from standalone `femic-k3z-instance` docs so the instance docs
  remain valid when consumed outside a FEMIC submodule checkout.
  - Replaced parent-specific script/path references (for example
    `scripts/k3z/rebuild_k3z_instance.py` and `reference/...`) with
    instance-local FEMIC command workflows and generic exemplar citations.
  - Added docs-contract guard:
    `test_k3z_standalone_docs_do_not_reference_parent_repo_paths`.
- 2026-03-11 (Phase 12 `P12.5a/P12.5b/P12.5c/P12.5d/P12.5e` completion):
  standardized FEMIC + standalone K3Z docs stacks against an FHOPS-aligned
  Sphinx template baseline with automated drift checks.
  - Added baseline guide:
    `docs/guides/sphinx-template-baseline.rst` and wired it into Guides index.
  - Aligned both docs configs with shared template controls:
    `autodoc_typehints="description"`, RTD theme options
    (`collapse_navigation=False`, `navigation_depth=3`), and template path.
  - Aligned standalone docs workflow to match current Pages baseline
    (Node24 env flag, `configure-pages`, artifact/deploy action versions,
    pull-request/main gating parity).
  - Added docs-contract enforcement:
    `test_fhops_aligned_sphinx_template_contract`.
  - Confirmed K3Z TSR data-package depth pages remain required via existing
    docs contracts.
- 2026-03-11 (Phase 12 `P12.6a/P12.6b/P12.6c` completion): formalized docs
  ownership and release operations for standalone K3Z documentation.
  - Added standalone governance page:
    `external/femic-k3z-instance/docs/docs-ownership-and-release.rst`.
  - Wired new page into standalone docs navigation:
    `external/femic-k3z-instance/docs/index.rst`.
  - Captured ownership matrix, refresh cadence, release tagging policy, and
    contributor onboarding/review workflow requirements.
  - Extended docs-contract checks (`tests/test_docs_contract.py`) to require
    the new page and its core governance sections.
- 2026-03-11 (Phase 12 `P12.7a/P12.7b/P12.7c/P12.7d` completion): implemented
  cross-platform geospatial dependency bootstrap hardening with runtime checks.
  - Added OS-aware geospatial preflight module:
    `src/femic/geospatial_preflight.py` (platform detection, install hints,
    Fiona import check, GDAL visibility check, shapefile I/O smoke test).
  - Added CLI command:
    `femic prep geospatial-preflight` (supports `--strict-warnings` and
    `--skip-shapefile-smoke`).
  - Updated `femic instance init` to surface geospatial readiness guidance and
    OS-specific install hints when dependencies are not yet ready.
  - Added user guide:
    `docs/guides/geospatial-runtime-bootstrap.rst` and wired it into guides
    navigation.
  - Updated deployment + CLI reference docs and docs-contract/test coverage for
    the new command and guide requirements.
- 2026-03-11 (Phase 13 `P13.1a/P13.1b/P13.1c/P13.1d` completion): defined the
  canonical FEMIC instance rebuild contract in human-readable and
  machine-readable forms.
  - Added contract specification document:
    `planning/femic_instance_rebuild_contract.md`.
  - Added canonical YAML contract artifact:
    `planning/femic_instance_rebuild_contract.v1.yaml`.
  - Captured required inputs/config/runtime prerequisites, authoritative rebuild
    sequence, required post-rebuild invariants, and failure-class remediation
    message requirements.
  - Added docs-contract enforcement in `tests/test_docs_contract.py` for
    contract artifact presence and required schema keys/sections.
  - Linked pipeline guide primary sources to the new rebuild contract doc:
    `docs/guides/pipeline-overview.rst`.
- 2026-03-11 (Phase 13 `P13.2a` completion): added a reusable deterministic
  rebuild-runner abstraction with JSON report sink support.
  - Added module:
    `src/femic/rebuild_runner.py` with:
    `RebuildStep`, `RebuildRunner`, `StepOutcome`,
    `RebuildExecutionReport`, and `JsonRebuildReportSink`.
  - Runner now supports dependency graph ordering (deterministic topological
    sort), stop-or-continue failure behavior, and machine-readable report
    emission through sink abstraction.
  - Added unit tests:
    `tests/test_rebuild_runner.py` covering deterministic order, failure
    handling modes, JSON sink output, unknown dependency errors, and cycle
    detection.
- 2026-03-11 (Phase 13 `P13.2b` completion): added CLI support for
  non-interactive, instance-rooted rebuild execution with explicit run IDs.
  - Added `femic instance rebuild` command in `src/femic/cli/main.py`.
  - Command now executes deterministic rebuild steps through
    `RebuildRunner` with step dependencies:
    case preflight, geospatial preflight, upstream compile, post-TIPSY bundle,
    and optional Patchworks preflight + matrix build.
  - Added machine-readable report path emission:
    `vdyp_io/logs/instance_rebuild_report-<run_id>.json`.
  - Added CLI regression tests in `tests/test_cli_main.py` for base/with-Patchworks
    step graph construction and run-id/context wiring.
  - Updated CLI docs and contracts:
    `docs/reference/cli.rst`, `docs/guides/pipeline-overview.rst`,
    `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 13 `P13.2c` completion): extended instance rebuild output
  reporting to include explicit manifest/log artifact references.
  - Added artifact-reference collector:
    `_collect_rebuild_artifact_references(...)` in `src/femic/cli/main.py`.
  - `femic instance rebuild` now enriches
    `instance_rebuild_report-<run_id>.json` with `artifact_references` that
    capture discovered run-manifest, Patchworks manifest/log, and report files.
  - Added CLI regression coverage:
    `tests/test_cli_main.py::test_collect_rebuild_artifact_references_filters_missing`.
  - Updated CLI reference docs to document report artifact-reference behavior:
    `docs/reference/cli.rst`.
- 2026-03-11 (Phase 13 `P13.2d` completion): added rebuild dry-run mode so
  operators can inspect full planned execution sequence without mutation.
  - Added `--dry-run` option to `femic instance rebuild` in
    `src/femic/cli/main.py`.
  - Dry-run now prints ordered step plan (with dependencies), run-id, and
    report path, then exits before constructing/running `RebuildRunner`.
  - Added CLI regression test:
    `tests/test_cli_main.py::test_instance_rebuild_dry_run_prints_plan_without_execution`.
  - Updated CLI docs/contracts:
    `docs/reference/cli.rst` and `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 13 `P13.3a` completion): defined the standard YAML rebuild
  spec schema for instance command steps and invariants.
  - Added schema artifact:
    `planning/femic_instance_rebuild_spec_schema.v1.yaml`.
  - Schema now standardizes root keys (`instance`, `runtime`, `steps`,
    `invariants`) plus step and invariant field structure/constraints.
  - Linked schema from canonical rebuild contract:
    `planning/femic_instance_rebuild_contract.md`.
  - Added docs-contract enforcement:
    `tests/test_docs_contract.py::test_instance_rebuild_spec_schema_artifact_is_present_and_structured`.
- 2026-03-11 (Phase 13 `P13.3b` completion): shipped default rebuild-spec
  template in instance bootstrap scaffolding.
  - Added template artifact:
    `src/femic/resources/instance/config/rebuild.spec.yaml`.
  - Updated instance bootstrap template file list so
    `femic instance init` now always writes `config/rebuild.spec.yaml`.
  - Updated instance quickstart template and deployment docs to include
    rebuild-spec customization guidance.
  - Added/updated test coverage:
    `tests/test_instance_bootstrap.py` and `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 13 `P13.3c` completion): backfilled K3Z as the reference
  rebuild-spec implementation using its known-valid sequence.
  - Added K3Z instance spec:
    `external/femic-k3z-instance/config/rebuild.spec.yaml`.
  - Updated K3Z standalone docs/rebuild runbook and README to treat
    `config/rebuild.spec.yaml` as the authoritative sequence source.
  - Extended parent docs-contract checks to require the K3Z rebuild spec and
    validate core schema-aligned fields and required step IDs.
- 2026-03-11 (Phase 13 `P13.3d` completion): added rebuild-spec schema
  validation with explicit diagnostics for malformed specs.
  - Added module:
    `src/femic/rebuild_spec.py` with load + validation helpers and
    human-readable issue reporting.
  - `femic instance rebuild` now validates `--spec` before planning/execution
    and exits with detailed field-level diagnostics on malformed specs.
  - Added command:
    `femic instance validate-spec --spec <path>` for direct schema checks.
  - Added tests:
    `tests/test_rebuild_spec.py`, plus CLI/contract coverage updates in
    `tests/test_cli_main.py` and `tests/test_docs_contract.py`.
  - Updated CLI reference docs for `--spec` and `instance validate-spec`.
- 2026-03-11 (Phase 13 `P13.4a` completion): added operational invariant
  extraction and evaluation for known regression risk dimensions.
  - Added module:
    `src/femic/rebuild_invariants.py` with metric collectors for managed area,
    managed species yield-account presence, seral-account presence,
    topology edge count, and matrix-builder block join mismatch detection.
  - `femic instance rebuild` now evaluates spec invariants against measured
    metrics, prints pass/warn/fail summaries with remediation text, and fails
    the command when any `severity: fatal` invariant regresses.
  - Rebuild reports now persist `metrics` and `invariant_results` sections
    alongside existing step outcomes and artifact references.
  - Added regression tests:
    `tests/test_rebuild_invariants.py`, and updated CLI/docs coverage in
    `docs/reference/cli.rst`.
- 2026-03-11 (Phase 13 `P13.4b` completion): added configurable baseline
  snapshot + structural diff support for rebuild outputs.
  - Added module:
    `src/femic/rebuild_baseline.py` to build/load/save baseline snapshots and
    diff key track-table + ForestModel XML structures.
  - `femic instance rebuild` now supports:
    `--baseline <path>` and `--write-baseline`, computes `baseline_match` /
    `baseline_diff_count` metrics, and records baseline diff payloads in the
    rebuild report under `baseline`.
  - Added tests:
    `tests/test_rebuild_baseline.py`, plus CLI/docs contract updates in
    `tests/test_cli_main.py` and `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 13 `P13.4c` completion): added explicit baseline-diff
  allowlist mechanism so intentional output deltas are tracked in git.
  - Added allowlist support in baseline utilities:
    `load_diff_allowlist(...)` and `apply_diff_allowlist(...)` in
    `src/femic/rebuild_baseline.py`.
  - `femic instance rebuild` now supports:
    `--allowlist <path>` (default `config/rebuild.allowlist.yaml`) and records
    `baseline_allowlist_match` + `baseline_unexpected_diff_count` metrics.
  - Rebuild report `baseline` section now captures allowlist path/payload and
    filtered unexpected diff results.
  - Added allowlist template files:
    `src/femic/resources/instance/config/rebuild.allowlist.yaml` and
    `instances/reference/config/rebuild.allowlist.yaml`.
  - Updated instance scaffolding (`femic instance init`) and quickstart docs
    so every new instance starts with a tracked allowlist file.
- 2026-03-11 (Phase 13 `P13.4d` completion): rebuild now fails fast with
  explicit actionable regression summaries for unexpected baseline drift.
  - `femic instance rebuild` now enforces runtime threshold
    `runtime.baseline_unexpected_diff_threshold` (default `0`) and exits
    non-zero when `baseline_unexpected_diff_count` exceeds threshold.
  - Added operator-facing remediation output for unexpected diffs:
    review report baseline allowlist results, update tracked allowlist, or
    regenerate baseline with `--write-baseline`.
  - Rebuild report now includes `regression_gate` with step/invariant/baseline
    gate status fields.
  - Updated baseline schema/template docs:
    `planning/femic_instance_rebuild_spec_schema.v1.yaml`,
    `src/femic/resources/instance/config/rebuild.spec.yaml`,
    `instances/reference/config/rebuild.spec.yaml`.
  - Added regression coverage:
    `tests/test_cli_main.py::test_instance_rebuild_fails_when_unexpected_diffs_exceed_threshold`.
- 2026-03-11 (Phase 13 `P13.5a` completion): added user-facing rebuild
  reproducibility contract guide.
  - Added docs page:
    `docs/guides/rebuild-repro-contract.rst` covering purpose, contract
    sources, operator workflow, required evidence artifacts, and failure
    classes.
  - Added guide navigation entry in `docs/guides/index.rst`.
  - Added docs-contract coverage:
    `tests/test_docs_contract.py::test_rebuild_repro_contract_guide_covers_core_sections`.
- 2026-03-11 (Phase 13 `P13.5b` completion): added authoring guide for new
  instance rebuild specs with copy-ready templates and execution workflow.
  - Added docs page:
    `docs/guides/author-instance-rebuild-spec.rst`.
  - Covered required spec sections, step/invariant authoring rules, minimal
    YAML example, K3Z reference spec usage, and dry-run/full rebuild commands.
  - Added guide navigation entries/links in:
    `docs/guides/index.rst` and `docs/guides/rebuild-repro-contract.rst`.
  - Added docs-contract coverage:
    `tests/test_docs_contract.py::test_author_instance_rebuild_spec_guide_covers_core_sections`.
- 2026-03-11 (Phase 13 `P13.5c` completion): added operator guide for rebuild
  report interpretation and regression triage workflow.
  - Added docs page:
    `docs/guides/interpret-rebuild-reports.rst`.
  - Documented how to interpret `outcomes`, `invariant_results`, `baseline`,
    and `regression_gate` sections in instance rebuild reports.
  - Added explicit triage sequence for resolving step failures, fatal
    invariant regressions, and unexpected baseline drift.
  - Added guide navigation links in:
    `docs/guides/index.rst` and `docs/guides/rebuild-repro-contract.rst`.
  - Added docs-contract coverage:
    `tests/test_docs_contract.py::test_interpret_rebuild_reports_guide_covers_core_sections`.
- 2026-03-11 (Phase 13 `P13.5d` completion): added contributor policy text
  making rebuild spec + checks mandatory for all new instance repositories.
  - Added explicit policy section in
    `docs/guides/rebuild-repro-contract.rst` requiring:
    tracked `config/rebuild.spec.yaml`, tracked
    `config/rebuild.allowlist.yaml`, spec validation, deterministic rebuild
    checks, and preserved rebuild evidence artifacts.
  - Added matching baseline contributor checklist in
    `docs/guides/deployment-instances.rst`.
  - Added docs-contract enforcement:
    `tests/test_docs_contract.py::test_contributor_policy_requires_rebuild_spec_and_checks`.
- 2026-03-11 (Phase 13 `P13.6a` completion): extended instance scaffolding so
  all new instance workspaces include rebuild runbook placeholders by default.
  - Updated `femic instance init` template set in
    `src/femic/instance_bootstrap.py` to include
    `runbooks/REBUILD_RUNBOOK.md` and create `runbooks/` directory.
  - Added runbook template resource:
    `src/femic/resources/instance/runbooks/REBUILD_RUNBOOK.md`.
  - Synced maintainer reference instance placeholder:
    `instances/reference/runbooks/REBUILD_RUNBOOK.md`.
  - Updated bootstrap docs/quickstart references in
    `src/femic/resources/instance/QUICKSTART.md` and
    `docs/guides/deployment-instances.rst`.
  - Added regression checks in
    `tests/test_instance_bootstrap.py` and
    `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 13 `P13.6b` completion): added docs-contract enforcement
  requiring rebuild-spec references in sample/new instance documentation.
  - Updated sample-model K3Z guide to include explicit rebuild workflow
    references:
    `config/rebuild.spec.yaml`,
    `config/rebuild.allowlist.yaml`,
    `runbooks/REBUILD_RUNBOOK.md`.
  - Updated case-onboarding guide template checklist to include rebuild
    spec/allowlist/runbook assets.
  - Added/extended docs-contract assertions in `tests/test_docs_contract.py`
    to enforce these references going forward.
- 2026-03-11 (Phase 13 `P13.6c` completion): added release-gate enforcement
  requiring passing reference-instance rebuild evidence.
  - Added tracked evidence artifact:
    `instances/reference/evidence/reference_rebuild_report.latest.json`
    with explicit `regression_gate` pass status fields.
  - Added GitHub Actions release-gate step in
    `.github/workflows/package-release-checks.yml`:
    `Reference instance rebuild evidence gate`.
  - Added docs + docs-contract enforcement for evidence path and required pass
    fields in:
    `docs/guides/deployment-instances.rst` and
    `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 13 `P13.6d` completion): formalized closure policy that no
  new instance phase can close without reproducible rebuild evidence.
  - Added mandatory policy section under Phase 13 in `ROADMAP.md`.
  - Added matching policy milestone entry in `CHANGE_LOG.md`.
  - Added docs-contract enforcement in `tests/test_docs_contract.py` to ensure
    the policy note remains present in roadmap and changelog artifacts.
- 2026-03-11 (Roadmap status normalization): marked completed parent checklist
  items as done where all child tasks were already complete.
  - Updated parent status for:
    `P12.3`, `P12.4`, `P12.5`, `P13.3`, `P13.4`, `P13.5`, and `P13.6`.
- 2026-03-11 (Phase 14 kickoff, `P14.1a/P14.1b/P14.1c` completion): added
  CLI automation to promote rebuild reports into normalized evidence artifacts.
  - Added command:
    `femic instance promote-evidence` in `src/femic/cli/main.py`.
  - Command supports explicit `--report` input or auto-selects latest
    `instance_rebuild_report-*.json` under `--log-dir`, and writes normalized
    payloads to `--output` (default
    `evidence/reference_rebuild_report.latest.json`).
  - Updated CLI reference docs and docs-contract/CLI test coverage in:
    `docs/reference/cli.rst`,
    `tests/test_docs_contract.py`,
    `tests/test_cli_main.py`.
- 2026-03-11 (Phase 14 `P14.2a` completion): added maintainer helper command
  to refresh reference rebuild evidence from current logs.
  - Added command:
    `femic instance refresh-reference-evidence` in `src/femic/cli/main.py`.
  - Command wraps `instance promote-evidence` with reference defaults:
    `--reference-root instances/reference`,
    output `evidence/reference_rebuild_report.latest.json`,
    log dir `vdyp_io/logs`.
  - Updated docs and test/contract coverage in:
    `docs/reference/cli.rst`,
    `docs/guides/deployment-instances.rst`,
    `tests/test_cli_main.py`,
    `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 14 `P14.2b` completion): added explicit contributor
  runbook release-prep step for evidence refresh.
  - Updated instance runbook templates:
    `src/femic/resources/instance/runbooks/REBUILD_RUNBOOK.md` and
    `instances/reference/runbooks/REBUILD_RUNBOOK.md` to include
    `femic instance refresh-reference-evidence --reference-root .`
    and expected post-refresh checks.
  - Updated `docs/guides/deployment-instances.rst` with contributor
    release-prep requirement text.
  - Added docs-contract enforcement in `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 14 `P14.3a` completion): added optional trend-drift
  warning thresholds for rebuild evidence summaries.
  - Extended `femic instance promote-evidence` with:
    `--max-warn-increase` and `--max-baseline-diff-increase`.
  - Added trend delta + warnings payload in evidence artifacts under
    `trend_drift` (previous summary, increases, thresholds, warnings).
  - Propagated threshold options through
    `femic instance refresh-reference-evidence`.
  - Updated CLI/deployment docs and contract/tests in:
    `docs/reference/cli.rst`,
    `docs/guides/deployment-instances.rst`,
    `tests/test_cli_main.py`,
    `tests/test_docs_contract.py`.
- 2026-03-11 (Phase 14 `P14.3b` completion): added release-operator guidance
  for interpreting evidence trend drift across releases.
  - Expanded `docs/guides/interpret-rebuild-reports.rst` with
    `Evidence Trend Drift Across Releases`, including:
    `trend_drift` field interpretation, threshold semantics, and a
    thresholded release workflow using
    `femic instance refresh-reference-evidence`.
  - Extended docs-contract enforcement in `tests/test_docs_contract.py` to
    require the drift-interpretation section and key `trend_drift` markers.
- 2026-03-11 (Phase 15 kickoff): opened species-account semantic hardening
  plan for K3Z to resolve `PL`/`PLC` ambiguity and prevent silent
  species-wise null regressions.
  - Execution order for next implementation pass:
    `P15.1a -> P15.1b -> P15.1c -> P15.2a -> P15.2b -> P15.2c`.
- 2026-03-11 (Phase 15 `P15.1a` completion + `P15.1b` implementation support):
  audited current K3Z species surfaces and added runtime support to exclude
  known-empty account rows during `protoaccounts -> accounts` promotion.
  - Audit evidence from
    `external/femic-k3z-instance/models/k3z_patchworks_model/yield/forestmodel.xml`:
    `managed_prop_PL_*` and `unmanaged_prop_PL_*` curves are all zero; `PLC`
    retains non-zero signal.
  - Added optional runtime config key:
    `matrix_builder.accounts_exclude_regex` in
    `src/femic/patchworks_runtime.py`.
  - Matrix-build manifests now record
    `accounts_sync.excluded_patterns` and `accounts_sync.excluded_row_count`.
  - Added tests in `tests/test_patchworks_runtime.py` for config parsing and
    regex-based exclusion behavior.
  - Added operator docs in `docs/guides/patchworks-wine-runtime.rst`.
  - Next execution step: apply the exclusion pattern in K3Z instance runtime
    config and verify account/target surfaces after matrix rebuild.
- 2026-03-11 (Phase 15 `P15.1b` completion): applied K3Z runtime account
  exclusion policy and verified matrix-build output surfaces.
  - Updated
    `external/femic-k3z-instance/config/patchworks.runtime.windows.yaml` with
    `matrix_builder.accounts_exclude_regex: ["\\.PL(\\.|$)"]`.
  - Re-ran matrix build:
    `python -m femic patchworks matrix-build --config external/femic-k3z-instance/config/patchworks.runtime.windows.yaml --run-id k3z_plc_cleanup_20260312b`.
  - Verified `tracks/accounts.csv` no longer includes `.PL` account rows while
    `.PLC` rows remain.
  - Verified manifest
    `vdyp_io/logs/patchworks_matrixbuilder_manifest-k3z_plc_cleanup_20260312b.json`
    reports
    `accounts_sync.excluded_patterns=["\\.PL(\\.|$)"]` and
    `accounts_sync.excluded_row_count=5`.
  - Next execution step: `P15.1c` docs note for student-facing species-code
    interpretation.
- 2026-03-11 (Phase 15 `P15.1c` completion): added explicit student-facing
  PL/PLC interpretation guidance in both standalone K3Z docs and FEMIC sample
  model docs.
  - Updated
    `external/femic-k3z-instance/docs/base-case-analysis.rst` with
    `Species Code Note (PL vs PLC)` defining `PLC` as canonical and clarifying
    that absent `PL` accounts are expected for K3Z.
  - Updated `docs/sample-models/k3z.rst` with
    `Species Code Semantics: PL vs PLC` including the active exclusion policy.
  - Added docs-contract guard in `tests/test_docs_contract.py` so this
    semantics note remains present.
- 2026-03-11 (Phase 15 `P15.2a` completion): added species-account completeness
  invariant support and wired K3Z fatal checks for PLC present / PL absent.
  - Added `accounts.list` metric in `src/femic/rebuild_invariants.py` and
    added `contains` / `not_contains` comparator support.
  - Extended rebuild-spec comparator allowlists in:
    `src/femic/rebuild_spec.py` and
    `planning/femic_instance_rebuild_spec_schema.v1.yaml`.
  - Added test coverage in:
    `tests/test_rebuild_invariants.py` and `tests/test_rebuild_spec.py`.
  - Added K3Z invariant policy entries in:
    `external/femic-k3z-instance/config/rebuild.spec.yaml`
    for:
    `product.Yield.managed.PLC`,
    `product.HarvestedVolume.managed.PLC.CC`,
    and exclusion of `product.Yield.managed.PL`,
    `product.HarvestedVolume.managed.PL.CC`.
  - Updated invariant-authoring docs in:
    `docs/guides/author-instance-rebuild-spec.rst`.
  - Next execution step: implement `P15.2b` configurable expected-empty policy
    semantics in rebuild spec/allowlist patterns.
- 2026-03-11 (Phase 15 `P15.2b` completion): added reusable rebuild-spec
  `species_account_policy` support so expected-empty vs required-present
  account surfaces are configurable by instance.
  - Added policy-invariant builder in
    `src/femic/rebuild_invariants.py` that emits fatal `contains` /
    `not_contains` checks over `accounts.list`.
  - Wired policy expansion into `femic instance rebuild` in
    `src/femic/cli/main.py`.
  - Extended rebuild-spec validation + schema in:
    `src/femic/rebuild_spec.py` and
    `planning/femic_instance_rebuild_spec_schema.v1.yaml`.
  - Added tests in:
    `tests/test_rebuild_invariants.py` and
    `tests/test_rebuild_spec.py`.
  - Migrated K3Z to policy-based configuration in:
    `external/femic-k3z-instance/config/rebuild.spec.yaml`.
  - Updated authoring docs in:
    `docs/guides/author-instance-rebuild-spec.rst`.
  - Next execution step: implement `P15.2c` to ensure rebuild command gating
    behavior is explicit and fail-fast for unexpected species-account null/empty
    regressions under policy.
- 2026-03-11 (packaging hotfix): fixed wheel package-data omission that caused
  release workflow wheel-smoke failure when `femic instance init` attempted to
  copy `resources/instance/runbooks/REBUILD_RUNBOOK.md`.
  - Added package-data include in `pyproject.toml`:
    `resources/instance/runbooks/*`.
  - Verified build output now includes runbook template in wheel payload.
- 2026-03-11 (Phase 15 `P15.2c` completion): rebuild now fails hard when
  species-account policy expects nonzero product labels and regenerated tracks
  regress to zero/null signal.
  - Added new rebuild metric extraction:
    `products.nonzero_labels` from `tracks/products.csv` + `tracks/curves.csv`
    in `src/femic/rebuild_invariants.py`.
  - Extended `runtime.species_account_policy` with:
    `required_nonzero` and `expected_zero` (fatal invariants over
    `products.nonzero_labels`).
  - Added/updated tests:
    `tests/test_rebuild_invariants.py`,
    `tests/test_cli_main.py`.
  - Updated spec-authoring docs and schema:
    `docs/guides/author-instance-rebuild-spec.rst`,
    `planning/femic_instance_rebuild_spec_schema.v1.yaml`.
  - Next execution step: start `P15.3a` (operator diagnostics helper for
    account/target coverage by species and AU).
- 2026-03-11 (repo hygiene): scrubbed real SPS license username from docs,
  configs, tests, and tracked manifests.
  - Replaced `frst424@auth.spatial.ca` with neutral example
    `sps_user@auth.spatial.ca` across FEMIC + K3Z instance repo content.
  - Purpose: avoid shipping user-identifying credentials in public-facing
    documentation/config examples while preserving executable examples/tests.
- 2026-03-11 (Phase 15 `P15.3a` completion): added first-class operator
  diagnostics helper for account-surface QA.
  - Added `femic instance account-surface` command in
    `src/femic/cli/main.py`.
  - Added account-surface parser/summarizer in
    `src/femic/account_surface.py` that reports:
    species-level yield/harvest account coverage and AU-level seral account
    coverage from `tracks/accounts.csv`.
  - Added tests in:
    `tests/test_account_surface.py`, `tests/test_cli_main.py`.
  - Updated CLI docs in:
    `docs/reference/cli.rst`.
  - Next execution step: implement `P15.3b` deterministic troubleshooting flow
    for "total OK, species-wise empty" failure signatures.
- 2026-03-11 (Phase 15 `P15.3b` completion): added deterministic
  troubleshooting flow for "total OK, species-wise empty" failures and wired it
  into diagnostics output expectations.
  - Extended `femic instance account-surface` diagnostics in
    `src/femic/account_surface.py` to compute:
    `diagnosis.total_ok_species_empty_signature` plus ordered
    `recommended_next_checks`.
  - Updated CLI output in `src/femic/cli/main.py` to emit explicit
    troubleshooting steps when the signature is detected.
  - Added regression tests in:
    `tests/test_account_surface.py`, `tests/test_cli_main.py`,
    `tests/test_docs_contract.py`.
  - Updated docs:
    `docs/guides/troubleshooting.rst`,
    `docs/reference/cli.rst`,
    `external/femic-k3z-instance/docs/troubleshooting.rst`.
  - Next execution step: implement `P15.3c` to wire diagnostics outputs into
    rebuild evidence/runbook guidance.
- 2026-03-12 (Phase 15 `P15.3c` + `P15.4` completion): wired account-surface
  diagnostics into rebuild evidence and finalized user-facing species-account
  docs coverage for K3Z.
  - `femic instance rebuild` now writes `diagnostics.account_surface` into
    rebuild reports when tracks are available and emits summary console lines.
  - `femic instance promote-evidence` now carries
    `summary.account_surface_total_ok_species_empty_signature` and
    `summary.account_surface_species_count`.
  - Updated runbook guidance in:
    `instances/reference/runbooks/REBUILD_RUNBOOK.md`,
    `src/femic/resources/instance/runbooks/REBUILD_RUNBOOK.md`.
  - Added expected-empty account matrix/checklist docs in:
    `docs/sample-models/k3z.rst` and
    `external/femic-k3z-instance/docs/base-case-analysis.rst`.
  - Expanded docs contract checks in `tests/test_docs_contract.py` to lock
    required species-account interpretation sections.
  - Phase 15 checklist is now complete.
- 2026-03-12 (K3Z regression recovery): restored matrix-builder coherence for
  K3Z after block-key mismatch + missing-seral-account regression.
  - Root causes addressed:
    - runtime config drifted `forestmodel_xml_path` away from model-local
      `models/k3z_patchworks_model/yield/forestmodel.xml`.
    - `build-blocks` model-root inference selected instance root in mixed
      `output/` + `models/` layouts.
    - `patchworks.license_value: null` was interpreted as literal `"None"`
      instead of falling back to `SPS_LICENSE_SERVER` env.
  - Implemented fixes:
    - Patched `src/femic/patchworks_runtime.py`:
      - `infer_patchworks_model_dir()` now prefers `tracks`/`yield` sibling
        roots when present.
      - `load_patchworks_runtime_config()` now treats null/blank
        `patchworks.license_value` as env fallback.
    - Added/updated tests in `tests/test_patchworks_runtime.py` for both
      behaviors.
    - Rebuilt K3Z forestmodel with seral stage attributes from
      `data/model_input_bundle/*` + `config/seral.k3z.yaml`, then reran matrix
      build (`run_id: k3z_regression_fix_final_20260312c`).
    - Rebuilt model-local `blocks.shp`/`topology_blocks_200r.csv` with
      `BLOCK <- BLOCK` and verified join-key parity (`csv_only=0`,
      `shp_only=0`).
  - Validation status:
    - `tracks/accounts.csv` now contains `feature.Seral.*` rows again.
    - matrix-builder stderr reports successful completion with
      `Managed : 1781.3132360577583` and no passive area.
- 2026-03-12 (K3Z docs-figure refresh): regenerated instance appendix
  `tipsy_vdyp_tsak3z-*.png` overlays from current `vdyp_transform` rebuild
  outputs and aligned figure wording to treated/scaled-VDYP semantics.
  - Verified rebuild provenance from
    `vdyp_io/logs/k3z_rebuild_report-k3z_rethread_win_20260312_1300.json`:
    `tipsy_curve_mode=vdyp_transform`, `matrix_returncode=0`,
    `block_join_csv_only=0`, `block_join_shp_only=0`.
  - Updated K3Z appendix heading/captions to "Treated (Scaled-VDYP) Curve
    Overlays" so student-facing docs match the actual curve mode.
  - Next step: publish refreshed submodule docs commit and update parent
    submodule pointer so GitHub Pages serves the regenerated overlays.
- 2026-03-14 (TSA-key hardening): strengthened TSA selection/index seams so
  stage 01a does not fail from TSA dtype/key-format drift.
  - Added canonical TSA normalizer in `src/femic/pipeline/tsa.py` and
    upgraded `select_tsa_slice(...)` to:
    - try normalized candidates,
    - fall back to normalized-index masking,
    - emit clearer missing-key diagnostics with available normalized keys.
  - Updated `src/femic/pipeline/stages.py::prepare_tsa_index(...)` to
    normalize TSA values when indexing legacy tables (including stale cached
    int/mixed-case TSA tokens).
  - Added regression tests in `tests/test_pipeline_helpers.py` for
    mixed-case named TSA (`K3Z`) and normalized index preparation behavior.
  - Validation gates run:
    `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
    `pre-commit run --all-files`.
- 2026-03-14 (TIPSY freshness guard): added fail-fast protection against stale
  BatchTIPSY outputs to prevent mismatched VDYP-vs-TIPSY overlays.
  - Added `validate_tipsy_output_is_fresh(...)` in
    `src/femic/pipeline/tipsy.py`.
  - Wired guard into both legacy 01b surfaces:
    `01b_run-tsa.py` and `src/femic/resources/legacy/01b_run-tsa.py`.
  - Default behavior now raises when `04_output-tsaXX.out` is older than
    `tipsy_params_tsaXX.xlsx`; temporary bypass available via
    `FEMIC_ALLOW_STALE_TIPSY_OUTPUT=1`.
  - Added regression tests in `tests/test_tipsy.py` for stale-detect and
    explicit-override paths.
  - Validation gates run:
    `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
    `pre-commit run --all-files`.
- 2026-03-14 (BatchTIPSY input contract clarification): aligned docs + runtime
  checks so `02_input-tsaXX.dat` is explicitly treated as the canonical
  BatchTIPSY handoff input artifact.
  - Added `tipsy_input_dat_path(...)` helper in
    `src/femic/pipeline/tipsy.py`.
  - Updated `validate_tipsy_output_is_fresh(...)` to:
    - prioritize DAT freshness checks over workbook-only checks,
    - fail fast if canonical DAT is missing when 01b is run,
    - continue allowing explicit override via
      `FEMIC_ALLOW_STALE_TIPSY_OUTPUT=1`.
  - Wired DAT-path freshness validation in both 01b runtime surfaces:
    `01b_run-tsa.py`, `src/femic/resources/legacy/01b_run-tsa.py`.
  - Clarified docs in:
    `docs/guides/stage-01a-vdyp-tipsy-input.rst`,
    `docs/guides/stage-01b-post-tipsy.rst`,
    `docs/guides/pipeline-overview.rst`.
  - Added tests for DAT-path helper + missing-DAT guard in
    `tests/test_tipsy.py`.
  - Validation gates run:
    `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
    `pre-commit run --all-files`, `.venv/bin/sphinx-build -b html docs _build/html -W`.
- 2026-03-15 (resume-skip contract fix for missing DAT): patched 01a skip logic
  to require canonical DAT output, preventing stale/missing handoff artifacts
  from being silently skipped in resume mode.
  - Root cause: `_should_skip_01a(...)` only required
    `tipsy_params_tsaXX.xlsx` + `vdyp_curves_smooth-tsaXX.feather`, so
    `02_input-tsaXX.dat` could be missing while 01a was still skipped.
  - Fixed in both active legacy surfaces:
    `00_data-prep.py`,
    `src/femic/resources/legacy/00_data-prep.py`
    by adding `tipsy_input_dat_path(tsa=...)` to required skip outputs.
  - Updated AST wiring expectations in
    `tests/test_legacy_orchestration_wiring.py`.
  - Validation gates run:
    `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
    `pre-commit run --all-files`, `.venv/bin/sphinx-build -b html docs _build/html -W`.
- 2026-03-15 (BatchTIPSY column alignment repair): fixed DAT writer mapping so
  generated `02_input-tsaXX.dat` aligns with operator BatchTIPSY field ranges
  (including species/regeneration columns) and no longer produces blank-species
  parsing failures.
  - Root cause: `src/femic/pipeline/tipsy.py` encoded
    `Proportion: (31, 31)`, forcing one-character width and destabilizing
    fixed-width export behavior for real `0.3`/`0.85` values.
  - Fix applied in `src/femic/pipeline/tipsy.py`:
    `Proportion` widened to `(31, 39)` while preserving screenshot-locked
    BatchTIPSY anchors (`Regen_Method` 64, `SPP_1` 97-99, `SI` 108-111, etc.).
  - Updated regression in `tests/test_tipsy.py` to keep overflow guard
    behavior by asserting width overflow on `FIZ` (1-char field) instead of the
    now-wider `Proportion` field.
  - Regenerated `data/02_input-tsa29.dat` and mirrored
    `external/femic-tsa29-instance/data/02_input-tsa29.dat` from the corrected
    writer path.
  - Validation gates run:
    `ruff format src tests`, `ruff check src tests`, `mypy src`, `pytest`,
    `pre-commit run --all-files`, `.venv/bin/sphinx-build -b html docs _build/html -W`.

## 2026-03-16 - Set default strata coverage to 0.80 and regenerated TSA29 fit outputs
- Updated legacy stage-00 default so `FEMIC_STRAT_TOP_AREA_COVERAGE` now defaults
  to `0.8` (instead of `None`/top-N fallback) in:
  - `00_data-prep.py`
  - `src/femic/resources/legacy/00_data-prep.py`
- Executed a full TSA29 smooth-curve rebuild with
  `FEMIC_STRAT_TOP_AREA_COVERAGE=0.8`, confirming:
  - `coverage 0.8061826878755755`
  - `count 18`
  - `resume: loaded pre-VDYP checkpoint (18 strata)`
- Regenerated TSA29 diagnostics:
  - `plots/strata-tsa29.png`
  - all `plots/vdyp_fitdiag_tsa29-*.png`
  - all `plots/vdyp_lmh_tsa29-*.png`
  - refreshed `data/vdyp_curves_smooth-tsa29.feather`
  - refreshed curve-event log:
    `vdyp_io/logs/vdyp_curve_events-tsa29-tsa29_cov80_refit_20260316T0115Z.jsonl`

## 2026-03-16 - VDYP fit selection status accepted-for-now; proceed to TIPSY-vs-VDYP review
- Fit selection behavior after current tail/toe/censoring updates is marked **OK for now**:
  there is remaining minor selection weirdness in some AUs, but no pathological
  failures and no null-curve total failures.
- Per review direction, deferred additional generalized fit-logic tuning and
  moved forward to regenerated TIPSY-vs-VDYP comparison outputs for visual QA.
- Regenerated TSA29 comparison plots:
  - all `plots/tipsy_vdyp_tsa29-*.png` (54 plots, refreshed at 2026-03-16 05:49 UTC)

## 2026-03-16 - Deferred high TIPSY/VDYP ratio AU review; proceed to ws3 smoke
- Scanned refreshed TSA29 AU-wise TIPSY-vs-VDYP comparisons and ratio diagnostics.
- With VDYP LMH curves currently plausible, queued high-ratio outliers for later
  focused review (not immediate blockers):
  - `ICH_CW L`, `SBPS_SX L`, `MS_PL L`, `SBPS_SX M`, `IDF_FDI L`
  - `ICH_CW H`, `IDF_FDI M`, `SBS_SX M`, `IDF_FD L`, `ICH_CW M`
- Immediate sequence decision: continue now to ws3 smoke on freshly regenerated
  curve and AU outputs, then revisit these AU ratio outliers in a dedicated pass.

## 2026-03-16 - Phase 19 checklist housekeeping reconciliation
- Reconciled Phase 19 parent-task status against completed subtask notes and
  changelog evidence:
  - marked `P19.13` complete,
  - marked `P19.14` complete,
  - marked `P19.16`/`P19.16e` complete.
- Active near-term Phase 19 open gate remains `P19.5` (full Patchworks-enabled
  rebuild validation/evidence promotion in validated runtime host).
- Phase 20 remains intentionally deferred to separate branch per current
  execution priority.
- Added new open task `P19.17` to perform a full TSA29 instance Sphinx docs
  deep-dive and augment thin/missing sections before Phase 19 closeout.
- Prepared Windows 11 Patchworks smoke handoff pack for the remaining `P19.5`
  gate in `planning/tsa29_patchworks_win11_smoke_handoff.md`, including
  exact input artifacts, pass/fail checklist, and evidence-capture targets.
- 2026-03-18 (K3Z checkpoint1 feature export handoff): generated a dedicated
  K3Z checkpoint1 feature artifact and exported it to shapefile, then published
  into the K3Z instance repo for downstream use.
  - Source extraction: masked 2024 VRI source
    `data/bc/vri/2024/VEG_COMP_LYR_R1_POLY_2024.gdb` with K3Z tenure boundary
    `data/bc/cfa/k3z/CFA K3Z Tenure.shp`.
  - Generated artifacts:
    `data/ria_vri_vclr1p_checkpoint1-tsak3z.feather`,
    `data/shp/ria_vri_vclr1p_checkpoint1-tsak3z.{shp,shx,dbf,prj,cpg}`,
    `data/shp/ria_vri_vclr1p_checkpoint1-tsak3z_fieldmap.csv`.
  - Published same artifacts in `external/femic-k3z-instance` and pushed
    submodule commit `a762076` to `origin/main`.

- 2026-03-20 (Phase 21 Windows smoke verification): synced this branch to
  parent commit `d289971` and K3Z submodule commit `ff7bd11`, then reran the
  K3Z Patchworks preflight + Matrix Builder on the validated Windows host.
  - Preflight passed with:
    `python -m femic patchworks preflight --config config/patchworks.runtime.windows.yaml --instance-root external/femic-k3z-instance`
  - Matrix Builder passed with:
    `python -m femic patchworks matrix-build --config config/patchworks.runtime.windows.yaml --instance-root external/femic-k3z-instance --run-id k3z_og_smoke_20260319`
  - Evidence/log paths:
    `external/femic-k3z-instance/vdyp_io/logs/patchworks_matrixbuilder_stdout-k3z_og_smoke_20260319.log`,
    `external/femic-k3z-instance/vdyp_io/logs/patchworks_matrixbuilder_stderr-k3z_og_smoke_20260319.log`,
    `external/femic-k3z-instance/vdyp_io/logs/patchworks_matrixbuilder_manifest-k3z_og_smoke_20260319.json`.
  - Smoke result summary:
    `returncode=0`, `Total=1781.3132360577583`, `Managed=1781.3132360577583`,
    `Passive=0.0`.
  - Verified compiled OG feature-account surface in K3Z tracks and published
    refreshed track tables in `external/femic-k3z-instance` commit `69322b2`.
  - Downstream Patchworks launch/UI smoke also passed: the revised K3Z model
    opened successfully in Patchworks and the new `og1`/`og2` accounts were
    visible and looked correct in the live model interface.

- 2026-03-20 (Phase 22 scaffold foundation): completed the first CT/fert scaffolding slice on branch `feature/k3z-ct-fert-treatment-scaffold` with matching K3Z instance branch `feature/k3z-ct-fert-treatment-option`.
  - Added a new silviculture-config path contract to Patchworks export (`--silviculture-config`) and threaded it through parent CLI/export plumbing without changing current runtime behavior.
  - Added a dedicated treatment-path fragment/XML field `SILV_STATE` with default value `baseline`, keeping `ORIGIN` reserved for natural/planted semantics.
  - Added silviculture scaffold templates:
    - parent bootstrap template: `src/femic/resources/instance/config/silviculture.case_template.yaml`
    - K3Z instance config: `external/femic-k3z-instance/config/silviculture.k3z.yaml`
  - Updated deterministic XML fixtures and regression coverage so the new define-field / fragment-schema contract is enforced before CT/fert treatment logic lands.
  - Next execution target remains Phase 22 treatment mechanics: provisional QMD support, CT curve/treatment synthesis, then fert chain logic.
- 2026-03-20 (Phase 22 CT/QMD slice): implemented the first treatment-mechanics pass on the active feature branches and verified that the optional K3Z variant compiles cleanly in Windows Patchworks Matrix Builder.
  - Pivoted `SILV_STATE` semantics from atomic placeholders to stacked treatment-path states: `baseline`, `cc_pl`, `cc_pl_ct`, `cc_pl_ct_f1`, `cc_pl_ct_f1_f2`, `cc_pl_ct_f1_f2_f3`.
  - Added provisional K3Z QMD feature curves and accounts (`feature.QMD.managed.<au_id>`, `feature.QMD.unmanaged.<au_id>`) with YAML-facing assumptions kept in the silviculture scaffold.
  - Added commercial thinning (`CT`) treatment support for the two initial eligible AUs (`985502001`, `985502002`), planted-only via `ORIGIN='planted'`, with per-AU age/removal parameters and temporary BA:volume conversion.
  - Added post-CT residual-volume curve synthesis so the CT path conserves the no-CT endpoint approximately by subtracting harvested volume at CT age from the planted baseline trajectory.
  - Regenerated the K3Z variant ForestModel XML and patched the validated fragments shapefile to carry `SILV_STATE`, then ran Matrix Builder smoke: `python -m femic patchworks matrix-build --config config/patchworks.runtime.windows.yaml --instance-root external/femic-k3z-instance --run-id k3z_ct_qmd_smoke_20260320`.
  - Smoke evidence: `external/femic-k3z-instance/vdyp_io/logs/patchworks_matrixbuilder_{stdout,stderr,manifest}-k3z_ct_qmd_smoke_20260320.*`; result `returncode=0`, `Managed=1692.2475729276887`, `Passive=89.06566313006975` (retention still active at 5%).
  - Generated tracks now include `CT` products (`product.HarvestedVolume.managed.Total.CT`, species-wise CT harvested volume) plus the provisional QMD account surface; next execution target is the fert1/fert2/fert3 chain.
- 2026-03-20 (Phase 22 fert-chain smoke): completed the first full CT + `fert1`/`fert2`/`fert3` compile pass on the optional K3Z variant and verified it downstream in live Patchworks.
  - Added YAML-driven fertilization sequencing and response-curve synthesis so eligible K3Z CT tracks now expose `F1`, `F2`, and `F3` in addition to `CT`.
  - Added a CT timing guard so effective CT age is pulled back to at most `F1_age - 10` when needed, ensuring there is space for the full fertilization chain.
  - Fresh Matrix Builder rerun: `python -m femic patchworks matrix-build --config config/patchworks.runtime.windows.yaml --instance-root external/femic-k3z-instance --run-id k3z_ct_f123_rerun_20260320`.
  - Fresh evidence/logs: `external/femic-k3z-instance/vdyp_io/logs/patchworks_matrixbuilder_{stdout,stderr,manifest}-k3z_ct_f123_rerun_20260320.*`.
  - Rerun result: `returncode=0`, with compiled tracks now materializing `CT`, `F1`, `F2`, and `F3` treatment rows plus the matching `product.Treated.managed.{CT,F1,F2,F3}` account/product surface.
  - Downstream Patchworks smoke passed: pulling on the `F3` treated-area target induced the expected upstream treatment chain (`F2`, `F1`, `CT`, `CC`) in prior timesteps.
- 2026-03-20 (Phase 22 docs follow-up queued): expand the standalone `femic-k3z-instance` Sphinx docs so they describe the full current K3Z Patchworks surface, not just the newest CT/fert slice.
  - Docs backlog now explicitly includes both:
    - Phase 21 OG rollout coverage (`feature.Area.og1.*`, `feature.Area.og2.*`, `og1`/`og2` curve semantics, and how those accounts appear in compiled Patchworks outputs), and
    - Phase 22 optional CT/QMD/fert variant coverage (YAML parameters, `SILV_STATE` path semantics, provisional curve heuristics, and how student groups pull the optional branch into their instance forks).
- 2026-03-20 (Phase 22 standalone docs pass): updated the standalone `femic-k3z-instance` Sphinx docs to reflect the current full K3Z Patchworks surface, including both the Phase 21 OG rollout and the optional Phase 22 CT/QMD/fert variant.
  - Updated K3Z docs pages: `getting-started.rst`, `model-anatomy.rst`, `assumptions-registry.rst`, `base-case-analysis.rst`, `operator-runbook.rst`, `edit-policy-and-scenarios.rst`, `rebuild-and-qa.rst`, and `metadata-and-lineage.rst`.
  - Added explicit documentation for `og1` / `og2` feature-area accounts, current OG curve semantics, optional branch usage (`feature/k3z-ct-fert-treatment-option`), `SILV_STATE` treatment-path semantics, provisional QMD outputs, and CT/F1/F2/F3 operator expectations.
  - Validation passed: `python -m sphinx -b html external/femic-k3z-instance/docs external/femic-k3z-instance/docs/_build/html -W`.
- 2026-03-20: CT/fert coexistence QA found that `ctfert.pin` now launches cleanly after fixing target-script account-path resolution. Follow-up on map layers is complete: `analysis/ctfert.pin` now includes `CT`, `F1`, `F2`, and `F3` in Current Treatments / Latest Treatments. Remaining open blocker for `P22.9e`: a clean variant rebuild from canonical K3Z inputs is currently blocked because the instance only carries `data/ria_vri_vclr1p_checkpoint1-tsak3z.feather`, while Patchworks export currently requires a later checkpoint that already includes `au`.
- 2026-03-20: repository process tightened in `AGENTS.md`: all non-trivial implementation plans must be recorded in `ROADMAP.md` before execution proceeds. Phase 22 coexistence work is now explicitly tracked under `P22.9` so the single-branch / multi-variant K3Z strategy is visible and auditable outside of chat.
- 2026-03-20 (Phase 23 Windows clean-start progress): the native Windows K3Z rerun now reaches the real VDYP handoff stage using the instance-local 2024 VRI stack, and the failure signature is narrowed enough to drive the next fixes deterministically.
  - Confirmed instance-local 2024 inputs are in use when `femic run` is launched without `FEMIC_EXTERNAL_DATA_ROOT`: `data/bc/vri/2024/VEG_COMP_LYR_R1_POLY_2024.gdb`, `data/bc/vri/2024/VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2024.gdb`, plus local TSA/siteprod junctions under the K3Z instance.
  - Added/validated Windows-specific runtime fixes already working: no Wine preflight requirement on Windows, ArcGIS Pro (`propy.bat`) fallback for SiteProd raster export/stack, and shared-root fallback for `vdyp_params-landp` existence checks.
  - Fresh evidence from `k3z_windows_2024_native_20260320_i` shows the blocking seam is now the actual native VDYP command assembly, not source-data access: VDYP is launched, but the command still dispatches `-p vdyp_params-landp` without a `-c <VDYP_CFG>` argument, producing empty outputs and `proc_stderr_head` = `ERROR: Unable to open parameter file name: 'vdyp_params-landp'` + `FATAL: VDYP7 Configuration Folder ('-c') has not been supplied.`
  - Downstream `01b` stale-BatchTIPSY failure is therefore currently interpreted as a secondary symptom of empty VDYP outputs, not the primary blocker.
  - Immediate next execution order for `P23.2`: fix Windows VDYP command assembly (`-p` resolved path + `-c` config dir), rerun clean-start K3Z on 2024 VRI, then revisit fresh 01b/TIPSY regeneration only after non-empty VDYP tables are confirmed.
- 2026-03-20: P22.9e corrective plan narrowed after the first canonical checkpoint7 regeneration succeeded mechanically but rebuilt the wrong K3Z landbase.
  - The regenerated checkpoint7 currently produces `au=27`, `fragments=260`, and raw THLB-driven unmanaged area, whereas the live teaching baseline is intentionally `THLB=1` everywhere with `fragments=218` across 14 AUs.
  - Corrective approach for the canonical rebuild: regenerate an AU-bearing checkpoint7 from `checkpoint1`, but preserve the current baseline footprint by using the tracked baseline fragment feature/AU mask as the authoritative K3Z teaching surface.
  - Success condition for `P22.9e`: the rebuilt CT/fert variant compiles from canonical upstream inputs and still behaves as an additive extension of the live baseline rather than a broader raw landbase reintroduction.

- 2026-03-20 (Phase 23 Windows native VDYP breakthrough): a clean-start K3Z rerun against the instance-local 2024 VRI stack (`run_id=k3z_windows_2024_native_20260320_l`) now succeeds through VRI load, ArcGIS Pro SiteProd export, VDYP bootstrap, two-pass SI rebin, and TIPSY-input generation on native Windows. The fixes that unlocked this were: (1) resolving `vdyp_params-landp` from FEMIC source root, (2) adding `-c <VDYP_CFG>` to the Windows VDYP command, (3) ensuring the `-c` path ends with a trailing slash so native VDYP can find `*.ctr` files, and (4) materializing `external/femic-k3z-instance/vdyp_io/VDYP.INI` so the parameter file's relative `-ini .\vdyp_io\VDYP.INI` reference resolves inside the instance. The remaining blocker is no longer Windows VDYP; it is the expected manual BatchTIPSY freshness boundary in Stage 01b (`external/femic-k3z-instance/data/04_output-tsak3z.out` is older than the newly generated `external/femic-k3z-instance/data/02_input-tsak3z.dat`). Treat the next execution order as: run BatchTIPSY manually on the fresh `02_input-tsak3z.dat`, replace `04_output-tsak3z.out`, rerun FEMIC Stage 01b/post-TIPSY, then decide whether to automate or explicitly preserve that GUI boundary in Phase 23 docs.

- 2026-03-20 (Phase 23 K3Z Windows handoff simplification): during the native Windows rerun, the remaining BatchTIPSY friction narrowed to a small low-yield tail in the K3Z treated AU set. The next remediation path is now explicit:
  - Exclude the `CWHvm_CW+YC` and `CWHvm_CW+PLC` K3Z strata from BatchTIPSY parameter generation altogether so Windows 01a no longer tries to produce treated TIPSY rows for those low-yield pathways.
  - Treat those same strata as fully netted out of THLB in Patchworks export by forcing `RETENTION = 1.0` for all matching fragments, while keeping their unmanaged VDYP/state surface available in the baseline model.
  - Immediate execution order: add config-driven TIPSY stratum exclusion + full-retention fragment overrides, rerun K3Z Stage 01a on instance-local 2024 VRI, confirm the regenerated `external/femic-k3z-instance/data/02_input-tsak3z.dat` no longer contains the problematic `PLC` treated row, then hand the fresh DAT to BatchTIPSY.

- 2026-03-20: K3Z Windows/TIPSY remediation plan narrowed further after operator review.
  - Accepted modeling simplification for the canonical K3Z rebuild: stop compiling BatchTIPSY rows for the low-yield `CWHvm_CW+YC` and `CWHvm_CW+PLC` strata, and instead net those strata out of THLB completely by forcing `RETENTION = 1.0` for matching fragments.
  - Accepted replacement teaching logic for the remaining treated TIPSY species mixes:
    - FD-pair AUs: `900 FD + 3100 HW`
    - CW-pair AUs: `900 CW + 3100 HW`
    - all other remaining treated AUs: `600 CW + 300 FD + 3100 HW`
  - Follow-through requirement: the user-facing K3Z docs must state this explicitly so students understand why these strata no longer appear in the treated/TIPSY handoff and why their area shows up only in the retained/unmanaged side of the baseline model.

- 2026-03-21 (Phase 23 true-TIPSY evaluation pass): after refreshing external/femic-k3z-instance/data/04_output-tsak3z.out, the downstream-only tsa post-tipsy path was repaired to read schema-v2 vdyp_prep-tsak3z.pkl checkpoints and to execute 01b_run-tsa.py from the instance root so relative ./data and ./plots paths resolve correctly. A true-TIPSY managed-curve rerun completed successfully with
run_id=k3z_post_tipsy_true_tipsy_20260321_d, rebuilt external/femic-k3z-instance/data/model_input_bundle/curve_table.csv and curve_points_table.csv, refreshed the current external/femic-k3z-instance/data/tipsy_curves_tsak3z.csv and tipsy_sppcomp_tsak3z.csv, and regenerated the current external/femic-k3z-instance/plots/tipsy_vdyp_tsak3z-*.png comparison set for the remaining treated AUs. The excluded low-yield strata (22006, 22008) no longer participate in BatchTIPSY and their stale comparison plots were removed so operator review now focuses only on the retained treated AU set. Next decision point: inspect the refreshed plots and decide whether K3Z should keep vdyp_transform as the teaching baseline or switch the managed-curve baseline to true TIPSY output.

- 2026-03-21 (Phase 23 VDYP smoothing triage): operator review of the refreshed K3Z TIPSY-vs-VDYP plots accepted the current true-TIPSY output for now, but flagged a new regression in some smoothed VDYP unmanaged curves: sharp post-peak drop-off followed by an implausible upward blend ramp into the flat tail. The next bounded experiment is to rerun only the cached K3Z smoothing plus downstream handoff from existing `vdyp_results-tsak3z.pkl` and `vdyp_prep-tsak3z.pkl` inputs while (1) removing the hard-coded `tail_blend_override_k3z` selection, (2) relaxing the default toe/right-shift policy away from the current global `body_c_min=20` and `toe_shift_years=20`, and then (3) regenerating downstream DAT/post-TIPSY comparison artifacts without rerunning raw VDYP.
- 2026-03-21 (Phase 23 cached smoothing experiment): reran the K3Z VDYP smoothing stage and downstream post-TIPSY artifacts without rerunning raw VDYP, using cached `external/femic-k3z-instance/data/vdyp_results-tsak3z.pkl` plus `vdyp_prep-tsak3z.pkl`. For this bounded trial, the hard-coded `tail_blend_override_k3z` path was disabled by default in `src/femic/pipeline/vdyp_stage.py`, and the rerun used relaxed fit defaults (`FEMIC_BODY_C_MIN=5`, `FEMIC_VDYP_TOE_SHIFT_YEARS=5`). The smoothing rebuild completed with `run_id=k3z_vdyp_smooth_relax_20260321_b`, rewrote `external/femic-k3z-instance/data/vdyp_curves_smooth-tsak3z.feather`, and recorded events in `external/femic-k3z-instance/vdyp_io/logs/vdyp_curve_events-tsak3z-k3z_vdyp_smooth_relax_20260321_b.jsonl`. Selection counts in that event log were `tail_blend=14`, `primary_nlls=10`, `censored_refit=3`, and importantly there were no `tail_blend_override_k3z` selections. Then `python -m femic tsa post-tipsy --instance-root external/femic-k3z-instance --tsa k3z --run-id k3z_post_tipsy_smooth_relax_20260321_b` completed successfully, refreshing the current `tipsy_vdyp_tsak3z-*.png` comparison plots for the retained treated AUs (timestamps around 2026-03-21 00:50). Next operator step: visually compare these refreshed plots against the backup snapshot under `external/femic-k3z-instance/plots/backup_smoothing_20260321_004810` and decide whether the relaxed smoothing policy is a keeper.
- 2026-03-21 (Phase 23 cached smoothing experiment, pass 2): a second bounded K3Z smoothing rerun pushed the toe and tail policy further in the same cached-results-only workflow. This pass kept `FEMIC_K3Z_FORCE_TAIL_BLEND=0` and used `FEMIC_BODY_C_MIN=0`, `FEMIC_VDYP_TOE_SHIFT_YEARS=0`, `FEMIC_TAIL_LINEAR_MIN_R2=0.45`, `FEMIC_TAIL_LINEAR_MAX_NRMSE=0.35`, `FEMIC_TAIL_LINEAR_PREFER_MIN_AGE=120`, `FEMIC_TAIL_LINEAR_FLAT_SLOPE_ABS=0.10`, `FEMIC_TAIL_LINEAR_MIN_SPAN_YEARS=40`, and `FEMIC_TAIL_BLEND_YEARS=60`. The smoothing rebuild completed with `run_id=k3z_vdyp_smooth_relax_20260321_c`, rewrote `external/femic-k3z-instance/data/vdyp_curves_smooth-tsak3z.feather`, and refreshed downstream post-TIPSY artifacts with `run_id=k3z_post_tipsy_smooth_relax_20260321_c`. The new event log is `external/femic-k3z-instance/vdyp_io/logs/vdyp_curve_events-tsak3z-k3z_vdyp_smooth_relax_20260321_c.jsonl`, and the refreshed `tipsy_vdyp_tsak3z-*.png` plots now carry timestamps around 2026-03-21 00:54. Selection counts in this pass were `tail_blend=20` and `primary_nlls=7`, so the longer-tail policy is materially more permissive than pass 1; operator review is needed to decide whether the visual result is better enough to keep.
- 2026-03-21 (Phase 23 cached smoothing experiment, pass 3 planned): operator review judged pass 2 as moving in the right direction but still too constrained on both the toe and tail. The next bounded trial will keep the cached-results-only workflow and push the same knobs further: allow an earlier body shift (`body_c_min < 0` if tolerated), keep `toe_shift_years=0`, and relax tail-detection / tail-span preferences again so more curves can carry longer, gentler tails before blend selection is considered harmful.
- 2026-03-21 (Phase 23 cached smoothing experiment, pass 3): pushed the toe/tail policy further with `FEMIC_BODY_C_MIN=-20`, `FEMIC_VDYP_TOE_SHIFT_YEARS=0`, `FEMIC_TAIL_LINEAR_MIN_R2=0.20`, `FEMIC_TAIL_LINEAR_MAX_NRMSE=0.50`, `FEMIC_TAIL_LINEAR_PREFER_MIN_AGE=90`, `FEMIC_TAIL_LINEAR_FLAT_SLOPE_ABS=0.20`, `FEMIC_TAIL_LINEAR_MIN_SPAN_YEARS=20`, and `FEMIC_TAIL_BLEND_YEARS=90`, still with `FEMIC_K3Z_FORCE_TAIL_BLEND=0`. Cached smoothing reran successfully with `run_id=k3z_vdyp_smooth_relax_20260321_d`, followed by downstream post-TIPSY refresh `run_id=k3z_post_tipsy_smooth_relax_20260321_d`. The new event log is `external/femic-k3z-instance/vdyp_io/logs/vdyp_curve_events-tsak3z-k3z_vdyp_smooth_relax_20260321_d.jsonl`; selection counts shifted to `tail_blend=15`, `primary_nlls=9`, `censored_refit=3` versus pass 2's `tail_blend=20`, `primary_nlls=7`. The refreshed `tipsy_vdyp_tsak3z-*.png` plots now carry timestamps around 2026-03-21 00:58 and should be compared against the previous pass backup under `external/femic-k3z-instance/plots/backup_smoothing_20260321_005744`.
- 2026-03-21 (Phase 23 fit-override interface note): K3Z VDYP smoothing does not yet expose a user-facing YAML interface for per-stratum/per-SI fit-parameter overrides. Current override surfaces are (a) global run/env knobs such as `FEMIC_VDYP_TOE_SHIFT_YEARS` and tail-linearity env vars, and (b) the code-level per-TSA override map in `src/femic/pipeline/vdyp_overrides.py`. Immediate practical path: use the existing override map for the pathological `CWHvm_DR+HW` curves while continuing to relax the global tail policy; follow-up task remains to promote these per-curve fit overrides into a documented YAML/config surface for case-specific tuning.

- 2026-03-22 (Phase 24 kickoff planning): queued a new documentation-focused phase to rebuild FEMIC's API docs to the `ws3` / `fhops` quality bar and to add agent-friendly technical documentation without maintaining two distinct parallel doc systems. Working hypothesis: the right pattern is one primary human-facing docs tree, augmented with compact technical contract surfaces (repo invariants, runtime prerequisites, canonical artifacts, recovery workflows, stage boundaries, and file/path maps) that are also easy for an embedded coding agent to consume quickly. This is intended to solve a real problem, not create duplicate documentation work.

- 2026-03-22 (Phase 24 audit checkpoint): completed the initial API-docs surface audit and style-reference pass. See planning/phase24_api_docs_audit.md for the concrete findings, rewrite target list, and proposed style rules. Bottom line: FEMIC's current API reference is dominated by autosummary stubs, while `fhops` demonstrates the stronger pattern we want (hand-authored package intros, typical usage, contract notes, then autodoc completeness). `ws3` is also useful as a module-oriented conceptual reference, though the local partial checkout is less polished as a direct API-doc exemplar. First rewrite targets remain `femic.cli.main`, `femic.pipeline.vdyp_stage`, `femic.fmg.patchworks`, `femic.pipeline.io`, `femic.pipeline.tipsy`, `femic.patchworks_runtime`, and `femic.workflows.legacy`.
- 2026-03-22 (Phase 24 rewrite pass 1): promoted `femic.cli.main` from autosummary stub to the first hand-authored API page, establishing the working rewrite pattern for the rest of Phase 24: module purpose, start-here guidance, command structure, common entry surfaces, contract boundaries, and cross-links back to the Guides.
- 2026-03-21 (Phase 23 fit-policy config follow-up): the current src/femic/pipeline/vdyp_overrides.py seam is acceptable as a short-term debugging lever, but it is too cludgey to remain the long-term user/deployment interface. Added low-priority P23.11 to migrate VDYP fit defaults and per-instance override rules into human-readable YAML, keep Python overrides as a narrow fallback only, and update user/developer docs when that interface lands. A dedicated GitHub feature-request issue should be opened when this moves from backlog to active work.

- 2026-03-21 (Phase 23 K3Z lock-in): accepted the current K3Z managed-curve and smoothing policy as the working baseline for now.
  - `config/run_profile.k3z.yaml` now uses `managed_curve_mode: tipsy` in both FEMIC and the standalone K3Z instance.
  - Current K3Z treated-curve baseline is: real BatchTIPSY output, driven by VDYP-derived SI, with CW+YC / CW+PLC excluded from BatchTIPSY and retained out of THLB via `RETENTION = 1.0`.
  - Current unmanaged smoothing checkpoint is the 2026-03-21 relaxed toe/tail policy plus extra DR+HW overrides; refreshed `tipsy_vdyp_tsak3z-*.png` plots are the review artifact of record.


- 2026-03-21 (Phase 22 coexistence expansion): added a third planned K3Z variant, pctct, so the single-branch coexistence model now targets three upstream-distinct variants on one mainline instance: baseline, ctfert, and pctct. The new variant will add a pre-commercial thinning (PCT) gate ahead of CT, apply it at age 10 by default, remove hardwood ingress while retaining the planted conifer component at a 900 stems/ha residual target, and require PCT before CT can fire. Follow-through requirement: extend the variant config/runtime/PIN surface (tracks_pctct, forestmodel_pctct.xml, analysis/pctct.pin, output/patchworks_k3z_pctct_validated/) and update standalone K3Z docs so students choose among the three variants by config/PIN rather than by Git branch.




- 2026-03-21 (Phase 22 closeout bookkeeping): roadmap status reconciled with the work that actually landed on main. `P22.9f`, `P22.9g`, and the parent `P22.10` checkbox are now marked complete because the standalone K3Z docs teach variant selection by config/PIN, the three-variant coexistence layout is merged to `main` in both repos, and `pctct.pin` smoke passed in live Patchworks. `P22.9e` remains open intentionally as the one unresolved canonical-rebuild cleanup item for the CT/fert variant.

- 2026-03-21 (Phase 22 pctct scaffold): implemented the third coexisting K3Z variant as a real compile target rather than just a roadmap stub. Parent FEMIC now supports `pre_commercial_thinning` silviculture config, new `SILV_STATE` values (`cc_pl_pct`, `cc_pl_pct_ct`), and post-PCT conifer-only managed species surfaces. The K3Z instance now carries `config/patchworks.variant.pctct.yaml`, `config/patchworks.runtime.pctct.windows.yaml`, `config/silviculture.k3z.pctct.yaml`, `models/k3z_patchworks_model/analysis/pctct.pin`, `models/k3z_patchworks_model/yield/forestmodel_pctct.xml`, `models/k3z_patchworks_model/tracks_pctct/`, and `output/patchworks_k3z_pctct_validated/`. Windows Matrix Builder smoke passed with `run_id=k3z_pctct_smoke_20260321`; remaining open work is the user-facing docs/runbook update under `P22.10g`.

- 2026-03-21 (Phase 23 docs sync): the standalone K3Z docs and the parent Phase 23 operator guides were reconciled with the accepted K3Z teaching baseline.
  - `external/femic-k3z-instance/docs/figure-appendix.rst` now describes the treated overlay figures as real TIPSY-vs-VDYP comparisons instead of the old scaled-VDYP wording.
  - The treated overlay appendix and plot inventory intentionally omit AUs `22006` and `22008`, because `CWHvm_CW+YC` and `CWHvm_CW+PLC` are now excluded from the treated/TIPSY pathway and retained out of THLB via `RETENTION = 1.0`.
  - Parent/operator docs now document the known-good Windows bootstrap sequence, the low-yield treated-strata netdown decision, and the simplified K3Z treated species-mix logic as the current baseline rather than as temporary operator lore.

- 2026-03-21 (Phase 23 Windows bootstrap/DataLad docs): promoted the Windows workstation ritual from tribal knowledge into the parent docs.
  - `docs/guides/geospatial-runtime-bootstrap.rst` now records the authoritative Windows/Linux runtime surfaces, required executables, and the known-good Windows bootstrap sequence for `.venv`, git/git-annex/DataLad, native VDYP, Java, Patchworks, and ArcGIS Pro fallback.
  - `docs/guides/public-data-mirror-runbook.rst` now includes a Windows-specific collaborator workflow, `.venv\Scripts\datalad.exe` usage, annex-backed payload smoke checks, and recovery guidance when GIS tools dirty the public-data submodule.
  - `docs/guides/deployment-instances.rst` now points Windows users at the bootstrap/runtime guide explicitly.


- 2026-03-21 (Phase 23 Windows preflight hardening): case preflight now understands the real Windows deployment shape instead of assuming every shared asset lives under the instance root. `src/femic/cli/main.py` now falls back from instance-local paths to the FEMIC source tree for shared Windows assets such as `data/tipsy_params_columns`, `vdyp_io/VDYP_CFG`, `VDYP7/VDYP7/VDYP7Console.exe`, and `ria_maptiles.csv`, so `femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml` passes on the known-good workstation. The same preflight path now also checks for `git` and `git-annex` on Windows and runs lightweight annex/DataLad smoke checks (`git -C external/femic-public-data annex version` and `datalad status external/femic-public-data`) whenever the case depends on the annex-backed public-data submodule. This closes `P23.1c` and `P23.4c`.

## Former ROADMAP.md lines 8702-10536 - extracted Phase 52 TSR/THLB narrative block

- Original insertion context: Active Phase 52 narrative moved out of the main roadmap into a dedicated planning note.
- Affected phases/issues: Primary TSR/THLB reconstruction work under `#128` and its child issues.

### Extracted Content

## Detailed Next Steps Notes

- 2026-04-11 (Tracker hygiene after closing `#131`):
  - `#122` now has enough delivered child work to close cleanly:
    - recipe schema/templates;
    - source-layer acquisition/build/run;
    - THLB recipe extraction and reviewed execution bridge;
    - TSA29 validation/reconciliation lane;
    - stage-aware parser/report/workbench/docs improvements; and
    - the strict reconstructed runner now finishing end to end on full TSA29.
  - Remaining open work should live under `#128`, not keep the old recipe-template umbrella artificially open.
  - `#128` should now be read narrowly:
    - the strict reconstructed lane is operational and documented;
    - the reviewed TSA29 bridge lane is still the benchmark-convergent working lane; and
    - the remaining question is why strict reconstructed THLB still lands so far below TSR.
- 2026-04-11 (`#128` should start with an explain-first comparison artifact):
  - Governing problem statement:
    - strict reconstructed full-TSA THLB currently lands at `903,685.409 ha`
      versus the TSR-reported `1,660,053.000 ha`, so the next move should be
      a parent-step comparison inventory, not another blind semantics edit.
  - First deliverable:
    - add `femic tsr thlb-reconstruction-compare` to emit
      `config/tsr/thlb_reconstruction_comparison.{md,json}` from the existing
      reviewed recipe/status and reconstructed audit/status surfaces.
  - Comparison contract:
    - group by parent step rather than compiled-step noise;
    - compare strict reconstructed vs TSR, reviewed bridge vs TSR, and strict
      vs reviewed together in the same report;
    - classify each parent-step difference using a bounded bucket set such as:
      - `close_match`;
      - `reviewed_bridge_only`;
      - `strict_overcut_candidate`;
      - `strict_undercut_candidate`;
      - `blocked_or_missing_source`;
      - `manual_or_reviewed_override`;
      - `aspatial_bridge_difference`; and
      - `not_comparable`.
  - Acceptance bar for this slice:
    - the report must make the largest strict-gap contributors obvious in
      plain language and identify whether the next corrective move should
      target reviewed bridge choices, strict overcuts, strict undercuts, or
      missing-source / blocked seams.
  - `#128` should now be read more narrowly:
    - runtime/usability of the strict reconstructed lane is solved;
    - docs/report/warm-start/fallback child work is solved; and
    - the remaining open problem is the large benchmark-reconciliation gap between the strict reconstructed THLB result and the TSR-reported THLB target.

- 2026-04-11 (`#128` comparison artifact landed on TSA29):
  - Added `femic tsr thlb-reconstruction-compare` and the new instance-local outputs:
    - `config/tsr/thlb_reconstruction_comparison.md`
    - `config/tsr/thlb_reconstruction_comparison.json`
  - The report now compares three surfaces parent-step by parent-step:
    - strict reconstructed vs TSR benchmark;
    - reviewed bridge vs TSR benchmark; and
    - strict reconstructed vs reviewed bridge.
  - The live TSA29 comparison output currently reports:
    - strict reconstructed THLB: `903,685.409 ha`
    - reviewed bridge THLB: `1,592,878.936 ha`
    - TSR reported THLB: `1,660,053.000 ha`
    - strict vs TSR delta: `-756,367.591 ha`
    - reviewed vs TSR delta: `-67,174.064 ha`
    - strict vs reviewed delta: `-689,193.528 ha`
  - The biggest current parent-step contributors are now explicit instead of hidden in chat:
    - `Non-forest` shows up as a major `reviewed_bridge_only` difference;
    - `Critical habitat for fish`, `Land not administered by the Province`, and `Wildlife habitat areas` show up as `strict_overcut_candidate` seams; and
    - `Sites with low growing timber potential` remains a `blocked_or_missing_source` contributor in the strict lane.
  - This means the next `#128` move should be chosen from this inventory rather than from another blind round of code edits.
- 2026-04-11 (`#128` comparison artifact needs engineering triage, not just buckets):
  - The current strict-vs-reviewed report identifies where the biggest gaps are, but it still does not cleanly answer the engineering question:
    - is this step wrong because FEMIC logic is too broad / too weak (`model_endogenous`)?
    - wrong because the required public data is unavailable or blocked (`data_exogenous`)?
    - different because the reviewed TSA29 lane is intentionally carrying an accepted bridge/skip/fallback (`reviewed_bridge_choice`)?
    - or genuinely mixed?
  - The next refinement to `thlb_reconstruction_comparison.{md,json}` should therefore add explicit per-parent-step fields such as:
    - `problem_ownership`
    - `difference_nature`
    - `engineering_interpretation`
    - `recommended_next_move`
  - Because `#128` is explicitly TSA29-first, it is acceptable to seed deterministic per-step interpretation overrides for the major TSA29 seams when a generic bucket alone is too vague to support decision-making.
- 2026-04-11 (`#128` engineering triage fields landed in the comparison artifact):
  - The TSA29 comparison report now persists, for each parent step:
    - `problem_ownership`
    - `difference_nature`
    - `engineering_interpretation`
    - `recommended_next_move`
  - This means the report itself now distinguishes between:
    - strict-lane logic problems we own (`model_endogenous`);
    - blocked/missing-data seams (`data_exogenous`);
    - accepted reviewed bridges/skips/fallbacks (`reviewed_bridge_choice`);
    - and genuinely mixed seams.
  - The next `#128` move should therefore be chosen from the report itself, not reconstructed from chat:
    - attack the largest `model_endogenous` seams first;
    - use `data_exogenous` seams to justify documented aspatial fallback or skip logic;
    - and leave `reviewed_bridge_choice` seams alone unless we intentionally reopen the accepted reviewed TSA29 bridge contract.
- 2026-04-11 (`#128` comparison contract correction: strict-vs-TSR comes first):
  - The report should not emotionally center strict-vs-reviewed deltas.
  - Governing interpretation order:
    - primary benchmark: strict reconstructed vs TSR;
    - secondary context: strict reconstructed vs reviewed; and
    - practical meaning: a step is a top-priority repair when strict is materially bad against TSR, not merely because strict differs from reviewed.
  - Immediate implementation follow-up:
    - add `tsr_fit_class` / `tsr_fit_interpretation` fields;
    - demote the reviewed bucket language to explanatory context;
    - add a stepwise adjudication queue that says whether to:
      - fix strict logic;
      - improve data/source coverage;
      - keep the reviewed bridge;
      - use documented aspatial fallback; or
      - defer a low-priority seam.
  - TSA29-first interpretation target:
    - step 2 should read as close enough to TSR and therefore not a top-priority repair even though reviewed is much lighter;
    - step 9 should still read as a real strict-lane problem because strict is badly high against TSR itself.
- 2026-04-11 (`#128` next phase: one-step-at-a-time adjudication pass):
  - Use `config/tsr/thlb_reconstruction_comparison.{md,json}` as the governing ledger.
  - Work parent steps in row-order sequence, one step at a time, instead of jumping between whichever seam looks most exciting.
  - For each parent step, answer in order:
    - is strict close enough to TSR already?
    - if not, is the gap mainly:
      - FEMIC logic we own;
      - missing/weak data we do not own;
      - or an accepted reviewed bridge/fallback choice?
    - what is the single next action:
      - `fix_strict_logic`
      - `improve_data_or_source`
      - `keep_reviewed_bridge`
      - `use_documented_aspatial_fallback`
      - `defer_low_priority`
  - This is an **active repair queue**, not a passive classification exercise:
    - once a step has been understood well enough to choose an action, implement that action immediately if it is actionable now;
    - only leave the step as analysis-only when the chosen action is explicitly:
      - `defer_low_priority`; or
      - a documented "wait for later" bridge/data decision such as `keep_reviewed_bridge` or `improve_data_or_source`.
  - Do not silently “fix ahead” on later steps while earlier-step interpretation is still unresolved.
  - Do not move to the next parent step after deciding `fix_strict_logic` or `use_documented_aspatial_fallback` unless the corresponding code/report change has actually been landed and checkpointed.
  - Reassess the whole-ladder read only after working through the final parent step again; that is the point where we should answer:
    - is strict THLB now close enough overall, or
    - still fundamentally “fix me” status?
- 2026-04-12 (Execution-discipline hardening after repeated scope drift):
  - For the active TSR/THLB adjudication game, `one step at a time` now means one bounded unit only:
    - one code change; or
    - one validation run; or
    - one report rebuild; or
    - one docs/issue/planning update.
  - Do **not** bundle implementation, broad rerun, and downstream validation together unless the developer explicitly asks for that bundle.
  - Before any expensive or broad command, report:
    - the exact command;
    - the one question it answers; and
    - why a smaller run is not enough.
  - After each bounded unit:
    - stop;
    - report; and
    - wait for the next instruction.
  - For this adjudication track specifically:
    - do not run downstream parent steps when the current question is about one parent step only;
    - do not launch whole-lane reruns just because they would eventually be needed; and
    - treat scope expansion as a correctness failure, not as initiative.
  - `scope breach` is the explicit stop word:
    - stop background work immediately;
    - return to the last agreed bounded unit; and
    - do not widen scope again until the developer does so explicitly.
- 2026-04-11 (`#128` strict-lane adjudication baseline artifact checkpoint):
  - The first full successful LU-wise strict-reconstructed TSA29 state should be preserved as a restart point before step-by-step adjudication begins.
  - Governing snapshot:
    - `external/femic-tsa29-instance/runtime/logs/tsr/reconstructed_lu/ria_vri_vclr1p_checkpoint1.20260411T203327Z`
  - Rationale:
    - without a tracked checkpoint of the per-step/per-LU feather outputs, a bad mid-adjudication experiment could force another ~96 minute full strict rerun just to get back to the start of the game.
  - Hygiene follow-up:
    - ignore future untracked `runtime/logs/tsr/reconstructed_lu/` scratch spill in the TSA29 submodule while keeping the tracked baseline snapshot and committed comparison artifacts as the clean adjudication starting point.
- 2026-04-11 (`#128` step 2 adjudicated):
  - Parent step:
    - `thlb_parent_002_land_not_administered_by_the_province`
  - Governing read:
    - strict removed area: `713,594.208 ha`
    - TSR benchmark marginal area: `697,033.000 ha`
    - strict-vs-TSR delta: `+16,561.208 ha`
  - Interpretation:
    - strict is close enough to TSR here for practical exploratory use even though the reviewed bridge lane is much lighter;
    - the large strict-vs-reviewed gap is not the governing benchmark for this step.
  - Adjudication action:
    - `defer_low_priority`
  - Next-move rule:
    - do not spend time tuning step 2 yet;
    - revisit only after higher-priority strict-vs-TSR seams are worked through.
- 2026-04-11 (`#128` step 3 adjudicated):
  - Parent step:
    - `thlb_parent_003_non_forest`
  - Governing read:
    - strict removed area: `1,690.701 ha`
    - TSR benchmark marginal area: `1,105,908.000 ha`
    - strict-vs-TSR delta: `-1,104,217.299 ha`
  - Interpretation:
    - this is a real seam, but not a simple “missing data” problem;
    - the strict lane is only doing the narrow direct waterbody/FMLB-style check while the reviewed lane carries a much broader non-forest bridge;
    - because reconstructed mode starts from `checkpoint1_aflb_initialization`, this early `GLB -> AFLB` stepwise delta is also a baseline-conditioned diagnostic rather than a literal raw-GLB replay.
  - Adjudication action:
    - `keep_reviewed_bridge`
  - Next-move rule:
    - do not rush into code edits for step 3 yet;
    - first decide and document the intended strict non-forest semantics, then revisit whether that bridge should stay accepted or be translated into strict logic later.
- 2026-04-11 (`#128` step 4 adjudicated):
  - Parent step:
    - `thlb_parent_004_roads_and_landings`
  - Governing read:
    - strict removed area: `0.000 ha`
    - reviewed removed area: `1,557.111 ha`
    - TSR benchmark marginal area: `50,434.000 ha`
    - strict-vs-TSR delta: `-50,434.000 ha`
  - Interpretation:
    - this is not just a case where the strict lane found no roads;
    - TSA29 section 6.2.3 explicitly says existing roads, trails, and landings are modeled non-spatially through partial AFLB reductions because the features are too small and incomplete to delineate reliably at landscape scale;
    - the current strict lane only executes the two narrow permanent-road buffer rules, and those buffers found no active LU-clipped fragments in the reconstructed run;
    - the current reviewed result is only a Williams Lake LU smoke proof, not a full-TSA bridge result, so the tiny reviewed number is not the real target either.
  - Adjudication action:
    - `use_documented_aspatial_fallback`
  - Next-move rule:
    - do not waste time tuning the current tiny spatial-only road result;
    - formalize an explicit aspatial AFLB reduction for existing roads, trails, and landings in the strict lane if we need this step to behave more like TSR.
- 2026-04-11 (`#128` step 4 implementation target locked):
  - Governing fallback target:
    - use `50,434 ha` for the strict-lane step-4 aspatial AFLB deduction.
  - Why this is the implementation target:
    - `50,434 ha` is the live `benchmark_marginal_area_ha` already parsed into the recipe and comparison ledger for `thlb_parent_004_roads_and_landings`;
    - the stepwise adjudication contract says strict-vs-TSR is the governing benchmark; and
    - the Table 6 category totals in the TSR text sum to about `50,433 ha`, which aligns with the benchmark after rounding.
  - Explicit non-target:
    - do **not** use the conflicting prose sentence `32,526 ha` as the fallback target.
  - Implementation rule:
    - formalize step 4 as a documented `aspatial_area_reduction` in the strict lane;
    - compute the remaining fallback as:
      - `max(0, 50,434 ha - exact_step4_removed_area_ha)`
    - for the current TSA29 strict run, the exact step-4 spatial substeps remove `0 ha`, so the effective fallback target is the full `50,434 ha`.
- 2026-04-11 (`#128` step 4 implemented and validated):
  - Implementation landed:
    - step 4 compiled logic now uses a documented `aspatial_area_reduction` fallback in the strict lane;
    - smoke-only approved review logic no longer freezes compiled logic during full-TSA rebuilds, so the old Williams Lake LU smoke placeholder does not override the new step-4 contract.
  - Reconstructed runner fix landed:
    - the diagnostic/resume runner now passes the TSR total-area benchmark through to `aspatial_area_reduction`, so step-only replay does not mislabel those rows as `unsupported`.
  - Step-only validation rule followed:
    - resume from the saved post-step-3 LU baseline;
    - run reconstructed diagnostic indices `3:6` only;
    - do not rerun downstream parent steps as part of step-4 validation.
  - Validated result:
    - step 4 exact road buffers still removed `0 ha`;
    - step 4 fallback removed exactly `50,434 ha`;
    - strict-vs-TSR delta for step 4 is now `0 ha`;
    - step 4 should now be treated as `defer_low_priority` instead of an active strict-lane blocker.
- 2026-04-11 (`#128` strict-lane baseline caveat for the remaining adjudication pass):
  - The current strict reconstructed lane is **not** yet a literal raw-GLB replay of the full TSA29 Table 3 ladder.
  - Current strict baseline:
    - `checkpoint1_aflb_initialization`
  - Practical consequence:
    - early `GLB -> AFLB` parent-step marginal deltas are baseline-conditioned diagnostics, not literal raw-GLB stepwise replays.
  - Working rule for the rest of the adjudication pass:
    - keep using the current strict-vs-TSR ledger to sort out stepwise strict logic/seam problems;
    - do **not** treat the current early-step marginal numbers as the final word on strict-lane correctness.
  - Required closure task before `#128` can close:
    - start the strict lane from a true raw-GLB geometry baseline;
    - rerun the full strict lane end to end from that raw GLB start;
    - confirm the resulting stepwise and cumulative behavior is sane before calling the strict lane “done”.

- 2026-04-12 (`#128` active next move: raw-GLB reset before further stepwise adjudication):
  - Pause the current one-step-at-a-time adjudication sequence here.
  - Use `data/ria_vri_vclr1p_checkpoint1.feather` as the raw geometry universe, but stop pre-filtering it into AFLB during reconstructed initialization.
  - Governing implementation order:
    - switch reconstructed initialization to `checkpoint1_raw_glb_initialization`;
    - rerun the full strict TSA29 lane from the top with the normal reconstructed command;
    - rebuild the strict-vs-TSR comparison ledger from that new run;
    - snapshot the new LU-wise strict baseline artifacts; and
    - restart adjudication from step 2 on the rebuilt ledger.
  - Do not continue adjudicating step 6+ from the old AFLB-conditioned strict run.

- 2026-04-11 (`#131` completed: LU-wise reconstructed THLB runtime is now operational on full TSA29):
  - Completion summary:
    - replaced the old reconstructed full-area row-batch exact overlay path with cached LU-wise decomposition over checkpoint1/AFLB;
    - carried LU chunk state forward through reconstructed steps so only touched chunks are re-cut;
    - kept explicit reconstructed aspatial fallback from `#132` working in the same lane;
    - added reconstructed timing summaries so the live audit/status surfaces show total runtime, timing buckets, and the slowest steps in plain language; and
    - completed the real production command `femic tsr thlb-netdown-run --execution-mode reconstructed` on full TSA29 without silent stand-binary fallback.
  - Governing full-TSA result:
    - runtime finished in about `96.09 min`;
    - exact fragment-overlay steps: `17`;
    - explicit aspatial fallback steps: `2`;
    - blocked exact-overlay steps: `0`;
    - debug stand-binary fallback steps: `0`;
    - LU-wise exact-overlay chunks touched: `1025`; and
    - final reconstructed THLB managed area: `903685.409 ha`.
  - Important plain-language read:
    - the strict geometry-first reconstructed lane is now operationally usable;
    - it is still slower than the reviewed TSA29 bridge lane, but it no longer dies on the old step-002 wall; and
    - the next performance question, if it ever matters again, is optional LU-bundled parallelization rather than basic viability.

- 2026-04-11 (Issue `#131` active again: LU-wise exact decomposition for reconstructed THLB runtime closure):
  - Objective:
    - keep the reviewed TSA29 parent-step lane untouched;
    - make the strict reconstructed lane finish in practical time by cutting the land base one Landscape Unit at a time instead of trying to cut the whole TSA at once; and
    - close `#131` with a real full-TSA reconstructed run rather than leaving it parked on timeout evidence.
  - Implementation direction:
    - reuse the existing LU partition/cache helpers already proven in the parent-step lane;
    - initialize checkpoint1/AFLB once, materialize cached LU chunk files once, and then carry those chunk files forward as the reconstructed step state;
    - for each spatial `exclude` step, load only the LU chunks touched by the exclusion geometry and run exact overlay inside those chunks instead of building one full-TSA candidate set;
    - preserve exactness by clipping per LU, keeping `SOURCE_FEATURE_ID` lineage, and regenerating global `FEATURE_ID` values only when merged output is written;
    - keep reconstructed explicit aspatial fallback from `#132` working in the same lane without auto-converting blocked spatial rows into fallback.
  - Acceptance target:
    - reconstructed tests prove LU-wise exact overlay returns the same binary THLB result as the current exact row-batch path on controlled inputs;
    - TSA29 reconstructed smoke still completes with exact overlay and no silent stand-binary fallback; and
    - the real full-TSA reconstructed run completes with practical wall time, clear audit/status reporting, and enough evidence to close `#131`.

- 2026-04-11 (Issue `#132` active: add explicit aspatial fallback for blocked THLB target-area steps in reconstructed mode only):
  - Objective:
    - keep the reviewed TSA29 parent-step/notebook lane unchanged;
    - fill the missing seam in `femic tsr thlb-netdown-run --execution-mode reconstructed` so recipe rows already compiled as `aspatial_reduction` or `aspatial_area_reduction` execute honestly instead of remaining outside the reconstructed runnable set; and
    - keep fallback explicit, recipe-driven, and visibly separate from exact spatial overlay.
  - Implementation direction:
    - expand reconstructed runnable actions from `use_land_base`, `no_deduction`, and `exclude` to also include `aspatial_reduction` and `aspatial_area_reduction`;
    - reuse the existing aspatial reduction helpers already used by the reviewed parent-step lane instead of inventing a second deduction path;
    - label those reconstructed rows as `aspatial_fallback` in runtime/audit/status surfaces;
    - do not auto-convert blocked spatial `exclude` rows into fallback unless the recipe row itself is already compiled as aspatial; and
    - keep `manual_review_required` and `reference_only` rows non-executable.
  - Acceptance target:
    - reconstructed tests prove `aspatial_reduction` and `aspatial_area_reduction` now execute in reconstructed mode;
    - reconstructed audit/status reporting separates exact overlay, explicit aspatial fallback, blocked exact overlay, debug stand-binary fallback, and no-deduction rows; and
    - a TSA29 reconstructed smoke run shows explicit aspatial fallback steps where the reviewed recipe already carries them, without changing the practical reviewed TSA29 lane.
- 2026-04-11: Issue `#132` is complete.
  - Reconstructed THLB now executes recipe rows already compiled as:
    - `aspatial_reduction`
    - `aspatial_area_reduction`
  - The change is intentionally narrow:
    - reconstructed runner only;
    - no reviewed parent-step/notebook lane behavior changed; and
    - blocked spatial `exclude` rows are still not auto-converted into fallback.
  - Reconstructed audit/status reporting now separates:
    - exact fragment overlay;
    - explicit `aspatial_fallback`;
    - blocked exact overlay; and
    - debug stand-binary fallback.
  - TSA29 reconstructed smoke proof:
    - `femic tsr thlb-netdown-run --instance-root external/femic-tsa29-instance --execution-mode reconstructed --auto-map-id-smoke-subset`
      completed successfully on `MAP_ID 092O071`;
    - smoke result recorded:
      - `fragment_overlay_step_count = 12`
      - `aspatial_fallback_step_count = 1`
      - `aspatial_fallback_area_ha = 297.242`
      - `blocked_exact_overlay_step_count = 0`
      - `stand_binary_fallback_step_count = 0`
    - live reconstructed status/audit surfaces now show the fallback bucket explicitly without presenting it as exact spatial reproduction.

- 2026-04-11 (Issue `#136` active: add no-LLM THLB warm-start checklist templates from recurring TSR netdown patterns):
  - Objective:
    - keep the current THLB recipe/status/workbench surfaces as canonical reviewed state;
    - add one explicit no-LLM warm-start artifact pair:
      - editable YAML template under `config/tsr/`; and
      - plain-language checklist Markdown under `workbench/tsr/`;
    - seed the first version from a bounded packaged THLB motif library rather than a broad corpus-mining engine.
  - Implementation direction:
    - reuse the existing stage-aware parent-step structure, exact-logic summaries, source-linkage state, and override state already carried by the reviewed THLB recipe;
    - classify each parent step into a small fixed warm-start status set (`compiled_ready`, `review_pattern_match`, `blocked_missing_source`, `manual_or_aspatial`, `no_pattern_match`);
    - match recurring motifs deterministically from current parent-step fields such as stage, candidate operation type, candidate layers/fields/values, execution class, and linked source status;
    - keep the new checklist/template explicitly non-canonical so it never auto-promotes into executable THLB logic.
  - Acceptance target:
    - `femic tsr thlb-netdown-warmstart-build --instance-root external/femic-tsa29-instance`
      emits:
      - `config/tsr/thlb_warmstart.yaml`; and
      - `workbench/tsr/thlb_netdown.warmstart.md`;
    - TSA29 late-step examples like steps `013`, `014`, `018`, `021`, and `023` render with plain-language review guidance that matches current accepted FEMIC state.
- 2026-04-11: Issue `#136` is complete.
  - Added a packaged bounded motif library at
    `src/femic/resources/tsr/thlb_warmstart_patterns.yaml`.
  - Added deterministic warm-start generation over the reviewed THLB recipe in
    `src/femic/tsr_catalog/recipes.py`, with CLI wiring for:
    - `femic tsr thlb-netdown-warmstart-build --instance-root PATH`
  - Default warm-start outputs are now:
    - `config/tsr/thlb_warmstart.yaml`
    - `workbench/tsr/thlb_netdown.warmstart.md`
  - The warm-start pair is explicitly non-canonical:
    - canonical executable THLB logic remains
      `config/tsr/thlb_netdown.recipe.yaml`
  - TSA29 acceptance result:
    - `femic tsr thlb-netdown-warmstart-build --instance-root external/femic-tsa29-instance`
      emitted the paired artifacts successfully;
    - emitted counts:
      - `milestone_count = 4`
      - `parent_step_count = 20`
      - `warmstart_status_compiled_ready = 11`
      - `warmstart_status_manual_or_aspatial = 9`
    - refreshed TSA29 review surfaces now point to
      `workbench/tsr/thlb_netdown.warmstart.md`
      without promoting it into canonical THLB logic.

- 2026-04-10 (Issue `#138` active: add a Windows ArcGIS Pro review-project
  emit command for FEMIC instances):
  - Objective:
    - emit a ready-to-open ArcGIS Pro `.aprx` plus manifest for an existing
      FEMIC instance so a human can inspect downloaded GIS layers and local
      context layers visually without hand-loading them one by one.
  - Implementation plan for this slice:
    - add `femic prep arcgis-review-project --instance-root PATH` with
      optional `--output-dir` and `--project-name`;
    - reuse the existing ArcGIS Pro Python resolution/execution seam already
      used by SiteProd fallback instead of duplicating `propy.bat`
      discovery logic in an ad hoc script;
    - generalize the TSA29 prototype script into core code that discovers
      reviewable `.shp` / `.gpkg` layers from the instance, applies simple
      deterministic naming/order/transparency defaults, and emits:
      - one `.aprx`;
      - one manifest JSON; and
      - helper `.lyrx` files under the same output root;
    - keep v1 intentionally review-oriented:
      - all layers default to `visible = off`;
      - no auto-launch of ArcGIS Pro; and
      - no change to FEMIC's canonical processing pipeline.
  - Acceptance target:
    - unit/CLI tests cover layer discovery, classification, manifest shaping,
      and clean ArcGIS-missing failure messages; and
    - a real Windows/ArcGIS Pro TSA29 run emits a usable project bundle whose
      manifest matches the loaded layers.
- 2026-04-10 (Issue `#138` implemented: FEMIC can now emit a ready-to-open
  ArcGIS Pro review project for an instance):
  - Delivered command surface:
    - added `femic prep arcgis-review-project --instance-root PATH` with
      optional `--output-dir` and `--project-name`;
    - reused the shared ArcGIS Pro Python runner seam now centralized in
      `src/femic/arcgis_pro.py`; and
    - kept the feature explicitly review-only rather than introducing a new
      GIS processing backend.
  - Review-project behavior:
    - discover instance-local `.shp` / `.gpkg` layers under `data/` and
      `output/`;
    - skip smoke-scoped cached BCDC overlays under
      `data/downloads/bcdc/smoke`;
    - emit a manifest-backed `.aprx` plus helper `.lyrx` files under the
      chosen output root;
    - keep all layers off by default at launch; and
    - stage GeoPackage layers as helper shapefiles inside the emitted bundle
      when ArcGIS Pro compatibility requires it.
  - Acceptance result on TSA29:
    - a real Windows/ArcGIS Pro run emitted
      `runtime/logs/arcgis_review_acceptance_tsa29_clean/tsa29_arcgis_review_20260410c.aprx`
      and the matching manifest JSON;
    - the project included `79` layers;
    - the command skipped `3` smoke-scoped cached BCDC artifacts; and
    - `77` GeoPackage-backed review layers were staged into the emitted bundle
      so ArcGIS Pro could load them reliably.

- 2026-04-10 (Issue `#139` active: model TSA29 section `7.1.5`
  broadleaf-volume exclusions as a later post-TIPSY yield assumption):
  - Governing split:
    - THLB step `015` stays exactly what TSA29 section `6.4.5` says it is:
      exclude broadleaf-leading stands from THLB area;
    - TSA29 section `7.1.5` is a separate later yield assumption, not a THLB
      polygon-removal rule.
  - Implementation plan for this slice:
    - add one narrow `yield_assumptions_path` seam to `tsa post-tipsy`,
      `tsa btc-post-tipsy`, and `modes.yield_assumptions_path`;
    - default to `config/tsr/yield_assumptions.yaml` under the instance root
      when present, otherwise do nothing;
    - after `build_bundle_tables_from_curves(...)` and before
      `write_bundle_tables(...)`, inspect untreated species-proportion sidecar
      curves, identify conifer-leading untreated AUs with non-zero broadleaf
      share, scale the untreated total curve by the conifer share, zero the
      untreated broadleaf sidecars, and renormalize the remaining untreated
      conifer sidecars to sum to `1.0`;
    - leave treated curves untouched and keep the rule completely separate
      from THLB step `015`;
    - record adjusted AUs, broadleaf share used, total untreated volume
      removed, and the config path in the post-TIPSY manifest.
  - Acceptance target:
    - rerun TSA29 `post-tipsy` / `btc-post-tipsy`, inspect the regenerated
      bundle tables directly, and confirm only the intended untreated
      conifer-leading mixed AUs changed while THLB step `015` notes still read
      as broadleaf-leading area exclusion only.
- 2026-04-10 (Issue `#139` implemented: TSA29 broadleaf-volume exclusions now
  run in the post-TIPSY bundle lane instead of the THLB netdown lane):
  - Added the narrow `yield_assumptions_path` seam to:
    - `femic tsa post-tipsy`;
    - `femic tsa btc-post-tipsy`; and
    - `modes.yield_assumptions_path` in run-profile YAML.
  - Default behavior now auto-loads `config/tsr/yield_assumptions.yaml` from
    the instance root when it exists, otherwise post-TIPSY behaves exactly as
    before.
  - Implemented the TSA29 section `7.1.5` rule after bundle assembly and
    before bundle-table write:
    - detect conifer-leading untreated AUs from untreated species-proportion
      sidecars;
    - remove the broadleaf share from the untreated total curve;
    - zero untreated broadleaf species-proportion sidecars; and
    - renormalize the remaining untreated conifer sidecars to `1.0`.
  - Manifest/report evidence now records:
    - the assumptions config path;
    - adjusted AU ids and stratum labels;
    - untreated broadleaf/conifer shares; and
    - total untreated volume removed.
  - TSA29 proving-ground result:
    - `femic tsa btc-post-tipsy --instance-root external/femic-tsa29-instance --run-config config/run_profile.tsa29.yaml --tsa 29 --run-id issue139_btc_post_tipsy_20260410a`
      completed successfully;
    - the broadleaf-volume rule adjusted `6` untreated AUs:
      `IDF_FD H`, `SBPS_PL M`, `SBPS_PL H`, `SBPS_SX H`, `SBS_SX M`, and
      `SBS_SX H`;
    - manifest summary recorded `69,020.56` untreated volume removed; and
    - a scratch no-assumption comparison confirmed the treated curves for all
      adjusted AUs were unchanged while the untreated curves differed exactly
      where expected.
  - THLB boundary remained intact:
    - TSA29 step `015` wording in `config/tsr/thlb_netdown.status.md` still
      describes only the broadleaf-leading stand area exclusion and continues
      to defer section `7.1.5` to the later yield-assumption lane.

- 2026-04-10 (Issue `#140` active finish pass: wire DWDS follow-up back into
  the TSR source-layer recipe runner):
  - Current state:
    - the DWDS helper seam is already real and live-proven in
      `src/femic/bcdc_dwds.py`;
    - `femic data bcdc-order-followup` already reloads saved manifests, retries
      the public status seam, falls back through `pickupByGUID`, and
      materializes the recovered artifact; but
    - `femic tsr source-layers-run` still stops at `ordered` for `dwds_order`
      entries and does not automatically reuse those saved manifests on rerun.
  - Finish-pass target:
    - persist one instance-relative `order_manifest_path` per DWDS-backed
      source-layer recipe entry;
    - teach `run_tsr_source_layers_recipe(...)` to follow up an existing saved
      manifest before considering any new submission;
    - promote recovered artifacts back into `artifact_path` automatically and
      mark the entry `materialized`;
    - keep `--allow-order` narrow so it only gates new DWDS submission; and
    - reconcile roadmap / issue state so `P52.6b4` matches the real code state
      after the TSR integration seam is finished.
- 2026-04-10 (Issue `#140` finished: TSR source-layer reruns now reuse saved
  DWDS manifests instead of stopping at `ordered`):
  - Added per-entry `order_manifest_path` persistence for DWDS-backed
    source-layer recipe entries.
  - `run_tsr_source_layers_recipe(...)` now does this in order for
    `dwds_order` entries:
    - reuse an already materialized local artifact if the saved manifest still
      points at one;
    - otherwise follow up the saved DWDS manifest automatically and promote any
      recovered artifact back into `artifact_path`;
    - only submit a new DWDS order when no saved manifest exists and
      `--allow-order` is explicitly enabled.
  - Source-layer runner statuses are now honest about the DWDS lifecycle:
    - `ordered`
    - `followup_pending`
    - `materialized`
  - TSA29 proving-ground confirmation:
    - a scratch source-layer recipe built from the real PSP case and a real live
      DWDS manifest advanced cleanly to `materialized` without a new order
      submission and recovered
      `data/downloads/bcdc/WHSE_FOREST_VEGETATION_GRY_PSP_STATUS_ACTIVE/GRY_PSP_STATUS_ACTIVE.gpkg`.

- 2026-04-06 (Issue `#140` opened: improve DWDS follow-up retrieval and
  artifact materialization after order submission):
  - Proven live seam:
    - FEMIC successfully submitted a clipped DWDS order for TSA29 step `017`
      (`WHSE_FOREST_VEGETATION.GRY_PSP_STATUS_ACTIVE`) and received
      `order_id=2551251`;
    - the public `/order/{id}` probe still reported the known false-negative
      "order does not exist" response; and
    - the missing piece is now clearly post-submission retrieval/materialization,
      not order creation.
  - Immediate implementation target:
    - persist enough structured DWDS follow-up state that FEMIC can retry
      retrieval without re-submitting blindly;
    - probe for stronger post-submission seams than the current fragile
      `/order/{id}` endpoint; and
    - feed any recovered artifact path back into TSR source-layer and THLB
      workflows so DWDS-backed steps like TSA29 step `017` can become runnable.
- 2026-04-06 (Issue `#141` opened: full-TSA29 THLB retest and recipe
  reconciliation after the Williams Lake LU ratchet pass):
  - The single-LU work is now pre-validation evidence only; the next hardening
    pass must rerun the currently executable TSA29 ladder on the full dataset
    against the canonical 2024 Table 3 marginal/cumulative benchmarks.
  - Scope for `#141`:
    - rerun every executable transformation row in canonical Table 3 order
      while preserving milestone rows as non-runnable nodes;
    - keep the established stage split:
      - `GLB -> AFLB` on checkpoint1-style land-base surfaces; and
      - `AFLB -> LHLB -> THLB` on the curve-ready pre-legacy-THLB checkpoint;
    - treat current LU soft approvals as candidate confirmations rather than
      final acceptance; and
    - emit one explicit full-run validation summary under `config/tsr/`
      recording per-step full-TSA benchmark comparison, disposition, and
      AFLB/THLB lock readiness.
  - Full-TSA validation must explicitly confirm:
    - early-stage area deductions like step `023` still recompute from stable
      canonical area and only overwrite `FEMIC_EFFECTIVE_AREA_SQM`;
    - later-stage exclusions preserve geometry/fragments and lower
      harvestability in place (`thlb_fact` / `thlb = 0`);
    - and steps should only be reopened when full-TSA evidence materially
      misses the TSR benchmark or exposes a semantic error the LU smoke could
      not reveal.
  - Immediate reconciliation subtask:
    - refresh the BC-wide `WHSE_ADMIN_BOUNDARIES.FADM_TSA` artifact from the
      BC Data Catalogue, then use that fresh TSA boundary to rebuild the TSA29
      masked 2024 VRI stand universe from the BC-scale VRI source;
    - compare the resulting fresh GLB proxy against:
      - the current full-TSA29 GLB proxy already being used in `#141`; and
      - the TSR Table 3 total TSA area benchmark;
    - use that comparison to decide whether the current ~`225k ha` GLB excess
      is coming from a stale/incorrect TSA mask seam or from a deeper VRI/input
      surface mismatch.
  - Current decision checkpoint:
    - the refreshed `FADM_TSA` Williams Lake dissolve is effectively exact
      against the TSR Table 3 total (`4,933,664.338 ha` vs `4,933,635 ha`);
    - the current full-TSA post-step-23 AFLB remains `2,905,358.090 ha`, about
      `152,147.910 ha` low relative to the implied Table 3 benchmark
      (`3,057,506 ha`);
    - the exact reason the individual `GLB -> AFLB` marginal rows do not line
      up remains unresolved, but the resulting AFLB is close enough overall to
      count as "good enough" for TSA29 validation; and
    - treat the early full-TSA `GLB -> AFLB` pass as green-lit and move the
      active `#141` work down into `AFLB -> LHLB` / `LHLB -> THLB` validation.
- 2026-04-06 (Issue `#143` opened: LU-wise local-process parallel THLB
  benchmark side quest):
  - Motivation:
    - full-TSA THLB step validation under `#141` is currently too slow for
      rapid recipe iteration on this workstation; and
    - we need a contained answer to whether exact LU-clipped decomposition plus
      local multi-process execution can materially shorten the feedback loop
      without changing THLB semantics.
  - Scope for `#143`:
    - keep GeoPandas/Shapely as the GIS engine;
    - prototype a Windows-first local `ProcessPoolExecutor` backend;
    - clip the active working geometry to LU boundaries so every worker gets a
      disjoint exact spatial slice;
    - benchmark only the expensive spatial step classes:
      - `004 Roads and landings`;
      - `007 Old growth management areas`;
      - `018 Riparian areas`; and
      - `019 Buffered trails`;
    - compare serial vs LU-parallel runtime, parity, and basic memory signals
      on the current workstation with worker counts `1`, `2`, `4`, `8`; and
    - decide whether the feature is worth keeping before touching the main
      `#141` validation lane.
  - Guardrails:
    - no centroid/map-sheet stand assignment heuristics;
    - no ArcGIS backend revival after the closed `#142` benchmark result;
    - do not adopt the feature if LU-parallel merge-back changes removed area,
      remaining area, or later-stage `thlb_fact` / `thlb` semantics beyond a
      very small tolerance; and
    - keep the side quest on its own feature branch so any experimental mess
      can be abandoned cleanly if the benchmark result is negative.
- 2026-04-06 (Issue `#143` prototype landed: LU-wise local-process parallel
  THLB benchmark harness and backend toggle):
  - Implementation status:
    - added an experimental LU-parallel execution mode to the THLB parent-step
      runner using local `ProcessPoolExecutor` workers, with explicit
      `serial` vs `lu_parallel` mode selection and optional worker-count
      control;
    - added LU clipping helpers that split the active working geometry into
      disjoint landscape-unit slices before dispatch;
    - added a new benchmark entrypoint:
      - `femic tsr thlb-netdown-parallel-benchmark`
    - added benchmark result artifacts under:
      - `runtime/logs/tsr/parallel_benchmarks/`
    - kept GeoPandas/Shapely as the only GIS engine in scope for this side
      quest.
  - Validation status:
    - regression coverage was added for LU-parallel parity on a controlled
      fixture plus benchmark-summary generation;
    - validation gates passed:
      - `pytest tests/test_tsr_recipes.py tests/test_cli_main.py -q`
      - `ruff check src/femic/tsr_catalog/recipes.py src/femic/tsr_catalog/__init__.py src/femic/cli/main.py tests/test_tsr_recipes.py tests/test_cli_main.py`
      - `mypy src`
      - `sphinx-build -b html docs _build/html -W`
  - First live benchmark signal:
    - benchmarked step `004` (`Roads and landings`) on the `Williams Lake` LU;
    - serial result:
      - runtime about `71.0 s`
      - removed area `1470.416 ha`
    - LU-parallel (`2` workers) result:
      - runtime about `75.2 s`
      - removed area `1388.719 ha`
      - parity failed relative to serial
    - current interpretation:
    - the prototype is real and benchmarkable;
    - the current partial-LU path is not yet adoption-worthy; and
    - the parity drift likely reflects the difference between exact LU
      clipping in the parallel path and the current non-clipped serial LU
      subset reference, so any further benchmark claims need to use a cleaner
      reference contract (ideally full-TSA/all-LU).
- 2026-04-06 (Issue `#143` next slice: grouped-LU chunking plus notebook
  progress UX for full-TSA step-6 testing):
  - Immediate motivation:
    - one-LU-per-chunk granularity is not obviously delivering enough speedup;
    - the live 4-LU tests show the `lu_parallel` path itself is internally
      stable across `1`, `2`, and `4` workers; and
    - the next meaningful experiment is full-TSA step `006`
      (`Parks, protected areas, area-base tenures`) with `8` grouped LU bundles
      and visible progress reporting in the notebook.
  - Planned implementation:
    - add a grouped-LU bundle mode on top of the current LU-clipped chunk
      preparation so the runner can partition the active LU set into a smaller
      number of worker bundles (for example `8`) instead of one worker task per
      LU;
    - keep the chunk contract exact by grouping already-clipped LU slices,
      rather than reverting to centroid or map-sheet heuristics;
    - add optional progress reporting backed by per-worker progress files so the
      parent process and generated notebook can render one progress bar per
      worker bundle;
    - regenerate the TSA29 THLB workbench notebook so step `006` can be launched
      from the notebook using the grouped-LU `8`-worker path.
  - Guardrails:
    - do not claim parity or performance success until the full-TSA grouped
      benchmark is compared against the matching grouped/clipped serial
      reference;
    - keep the notebook progress UX optional and degrade cleanly to plain-text
      notes if widget support is unavailable.
- 2026-04-06 (Issue `#143` follow-up: step-6 tenure semantics note plus
  profiling-first optimization pass):
  - Tenure follow-up to preserve:
    - step `006` still lacks validated automation logic for the "small
      area-based tenures and woodlots" portion even though fetched public
      tenure-adjacent layers are already on disk;
    - likely next seam is to mine BC Data Catalogue metadata/dictionaries for:
      - `TA_CROWN_TENURES_SVW`;
      - `WHSE_TANTALIS.TA_CROWN_TENURES_SVW`; and
      - `WHSE_FOREST_TENURE.FTEN_MANAGED_LICENCE*_SVW`
      to find defensible field/value logic for the missing tenure classes; and
    - keep the current step-6 parks/protected-areas automation separate from
      that still-unresolved tenure sublogic.
  - Immediate profiling mission:
    - collect structured timing for the grouped-LU full-TSA step-6 path so we
      can separate:
      - LU-partition materialization/cache time;
      - worker feather/shard load time;
      - worker GIS execution time;
      - worker output-write time; and
      - parent-process merge/readback time;
    - use that profile to decide whether the next optimization should be:
      - preloading/caching larger LU bundles once before step 6;
      - reducing repeated shard reads by caching bundle-ready datasets; or
      - keeping the notebook kernel hot with preloaded data if file I/O turns
        out to dominate runtime.

- 2026-04-06 (Issue `#140` checkpoint landed: DWDS follow-up/materialization
  no longer stops at submission):
  - Added a manifest-driven follow-up lane in `src/femic/bcdc_dwds.py`:
    - reload existing DWDS order manifests;
    - retry the public order-status seam later; and
    - materialize the artifact into a download root when DWDS exposes a
      download URL.
  - Added CLI command:
    - `python -m femic data bcdc-order-followup ORDER_MANIFEST`
    - default behavior updates the saved manifest in place with:
      - `latest_followup_utc`;
      - `latest_followup_status_probe`;
      - `materialized_artifact_path` / bytes / content type when available; and
      - explicit follow-up warnings when the public seam still withholds a
        download URL.
  - Live TSA29 PSP follow-up result:
    - the original DWDS submission (`order_id=2551251`) is now re-probeable
      from FEMIC instead of being a dead-end manifest;
    - the public `/order/{id}` seam still returns the known false negative; and
    - FEMIC now records that state honestly in the manifest instead of stopping
      at raw submission metadata.
- 2026-04-06 (Issue `#140` email fallback added for live DWDS orders):
  - `femic data bcdc-order` now resolves the DWDS notification email in this
    order:
    - explicit `--email`;
    - `FEMIC_BCDC_DWDS_EMAIL`; then
    - `git config user.email`.
  - If none of those sources are available, FEMIC now fails early with a clear
    instruction instead of silently submitting a no-email order.
  - Live validation:
    - submitted a fresh PSP order for the TSA29 `Williams Lake` LU without
      `--email`;
    - FEMIC picked up the local git email and the order summary now reports
      `email: 0@01101.io`;
    - new order manifest:
      `runtime/logs/bcdc_psp_status_active_williams_lake_order_manifest_with_email.json`.
- 2026-04-06 (Issue `#142` closed: ArcGIS Pro THLB benchmark completed and not
  adopted):
  - The ArcGIS Pro subprocess side-quest was benchmarked head-to-head against
    the canonical GeoPandas/Shapely lane on the `Williams Lake` LU subset.
  - Results on this workstation:
    - step `003` (`Non-forest`):
      - GeoPandas about `18.4 s`;
      - ArcGIS about `145.5 s`;
      - output parity close enough to count as parity.
    - step `004` (`Roads and landings`):
      - GeoPandas about `70.0 s`;
      - ArcGIS about `190.4 s`;
      - ArcGIS still landed in `applied_with_unsupported` because one
        road-buffer substep failed.
    - steps `018` (`Riparian areas`) and `019` (`Buffered trails`):
      - GeoPandas completed in about `22.6 s` and `24.0 s`;
      - ArcGIS did not complete either step within an eight-minute timeout and
        had to be terminated manually.
  - Decision:
    - keep GeoPandas/Shapely as the canonical THLB GIS execution engine;
    - do not merge the ArcGIS experimental backend into the main THLB branch;
    - treat `#142` as answered `not worth extending` for now and return focus
      to `#141`.
- 2026-04-06 (Issue `#140` pickup-by-GUID retrieval seam discovered and wired
  into FEMIC follow-up):
  - Live TSA29 PSP order `2551234` proved the stronger public retrieval path:
    - DWDS sent an email saying the order was assembled;
    - the emailed `pickupByGUID` URL was an HTML launcher page, not the final
      package; and
    - that launcher page exposed the real
      `distribution.data.gov.bc.ca/...zip` URL for the assembled artifact.
  - FEMIC now mirrors that path in `follow_up_bcdc_dwds_order(...)`:
    - retry `/order/{id}` first;
    - if no download URL is exposed and `order_guid` exists, fetch the
      `pickupByGUID` launcher page;
    - parse the launcher HTML for the final distribution zip URL; then
    - download/materialize the artifact and record both URLs in the manifest.
  - User/agent-facing documentation must now treat DWDS notification email as
    part of the usable public-order workflow, not just as an optional courtesy,
    because the email-driven launcher may be the only discoverable route to the
    final package when `/order/{id}` is still unreliable.

- 2026-04-06 (Issue `#139` opened: split TSA29 step `015` area netdown from
  TSR Section `7.1.5` later yield-assumption logic):
  - The active TSA29 interpretation is now explicit:
    - `6.4.5 Non-merchantable timber profiles` stays in the THLB area-netdown
      lane only for the rule:
      - exclude **broadleaf-leading stands** from THLB;
    - `7.1.5 Volume exclusions for broadleaf species in coniferous stands`
      does **not** stay in the THLB area-netdown lane;
      it becomes a separate later-stage yield/volume assumption after AU
      compilation and VDYP/TIPSY/yield preparation.
  - Immediate follow-through:
    - keep TSA29 step `015` in the notebook/workbench ratchet flow as the
      broadleaf-leading-stand THLB exclusion only;
    - do not fold mixed conifer-stand deciduous-volume handling back into the
      THLB area-netdown recipe;
    - implement the `7.1.5` volume-exclusion logic under GitHub issue `#139`
      once the remaining THLB area-netdown steps are sorted out.

- 2026-04-03 (Issue `#83` reconciled and ready to close: Windows Codex local-link recovery docs were already landed):
  - GitHub issue `#83` no longer reflects missing implementation work; the
    requested Windows VS Code/Codex recovery guidance is already present in the
    current repo surfaces:
    - `AGENTS.md`
    - `README.md`
    - `docs/guides/vscode-coding-agent-onboarding.rst`
    - `docs/guides/case-onboarding.rst`
    - `docs/guides/deployment-instances.rst`
  - The shipped guidance already covers:
    - the maintained `codex-local-file-link-patch` repo;
    - the Windows-only scope of the workaround;
    - the PowerShell patch command; and
    - the post-patch `Developer: Reload Window` step.
  - Immediate follow-through:
    - post a closeout comment on GitHub issue `#83` pointing to the existing
      docs and close the issue as tracker reconciliation rather than new code
      or docs work.

- 2026-04-03 (Issue `#11` implemented: Windows `validate-case` now diagnoses
  canonical TSA FileGDB materialization before blaming GDAL):
  - What shipped:
    - extended the existing Windows annex/runtime seam inside
      `femic prep validate-case` instead of adding a new CLI command;
    - added a lightweight canonical TSA FileGDB layer probe against
      `external/femic-public-data/data/bc/tsa/FADM_TSA.gdb`;
    - the new helper now distinguishes:
      - missing geospatial backends (`pyogrio` / `fiona`);
      - missing or empty canonical FileGDB payloads;
      - pointer-like annex worktree exposure inside the FileGDB; and
      - generic read failures that still need the annex/materialization
        recovery sequence ruled out first;
    - the emitted Windows error path now points operators to the exact
      low-noise recovery sequence:
      - `git -C external/femic-public-data annex enableremote arbutus-s3`
      - `datalad get -r external/femic-public-data/data`
      - `git -C external/femic-public-data annex unlock data/bc/tsa/FADM_TSA.gdb`
      - rerun `femic prep validate-case`
    - `femic prep geospatial-preflight` stayed generic, while the Windows
      geospatial/runtime docs now explicitly explain that `validate-case` is
      the case-aware canonical TSA/FileGDB readability check and that ArcGIS
      Pro / `arcpy` is only a fallback recovery leg.
  - Validation:
    - focused CLI/runtime tests passed for the new Windows annex/FileGDB seam;
    - full docs-contract coverage passed after updating the Windows guides;
    - full repo validation passed:
      - `python -m ruff format src tests`
      - `python -m ruff check src tests`
      - `python -m mypy src`
      - `python -m pytest -q`
      - `python -m sphinx -b html docs _build/html -W`
      - `python -m pre_commit run --all-files`
  - Immediate follow-through:
    - post the implementation/validation closeout to GitHub issue `#11`;
    - close `#11` if no new Windows FileGDB scope is added in review.

- 2026-04-03 (Issue `#11` kickoff: diagnose canonical Windows TSA FileGDB
  materialization before users chase fake GDAL ghosts):
  - Governing issue:
    - GitHub issue `#11`
  - Planned branch:
    - `feature/issue-11-windows-filegdb-materialization`
  - Root-cause read for this pass:
    - the misleading Windows `FADM_TSA.gdb` failures are not automatically
      proof that GDAL/FileGDB support is broken on Windows;
    - on the known workstation, the more common seam is annex-backed
      `external/femic-public-data` worktree materialization, where the
      canonical TSA geodatabase can still present pointer-like/unusable content
      until the public-data checkout is properly materialized and unlocked;
    - `femic prep geospatial-preflight` should remain the generic
      package/runtime smoke, while `femic prep validate-case` should become the
      low-noise place to detect the active-case canonical TSA FileGDB seam.
  - Active implementation target:
    - extend the existing Windows annex/runtime helper inside
      `femic prep validate-case` rather than adding a new CLI command;
    - probe the canonical TSA boundary geodatabase with a lightweight layer-list
      read and distinguish:
      - missing geospatial libraries;
      - missing/unmaterialized annex payload;
      - pointer-like/unusable worktree exposure; and
      - genuine FileGDB read failure;
    - fail with the exact recommended recovery sequence:
      - `git -C external/femic-public-data annex enableremote arbutus-s3`
      - `datalad get -r external/femic-public-data/data`
      - `git -C external/femic-public-data annex unlock data/bc/tsa/FADM_TSA.gdb`
      - rerun `femic prep validate-case`
    - keep ArcGIS Pro / `arcpy` as documentation-only fallback guidance.
  - Validation target:
    - add focused regression tests for the new Windows FileGDB materialization
      seam inside `validate-case`;
    - update the Windows/bootstrap docs to distinguish
      `geospatial-preflight` from active-case FileGDB readability;
    - run the full lint/type/test/docs/pre-commit sweep once the narrow helper
      and docs are in place.

- 2026-04-03 (Issue `#80` validated and closeout-ready):
  - Delivered exactly the narrow layout split planned at kickoff:
    - durable VDYP runtime assets stay at `vdyp_io/VDYP.INI` and
      `vdyp_io/VDYP_CFG/**`;
    - disposable per-batch raw spill now lands under `vdyp_io/scratch/`;
    - VDYP-specific event/stdout evidence stays under `vdyp_io/logs/`.
  - Closeout evidence:
    - focused runtime-layout regressions passed;
    - full lint/type/test/docs/pre-commit gates passed;
    - direct TSA29 inspection now shows a clean `vdyp_io/` root with the old
      raw spill relocated into `vdyp_io/scratch/`.
  - Immediate follow-through:
    - checkpoint the branch commits and submodule pointers;
    - post the implementation/validation closeout on GitHub issue `#80` and
      close it if no further scope is added.

- 2026-04-03 (Issue `#80` active implementation: move raw VDYP batch spill,
  not the durable runtime contract):
  - Immediate execution order:
    - update the roadmap/changelog first and keep `#80` as the governing issue;
    - refactor the VDYP batch temp-file creation path so raw `.csv/.out/.err`
      spill lands in a dedicated scratch directory instead of the top-level
      `vdyp_io/` root;
    - leave `vdyp_io/VDYP.INI`, `vdyp_io/VDYP_CFG/**`, and the existing
      evidence-bearing log surfaces intact in this pass;
    - update instance bootstrap, tests, and docs/contracts to describe the new
      durable-runtime-versus-disposable-scratch boundary;
    - directly inspect the live TSA29 `vdyp_io/` tree after the code change so
      the fix is verified on a real representative instance rather than only in
      unit tests.

- 2026-04-03 (Issue `#81` rescue-guard fix validated):
  - Narrow scope delivered exactly as planned:
    - late `fit_quality_gate` rescue now considers only candidates that earlier
      policy stages actually accepted/selected;
    - raw rejected `tail_blend` no longer re-enters rescue comparison just
      because it clears `early_overshoot_exceeds_gate`.
  - Validation outcome for this pass:
    - focused regression coverage now locks the failure seam where
      `tail_blend_selection` rejects a worse tail curve and the final selected
      path must stay off `tail_blend`;
    - accepted-candidate rescue remains covered by the existing
      `merchantable_floor` rescue regression;
    - replaying the saved clean-clone TSA29 evidence through the live repo code
      now keeps both `ICH_SX / M` and `ICH_SX / H` on `primary_nlls` with
      `selected_curve_gate_unresolved` instead of rescuing to `tail_blend`.
  - Immediate follow-through:
    - run the full lint/type/test/docs gates;
    - post the validation closeout to GitHub issue `#81` and close it if the
      full repo gates stay green.

- 2026-04-03 (Issue `#81` active implementation: rescue guard, not broad tail retune):
  - Root-cause read for this pass:
    - the known TSA29 `ICH_SX / M` and `ICH_SX / H` mis-selections are not
      being caused by the earlier `tail_blend_selection` step;
    - in the saved clean-clone evidence, `tail_blend_selection` already rejects
      the raw `tail_blend` candidate for both cases, but the later
      `fit_quality_gate` rescue still revives raw `tail_blend` because it
      clears `early_overshoot_exceeds_gate`.
  - Active implementation target:
    - keep the issue narrow to the late rescue-candidate set;
    - allow gate rescue to consider only candidates that earlier policy stages
      actually accepted/selected;
    - do not broaden this pass into a general retune of tail-detection,
      tail-blend thresholds, or fit-quality gate constants.
  - Validation target for this pass:
    - add focused regression coverage for "rejected tail_blend must not be
      revived by gate rescue";
    - preserve at least one accepted-candidate gate-rescue path;
    - replay the saved TSA29 `ICH_SX / M` and `ICH_SX / H` evidence through the
      live repo code and confirm the final selected path no longer ends at
      `tail_blend`.

- 2026-04-03 (Issue `#82` closeout; issue `#81` is the next active VDYP follow-on):
  - Issue `#82` is now closeout-complete:
    - the polygon/layer batch writer was repaired so VDYP input CSVs now keep
      only the shared `FEATURE_ID` set and preserve stable within-feature layer
      ordering;
    - saved-batch replay confirmed the old bad TSA29 `ESSF_SE / H` sample no
      longer collapses to a one-table parse after the alignment fix;
    - narrow bucket rerun confirmed `ESSF_SE / H` now rebuilds as a plausible
      full smoothed curve instead of the broken near-two-point fallback.
  - Next active issue is `#81`:
    - focus now shifts from the batch-alignment seam to the fit-selection
      policy seam;
    - the intended next pass is to tighten rescue selection so
      `tail_blend` cannot replace a materially better primary/current fit just
      to satisfy the early-overshoot gate.

- 2026-04-03 (Issue `#82` active implementation: VDYP polygon/layer batch alignment):
  - Root-cause read for this pass:
    - the broken TSA29 `ESSF_SE / H` curve is currently traced to the sampled
      VDYP input-writer seam, not to stratum sizing;
    - the saved bad batch had `100` polygon rows but only `95` unique matching
      layer `FEATURE_ID`s, and the first polygon row had no corresponding layer
      row before VDYP consumed the batch.
  - Active implementation target:
    - repair `write_vdyp_infiles_plylyr(...)` so FEMIC only writes
      feature-aligned polygon/layer batches to VDYP;
    - preserve deterministic per-feature ordering for multi-layer rows instead
      of relying on an unstable generic sort;
    - add focused regression coverage for missing-layer and duplicated-layer
      cases so the sampled TSA29 failure shape stays reproducible in tests.
  - Validation target for this pass:
    - rerun the relevant narrow TSA29 Stage 01a bucket after the writer fix;
    - confirm `ESSF_SE / H` no longer degenerates into the broken near-two-point
      fallback curve and that AU `23009` regains a plausible VDYP overlay.

- 2026-04-03 (Issue `#79` follow-on VDYP bug split after plot QA):
  - The BTC/null-volume seam targeted by issue `#79` is now fixed and the
    Windows annex-raster blocker from the same clean-clone rerun is also
    resolved, but direct review of the regenerated TSA29 VDYP QA plots exposed
    two separate follow-on VDYP defects that should be handled outside issue
    `#79`:
    - issue `#82`: sampled VDYP polygon/layer temp files can become misaligned
      when polygons without matching layer rows are written into the same batch,
      collapsing healthy strata such as `ESSF_SE / H`;
    - issue `#81`: the fit-quality rescue policy can replace a materially better
      primary/current fit with a much worse `tail_blend` curve just to satisfy
      the early-overshoot gate (for example `ICH_SX / M` and `ICH_SX / H`).
  - Current closeout read on issue `#79`:
    - the original BTC acceptance criteria are satisfied;
    - the newly split VDYP bugs are real and worth fixing, but they do not
      reopen the repaired BTC natural-ingress contract itself;
    - issue `#79` should be treated as closeout-ready once its final closeout
      note explicitly links the two follow-on VDYP bug tickets.

- 2026-04-03 (Windows annex-pointer raster follow-up after issue `#79` validation):
  - The clean-clone TSA29 rerun exposed a narrower Windows-only public-data seam
    beyond the earlier missing-path fallback work:
    - `datalad get` / `git annex get` can still leave annexed raster worktree
      paths as tiny pointer stub files on native Windows submodule checkouts;
    - direct `rasterio.open(...)` against those worktree paths fails even when
      the real annex payload exists in the object store.
  - The intended fix for this pass is intentionally narrow:
    - add a Windows-only resolver for annex pointer-style raster paths;
    - use it only at the direct raster-open seams (`misc.thlb.tif`,
      canonical `siteprod.tif`);
    - leave Linux behavior unchanged and avoid broad new environment policy.
  - Completion evidence:
    - added a Windows-only annex-pointer resolver that maps tiny worktree stub
      files to the real annex payload under the submodule gitdir before direct
      raster opens;
    - wired that resolver into the THLB and SiteProd raster-open seams only;
    - confirmed the earlier failing clean-clone command now passes the old THLB
      blocker and completes:
      `femic run --instance-root external/femic-tsa29-instance --run-config config/run_profile.tsa29.yaml --run-id tsa29_issue79_windows_annexfix_20260403b`
      from `F:\projects\tmp\femic-issue10-closeout-20260402-clean`.

- 2026-04-03 (Issue `#79` implementation + fresh BTC/post-TIPSY validation):
  - Share audit result:
    - the problematic TSA29 `planted_percent < 100` rows were **not** caused by
      random arithmetic drift;
    - fresh `03_input-tsa29.csv` values such as `30`, `85`, and `90` trace
      directly to explicit `config/tipsy/tsa29.yaml` `Proportion` assignments,
      so the mixed-share behavior is currently treated as deliberate TSA29
      compile logic.
  - BTC seam fix now in place:
    - `build_btc_msyt_input_table()` now pairs the planted-side `f` payload with
      the matching natural-side `e` payload when emitting BTC `MSYT.csv`;
    - rows with `planted_percent < 100` now receive explicit
      `natural_species*` / `natural_density*` fields;
    - FEMIC now fails fast before BTC if a mixed-share row lacks a usable
      natural-ingress payload.
  - Fresh validation evidence from rerun `tsa29_issue79_20260403a` in
    `F:\projects\tmp\femic-issue10-closeout-20260402-clean`:
    - regenerated `03_input-tsa29.csv` now shows the old problem rows carrying
      real natural-ingress payload (for example `21000` / `22000` now include
      `natural_species1=Pl`, `natural_density1=871`, `natural_species2=At`,
      `natural_density2=100`);
    - fresh unattended BTC plus `femic tsa btc-post-tipsy` completed
      successfully against that regenerated handoff;
    - fresh `04_error-tsa29.csv` is now header-only;
    - fresh `04_output-tsa29.csv` now has `54/54` rows with positive
      non-null `gVol_*` output and `0` all-null rows.
  - Remaining validation caveat:
    - the full clean-clone `femic run` command still hit an unrelated THLB
      fallback-raster open failure in
      `F:\projects\femic\external\femic-public-data\data\misc.thlb.tif` after
      Stage 01a had already regenerated the canonical BTC handoff;
    - that raster-format issue did **not** block the issue-79 seam proof
      because the fresh Stage 01a outputs plus `femic tsa btc-post-tipsy`
      rerun were sufficient to validate the repaired BTC contract end to end.

- 2026-04-03 (Issue `#79` active implementation: mixed-share TSA29 BTC contract):
  - Root-cause audit now points at the BTC handoff seam rather than stale
    provenance or random arithmetic drift:
    - the fresh failing BTC rows in clean-clone `03_input-tsa29.csv` carry
      `planted_percent` values such as `30`, `85`, and `90`;
    - those values match explicit TSA29 rule `Proportion` settings already
      encoded in `config/tipsy/tsa29.yaml` (`0.30`, `0.85`, `0.90`) rather than
      an apparent downstream accounting error;
    - the current issue-79 working assumption is therefore that mixed-share
      planted input is deliberate TSA29 compile logic, but FEMIC exports it
      incompletely for BTC.
  - Active implementation target:
    - preserve the intended mixed-share TSA29 behavior;
    - repair the BTC export so any row with `planted_percent < 100` also carries
      explicit natural-ingress species/density payload;
    - fail fast before BTC if FEMIC is about to emit a mixed-share row without
      usable natural-ingress fields.
  - Validation target for this pass:
    - regenerate fresh `03_input-tsa29.csv`;
    - rerun the clean TSA29 BTC/post-TIPSY chain;
    - prove the 21 previously failing feature IDs no longer hit fresh
      `Natural has no Species` errors, or else document a narrower remaining
      contract gap explicitly before any further TSA29 prototype claims.

- 2026-04-03 (Issue #10 fresh-clone closeout achieved; follow-on moves to `#79`):
  - Fresh validation closeout completed from:
    - source workspace: `F:\projects\femic`
    - clean validation clone:
      `F:\projects\tmp\femic-issue10-closeout-20260402-clean`
    - shared public-data mirror:
      `F:\projects\femic\external\femic-public-data\data`
  - Clean-clone bootstrap and validation notes:
    - rebuilt the moved clean-clone `.venv` from scratch instead of trusting the
      migrated virtual environment;
    - restored only the minimal TSA29-local prerequisites needed for the clean
      rerun (`tipsy_params_columns`, `tsa_boundaries.feather`,
      `ria_vri_vclr1p_checkpoint1..8.feather`);
    - removed stale downstream TSA29 runtime products before rerun so the final
      evidence chain stayed single-lineage and auditable;
    - found a real packaging gap during the clean rerun and added `openpyxl` to
      `pyproject.toml` and `requirements.txt` because Stage 01a and tests write
      `tipsy_params_tsa29.xlsx`.
  - Fresh closeout run `tsa29_issue10_closeout_20260402f` now proves:
    - `femic prep validate-case --instance-root external/femic-tsa29-instance --run-config config/run_profile.tsa29.yaml`
      passed in the clean clone;
    - `femic prep geospatial-preflight` passed in the clean clone;
    - `femic run` emitted fresh `03_input-tsa29.csv` and Stage 01a/01b runtime
      artifacts;
    - unattended BTC completed with `exit_code=0` and wrote fresh
      `04_output-tsa29.csv` / `04_error-tsa29.csv`;
    - `femic tsa btc-post-tipsy` completed with fresh
      `tipsy_curves_tsa29.csv`, `tipsy_sppcomp_tsa29.csv`,
      `data/model_input_bundle/*`, and fresh `plots/tipsy_vdyp_tsa29-*.png`;
    - `femic export patchworks`, `femic patchworks build-blocks --with-topology --topology-backend patchworks-raster`,
      and `femic patchworks matrix-build --run-id tsa29_issue10_closeout_20260402f`
      all completed successfully in the clean clone;
    - the regenerated topology file
      `models/tsa29_patchworks_model/blocks/topology_blocks_200r.csv` is now
      non-empty (`29,954,243` bytes; `1,266,753` topology edges);
    - the fresh Matrix Builder manifest records `returncode=0`,
      `failures=[]`, inherited
      `SPS_LICENSE_SERVER=frst424@auth.spatial.ca`, and the output-local
      validated XML path beside the matching fragments set.
  - Fresh-provenance null-volume resolution:
    - the apparent TSA29 null/no-volume pattern is **not** stale artifact
      confusion;
    - fresh `04_output-tsa29.csv` contains `54` rows total, with `33` rows
      showing positive `gVol_*` output;
    - the remaining `21` all-null `gVol_*` rows line up exactly with fresh
      `04_error-tsa29.csv` rows reporting `Natural has no Species`;
    - there were no additional all-null volume rows outside that fresh BTC
      error set.
  - Closeout consequence:
    - issue `#10` can close as a rebuild-contract, provenance, and evidence
      closeout;
    - the remaining TSA29 v0 behavior investigation moves to follow-on issue
      `#79` (`TSA29 v0: investigate fresh BTC null-volume rows with "Natural has no Species" errors`).
  - Immediate next task:
    - use issue `#79` as the active surface for root-causing the fresh
      `Natural has no Species` subset and repairing the affected TSA29 BTC
      inputs without reopening issue `#10`.
  - Windows public-data hygiene follow-up:
    - local testing in `external/femic-public-data` showed Windows false-dirty
      churn was being amplified by `core.autocrlf=true` against annex-managed
      GIS payloads;
    - committed `external/femic-public-data` submodule fix `155711f`
      (`Harden binary GIS attributes for Windows clones`) to mark FileGDB
      payloads plus raster/feather/GPKG artifacts as binary (`-text`) in
      `.gitattributes`;
    - parent merge work should advance the public-data submodule pointer to
      `155711f` together with the existing TSA29 pointer update, but must still
      keep the large TSA29 runtime spill out of the intentional Git payload.
  - TSA29 merge-hygiene follow-up:
    - committed `external/femic-tsa29-instance` submodule fix `1b9a3cb`
      (`Ignore transient VDYP raw output spill`) to ignore the largest
      throwaway `vdyp_io` raw-output families
      (`vdyp_err_*.err`, `vdyp_lyr_*.csv`, `vdyp_out_*.out`,
      `vdyp_ply_*.csv`);
    - that change cut the TSA29 Git-visible worktree noise from roughly
      `7,886` files to `179` files without hiding the JSON evidence manifests;
    - remaining TSA29 dirt is now concentrated in still-meaningful runtime
      artifacts (`data/*`, `plots/*`, fragments, manifests, and local
      `VDYP_CFG` / `VDYP.INI`) rather than the transient raw spill.
    - follow-on issue `#80` now tracks redesigning the `vdyp_io` layout so the
      essential local runtime assets (`VDYP_CFG`, `VDYP.INI`) no longer live in
      the same directory as thousands of transient raw VDYP spill files that
      need periodic cleanup on Windows.
  - Non-VDYP runtime-log split:
    - redirected non-VDYP run/manifests/rebuild-report defaults from
      `vdyp_io/logs` to `runtime/logs` in the parent CLI/workflow defaults and
      in the TSA29/K3Z instance configs/docs;
    - moved the current TSA29 non-VDYP runtime artifacts (BTC manifests/logs,
      post-TIPSY run manifests, Patchworks matrix-builder manifests/logs) out
      of `vdyp_io/logs` into `runtime/logs`;
    - left true VDYP event/stdout logging under `vdyp_io/logs`, keeping
      `VDYP.INI` / `VDYP_CFG` untouched as essential runtime assets.

- 2026-04-02 (Issue #10 BTC-first TSA29 migration checkpoint):
  - Completed in this branch:
    - added repo-local planning note `planning/tsa29_p19_5_btc_reentry.md`;
    - updated the Phase 19 `P19.5` wording so issue `#10` now tracks the
      BTC-first rebuild/evidence closeout explicitly;
    - migrated the linked TSA29 instance docs/runbook/spec/runtime wiring so
      the active contract is now `03_input-tsa29.csv` -> unattended BTC ->
      `04_output-tsa29.csv` / `04_error-tsa29.csv` ->
      `femic tsa btc-post-tipsy`;
    - repaired the stale TSA29 Patchworks runtime config so it no longer points
      at K3Z model paths;
    - added the smallest necessary parent blocker fix so `femic instance rebuild`
      can honor a TSA29 spec that declares `btc_post_tipsy_bundle` instead of
      silently forcing the old legacy `post_tipsy_bundle` step;
    - refreshed docs/CLI contract tests to match current FMU-first wording and
      current checked-in K3Z artifact reality on `origin/main`.
  - Validation completed:
    - `python -m pytest tests/test_cli_main.py -k "instance_rebuild"`
    - `python -m pytest tests/test_docs_contract.py -k "tsa29"`
    - `python -m sphinx -b html docs _build/html -W`
    - `python -m sphinx -b html external/femic-tsa29-instance/docs external/femic-tsa29-instance/docs/_build/html -W`
    - `ruff format src tests`
    - `ruff check src tests`
    - `mypy src`
    - `pytest`
    - `pre-commit run --all-files`
  - Immediate next execution order:
    - checkpoint only the permanent contract/runtime/doc fixes, keeping large
      TSA29 runtime spill out of the intentional Git payload;
    - prove fresh-seam provenance explicitly for one final closeout run:
      `03_input-tsa29.csv` -> fresh BTC `04_output-tsa29.csv` /
      `04_error-tsa29.csv` -> fresh post-TIPSY curves/bundle/plots;
    - treat blank/null BTC output as a blocker, and treat any remaining
      fresh-provenance no-volume plot pattern as a follow-on TSA29 v0 issue
      rather than widening `#10` into a full behavior investigation;
    - run the final acceptance/evidence pass from a fresh/current FEMIC
      checkout using the approved Windows Patchworks contract:
      inherited `SPS_LICENSE_SERVER`, output-local validated XML/fragments,
      `patchworks-raster` topology backend, and successful Matrix Builder
      completion with `returncode=0`.

- 2026-04-02 (Issue #10 Patchworks + provenance checkpoint):
  - Current synced-workspace evidence now proves:
    - TSA29 Patchworks Matrix Builder succeeds when FEMIC inherits the real
      Windows `SPS_LICENSE_SERVER` value instead of overriding it with the old
      placeholder runtime config value;
    - TSA29 Matrix Builder must point at
      `output/patchworks_tsa29_validated/forestmodel.xml` beside the matching
      validated fragments, not at stale model-local
      `models/tsa29_patchworks_model/yield/forestmodel.xml`;
    - the reviewed `plots/tipsy_vdyp_tsa29-*.png` family in this forensic
      workspace was regenerated immediately after the fresh
      `tsa29_btc_boundary_smoke_20260402b` BTC-first run chain, not from the
      old historical DAT/out seam.
  - Verified current-workspace provenance chain:
    - `data/03_input-tsa29.csv` mtime `2026-04-02 01:34:59`
    - `data/04_output-tsa29.csv` / `data/04_error-tsa29.csv` mtimes
      `2026-04-02 01:37:17`
    - `data/tipsy_curves_tsa29.csv` mtime `2026-04-02 01:37:27`
    - `plots/tipsy_vdyp_tsa29-*.png` mtimes `2026-04-02 01:37:27` through
      `2026-04-02 01:37:34`
    - BTC manifest `tsa29_btc_boundary_smoke_20260402b_tsa29` records
      `TIPSYbtc.exe /TSR` consuming fresh `03_input-tsa29.csv` and returning
      fresh `04_output-tsa29.csv` / `04_error-tsa29.csv`
    - post-TIPSY manifest `tsa29_btc_boundary_smoke_20260402b` records fresh
      `tipsy_curves_tsa29.csv`, `tipsy_sppcomp_tsa29.csv`, and rebuilt bundle
      tables from the same run lineage.
  - Remaining closeout move:
    - repeat this same proof from a fresh/current checkout and use that run as
      the final issue-`#10` closeout evidence.

- 2026-04-02 (Issue #10 F-drive re-ground + clean validation plan):
  - Live workspace sanity check now confirms:
    - source repo root: `F:\projects\femic`
    - fresh validation checkout:
      `F:\projects\tmp\femic-issue10-closeout-20260402-clean`
    - both repos are on `work/p19.5-tsa29-btc-reentry`
    - the intended shared public-data mirror for
      `FEMIC_EXTERNAL_DATA_ROOT` remains
      `F:\projects\femic\external\femic-public-data\data`
  - Immediate execution order from this point:
    - finish editable bootstrap in the fresh validation checkout so
      `python -m femic` resolves from its local `.venv`;
    - restore only the missing TSA29-local prerequisite files needed for the
      clean closeout chain from the source workspace into the fresh clone;
    - remove stale downstream TSA29 runtime products in the fresh clone before
      the rerun so provenance stays single-lineage and auditable;
    - rerun `validate-case`, `geospatial-preflight`, the BTC-first TSA29 chain,
      and the Patchworks closeout steps from the clean checkout;
    - inspect the rebuilt BTC/TIPSY manifests and outputs explicitly to decide
      whether the apparent null-volume pattern is fresh behavior or stale-mix
      confusion before touching issue `#10` closure state.

- 2026-04-02 (Issue #10 BTC-first TSA29 re-entry plan):
  - Governing issue:
    - GitHub issue `#10`
  - Branch:
    - `work/p19.5-tsa29-btc-reentry`
  - Re-entry decision:
    - retire the stale TSA29 closeout framing built around the old manual
      BatchTIPSY DAT/out seam;
    - treat the freshly synced parent `origin/main` BTC workflow as the
      authoritative contract;
    - use the preserved pre-sync TSA29 backup snapshot as the forensic source
      for selective carry-forward only, without relying on any stale `C:`
      checkout paths.
  - Approved execution sequence:
    - migrate the TSA29 instance docs/runbook/spec/runtime wiring so the active
      seam is:
      - `data/03_input-tsa29.csv`
      - unattended BTC
      - `data/04_output-tsa29.csv`
      - `data/04_error-tsa29.csv`
      - `femic tsa btc-post-tipsy --run-config config/run_profile.tsa29.yaml --tsa 29 --run-id <id>`
    - keep legacy `02_input-tsa29*.dat` / `04_output-tsa29.out` references as
      historical or compatibility context only;
    - make only the smallest necessary parent-code blocker fixes if the current
      `origin/main` rebuild runner cannot honor the BTC-first TSA29 contract;
    - after migration, run the final acceptance/evidence pass from a fresh
      current FEMIC checkout rather than from the old forensic workspace.
  - Immediate execution order:
    - patch `ROADMAP.md`, `CHANGE_LOG.md`, and
      `planning/tsa29_p19_5_btc_reentry.md` so the approved re-entry plan lives
      in-repo and matches the updated GitHub issue `#10`;
    - migrate the linked TSA29 instance surfaces:
      `README.md`, `docs/getting-started.rst`,
      `docs/rebuild-and-qa.rst`, `docs/data-and-provenance.rst`,
      `docs/troubleshooting.rst`, `runbooks/REBUILD_RUNBOOK.md`,
      `config/rebuild.spec.yaml`, and
      `config/patchworks.runtime.windows.yaml`;
    - validate the migrated contract with focused docs/spec checks plus a
      targeted BTC-boundary smoke before attempting the final clean rebuild
      closeout.

- 2026-03-30 (Issue #65 kickoff): start the narrow K3Z ctfert log-grade harvested product/account rollout on branch `feature/issue-65-k3z-ctfert-log-grades`.
  - Governing issue:
    - GitHub issue `#65`
  - Rollout scope:
    - only `ctfert_l15h5`
    - only `ctfert_l20h0`
    - CC harvested product/account family only
    - no CT log-grade surfaces yet
    - no broader rollout to baseline, `pct_*`, `intensive_*`, or generalized treated surfaces yet
  - Immediate execution order:
    - wire the existing BTC `log-grades` bank into the shared Patchworks exporter only as far as needed for the two ctfert variants;
    - request the bank explicitly from the two ctfert silviculture configs;
    - rebuild the affected validated ForestModel XMLs before rerunning Matrix Builder on the two ctfert variants;
    - inspect rebuilt `products.csv`, `protoaccounts.csv`, and `accounts.csv` directly to confirm all expected grade members are present as CC-only families;
    - finish with one representative Patchworks smoke that schedules harvest volume and shows the new saved runtime log-grade family in concrete outputs.
- 2026-03-30 (Issue #65 progress): the narrow ctfert log-grade rollout is working end to end.
  - Shared exporter support now emits `product.Logs_Grade_{D,F,H,I,J,U,X,Y,All}.managed.Total.CC` only for the two active ctfert variants, and the adapter layer now loads `Logs_Grade_*` curves from the K3Z BTC export.
  - The two ctfert silviculture configs now request the existing BTC `log-grades` bank, `data/tipsy_curves_tsak3z.csv` now carries the `Logs_Grade_*` columns, and the rebuilt `tracks_ctfert_l15h5/` and `tracks_ctfert_l20h0/` products/protoaccounts/accounts surfaces now contain the full nine-member CC-only family.
  - The initial ctfert runtime smoke failure was traced to missing `headless_runtime_common.bsh` hooks in `analysis/ctfert_l15h5.pin` and `analysis/ctfert_l20h0.pin`; after restoring that shared headless contract, `femic patchworks run-headless ...ctfert_l15h5.pin --scenario-mode max-even-flow-smoke --run-id issue65_ctfert_loggrades_runtime_rerun` completed successfully.
  - Representative live runtime proof now exists at:
    - `external/femic-k3z-instance/vdyp_io/logs/headless_stage/issue65_ctfert_loggrades_runtime_rerun/targets/product_Logs_Grade_H_managed_Total_CC.csv`
    - `external/femic-k3z-instance/vdyp_io/logs/headless_stage/issue65_ctfert_loggrades_runtime_rerun/targets/product_Logs_Grade_D_managed_Total_CC.csv`
    proving that materially populated and zero-only CC log-grade surfaces are both saved at runtime and that no matching `...CT` log-grade products were introduced in this slice.
- 2026-03-31 (Issue #65 semantics correction): reopen the ctfert log-grade rollout on the same feature branch to repair the bank contract before final closeout.
  - Current interpretation issue:
    - raw BTC inspection shows `Logs_Grade_D/F/H/I/J/U/X/Y` behave like a partition of merchantable `Yield`, while `Logs_Grade_All` is a distinct scaled-log quantity that can exceed `Yield`;
    - carrying `Logs_Grade_All` as a peer product account in the additive K3Z harvested family is therefore misleading.
  - Immediate correction order:
    - add a generic bank compile-recipe seam in FEMIC, starting with a recipe-backed `log-grades` bank;
    - make the default log-grade recipe exclude `Logs_Grade_All`, but support an explicit `include_all_grades` opt-in when a model really wants it;
    - add user-tweakable per-grade ratio weights and normalize them inside FEMIC so users can shift grade shares without changing net harvested volume;
    - add treatment-specific ratio overrides so K3Z CT can deliberately favor `J/U/X/Y` material in line with early-age thinning from below and the BC coast grading manual's small-radius/utility/chipper grades;
    - keep the shipped reference recipe inside FEMIC and merge an optional user overlay from `~/.femic/recipe-overlays`;
    - apply the same harvested-volume utilization multiplier to the emitted log-grade harvested product accounts so the grade family sums to effective harvested volume rather than raw merchantable yield;
    - push the repaired recipe through the broader affected K3Z family, not just the two ctfert variants, so natural-origin harvest surfaces participate too;
    - finish with a harvest-producing headless smoke that confirms saved runtime grade-family totals line up with harvested-volume totals in concrete output files.
- 2026-03-31 (Issue #65 semantics correction closeout): the repaired compile-recipe
  contract is now in place and validated end to end.
  - The shipped reference recipe now excludes `Logs_Grade_All` by default, keeps
    an explicit opt-in path for that separate scaled-log metric, exposes
    user-tweakable ratio weights plus user overlay support, and normalizes the
    explicit grade family so it sums to `product.HarvestedVolume.*` instead of
    raw BTC merchantable yield.
  - K3Z runtime semantics are now deliberately split by treatment:
    - `CC` continues to follow the normalized BTC-derived grade mix;
    - `CT` now uses recipe-backed ratio overrides to bias harvested material
      toward `J/U/X/Y` small-log and utility/chipper classes in line with the
      BC coast grading manual and the teaching-instance "thinning from below"
      rationale.
  - The rebuilt broader K3Z family now carries the repaired contract through
    both managed and natural-origin harvest surfaces, and the representative
    ctfert runtime proof at
    `external/femic-k3z-instance/vdyp_io/logs/headless_stage/issue65_loggrade_ctfert_runtime_ctoverride`
    confirms:
    - some harvest occurs;
    - explicit `CT` and `CC` grade files are saved at runtime;
    - grade-family totals track harvested-volume totals within small rounding
      noise; and
    - `CT` output now shows a clearly lower-grade mix concentrated in
      `J/U/X/Y`.
  - Final validation is green:
    - `python -m ruff format src tests`
    - `python -m ruff check src tests`
    - `python -m mypy src`
    - `python -m pytest`
    - `python -m pre_commit run --all-files`
    - `python -m sphinx -b html docs _build/html -W`
    - `python -m sphinx -b html docs docs/_build/html -W` from the standalone
      K3Z docs root.
- 2026-03-31 (Issue #65 scope expansion parked): the next log-grade phase is now
  defined but intentionally parked while `main` is pushed and cleaned up.
  - Reopened issue `#65` and widened the follow-on scope to include:
    - AU-wise, species-wise log-grade harvested product/account splits;
    - user-overridable species x log-grade price surfaces built from the 2025
      coast market reports attached on the issue; and
    - derived value-account families that multiply AU/species/log-grade volume
      by the price matrix so users can aggregate upward with
      `duplicateAccount()` inside Patchworks.
  - This is planning-only at this point:
    - no new code shipped in this pass;
    - no new branch remains active; and
    - the work is parked on `main` until the stacked local commits are pushed
      and we circle back to implementation.
- 2026-03-31 (Issue #65 P51.5 reactivated): resume the widened log-grade follow-on
  on branch `feature/issue-65-log-grade-value-accounts`.
  - Governing issue:
    - GitHub issue `#65`
  - Immediate execution order:
    - add AU-wise, species-wise harvested log-grade product/account families on
      top of the repaired additive compile-recipe contract;
    - implement the species x grade split as a margin-preserving outer-product
      recipe:
      - use the already-working species-wise harvested-volume totals as one
        margin;
      - use the already-working log-grade totals as the other margin; and
      - compute each AU/species/log-grade cell as
        `species_total * grade_total / harvested_total` so species sums and
        grade sums both remain coherent with the existing harvested-volume
        contract;
    - apply the same cross-split logic to natural-origin/unmanaged harvested
      states so forest-wide harvested volume still equals the sum of the
      explicit species/grade family rather than only the managed/TIPSY-driven
      subset;
    - scrape the newly attached 2025 coast market-report PDFs from issue `#65`
      into a FEMIC-owned, user-overridable species x grade price surface;
    - keep the repo-owned reference price matrices inside FEMIC and merge an
      optional user overlay from `~/.femic/recipe-overlays`;
    - wire the first price-surface contract to distinguish second-growth and
      old-growth coast reports, with a simple runtime selector that maps
      managed/second-growth harvests to the second-growth matrix and
      natural-origin/old-growth harvests to the old-growth matrix unless
      overridden by recipe/user config;
    - add derived value-account families that multiply AU/species/log-grade
      harvested volumes by the price matrix coefficients;
    - rebuild the affected K3Z XML / tracks surfaces before rerunning Matrix
      Builder;
    - finish with a representative headless Patchworks smoke that writes
      species-wise harvested product volume outputs and confirms the new
      price-linked value surfaces are present in concrete runtime artifacts.
- 2026-03-31 (Issue #65 P51.5 progress): the AU/species/log-grade bridge and
  value-account layer are now wired into the shared K3Z export path.
  - The shipped `log-grades` recipe now carries:
    - `species_grade_split.enabled`;
    - matrix selectors for managed vs natural-origin harvest;
    - explicit market-species proxy mappings; and
    - FEMIC-owned reference price matrices in
      `src/femic/resources/patchworks/log_grade_price_matrices.yaml`.
  - Rebuilt K3Z XML and active track surfaces now contain:
    - AU/species/log-grade harvested products; and
    - matching AU/species/log-grade value products.
  - Runtime smoke on `base` and `ctfert_l15h5` confirms:
    - non-zero species-grade harvested outputs are saved;
    - non-zero value-account outputs are saved; and
    - the price-linked bridge is live in concrete Patchworks stage artifacts.
  - Acceptance note:
    - rebuilt static `products.csv` / `accounts.csv` surfaces now reconcile the
      AU/species/log-grade bridge against the existing harvested-volume margins
      on representative K3Z tracks;
    - Patchworks saved target CSVs still do not provide a clean whole-stage
      additive proof surface for this matrix layer, so closeout should rely on
      the rebuilt static track/account surfaces plus representative non-zero
      runtime target files rather than whole-stage target summation alone.
- 2026-03-31 (Issue #65 deterministic managed-AU crosswalk repair): stop
  guessing raw managed TIPSY rows from curve shape and use a first-class
  deterministic crosswalk instead.
  - Immediate execution order:
    - persist the raw local managed/unmanaged AU linkage in the bundle AU table
      alongside the existing namespaced K3Z AU ids;
    - extend the FMG bundle context to carry that linkage forward as normalized
      analysis-unit metadata;
    - replace the exact yield-curve matching seam in
      `femic.fmg.adapters` with deterministic lookup by the persisted/raw local
      managed AU id (with a reversible namespace-derived fallback only for old
      bundle tables);
    - add focused regression tests proving managed indicator curves and QMD
      support load through the deterministic crosswalk rather than curve-shape
      rediscovery; and
    - rebuild `ctfert_l15h5` first and verify `Logs_Grade*` products/accounts
      return before broadening any further `#65` closeout work.
- 2026-03-31 (Urgent bug prep): park the current `#65` feature slice behind a
  new upstream K3Z bug for ctfert species-universe narrowing.
  - Governing issue:
    - GitHub issue `#66`
  - Immediate symptom:
    - current `ctfert_*` surfaces only emit `CW/FDC/HW` in
      `feature.Yield.managed.*`, `product.HarvestedVolume.managed.*`, and the
      new `product.Logs_Grade*` families, while AU strata tokens such as
      `CWHvm_DR_HW_M`, `CWHvm_HW_BA_M`, and `CWHvm_HW_SS_M` clearly imply
      additional expected species (`DR`, `BA`, `SS`).
  - Key evidence:
    - the same ctfert species narrowing is already present on published
      `main` before the current `#65` feature branch;
    - `pct_*` surfaces still carry the broader species set
      (`CW/FDC/HW/PLC/YC`), so this is not a generic issue with the new
      species-grade bridge itself;
    - the new bridge is inheriting an already-too-narrow ctfert harvested
      species margin.
  - Additional reported symptom to verify on this bug track:
    - many blocks reportedly show no visible seral stage in Patchworks map
      views on the current main-branch state;
    - treat this as a potentially related regression signal until proven
      otherwise, and explicitly inspect seral-stage feature emission / XML
      wiring / matrix-build outputs during the bug investigation.
  - Immediate next steps:
    - switch to the dedicated bug branch
      `bug/issue-66-ctfert-species-universe` off `main`;
    - trace why ctfert harvested-volume species families on `main` already
      collapse to `CW/FDC/HW` even when AU strata naming implies additional
      species; and
    - restore the broader expected species membership before resuming
      additional `#65` feature work.
- 2026-03-31 (Issue #66 active fix): restore broader ctfert species families
  by repairing the missing `01a` fallback path in post-TIPSY bundle assembly.
  - Root cause:
    - when `vdyp_prep-tsa<tsa>.pkl` was missing, `run_post_tipsy_bundle(...)`
      rebuilt AU maps from the persisted bundle `au_table.csv` but silently set
      `vdyp_species_proportions[tsa] = {}`;
    - that left unmanaged species-proportion curves as zero dummy rows for the
      affected ctfert AUs and prevented the treated repair seam from
      reintroducing companion species such as `DR`, `BA`, and `SS`.
  - Repair:
    - added a new fallback that rebuilds unmanaged species proportions from the
      shipped `data/vdyp_lyr-tsak3z.feather` surface when `01a` prep is absent;
    - for each persisted `(stratum_code, si_level)` pair, the fallback matches
      the leading species pair in the AU token against the dominant-pair mix in
      `vdyp_lyr`, aggregates the full top-6 species composition, and normalizes
      it before bundle emission;
    - the treated repair seam now has a real unmanaged companion map to merge
      against the planted-species TIPSY mix.
  - Verified bundle result:
    - rebuilt `treated_species_prop_*` / `untreated_species_prop_*` rows for
      `CWHvm_DR+HW`, `CWHvm_HW+SS`, and `CWHvm_HW+BA` now carry non-zero
      `DR` / `SS` / `BA` values instead of zero dummy curves.
  - Verified ctfert rebuild result:
    - refreshed `tracks_ctfert_l15h5` and `tracks_ctfert_l20h0` now carry
      broader managed species families again in
      `feature.Yield.managed.*` and `product.HarvestedVolume.managed.*`;
    - representative species now present again include `DR`, `BA`, and `SS`.
  - Verified runtime result:
    - headless ctfert smoke `issue66_ctfert_runtime_species` wrote non-zero
      runtime targets for
      `product.HarvestedVolume.managed.{DR,BA,SS}.{CC,CT}`.
  - Broadened validation:
    - rebuilt validated XML plus Matrix Builder outputs across all active K3Z
      variants, not just the two ctfert surfaces;
    - static track reconciliation now shows species-wise
      `feature.Yield.managed.*` and `product.HarvestedVolume.managed.*`
      families present across base, PCT, ctfert, intensive, and overlay
      variants, with maximum species-vs-total curve differences only in the
      small rounding-noise range (`0.1` to `0.2`);
    - discovered and fixed a separate PCT runtime seam while doing the smoke
      pass: `pct_light.pin`, `pct_moderate.pin`, and `pct_heavy.pin` were
      missing the shared `headless_runtime_common.bsh` hook and never queued
      the FEMIC worker thread, so their earlier headless failures were not
      species-account regressions at all.
  - Runtime sweep result:
    - successful headless Patchworks smokes now exist for every active K3Z
      variant:
      `base`, `pct_light`, `pct_moderate`, `pct_heavy`,
      `ctfert_l15h5`, `ctfert_l20h0`,
      `intensive_light`, `intensive_moderate`, `intensive_heavy`,
      `intensive_light_standstructure`,
      `overlay_basecase_sum`, `overlay_scenario1_sum`,
      `overlay_scenario2_sum`, and `overlay_basecase_riparian`;
    - every smoke wrote a saved stage with `returncode=0`.
  - Seral-stage symptom status:
    - user live-tested `ctfert_l15h5` and confirmed blocks do carry seral
      stage attributes and managed/unmanaged area sums look good;
    - treat the earlier “missing seral stage” report as a non-reproduced
      student-side symptom, not an active FEMIC/K3Z defect.
  - Detailed Next Steps:
    - record the full all-variant validation and PCT headless-pin repair in
      `CHANGE_LOG.md`;
    - post a final closeout comment on GitHub issue `#66`;
    - merge/push the K3Z submodule rebuild + PCT headless-pin fix;
    - update the parent repo submodule pointer and close the bug.
- 2026-03-30 (Issue #64 kickoff): start the urgent K3Z species-account regression repair on branch `bug/issue-64-k3z-species-account-dropout`.
  - Current local evidence:
    - baseline and `pct_light` now report `species=1 complete_species=1` with the `total OK, species-wise empty` diagnosis;
    - checked-in K3Z tracks and validated XML have collapsed to `feature.Yield.*.Total` / `product.Yield.*.Total` / `product.HarvestedVolume.*.Total.*` only;
    - `external/femic-k3z-instance/data/model_input_bundle/curve_table.csv` is missing all `treated_species_prop_*` / `untreated_species_prop_*` rows;
    - the active K3Z instance ships `data/ria_vri_vclr1p_checkpoint1-tsak3z.feather`, while the species-universe loader is still hard-wired to `data/ria_vri_vclr1p_checkpoint8.feather`.
  - Immediate execution order:
    - repair the species-universe source fallback first;
    - rebuild the shared K3Z XML / tracks surfaces from the repaired bundle path;
    - then prove the recovery through both `account-surface` diagnostics and a harvest-producing Patchworks smoke with species-wise harvested output.
- 2026-03-30 (Issue #64 progress): the shared K3Z species-account contract is repaired and rehydrated on disk.
  - `_load_species_universe_for_tsas(...)` now falls back from missing `checkpoint8` to the shipped `data/ria_vri_vclr1p_checkpoint1-tsak3z.feather` case artifact when it contains `tsa_code` plus top-6 species columns.
  - `femic tsa btc-post-tipsy --run-config config/run_profile.k3z.yaml --tsa k3z --run-id issue64_species_fix` now reports `species proportion export enabled for 10 species`, and `data/model_input_bundle/curve_table.csv` once again contains `treated_species_prop_*` / `untreated_species_prop_*` rows.
  - Regenerated active validated K3Z ForestModel XMLs from the repaired bundle path and reran Matrix Builder across baseline, `ctfert_*`, `pct_*`, `intensive_*`, `intensive_light_standstructure`, and overlay runtime surfaces.
  - Representative validation now shows:
    - baseline `account-surface`: `accounts=213 species=6 complete_species=6 au=14`;
    - `pct_light` `account-surface`: `accounts=331 species=6 complete_species=6 au=14`;
    - `ctfert_l15h5` `account-surface`: `accounts=322 species=4 complete_species=4 au=14`.
  - Headless runtime smoke:
    - `femic patchworks run-variant k3z.base --scenario-mode max-even-flow-smoke --scenario-target product.HarvestedVolume.managed.CW.CC --scenario-min-annual 100 --run-id issue64_species_runtime --log-dir vdyp_io/logs`
    - produced non-empty `scenario/schedule.csv` plus `targets/product_HarvestedVolume_managed_CW_CC.csv` with non-zero per-period harvest values, proving species-wise harvested runtime output is back.
- 2026-03-30 (Issue #64 closeout): the repaired K3Z contract is now fully back in compliance with the pre-existing docs-contract expectations.
  - Rebuilt the baseline validated ForestModel against `config/silviculture.k3z.base.yaml` before rerunning baseline and overlay Matrix Builder surfaces, restoring the expected baseline `feature.Height.*`, `feature.QMD.*`, and `product.QMDNumerator.*` families alongside the repaired species-wise yield/harvested-volume accounts.
  - Final validation is green:
    - `python -m ruff format src tests`
    - `python -m ruff check src tests`
    - `python -m mypy src`
    - `python -m pytest`
    - `python -m pre_commit run --all-files`
    - `python -m sphinx -b html docs _build/html -W`
    - `python -m sphinx -b html external/femic-k3z-instance/docs external/femic-k3z-instance/docs/_build/html -W`
  - The representative runtime smoke remains the direct proof that live scenario output is no longer Total-only:
    - `vdyp_io/logs/headless_stage/issue64_species_runtime/targets/product_HarvestedVolume_managed_CW_CC.csv`
- The BTC/TIPSY cutover and optional indicator-bank rollout are complete
  through issues `#56`, `#57`, and `#58`.
- The current documented BTC contract should remain explicit everywhere:
  - the live user-overlay
    ``<Documents>\BatchTIPSY Composer\TimberSupply.rpt`` path is the only
    known-valid unattended FEMIC ``/TSR`` seam;
  - BTC `/No_GUI` is a reverse-engineering dead end, not a supported FEMIC
    runtime seam.
- The FAN$IER extraction seam is complete through issue `#59`:
  - tracked user-facing surfaces now include:
    - `femic fansier run-batch`
    - `femic fansier parse-batch-output`
    - `femic fansier run-and-parse`
  - the practical machine-ingest default remains:
    - `txt`
    - raw `0%` discount posture
    - short report for lean ingest, long report for broader archive/discovery
- The Patchworks registry/operator surface is complete through issue `#60`:
  - `instances list`
  - `variants list/show/register/update/remove`
  - `variants materialization-plan`
  - `scenarios list`
  - `scenario-sets list/show`
  - `run-variant`
  - `run-scenario`
  - `run-default-scenario`
  - `run-scenario-set`
  - `run-default-scenario-set`
- The docs reconciliation sweep is now complete under issue `#61`:
  - stale `#60` roadmap closeout notes were removed;
  - user-facing guides now cover:
    - unattended BTC/FAN$IER runtime and extraction;
    - Patchworks variant/scenario/scenario-set management;
  - the API/CLI reference now carries clearer operator-facing notes for the
    shipped BTC, FAN$IER, and Patchworks seams;
  - the contract/onboarding docs now surface the current proprietary-tool
    seams more directly for agents and maintainers.
- Issue `#62` packaged-install built-in instance install is now in place:
  - FEMIC now carries a packaged-install user config contract at
    `~/.femic/user.yaml` (or the Windows equivalent);
  - managed built-ins can now be listed/installed under the configured
    managed external root;
  - `femic instance init --instance-name <name>` now resolves through the
    configured visible user-instance root;
  - shipped Patchworks built-ins now resolve from repo-local `external/...`
    first and otherwise from the configured managed built-in root;
  - built-in Patchworks launches now fail with a direct install hint when the
    underlying built-in instance is missing.
- Issue `#63` expansion rename is now in place:
  - `Forest Estate Modelling Integration Core` is now the governing
    spelled-out expansion of FEMIC;
  - package metadata, CLI help, docs index, and planning/history surfaces now
    use the new expansion consistently;
  - the stable runtime identifiers `femic` / `FEMIC` were intentionally left
    unchanged.
- Keep issue `#8` open as the narrower follow-on docs task for native Windows
  Patchworks runtime orientation and the SiteProd default/fallback summary.
- The optional-bank rollout under GitHub issue `#48` is now complete:
  - treat the remaining missing optional BTC/TIPSY indicators as one umbrella
    rollout track, grouped into logical banks rather than split across a large
    pile of tiny issues;
  - start with the most downstream-useful product-oriented families, but keep
    the issue broad enough to absorb the other missing banks as they are
    proven;
  - probe each candidate bank through the proven live user-overlay
    `TimberSupply.rpt` seam, not through oversized clean-room replacement
    reports;
  - keep the rollout proving-ground-only first, following the same dedicated
    `intensive_*` K3Z pattern used for the stand-structure bank;
  - add a durable field-inventory ledger so optional-bank scope does not drift
    between turns.
  - treat the installed BTC `OutputColumns.txt` field map as the canonical
    indicator inventory for that ledger; keep `planning/AllFieldsSQL.rpt` only
    as a secondary GUI/report-template reference for alias discovery.
  - first new post-stand-structure bank result now in hand:
    - the full `log-grades` family (`D/F/H/I/J/U/X/Y/All`) probes cleanly
      through the live unattended `/TSR` overlay seam and is the next shipped
      optional bank candidate.
    - the `lumber-2-or-better` family and `residual-fibre` family also probe
      cleanly through that same seam, so the first product-oriented rollout can
      land as a small cluster of proven banks rather than a one-bank bottleneck.
    - the `lumber-graded`, `lumber-degraded`, and `industrial-logs` families
      also probe cleanly through that seam, so the full product-output bank
      block can be rolled forward as one cohesive second-wave slice.
  - issue `#48` should now be treated as the umbrella tracker for finishing all
    remaining logical banks from the canonical ledger, not just the earlier
    first-wave product families.
  - the live-overlay threshold-triplet recovery slice is now in hand too:
    - `stand-structure-threshold-raw` probes cleanly through the real
      user-overlay `TimberSupply.rpt` seam on the simple generic transposed
      line, without needing copied-install experiments or alias fallback to
      win;
    - the landed bank shape follows the explicit triplet rule and now includes
      `Volume000/125/175`, `BasalArea000/125/175`, `MeanDBHg000/125/175`,
      `MAI000/125/175`, `VPT000/125/175`, `Juvenille_Volume000/125/175`, and
      `Juvenille_Percent000/125/175`;
  - the final `yield-and-age-core` closeout slice is now also in hand:
    - live overlay one-token isolation plus a combined candidate run showed a
      coherent shipped subset:
      `Year`, `TotalAge`, `BHAge`, `StandAge`, `HeightSindex`, `Height`,
      `Volume`, `VPT`, `HeightTassTop`, `HeightTassMean`,
      `HeightTassPredom`;
    - `CC` and `VolumeGross` remain part of the unattended TSR base preset
      rather than the optional bank;
    - only the non-threshold `Juvenille_Volume` and `Juvenille_Percent` totals
      still modal-crash through the real live overlay seam, while their
      threshold-specific variants are already shipped in
      `stand-structure-threshold-raw`;
    - Issue `#48` now has no remaining unshipped logical banks.
  - operator-supervision cleanup to land alongside this work:
    - move BTC/TIPSY CLI default runtime artifacts from `vdyp_io/logs` into
      `tipsy_io/logs`, with default scratch under `tipsy_io/scratch`, so
      supervised BTC runs no longer look like VDYP runs at a glance;
    - treat live unattended `/TSR` overlay validation as strictly sequential,
      not parallel, because the user-overlay `TimberSupply.rpt` seam is shared
      across runs.
- The first optional unattended BTC indicator-bank switch is now wired through
  the live user-overlay TSR seam:
  - `--indicator-bank stand-structure-basic`
  - current safe contents:
    - `MAI`
    - `BasalArea:000`
    - `DBHg:000`
    - `SPH:000`
    - `StemCount000`
    - `StemCount125`
    - `StemCount175`
- The critical runtime rule is now:
  - preserve and extend the hidden stock `TimberSupply.rpt` contract through
    the real per-user overlay path under the current user's Documents folder;
  - do not rely on copied-install-local `TimberSupply.rpt` overrides alone
    when validating optional-bank output, because the live overlay can shadow
    them and create false conclusions.
- The next concrete implementation edge is:
  - revisit managed K3Z QMD using the live BTC-native diameter signals already
    present in the first stand-structure bank;
  - current evidence from `tipsy_curves_tsak3z.csv` is that `DBHg000` closely
    matches the QMD implied by BTC `BasalArea000` + `SPH000`, while FEMIC's
    older volume/height/stems approximation tends to run lower on the same
    live K3Z outputs;
  - so the first intended change is to prefer BTC-native managed diameter
    curves where available and retain the older approximation only as a
    fallback;
  - prove that revised contract first on
    `intensive_light_standstructure`, inspect rebuilt XML/tracks directly, and
    run the relevant Patchworks smoke before widening anything else.
- The headless Patchworks runtime guardrail is now:
  - let FEMIC default unattended `saveStage(...)` output to
    `vdyp_io/logs/headless_stage/<run_id>` so report bundles do not spill into
    tracked `analysis/` paths;
  - only use `--stage-label` for a custom destination when that different save
    location is intentional and reviewed.
- The new human-facing inventory ledger for indicator-bank planning is:
  - `planning/tipsy_indicator_bank_checklist.md`
  - source inventory: `planning/AllFieldsSQL.rpt`
  - cross-reference sources:
    - `C:\Program Files\TIPSY 4.7\BTC\OutputColumns.txt`
    - `C:\Program Files\TIPSY 4.7\BTC\btpfields.txt`
  - status rule:
    - `[x]` means the indicator family is already surfaced through a shipped
      FEMIC BTC path;
    - `[ ]` means the field is still only in planning inventory and has not
      yet been rolled into a shipped bank/switch.
  - current cross-reference finding:
    - `OutputColumns.txt` carries useful output names that are not present in
      `AllFieldsSQL.rpt`, especially the threshold-specific raw stand
      structure aliases (`BasalArea000`, `MeanDBHg000`, `StemCount000`, etc.)
      plus the Carbon / CO2e families;
    - `btpfields.txt` appears to be a BTP input-field map, not an output-field
      ledger, but it is still worth keeping as a side reference when we later
      work on BTC/BTP input-side features.
- Keep the parallel seam-detection mission alive:
  - for any future failing column, collect clues about report family, token
    syntax, stock report membership, and `OutputColumns.txt`/Tcl references so
    we can infer why some `/TSR` columns pass and others fail.
- The installed BTC defaults file `C:\Program Files\TIPSY 4.7\BTC\gw.txt`
  should be treated as a likely first source for default FEMIC genetic gain
  settings in the cutover, with explicit documentation that those defaults are
  exploratory / educational rather than an operational recommendation.
- The installed BTC defaults file `C:\Program Files\TIPSY 4.7\BTC\oafs.txt`
  should be treated as a likely first source for default FEMIC OAF settings in
  the cutover, including OAF1/OAF2 and packaged custom OAF response shapes.
- The installed BTC field map `C:\Program Files\TIPSY 4.7\BTC\OutputColumns.txt`
  should be treated as the likely first output-field mapping reference if we
  can unlock a richer non-GUI BTC output mode beyond the default TSR
  volume/height CSV.

## Former ROADMAP.md lines 16689-17021 - extracted Phase 53 named-pipeline narrative block

- Original insertion context: Active Phase 53 narrative moved out of the main roadmap into a dedicated planning note.
- Affected phases/issues: Named-pipeline / yield-bridge / strict reproducibility work under `#163`, `#164`, `#167`, `#168`, and `#169`.

### Extracted Content

## Detailed Next Steps Notes

- 2026-04-18: Opened the post-THLB-reconciliation umbrella for the deeper pipeline/runbook refactor.
  - Governing umbrella issue:
    - `#163` — refactor FEMIC around named pipelines built from recipe sequences.
  - First concrete child issue:
    - `#164` — add an explicit `AFLB -> strata/AU/yield -> THLB` interruption seam inside the THLB workflow.
  - Working interpretation:
    - the recently validated TSA29 strict THLB lane exposed that THLB is not logically one uninterrupted recipe chain;
    - it must pause after AFLB to derive strata, define AUs, satisfy VDYP/TIPSY/FANSIER yield dependencies, and then resume late-stage THLB.
  - Current bounded next step for this new arc:
    - audit the current runtime path against the desired seam and document exactly where FEMIC already has reusable artifacts (`aflb_checkpoint`, strata/AU helpers, VDYP cache checks, BTC/TIPSY runners, yield-curve compile logic) versus where the interruption/resume contract is still implicit.
- 2026-04-18: Completed the first `#164` seam audit and turned it into a concrete artifact/command contract.
  - Audit result:
    - the repo already has most of the functional pieces:
      - restart-grade THLB checkpoints (`aflb_checkpoint`, `lhlb_checkpoint`, `lhlb_curve_ready_checkpoint`);
      - stratification and AU helpers in `src/femic/pipeline/tsa.py`;
      - top-area coverage config in `selection.stratification.top_area_coverage`;
      - VDYP prep/result caches; and
      - BTC/TIPSY resume surfaces via `femic tsa post-tipsy` and `femic tsa btc-post-tipsy`.
  - The missing contract is the explicit bridge between:
    - `AFLB`
    - strata/AU/yield compilation
    - and downstream THLB continuation.
  - Proposed new canonical artifacts for `#164`:
    - `data/tsr/aflb_strata_checkpoint.feather`
    - `data/tsr/aflb_au_checkpoint.feather`
    - `data/tsr/aflb_yield_bridge_manifest.json`
    - `data/tsr/aflb_yield_ready_checkpoint.feather`
  - Proposed first command surface:
    - `femic tsr build-yield-bridge --instance-root ... --run-config ... --tsa ...`
  - Working spec note is now captured in:
    - `planning/aflb_yield_bridge_seam.md`
  - Next bounded implementation step:
    - formalize the manifest schema and publish the first two restart seams (`aflb_strata_checkpoint` and `aflb_au_checkpoint`) before wiring the full VDYP/TIPSY resume bridge.
- 2026-04-18: Active `#164` implementation scope is the first artifact-only slice, not the full yield bridge.
  - This bounded slice will publish only:
    - `data/tsr/aflb_strata_checkpoint.feather`
    - `data/tsr/aflb_au_checkpoint.feather`
    - `data/tsr/aflb_yield_bridge_manifest.json`
  - It will not yet:
    - run VDYP/TIPSY/FANSIER;
    - publish `aflb_yield_ready_checkpoint.feather`; or
    - generalize into the broader named-pipeline registry under `#163`.
  - Current execution precondition:
    - local `external/femic-tsa29-instance/data/tsr/aflb_checkpoint.feather` may be absent after the generated-artifact hygiene cleanup, so the first command surface must either regenerate that upstream checkpoint explicitly or fail with a clear remediation message instead of assuming the file is still present.
- 2026-04-18: The next bounded `#164` slice is `P53.2c.1`, still inside the existing `build-yield-bridge` command.
  - Implementation target:
    - add conservative cache-sufficiency inspection for the current AFLB-derived strata/AU selection without widening into VDYP/TIPSY/FANSIER execution.
  - Required outputs for this slice:
    - extend `data/tsr/aflb_yield_bridge_manifest.json` with stable provenance for the current AFLB/run-config/selection state; and
    - add a three-state cache verdict (`sufficient`, `insufficient`, `blocked_missing_inputs`) plus evidence/reason details.
  - Required inspection surfaces:
    - prior `aflb_yield_bridge_manifest.json` when present;
    - `data/vdyp_results-tsaXX.pkl`;
    - `data/vdyp_curves_smooth-tsaXX.feather`;
    - `data/model_input_bundle/{au_table,curve_table,curve_points_table}.csv`; and
    - optional supporting evidence from post-TIPSY/BTC manifests and `03_input` / `04_output` / `04_error` handoff files.
  - Scope boundary:
    - keep missing `curve_table.csv` / `curve_points_table.csv` in `blocked_missing_inputs`;
    - treat absent post-TIPSY/BTC evidence as `insufficient`, not blocked; and
    - do not publish `aflb_yield_ready_checkpoint.feather` yet.
- 2026-04-18: Opened parked bug `#166` for branch-level full-suite pytest failures discovered during the `P53.2c.1` milestone sweep.
  - Current policy:
    - keep those failures out of the active yield-bridge delivery lane unless a future slice explicitly targets them.
  - Current failing surfaces recorded in `#166`:
    - the branch-level failures currently sit in `tests/test_tsr_recipes.py` and `tests/test_tsr_step13_attributes.py`.
- 2026-04-18: The next bounded `#164` slice after cache inspection is `P53.2d.1`, still on `femic tsr build-yield-bridge`.
  - Implementation target:
    - promote a cache-sufficient AFLB AU checkpoint into `data/tsr/aflb_yield_ready_checkpoint.feather` using existing local bundle/cache artifacts only.
  - Required outputs for this slice:
    - `data/tsr/aflb_yield_ready_checkpoint.feather`;
    - manifest `yield_ready` status/path metadata; and
    - CLI/result reporting for `yield_ready_status`.
  - Shared implementation seam:
    - factor a small reusable AU-table-to-curve assignment helper so the AFLB yield-ready promotion and late-stage step13 curve-ready enrichment use the same bundle mapping semantics.
  - Scope boundary:
    - do not launch BTC/TIPSY/FANSIER;
    - do not resume downstream THLB execution yet; and
    - if cache sufficiency is not `sufficient`, stop after writing the manifest and bounded strata/AU artifacts with a clear remediation message.
- 2026-04-18: The next bounded `#164` slice after `P53.2d.1` is `P53.2d.2`, focused on downstream THLB acceptance of the yield-ready restart seam.
  - Implementation target:
    - accept `data/tsr/aflb_yield_ready_checkpoint.feather` as an explicit `--checkpoint-path` surface for downstream reconstructed THLB runs without changing default checkpoint discovery order.
  - Required behavior:
    - recognize a distinct restart mode such as `aflb_yield_ready_checkpoint_restart`;
    - skip only `GLB -> AFLB` steps, not `AFLB -> LHLB`;
    - validate that the checkpoint carries downstream-ready fields (`stratum`, `stratum_matched`, `si_level`, `au`, `curve1`, `curve2`); and
    - surface the new restart signal in THLB run metadata/audit output.
  - Scope boundary:
    - explicit checkpoint only;
    - no auto-discovery preference changes;
    - no auto-build of the yield bridge from THLB commands; and
    - no new command surface.
- 2026-04-18: Completed `P53.2d.2` under `#164` by teaching downstream THLB runners to accept the new yield-ready restart seam explicitly.
  - Implemented behavior:
    - reconstructed THLB runs now recognize `data/tsr/aflb_yield_ready_checkpoint.feather` as `aflb_yield_ready_checkpoint_restart`;
    - explicit yield-ready restarts skip only `GLB -> AFLB` while still executing `AFLB -> LHLB` and `LHLB -> THLB`; and
    - both `thlb-netdown-run` and `thlb-netdown-step-run` accept the explicit checkpoint path without adding new flags.
  - Guardrails:
    - explicit yield-ready checkpoints now fail fast unless they contain `stratum`, `stratum_matched`, `si_level`, `au`, `curve1`, and `curve2`;
    - default checkpoint auto-discovery order remains unchanged; and
    - THLB commands still do not auto-build the AFLB yield bridge.
  - Validation:
    - targeted recipe tests cover restart-mode recognition, invalid yield-ready rejection, and parent-step acceptance;
    - targeted CLI tests cover explicit checkpoint forwarding and restart-signal summary output; and
    - lint/type checks passed on the touched surface.
- 2026-04-18: The next bounded `#164` slice after THLB restart acceptance is `P53.2d.3`, still on `femic tsr build-yield-bridge`.
  - Implementation target:
    - execute the real AFLB yield bridge from existing VDYP cache when cache sufficiency is `insufficient`, rather than stopping after inspection.
  - Required behavior:
    - keep the existing fast path for `cache_sufficiency == sufficient`;
    - treat `blocked_missing_inputs` as a hard stop;
    - on `insufficient`, compile fresh bridge-owned `tipsy_params_tsaXX.xlsx`, `02_input-tsaXX.dat`, and `03_input-tsaXX.csv`;
    - then run either `btc-post-tipsy` or `post-tipsy` helper workflows based on managed-curve mode; and
    - republish `aflb_yield_ready_checkpoint.feather` from the rebuilt bundle outputs.
  - Provenance/reporting requirements:
    - extend the manifest with execution-path metadata (`local_cache`, `post_tipsy_resume`, or `btc_post_tipsy`);
    - record 02/03/04 handoff paths plus post-TIPSY/BTC manifest evidence; and
    - surface the execution path in CLI summary output.
  - Scope boundary:
    - reuse the existing VDYP cache only;
    - do not add a new VDYP rerun lane yet;
    - defer FANSIER; and
    - keep the command surface unchanged.
- 2026-04-18: Completed `P53.2d.3` under `#164` by turning the yield bridge into a real execution path when reusable VDYP cache exists.
  - Implemented behavior:
    - `femic tsr build-yield-bridge` still fast-paths `sufficient` cache cases to local promotion;
    - `blocked_missing_inputs` remains a hard stop; and
    - rebuildable `insufficient` cases now compile fresh `tipsy_params_tsaXX.xlsx`, `02_input-tsaXX.dat`, and `03_input-tsaXX.csv`, then run `btc-post-tipsy` or `post-tipsy` based on managed-curve mode before republishing `aflb_yield_ready_checkpoint.feather`.
  - Provenance/reporting:
    - the manifest now records execution-path metadata, bridge handoff artifact paths, post-TIPSY/BTC manifest evidence, and execution failure reasons;
    - the CLI summary now prints `yield_bridge_execution_path`; and
    - CLI failure messaging now prefers the bridge execution failure reason when yield-ready publication does not complete.
  - Scope boundary preserved:
    - no new CLI command;
    - no VDYP rerun lane;
    - FANSIER still deferred; and
    - downstream THLB restart acceptance remains unchanged from `P53.2d.2`.
- 2026-04-18: The next bounded `#164` slice after the execution bridge is `P53.2d.4`, focused on real TSA29 proof and issue closeout.
  - Implementation target:
    - run the bridge on the real TSA29 instance, inspect the concrete artifacts, smoke the downstream THLB restart seam from `aflb_yield_ready_checkpoint.feather`, and close the issue if the evidence is good.
  - Required execution steps:
    - regenerate `data/tsr/aflb_checkpoint.feather` first if the local TSA29 hygiene cleanup removed it;
    - run `femic tsr build-yield-bridge --instance-root external/femic-tsa29-instance --run-config config/run_profile.tsa29.yaml --tsa 29`;
    - inspect the rebuilt manifest, yield-ready checkpoint, bundle tables, and runtime manifests; and
    - run one downstream THLB smoke from `--checkpoint-path data/tsr/aflb_yield_ready_checkpoint.feather`.
  - Closeout requirements:
    - mark the `P53.2*` issue-164 work complete in roadmap notes/checklists as appropriate;
    - append the final validation summary to `CHANGE_LOG.md`; and
    - post an explicit GitHub closeout note on `#164` before closing it.
- 2026-04-18: `P53.2d.4` real TSA29 validation proved the bridge itself, but blocked issue closeout on one remaining downstream restart seam.
  - Real TSA29 bridge proof succeeded:
    - republished `data/tsr/aflb_checkpoint.feather` and `data/tsr/lhlb_checkpoint.feather` from the reconstructed THLB lane;
    - `femic tsr build-yield-bridge --instance-root external/femic-tsa29-instance --run-config config/run_profile.tsa29.yaml --tsa 29` completed successfully;
    - the bridge manifest recorded `slice_status = yield_ready_from_bridge_execution`;
    - the execution path was `btc_post_tipsy`; and
    - `data/tsr/aflb_yield_ready_checkpoint.feather` was published with `371627` rows.
  - Remaining blocker before `#164` can close:
    - downstream THLB smoke from `--checkpoint-path data/tsr/aflb_yield_ready_checkpoint.feather` failed during step-13 curve-ready enrichment;
    - current failure surface is `KeyError` from `assign_stratum_matches_from_au_table(...)` / `build_stratum_lexmatch_alias_map(...)`; and
    - the missing-index strata named in the real run included `MS_PLI`, `IDF_FD`, `MS_PL`, `ESSF_BL`, `ESSF_PL`, `ESSF_SE`, and `ESSF_PLI`.
  - Immediate next bounded slice:
    - repair the real-instance compatibility seam between the new AFLB yield-ready checkpoint and the downstream step-13/LHLB curve-ready enrichment path, then rerun the same explicit-yield-ready THLB smoke before attempting issue closeout again.
- 2026-04-18: The next bounded `#164` slice after the real TSA29 proof blocker is `P53.2d.5`, focused on step-13 compatibility and closeout retry.
  - Implementation target:
    - teach late-stage curve-ready compilation to reuse precomputed yield-ready fields when the restart checkpoint already carries valid `stratum_matched`, `si_level`, `au`, `curve1`, and `curve2` assignments.
  - Scope boundary:
    - keep normal `lhlb_checkpoint.feather` step-13 compilation behavior unchanged;
    - do not reopen the yield-bridge execution path; and
    - rerun only the same explicit-yield-ready THLB smoke needed to answer the closeout question.
- 2026-04-18: Completed `P53.2d.5` and closed the last real TSA29 blocker for `#164`.
  - Step-13 compatibility fix:
    - late-stage curve-ready compilation now reuses precomputed `stratum_matched`, `si_level`, and `au` assignments when a yield-ready restart checkpoint already carries them;
    - the normal `lhlb_checkpoint.feather` step-13 derivation path remains unchanged; and
    - a focused regression test now guards against step 13 recomputing those yield-ready fields.
  - Real closeout validation passed:
    - the same explicit restart smoke now succeeds:
      - `femic tsr thlb-netdown-run --instance-root external/femic-tsa29-instance --execution-mode reconstructed --checkpoint-path data/tsr/aflb_yield_ready_checkpoint.feather --map-id 093B023 --no-aflb-gpkg --no-lhlb-gpkg --no-lhlb-curve-ready-gpkg`;
    - the run reported `baseline_signal = aflb_yield_ready_checkpoint_restart`;
    - it wrote `data/tsr/lhlb_curve_ready_checkpoint.feather`; and
    - the previous step-13 `KeyError` did not recur.
  - Validation status for issue closeout:
    - targeted `#164` tests passed;
    - `ruff check src tests` and `mypy src` passed;
    - full `pytest` still fails only on the already-parked unrelated set tracked under `#166`; and
    - `#164` is now closeout-ready because the explicit AFLB -> strata/AU/yield -> THLB seam itself is complete and the remaining branch-level failures are outside this issue's scope.
- 2026-04-18: With `#164` closed, the next rollout-management move under umbrella `#163` is to open exactly one new child issue for the registry/runbook contract layer.
  - Intended child scope:
    - define named pipeline identity and naming rules;
    - define registry discovery/layering and lookup precedence;
    - define the runbook contract for selecting a pipeline and restart seam; and
    - keep full named-pipeline runner implementation explicitly out of scope.
  - Rollout constraint:
    - do not open multiple new feature children under `#163` until the contract-first child has narrowed the next implementation seam.
- 2026-04-18: Opened `#167` as the next active child under umbrella `#163`.
  - Child issue:
    - `#167` — define named pipeline registry and runbook contracts.
  - Why this child now:
    - `#164` already proved the interruption/resume seam pattern;
    - the next unresolved architecture boundary is the contract for named pipeline identity, registry layering, and runbook seam selection; and
    - the full named-pipeline runner should remain out of scope until `#167` is decision-complete.
- 2026-04-18: Started `#167` by landing the first contract spec note for named pipeline registries and machine-readable runbooks.
  - Spec note:
    - `planning/named_pipeline_registry_runbook_contract.md`
  - Current contract decisions captured there:
    - default registry tiers and file locations (built-in, user, instance-local, explicit extras);
    - merge order and override policy by `pipeline_id`;
    - the first YAML contract shape for pipeline registries;
    - the first YAML contract shape for machine-readable pipeline runbooks;
    - restart object policy for scratch vs checkpoint-backed seams; and
    - compatibility mapping from current TSR/THLB recipe surfaces into future named-pipeline ids and seam ids.
  - Immediate next bounded step for `#167`:
    - pressure-test the proposed contract against the current TSR THLB proof lane and identify the narrowest implementation child needed to load registries and resolve one runbook without broad workflow migration.
- 2026-04-18: Pressure-tested the `#167` contract against the live TSA29 reviewed THLB proof lane.
  - Pressure-test result:
    - the current TSA29 lane already provides stable run-profile, recipe, overlay, and checkpoint surfaces that fit the proposed registry/runbook model without inventing a parallel config tree.
  - Additional spec decisions now captured:
    - the first runner child should target one proof pipeline id only: `tsr.thlb_reviewed`;
    - the first runner child only needs seams `scratch`, `aflb`, `aflb_yield_ready`, and `lhlb_curve_ready`;
    - the first runner should be orchestration-only and delegate to the existing TSR helpers/commands; and
    - Patchworks/ws3 and broader multi-family execution remain out of scope for that first runner child.
  - Immediate next bounded step for `#167`:
    - open or draft the runner-implementation child using the now-pressure-tested minimum scope instead of a broad generic pipeline-execution ticket.
- 2026-04-18: The next rollout-management move after the `#167` pressure test is to open one narrow runner child, not to start broad pipeline execution work.
  - Intended child scope:
    - registry loading and merge resolution;
    - runbook loading and validation;
    - one proof command for `tsr.thlb_reviewed`; and
    - seam-aware delegation into the existing TSR reviewed THLB lane.
  - Explicit non-goals for that child:
    - no registry mutation commands;
    - no multi-family pipeline runner;
    - no replacement of existing `femic tsr ...` commands; and
    - no Patchworks/ws3 pipeline execution.
- 2026-04-18: Opened `#168` as the first named-pipeline runner implementation child under umbrella `#163`.
  - Child issue:
    - `#168` — implement the first named-pipeline proof runner from runbooks.
  - Implementer-facing scope:
    - load registry tiers plus explicit runbook registry paths;
    - load one machine-readable runbook;
    - resolve the proof pipeline id `tsr.thlb_reviewed`;
    - support seams `scratch`, `aflb`, `aflb_yield_ready`, and `lhlb_curve_ready`; and
    - delegate into the existing reviewed TSR THLB lane instead of inventing a new execution engine.
  - Rollout relationship:
    - `#167` remains the contract-definition child; and
    - `#168` is the first narrow execution child that should consume that contract without widening into multi-family pipeline work.
- 2026-04-18: Implemented the first proof-oriented named-pipeline runner surface for `#168`.
  - Delivered code surfaces:
    - new module `src/femic/named_pipelines.py` for built-in registry loading, registry layering, runbook loading, runbook-to-plan resolution, and proof-runner dispatch;
    - packaged built-in registry resource under `src/femic/resources/pipelines/registry.yaml`; and
    - new CLI surface `femic pipelines run --runbook ... [--instance-root ...]`.
  - Current bounded proof scope:
    - only `pipeline_id = tsr.thlb_reviewed`;
    - only seams `scratch`, `aflb`, `aflb_yield_ready`, and `lhlb_curve_ready`; and
    - execution is orchestration-only, delegating into the existing reviewed TSR THLB lane via reconstructed mode.
  - Validation state for this slice:
    - focused named-pipeline and CLI tests passed;
    - full `pytest` returned only the same eight unrelated parked failures tracked under `#166`; and
    - no new runner-specific failures remained after restoring the existing THLB CLI outcome-count summary.
  - Next bounded step for `#168`:
    - pressure-test the new `femic pipelines run` surface with a checked-in proof runbook or real TSA29 smoke path without widening into registry-mutation commands or multi-family execution.
- 2026-04-19: The next bounded `#168` slice will use the checked-in proof-runbook option rather than mutating the TSA29 submodule.
  - Implementation target:
    - add one repo-tracked machine-readable proof runbook for `tsr.thlb_reviewed` that is intended to run with an explicit `--instance-root`.
  - Scope boundary:
    - do not modify `external/femic-tsa29-instance` just to host the runbook;
    - do not broaden into registry-mutation commands or automatic default-runbook discovery; and
    - keep validation focused on runbook loading, plan resolution, CLI wiring, and proof-command delegation.
- 2026-04-19: Added the first checked-in proof runbook for `#168` and taught the CLI to accept repo-tracked runbook paths cleanly.
  - Delivered surfaces:
    - repo-tracked machine-readable runbook `runbooks/pipelines/tsa29.tsr.thlb_reviewed.aflb_yield_ready.yaml`;
    - `femic pipelines run` now prefers an existing cwd/repo-relative runbook path before falling back to the instance root; and
    - focused coverage now validates both the checked-in runbook contract and the CLI wiring for that path.
  - Validation state for this slice:
    - focused named-pipeline / CLI tests passed;
    - `ruff check src tests`, `mypy src`, `sphinx-build -b html docs _build/html -W`, and `pre-commit run --all-files` passed; and
    - full `pytest` still returned only the same eight unrelated failures parked under `#166`.
  - Next bounded step for `#168`:
    - use the checked-in proof runbook for one real TSA29 runner smoke (`femic pipelines run --runbook ... --instance-root external/femic-tsa29-instance`) without widening into broader pipeline-engine work.
- 2026-04-19: Pivot the active `#168` proof target from the reviewed scaffold lane to the strict product lane.
  - Product decision:
    - the strict reconstructed THLB lane is the real named-pipeline target;
    - the reviewed lane should be treated as legacy scaffolding or explanatory context, not the primary product proof.
  - Immediate implementation target:
    - add `pipeline_id = tsr.thlb_strict`;
    - add a checked-in TSA29 strict proof runbook; and
    - retarget the next real smoke to that strict runbook with the same bounded restart seam set.
  - Scope boundary:
    - do not widen into a generic multi-family pipeline engine;
    - do not add registry-mutation commands; and
    - keep the strict pipeline implementation on the existing reconstructed TSR THLB runner surface rather than inventing a new execution engine.
- 2026-04-19: The strict TSA29 named-pipeline smoke completed successfully from the checked-in strict runbook.
  - Smoke command:
    - `femic pipelines run --runbook runbooks/pipelines/tsa29.tsr.thlb_strict.aflb_yield_ready.yaml --instance-root external/femic-tsa29-instance`
  - Observed strict-lane runtime evidence:
    - LU-wise reconstructed runtime artifacts advanced through parent-step directories such as step `006`, `008`, `011`, `013`, `016`, `018`, `019`, `021`, and `023`;
    - later strict restart artifacts were written for `curve_threshold_checkpoint`, `lhlb_checkpoint`, `thlb_step13_compile_attributes`, `lhlb_curve_ready_checkpoint`, and the final `thlb_reconstructed_status_report`; and
    - the wrapper process exited cleanly after writing the final summary.
  - End-of-run strict summary:
    - pipeline id `tsr.thlb_strict`;
    - baseline signal `aflb_yield_ready_checkpoint_restart`;
    - full input (not MAP_ID subset);
    - `step_count = 37`;
    - `outcome_applied = 21`;
    - `outcome_applied_noop = 9`;
    - `outcome_unsupported = 7`; and
    - `final_managed_area_ha = 559,967.504`.
  - Closeout interpretation for `#168`:
    - the first named-pipeline proof runner is now demonstrated on the strict product lane rather than only on the reviewed scaffold lane.
- 2026-04-19: Opened `#169` as the next active child under umbrella `#163`.
  - Tracker split:
    - `#168` stays closed as the first proof-runner/orchestration child; and
    - `#169` is now the active strict reproducibility validation child.
  - Governing strict validation contract:
    - authoritative reference is the latest TSA29 locked-chain strict result, not the older frozen workbench snapshot and not the mutable live recipe;
    - first proof target is chained-restart stepwise plus final reproduction through step `23`; and
    - mutable live recipe drift must fail fast instead of silently becoming the validation surface.
  - Immediate next bounded step for `#169`:
    - define the TSA29-specific strict-validation contract surface and validation path before attempting broader multi-instance machinery.
- 2026-04-18: Opened `#165` to fix the TSA29 submodule generated-artifact hygiene seam that made VS Code SCM and parent `git status` disagree.
  - Root cause:
    - the parent repo had a local config override `submodule.external/femic-tsa29-instance.ignore=untracked`, so parent `git status` could look clean while the submodule itself still had hundreds of untracked generated artifacts.
  - High-volume offender roots observed inside `external/femic-tsa29-instance`:
    - `runtime/logs/glb_build/`
    - `runtime/logs/tsr/raw_glb_clip_*/`
    - `runtime/logs/tsr/lu_partition_profiles/`
    - `data/tsr/*.gpkg`
    - `data/tsr/post_step*_restart/`
    - `workbench/arcgis_review/`
  - Required fix:
    - teach the submodule to ignore its own generated artifacts correctly;
    - clean the existing untracked set; and
    - remove the parent masking config so CLI and VS Code report the same state.
