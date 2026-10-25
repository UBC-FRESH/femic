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
  volume curve and assigns it to the softwood or hardwood classifier, following
  the WS3 reference. The softwood and hardwood shares remain in the track map for
  provenance and for a later species-resolved curve.
- **Canonical track names when no dataset is supplied.** The default
  ``AU(<id>)+IFM(<ifm>)+treatment()`` form matches the simple matrix builder. A
  model with additional themes should pass ``--dataset-dir`` or supply an
  explicit track-name map in code.
- **Managed and unmanaged land class both default to 0.** This matches the WS3
  reference. Land class 16 is available as an opt-in.
- **A missing species code falls back explicitly.** The fallback is
  ``Unspecified softwood species`` or ``Unspecified hardwood species`` and is
  recorded in the package; it is not a silent zero.

Validation
----------

The package consumer validates the same contract. Before handing a package to
WS4, check:

- every inventory track is in ``track_carbon_map.csv``;
- every track has a yield row on the age grid;
- every classifier set has the right number of values;
- every leading species is in ``species_map.csv``;
- every track's eco boundary matches the manifest;
- the CBM defaults hash matches the environment used for the run.

WS4 exposes the consumer-side checks in ``docs/reference/carbon.rst`` and
``ws4/carbon/package.py``.

Caveats
-------

- The crosswalks under ``config/carbon/`` are draft defaults and need CBM/CFS
  review.
- The first exporter does not run a carbon engine. Use WS4 P51.2/P51.3 for the
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
