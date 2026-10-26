Carbon Package Export
=====================

``femic carbon export-package`` builds the static carbon input package consumed by
WS4 and WS3. The package contains the CBM classifiers, disturbance map, age
classes, initial inventory, merchantable yield table, track and species maps,
boundaries, and a provenance manifest.

The package is the cross-repo contract. It does not contain schedule events or
WS4 treatment transitions; WS4 adds those at run time.

Prerequisites
-------------

- A FEMIC model-input bundle with ``au_table.csv``, ``curve_table.csv``, and
  ``curve_points_table.csv``.
- A FEMIC checkpoint feather with the fragment inventory.
- The draft crosswalks under ``config/carbon/``.
- A CBM defaults version and SHA-256. When ``libcbm`` is installed in the active
  environment, FEMIC detects both from the bundled database. Otherwise pass
  ``--cbm-defaults-version`` and ``--cbm-defaults-sha256`` explicitly.
- Optional: a compiled WS4 dataset. When supplied, FEMIC reads its
  ``tracks.parquet`` and resolves exact ``track_name`` values from the
  ``AU(<id>)`` and ``IFM(<state>)`` tokens. Without it, FEMIC generates the
  canonical ``AU(<id>)+IFM(<ifm>)+treatment()`` names.

Command
-------

The supported form selects an instance configuration:

.. code-block:: bash

   femic carbon export-package \
     --config config/carbon/tsa24.yaml \
     --bundle-dir data/model_input_bundle \
     --checkpoint data/vri_vclr1p_checkpoint7.feather \
     --output-dir output/carbon/tsa24 \
     --dataset-dir output/ws4/tsa24/compiled

``config/carbon/tsa24.yaml`` and ``config/carbon/mkrf.yaml`` carry the default
boundary, crosswalk paths, CBM defaults hash, age grid, and review status. The
config also supplies the TSA/FMU codes, so ``--tsa`` is optional when
``--config`` is used.

The explicit form remains available for a one-off export:

.. code-block:: bash

   femic carbon export-package \
     --tsa 24 \
     --bundle-dir data/model_input_bundle \
     --checkpoint data/vri_vclr1p_checkpoint7.feather \
     --output-dir output/carbon/tsa24 \
     --dataset-dir output/ws4/tsa24/compiled \
     --admin-boundary "British Columbia" \
     --eco-boundary "Montane Cordillera"

The CLI resolves paths through the active instance context. Use
``--instance-root`` when the current directory is not the instance root.

The ``carbon:`` block is documented by ``config/carbon/carbon.example.yaml``.
Every key has a default except the crosswalk paths, the boundaries, and the CBM
defaults version. ``validation.expected_area_ha`` and
``validation.expected_track_count`` are optional pins for a fixture or a release
check.

What it writes
--------------

.. code-block:: text

   output/carbon/tsa24/
     manifest.json
     classifiers.csv
     disturbance_types.csv
     age_classes.csv
     inventory.csv
     yield.csv
     track_carbon_map.csv
     curve_carbon_map.csv
     species_map.csv
     boundaries.csv

The manifest records the source hashes, producer version, CBM defaults version
and hash, units, boundaries, table files, and table hashes. The package id
contains a short fingerprint of the tables and sources.

Model choices in the first version
----------------------------------

- **One leading species per track.** The yield table uses the total merchantable
  volume curve and assigns it to the CBM species classifier (for example
  ``White spruce``), following the WS3 reference. The softwood and hardwood shares
  remain in the track map for provenance and for a later species-resolved curve.
- **Canonical track names when no dataset is supplied.** The default
  ``AU(<id>)+IFM(<ifm>)+treatment()`` form matches the simple matrix builder. A
  model with additional themes should pass ``--dataset-dir`` or supply an
  explicit track-name map in code.
- **Land class follows the CBM-CFS3 definitions.** Managed forest land is class
  ``0`` (Forest Land remaining Forest Land); unmanaged forest land is class ``16``
  (Unmanaged Forest Land). This deliberately differs from the WS3 parity fixture,
  which used ``0`` for both. An IFM state with no mapping is an error rather than a
  silent class-0 fallback.
- **A missing species code falls back explicitly.** The fallback is
  ``Unspecified softwood species`` or ``Unspecified hardwood species`` and is
  recorded in the package; it is not a silent zero. Species keys follow the public
  BC VRI data dictionary (for example ``Bl`` subalpine fir, ``Sb`` black spruce,
  ``Ep`` paper birch), with clearly marked legacy aliases.

Validation
----------

Run the producer-side validator before handing a package to WS4:

.. code-block:: bash

   femic carbon validate output/carbon/tsa24
   femic carbon validate output/carbon/tsa24 --config config/carbon/tsa24.yaml
   femic carbon validate output/carbon/tsa24 --expect-area-ha 6016466.4

The command checks the manifest shape, table files and hashes, package
fingerprint, boundaries, classifiers, inventory, yield grid, curve shares, and
declared disturbances. It exits non-zero on an area, classifier, or manifest
mismatch. The optional ``--expect-area-ha`` and ``--expect-tracks`` flags can be
pinned in the instance config under ``validation`` for a fixture.

The public-safe TSA24 fixture at
``tests/fixtures/carbon/tsa24_minimal`` exercises the validator in CI. It is a
synthetic one-track package, not real TSA24 inventory.

WS4 exposes the consumer-side checks in ``docs/reference/carbon.rst`` and
``ws4/carbon/package.py``.

Caveats
-------

- The crosswalks under ``config/carbon/`` are draft defaults and need CBM/CFS
  review.
- The first exporter does not run a carbon engine. Use WS4 P58.2/P58.3 for the
  SIT compile and the libcbm run.
- The first exporter does not model retention splits or partial harvest beyond
  the disturbance map. WS4 rejects unsupported retention explicitly.
- The first exporter uses one eco boundary per package. A multi-boundary
  instance is split into packages or handled by a later extension.

Related
-------

- ``docs/reference/contracts/carbon-domain.rst`` — package contract.
- ``planning/phase115_forest_carbon.md`` — phase plan.
- WS4 ``docs/reference/carbon.rst`` — consumer contract.
