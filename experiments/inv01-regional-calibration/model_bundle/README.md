# INV-01 regional model bundle

Experimental TSA 23 IDF inventory bundle using regional open-data calibration.

Models:

- `models/als_tsa23_idf_basal_area_regional_2026c.json`
- `models/als_tsa23_idf_gross_volume_regional_2026c.json`

Height remains on the published `als_tsa23_idf_lorey_height_2026.json` card.

The BA/volume cards are loaded by `femic.lidar.inventory.load_inventory_als_model`.
They are not operational cards: the external check is four clustered TSA 23
plots, and leave-one-TSA-out regional CV is mixed.  See
`../inv01-tsa23-regional-calibration.md` and `regional_cv.json`.

For the full grid, `examples/inv01_tsa23_validation/apply_regional_inventory.py`
applies the cards to the 9.5 M-cell feature table.  The standard FEMIC
`femic lidar inventory` path can use the cards with a validated LiDAR bundle and
an explicit `--features` table.

No raw data is in this bundle.
