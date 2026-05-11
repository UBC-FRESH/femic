# Phase 68: TSA29 Comparison Plot Refresh and Instance Docs Rebuild

## Scope

Phase 68 is the TSA29-instance downstream publication/docs lane.

Active instance issues:
- `UBC-FRESH/femic-tsa29-instance#4` for the comparison-plot refresh and acceptance lane
- `UBC-FRESH/femic-tsa29-instance#3` for the child docs reread/rebuild lane

Active isolated instance branch:
- `external/femic-tsa29-instance:feature/tsa29-tipsy-vdyp-comparison-refresh`

Canonical accepted comparison library:
- `plots/tipsy_vdyp_tsa29-21000..21017.png`
- `plots/tipsy_vdyp_tsa29-22000..22017.png`
- `plots/tipsy_vdyp_tsa29-23000..23017.png`

The earlier `.out`-derived `30`-plot subset is retired and is not an admissible
Phase 68 acceptance surface.

## Completed Comparison-Library Work

### P68.1

`P68.1` is complete.

Accepted state:
- the comparison library is the refreshed `54`-plot set, not the stale
  `.out`-derived `30`-plot subset;
- the comparison refresh has already been committed on the isolated TSA29
  instance branch and tracked on issue `#4`; and
- any remaining branch/PR work belongs to overall Phase 68 closeout rather
  than to the comparison-library acceptance contract itself.

### P68.1e

- parent issue `#190` tracks the CSV-canonical handoff normalization;
- parent/runtime code now treats `03_input-tsaXX.csv` ->
  `04_output-tsaXX.csv` as the only canonical BatchTIPSY/BTC handoff lane;
- the BTC -> post-TIPSY workflow now refreshes the input fingerprint sidecar
  after unattended BTC rebuilds so the downstream freshness guard accepts the
  newly rebuilt `04_output-tsaXX.csv` surface; and
- plot acceptance must continue from the CSV-canonical lane and must not
  reintroduce DAT / `.out` trap artifacts.

### P68.1f

- the official TSR 2024 data package managed-AU surface was re-anchored to
  Table 40 in `reference/29ts_dpkg_2024.pdf`;
- the instance evidence table is:
  `external/femic-tsa29-instance/evidence/managed_au_rule_audit-tsa29-p68_1f_20260510a.csv`;
- that audit table shows:
  - `54` current TSA29 managed/TIPSY AUs;
  - `24` AUs hitting the literal `tsa29_all_aus_catchall` fallback rule; and
  - `27` AUs whose source stratum/BEC/site-productivity combination does not
    map cleanly to any official Table 40 managed AU.

### P68.1g

- the TSA29 treated SI transform now uses the user-requested
  `SI_c1=1.0`, `SI_c2=0.0`;
- the obvious Table 40-aligned managed families were promoted out of literal
  catchall into explicit TSA29 proxy rules for:
  - non-IDF fir,
  - SBS spruce, and
  - ICH cedar; and
- literal `tsa29_all_aus_catchall` usage in live
  `build_tipsy_params_for_tsa(...)` output dropped from `24` AUs to `17`
  while preserving `0` inverted `L/M/H` SI ladders.

### P68.1h

- `btc-post-tipsy` was confirmed to be a consumer-only seam that does not
  regenerate Stage 01a TIPSY inputs;
- the stale input problem was resolved by rebuilding `03_input-tsa29.csv`
  directly from the cached TSA29 PKL/feather surfaces and live
  `build_tipsy_params_for_tsa(...)` logic before rerunning BTC;
- agreed additional remaps applied before rerun:
  - ICH cedar `HW` alias expansion,
  - `MS_PL` low-site pin back into the MS pine proxy, and
  - `SBPS_PL` / `SBPS_PLI` high-site pins back into the SBPS pine proxy;
- intentionally deferred provisional families:
  - `ESSF_PL`,
  - `ESSF_PLI`,
  - `ICH_SX`, and
  - `SBPS_SX`;
- rebuilt exported TSA29 TIPSY input surfaces carry sane monotone SI ladders,
  for example:
  - `ESSF_SE`: `7.4 / 9.3 / 12.3`,
  - `ICH_CW`: `9.4 / 12.0 / 16.3`, and
  - `SBS_SX`: `14.3 / 17.4 / 19.6`;
- the rebuilt `btc-post-tipsy` run manifest at
  `runtime/logs/run_manifest-p68_1h_tipsy_remap_refresh_20260510c.json`
  reports:
  - `54` AU rows,
  - `108` curves, and
  - `18,090` curve points; and
- the regenerated comparison library now contains the full `54`
  `plots/tipsy_vdyp_tsa29-*.png` overlays rebuilt from the fresh Stage 01a
  handoff rather than a stale exported input surface.

### P68.1i

- `external/femic-tsa29-instance/data/tipsy_params_tsa29.xlsx` has been
  removed from the active TSA29 Phase 68 lane;
- TSA29 instance docs, rebuild metadata, and runbooks now describe
  `03_input-tsa29.csv` as the only live BatchTIPSY handoff artifact for this
  lane; and
- future Phase 68 reruns should not regenerate or inspect the dead-end
  workbook mirror when answering comparison-plot questions.

### P68.1j

- the config-driven TIPSY builder seam was patched so
  `build_tipsy_params_for_tsa(...)` passes both `stratum_code` and `si_level`
  into the config-driven rule matcher;
