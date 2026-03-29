# Extracted CHM Help Trees

This directory archives the fully extracted HTML Help trees from the installed
`C:\Program Files\TIPSY 4.7\` product set.

## Provenance

Source CHM files:

- `C:\Program Files\TIPSY 4.7\TIPSY\TIPSY45.chm`
- `C:\Program Files\TIPSY 4.7\Fansier\Fansier.chm`
- `C:\Program Files\TIPSY 4.7\SiteTools\SiteTools.chm`
- `C:\Program Files\TIPSY 4.7\Plotsy2\Plotsy2.chm`

Extraction date:

- `2026-03-29`

Working extraction method:

1. Copy each `.chm` to a short, no-space path such as `C:\chm\`.
2. Run `hh.exe -decompile <short_output_dir> <short_path_chm>`.
3. Copy the extracted tree into this tracked repo directory.

The short-path workaround matters. Earlier `hh.exe -decompile` attempts against
long paths with spaces produced empty outputs, while the same command worked
cleanly once both the input `.chm` and output directory lived under
`C:\chm\...`.

## Archived Trees

- `TIPSY45/`
  - extracted from `TIPSY45.chm`
  - file count: `257`
- `Fansier/`
  - extracted from `Fansier.chm`
  - file count: `103`
- `SiteTools/`
  - extracted from `SiteTools.chm`
  - file count: `76`
- `Plotsy2/`
  - extracted from `Plotsy2.chm`
  - file count: `29`

These trees are intended for repo-local searching and citation during future
reverse-engineering of:

- BTC/TIPSY output/report seams;
- FANSIER regime and product-price linkage;
- SiteTools batch/site-index behavior;
- Plotsy report/export help surfaces.
