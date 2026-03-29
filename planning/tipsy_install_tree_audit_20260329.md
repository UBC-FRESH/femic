# Installed TIPSY Tree Audit (2026-03-29)

## Scope

This note records the `P48.3d` audit of the installed
`C:\Program Files\TIPSY 4.7\` tree after the core BTC CSV cutover and optional
indicator-bank rollout landed.

The audit goal was not to rediscover the already-proven unattended
`/TSR` user-overlay seam. The goal was to scan the wider installed tree for
additional packaged clues that could matter for future FEMIC work, especially:

- CLI/runtime entry points;
- report-template coupling and output-column metadata;
- regime-file seams for downstream tools;
- packaged help content and documentation that had not yet been folded into
  FEMIC planning.

## Audit Artifacts

Runtime audit artifacts were saved under the ignored workspace:

- `tipsy_io/logs/p48_3_install_audit/pdf_text/`
- `tipsy_io/logs/p48_3_install_audit/chm/`

Those artifacts now include:

- PDF text extracts for:
  - `BTC\userguide1.4.pdf`
  - `CBM\TIPSY-CBM.pdf`
  - `Plotsy2\Plotsy2Help.pdf`
  - `SiteTools\sicourse.pdf`
  - `TIPSY\WhatsNew.pdf`
- CHM topic inventories for:
  - `TIPSY\TIPSY45.chm`
  - `Fansier\Fansier.chm`
  - `SiteTools\SiteTools.chm`
  - `Plotsy2\Plotsy2.chm`

## Key Installed-Tree Findings

### 1. BTC CLI entry points are broader than the first landed seam

The packaged BTC user guide confirms that the command line can start from:

- a saved `.btc` project file;
- `/TSR`, which uses `TimberSupply.rpt`;
- `/FLP`, which uses `ForestLandscapePlan.rpt`.

The same guide also confirms the positional CLI contract:

1. input filename (unless the first argument is a `.btc` project);
2. optional output filename;
3. optional error filename.

This matters because FEMIC has already proven unattended `/TSR`, but the
installed docs make it clear that saved BTC projects and `/FLP` remain valid
follow-on reverse-engineering surfaces if a future workflow needs richer report
coupling than the current `/TSR` overlay path.

### 2. Standard exit codes are documented and stable

The installed BTC materials explicitly document standard exit-code behavior, and
the BTC changelog notes that v1.4.2 added standard exit-code returns.

This aligns with FEMIC's current supervision logic and strengthens the decision
to treat returned exit codes as part of the automation contract rather than as a
best-effort hint.

### 3. BTC still obeys ordinary configuration files in command-line mode

The user guide explicitly says the batch process obeys regular configuration
files such as `settings.txt`.

Planning implication:

- the installed-tree audit should continue to treat packaged config/default
  files as first-class runtime seam evidence, not just GUI implementation
  clutter.

### 4. Regime-file export is a real downstream seam

Two installed sources reinforce the regime-file story:

- `BTC\userguide1.4.pdf`
- `CBM\TIPSY-CBM.pdf`

The strongest concrete clue is the explicit BTC command-line note that
BatchTIPSY can use `-RGM` to create one regime file per processed input line.

Planning implication:

- future FEMIC follow-on work can plausibly target:
  - `FEMIC -> BTC/BatchTIPSY -> .rgm -> TIPSY-CBM`
  - `FEMIC -> BTC/BatchTIPSY -> .rgm -> FANSIER`

This is no longer a vague possibility. It is a documented installed-product seam
that sits adjacent to the landed CSV cutover.

### 5. `OutputColumns.txt` is the canonical output ledger

The installed `BTC\OutputColumns.txt` confirms the canonical output families and
their grouping metadata. In particular, it encodes the repeated
`{000,125,175}` utilization-threshold triplets for:

- `Volume`
- `BasalArea`
- `DBHg -> MeanDBHg`
- `SPH -> StemCount`
- `MAI`
- `VPT`
- `Juvenille_Volume`
- `Juvenille_Percent`

This supports the rule already adopted in FEMIC: when BTC exposes a metric at
all three merchantability cutoffs, FEMIC should treat the triplet as one atomic
bank unit unless a live-overlay blocker is proven and documented.

### 6. Packaged defaults/config files expose richer model semantics

Several packaged text files contain higher-level semantics that are useful
beyond the immediate CSV cutover:

- `BTC\oafs.txt`
  - documents `ApplyAt`, `Type`, `Levels`, and `Extrapolate`
  - explicitly shows BTC OAF logic can anchor to `Year`, `Age`, or `Height`
  - distinguishes `Volume` versus `Mortality` responses
- `BTC\utiliz.txt`
  - documents utilization-threshold behavior, including the note
    `CBM pine_Decid 12.5 and others 17.5`
- `BTC\gw.txt`, `BTC\FertRespMOF.txt`, and `BTC\vriSpecies.txt`
  - remain strong reverse-engineering surfaces for future genetics,
    fertilization, and species-mapping follow-ons

Planning implication:

- future FEMIC work that needs custom OAF semantics, utilization reasoning, or
  regime exports should start with these packaged defaults before guessing at
  hidden GUI behavior.

### 7. CHM help extraction split into two outcomes

The `.chm` audit produced mixed but still useful results:

- full HTML decompile with local `hh.exe -decompile` did not yield extracted
  files in this environment;
- however, the compiled help files do expose machine-readable topic paths, which
  were recovered by scanning embedded path strings directly from the `.chm`
  binaries.

Recovered topic inventories now live at:

- `tipsy_io/logs/p48_3_install_audit/chm/TIPSY45_topics.txt`
- `tipsy_io/logs/p48_3_install_audit/chm/Fansier_topics.txt`
- `tipsy_io/logs/p48_3_install_audit/chm/SiteTools_topics.txt`
- `tipsy_io/logs/p48_3_install_audit/chm/Plotsy2_topics.txt`

Useful examples surfaced from those topic inventories include:

- TIPSY help topics for:
  - timber supply format tables;
  - BatchTIPSY custom tables and custom output tables;
  - BatchTIPSY fertilization, custom OAFs, and mortality tables;
  - regime/export topics for downstream tools.
- Fansier help topics for:
  - regime tabs;
  - product/price sections covering logs, lumber, mill residues, biomass,
    carbon, and CO2e;
  - economics background and analysis sections.
- SiteTools help topics for:
  - batch input/output columns;
  - batch output filenames;
  - site-index methods, growth intercept models, and years-to-breast-height.

Planning implication:

- the local environment did not deliver full CHM HTML extraction, but the audit
  still recovered a platform-independent topic map that is good enough to guide
  future targeted digging without reopening the whole install-tree hunt.

## Overall Conclusion

`P48.3d` did surface real follow-on seams beyond the already-landed BTC CSV
cutover:

- saved BTC project launches (`.btc`);
- `/FLP` as a still-valid alternate report seam;
- documented `-RGM` regime-file export for CBM/FANSIER-adjacent workflows;
- packaged config/default files that explain OAF, utilization, genetics, and
  fertilization semantics;
- machine-readable CHM topic inventories even though full HTML decompile stayed
  unavailable locally.

The installed tree is therefore no longer an unexplored black box. FEMIC now
carries an auditable installed-tree evidence note plus concrete artifact paths
for future follow-on work.