- narrow provisional treated-side SI uplift pins were tuned on the live
  builder surface for:
  - `SBPS_PL` / `SBPS_PLI` low and medium,
  - `MS_PL` medium, and
  - `ESSF_PL` / `ESSF_PLI` low, medium, and high;
- fresh `03_input-tsa29.csv` was regenerated directly from the cached TSA29
  PKL/feather inputs and the fixed live builder surface;
- unattended BTC was rerun against that fresh CSV handoff and the refreshed
  `04_output-tsa29.csv` was reparsed into:
  - `external/femic-tsa29-instance/data/tipsy_curves_tsa29.csv`, and
  - the full `54` `external/femic-tsa29-instance/plots/tipsy_vdyp_tsa29-*.png`
    comparison overlays; and
- on the originally weak low-yield comparison families, the refreshed
  age-200 `TIPSY / VDYP` ratios now land in a usable band of roughly
  `0.81 .. 1.18`.

### P68.1k

- the legacy `01b_run-tsa.py` seam no longer falls back to
  `tipsy_params_tsa29.xlsx`;
- `01b` now reconstructs its minimal legacy comparison-input view directly from
  the canonical `03_input-tsaXX.csv` handoff and raises clearly if that CSV is
  missing;
- a focused regression test now exercises the CSV-only 01b path without any
  workbook present; and
- the live CLI seam was revalidated with
  `femic tsa btc-post-tipsy --instance-root external/femic-tsa29-instance --run-config config/run_profile.tsa29.yaml --tsa 29 --run-id p68_1k_legacy_post_tipsy_csv_20260511b`,
  which completed successfully on the CSV-only lane with:
  - `54` AU rows,
  - `108` curves, and
  - `18,090` curve points.

## Docs Audit

### P68.2a

`P68.2a` is complete.

The TSA29 instance docs audit found active drift in:
- `docs/figure-appendix.rst`
- `docs/data-and-provenance.rst`
- `docs/rebuild-and-qa.rst`
- `docs/getting-started.rst`
- `docs/troubleshooting.rst`
- `README.md`
- `runbooks/REBUILD_RUNBOOK.md`

Main stale themes:
- continued references to removed DAT / `.out` / workbook-era seam artifacts;
  and
- missing or stale figure/count/narrative coverage for the accepted `54`-plot
  `tipsy_vdyp_tsa29-*.png` comparison library.

## Next Bounded Move

### P68.2b

`P68.2b` is complete.

Updated surfaces:
- `external/femic-tsa29-instance/README.md`
- `external/femic-tsa29-instance/docs/getting-started.rst`
- `external/femic-tsa29-instance/docs/troubleshooting.rst`
- `external/femic-tsa29-instance/docs/data-and-provenance.rst`
- `external/femic-tsa29-instance/docs/rebuild-and-qa.rst`
- `external/femic-tsa29-instance/docs/figure-appendix.rst`
- `external/femic-tsa29-instance/docs/land-base-and-assumptions.rst`
- `external/femic-tsa29-instance/runbooks/REBUILD_RUNBOOK.md`

What changed:
- retired lingering DAT / `.out` / workbook-era seam references from the active
  TSA29 comparison/docs lane;
- normalized rebuild/runbook/getting-started language to the CSV-only
  `03_input-tsa29.csv` -> `04_output-tsa29.csv` seam; and
- updated comparison-surface narrative and counts to the accepted refreshed
  `54`-plot `tipsy_vdyp_tsa29-*.png` library.

### P68.2c

`P68.2c` is complete.

Updated docs surfaces:
- `external/femic-tsa29-instance/docs/index.rst`
- `external/femic-tsa29-instance/docs/getting-started.rst`
- `external/femic-tsa29-instance/docs/rebuild-and-qa.rst`
- `external/femic-tsa29-instance/docs/figure-appendix.rst`
- `external/femic-tsa29-instance/docs/yield-curve-comparisons.rst`

What changed:
- added a dedicated TSA29 `yield-curve-comparisons` page that renders the
  accepted refreshed `54`-plot `tipsy_vdyp_tsa29-*.png` gallery inline;
- wired that page into the instance docs toctree and guide flow; and
- updated figure-appendix/rebuild/getting-started references so the accepted
  comparison plots are directly surfaced rather than only mentioned in prose.

## Next Bounded Move

### P68.2d

`P68.2d` is complete.

Validation run:
- `..\..\.venv\Scripts\python.exe -m sphinx -b html docs _build/html -W`
  from `external/femic-tsa29-instance`

Outcome:
- the TSA29-instance Sphinx build completed warning-clean on the refreshed
  docs surface;
- the rendered build included the new `yield-curve-comparisons` page and copied
  the full accepted `54`-plot `tipsy_vdyp_tsa29-*.png` gallery into
  `_build/html`; and
- no additional doc fixes were required to satisfy the warning gate.

## Next Bounded Move

### P68.2e

`P68.2e` is complete.

Lock/closeout work:
- Phase 68 docs-refresh planning is now marked complete in the parent roadmap;
- the TSA29-instance issue trail has the matching progress comments for
  `P68.2b`, `P68.2c`, and `P68.2d`;
- the instance docs-refresh branch is the authoritative implementation surface:
  `feature/tsa29-tipsy-vdyp-comparison-refresh`; and
- the corresponding parent coordination branch is:
  `feature/canonical-btc-csv-handoff`.

## Next Bounded Move

Phase 68 implementation is complete locally. The next move is review/merge of
the Phase 68 PRs rather than further local docs edits.
