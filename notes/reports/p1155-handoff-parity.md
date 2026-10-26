# P115.5 TSA24 handoff and WS3/WS4 parity

Date: 2026-10-26
Phase: P115
Task: P115.5
Parent: #361
Issue: #366

## 1. Package handoff

The real TSA24 carbon package is in the shared workspace at
`/tmp/opencode/tsa24_carbon_package_ds` and in the deterministic handoff archive
`/srv/shared-data/gep/ws4/carbon-handoff/femic-carbon-24-tsa24.tar.gz`.

| Item | Value |
| --- | --- |
| Package id | `femic-carbon-24-fc431f827c66` |
| WS4 fingerprint | `cd33653608119121c11256628aabe3bbf8111d53fcf05e6383c97db948dfd8a3` |
| `manifest.json` SHA-256 | `0dca089d63e67e05aa60c36a9dd06677e012ff56b70353917142bd9982d613db` |
| Archive SHA-256 | `74f858eed4a7381c5c7e1e710edd5d2f8b310a6b0d144184b2ef350619c062cc` |
| Inventory area | 6,016,466.4 ha |
| Tracks / yield rows | 108 / 3,348 |
| CBM defaults | `1.2.9300.391`, SHA-256 `4bd722d8825abeda3c9cf77247bbd4903824259e2fcc046d9a335336c8842155` |

Join contract: exact `track_name`; units `ha`, `m3/ha`, `tC`; species values are CBM
species names (for example `White spruce`), not SW/HW aggregates.

## 2. WS3 reference run

Command (external WS3/libcbm environment):

```bash
/tmp/opencode/libcbm-venv/bin/python scripts/ws3_carbon_reference.py \
  --ws3-repo /srv/shared-data/gep/ws4/ws3 \
  --model-dir /srv/shared-data/gep/ws4/ws3/examples/data/woodstock_model_files_tsa24_clipped \
  --out /srv/shared-data/gep/ws4/carbon-handoff \
  --n-steps 20
```

Result on `tsa24_clipped`:

- 25 SIT inventory rows, 24 SIT yield rows.
- 20 annual steps (offsets 0-20).
- Ecosystem carbon: **264,504.7 -> 274,479.4 tC**.
- Initial pools:
  - `SoftwoodMerch` 36,160.8059 tC
  - `HardwoodMerch` 97.4853 tC
  - `AboveGroundSlowSoil` 33,866.2300 tC
  - `Products` 7,355.0559 tC
- Artifacts: `ws3_carbon_accounts.csv`, `ws3_carbon_pools.csv`,
  `ws3_carbon_manifest.json` under `/srv/shared-data/gep/ws4/carbon-handoff`.
- Accounts SHA-256: `3bc920a5f86803bba1ab5d676a86bbb6f9cd0b0ac2e64a06d65b48effcf0b864`.

## 3. WS3/WS4 parity

The P58.5 parity adapter was rerun against the current WS3 model:

- WS3 inventory 25 rows; WS4 inventory 25 rows.
- WS3 yield 24 rows; WS4 yield 24 rows.
- Pool comparison: `max_abs = 0.0`, `max_rel = 0.0`.
- Flux comparison: `max_abs = 0.0`, `max_rel = 0.0`.
- Initial pools matched exactly, including the four values above.

Tolerance: `atol = 1e-6`, `rtol = 1e-6` in `scripts/carbon_parity.py`.
This is exact on the clipped fixture because both paths use the same SIT tables and
`libcbm==2.10.2`.

## 4. Production TSA24 WS4 evidence

The real TSA24 package/AU 2401005 WS4 run (five years, no schedule events) is:

- Ecosystem carbon: **21,774,124.4 -> 21,949,881.3 tC**.
- package id `femic-carbon-24-fc431f827c66`; fingerprint
  `cd33653608119121c11256628aabe3bbf8111d53fcf05e6383c97db948dfd8a3`.
- Run manifest: `/tmp/opencode/tsa24_subset_carbon/carbon_manifest.json`.

This is a production-package run, not a direct WS3 comparison: WS3's clipped fixture
uses softwood/hardwood aggregate species and a 1,366.7-area-unit model, while the FEMIC
package uses CBM species and the full TSA24 footprint.

## 5. GCBM same-landscape smoke

The P115.4 GCBM export/run on 500 fragments of AU 2401005 (4,789.8 ha, 0.005 deg,
2020-2030) produced:

- WS4 GCBM reader: 12 steps, **1,489,453.2 -> 1,504,436.7 tC**.
- 276 processed land units, 196 result locations, 0 errors.

This is a useful spatial bridge, but not a parity claim: GCBM uses the spatial raster
model, a constant MAT placeholder, one baseline species/curve per AU/IFM, and a
different footprint from the WS4/WS3 runs above.

## 6. Parity caveats

- WS3 uses `softwood`/`hardwood` CBM species aggregates; FEMIC/WS4 use CBM species
  names. The clipped parity adapter preserves WS3's own species values.
- The WS3 fixture is clipped; the FEMIC TSA24 package covers the full TSA24 area.
- GCBM is a separate spatial lane; it is compared by footprint and resolution, not by
  row identity.
- Package drift invalidates parity. Use the package id, fingerprint, and manifest hash
  above for any later comparison.

## 7. Cross-repo handoff

Posted to the WS4 carbon thread (#357): join keys, package hashes, expected WS3/WS4
values, GCBM smoke values, tolerance, and the caveats above.
