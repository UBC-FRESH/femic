Forest Carbon Domain and CBM Package Contract
=============================================

Status: reviewed against public VRI/CBM/GIS sources; residual model extensions documented
Phase: P115 (forest carbon domain and CBM packages)

Purpose
-------

This page is the producer-side contract for FEMIC's forest carbon packages. FEMIC
owns the static carbon domain: the CBM boundaries, the species and disturbance
crosswalks, the initial inventory, the merchantable yield curves, and the
provenance that ties them to a source dataset.

WS4 consumes the package, joins it to a compiled dataset by track name, adds the
schedule-dependent events and treatment-dependent transitions, and runs the
carbon engine. WS3 is the reference implementation and parity oracle.

The package is the stable cross-repo contract. The engine is replaceable:
``libcbm`` now, CBM4 later, and GCBM as a separate spatially explicit lane.

What belongs in FEMIC
---------------------

- The package schema, units, rounding, and manifest.
- The BC species to CBM species crosswalk.
- The TSA/AU to CBM eco-boundary crosswalk.
- Land-class and historical-disturbance defaults.
- The initial inventory and the SIT-compatible yield tables.
- The WS4 treatment label to CBM disturbance-type crosswalk.
- The GCBM walltowall export, when that lane is active.

What does not belong in FEMIC
-----------------------------

- Running ``libcbm`` for every WS4 schedule.
- Schedule-dependent disturbance events.
- WS4 treatment transitions.
- A CBM4 implementation.
- A promise that the first crosswalks are science-complete. They are reviewed
  defaults with explicit confidence and fallbacks.

Package layout
--------------

.. code-block:: text

   carbon_package/
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

CSV is the interchange form so a reviewer can inspect the crosswalks and the
inventory without a database. Strings are written as strings so classifier codes
and species codes keep their leading characters.

Manifest
--------

``manifest.json`` is a closed schema. Unknown fields are rejected by the
consumer so a typo cannot silently disable a check.

Required content:

``schema_version``
   ``0.1`` for this contract.

``package_id``
   Producer-assigned identifier, normally containing the instance and a hash.

``created_utc``
   ISO-8601 creation timestamp.

``producer``
   ``name`` and ``version``.

``sources``
   Upstream source records with a public-safe ``path`` and a ``sha256`` digest.
   The crosswalk files (``config/carbon/*.bc.csv``) are recorded here so the
   package states which crosswalk version produced it.

``cbm_defaults``
   The CBM default parameter database ``version``, ``sha256``, and ``source``.
   For the first lane this is the database bundled with ``libcbm``.

``units``
   ``area`` = ``ha``, ``volume`` = ``m3/ha``, ``carbon`` = ``tC``,
   ``carbon_density`` = ``tC/ha``, ``co2e`` = ``tCO2e``.

``boundaries``
   The CBM administrative and ecological boundary names.

``mapping``
   ``track_key`` = ``track_name``, the species classifier name, and the
   disturbance classifier name (``user_dist_type``).

``event_source``
   ``ws4.schedule``.

``transition_source``
   ``ws4.treatments``.

``table_files``
   Optional table name to file name mapping; defaults to the layout above.

``table_hashes``
   Optional table name to SHA-256 digest. When present, the consumer verifies
   every digest.

Tables
------

``classifiers.csv``
   Long-form classifier values: ``classifier_id``, ``classifier``, ``value``,
   and optional ``description``. A classifier id has one name; a
   ``classifier_id``/``value`` pair is unique. ``classifier_id`` defines the
   order used by ``track_carbon_map.classifier_set``. In the first lane the
   species classifier values are the CBM species names (for example
   ``White spruce``), not the softwood/hardwood aggregate, so CBM can use its
   species-specific volume-to-biomass parameters.

``disturbance_types.csv``
   ``user_dist_type``, ``default_dist_type``, ``removes_biomass``,
   ``transition_reset_age``, ``regen_delay``, and optional ``notes``. Each WS4
   treatment gets its own user type even when several map to the same CBM
   default; this keeps transition rules unambiguous.

``age_classes.csv``
   ``name`` and ``class_size``. The first row has size 0; every later row has a
   positive, constant width. The yield table is sampled on this grid.

``inventory.csv``
   ``track_name``, ``age``, ``area_ha``, ``delay``, ``landclass``,
   ``historic_disturbance``, ``last_pass_disturbance``. The consumer checks
   area, age, delay, land class, and that each disturbance is declared. An
   optional ``stand_id`` may be added later for fragment-level mapping.

``yield.csv``
   ``track_name``, ``species``, ``leading_species``, ``age``, ``volume_m3_ha``.
   The key is ``track_name``/``species``/``age``. Every track has at least one
   row. Volume is merchantable volume in ``m3/ha``. ``species`` and
   ``leading_species`` both carry the CBM species classifier value.

``track_carbon_map.csv``
   The bridge table: ``track_name``, ``classifier_set``, ``leading_species``,
   ``softwood_share``, ``hardwood_share``, ``landclass``, ``last_disturbance``,
   ``eco_boundary``, ``volume_feature_label``. ``classifier_set`` is a
   semicolon-separated list in ascending ``classifier_id`` order. Shares are
   0-1 and sum to at most one. Every leading species is in the species map.

``curve_carbon_map.csv``
   ``track_name``, ``feature_label``, ``species``, ``share``. It maps a WS4
   feature label to a species component. The key is unique; share is 0-1.

``species_map.csv``
   ``bc_species``, ``cbm_species``, ``wood_type``, ``confidence``, and optional
   ``notes``. ``wood_type`` is ``softwood`` or ``hardwood``. The table is unique
   by ``bc_species``.

``boundaries.csv``
   ``admin_boundary`` and ``eco_boundary``, with optional ``spatial_unit_id``,
   ``source``, and ``notes``. At least one row matches the manifest boundaries.

Why the join key is the track name
----------------------------------

Dataset-local track ids are stable only within one compiled matrix. Track names
carry the state vocabulary and survive a rebuild. The package records the exact
``tracks.name`` strings and WS4 matches them exactly. An unmatched dataset track
is a hard failure by default; a fallback is allowed only when the caller records
it in the run provenance.

Crosswalks
----------

The crosswalk files live under ``config/carbon/`` and are versioned with the
code. Each row carries a ``confidence`` and a source note. The first versions
are deliberately conservative.

Species
~~~~~~~

``config/carbon/species_map.bc.csv`` maps public BC VRI species codes to CBM
default species names. Where a CBM default is broader than the VRI code, the mapping
uses the broader default and lowers the confidence. Two explicit fallbacks exist:

- ``Unspecified softwood species`` for an unmapped conifer.
- ``Unspecified hardwood species`` for an unmapped broadleaf.

A fallback is recorded in the package manifest; it is never a silent zero.

Eco boundary
~~~~~~~~~~~~

``config/carbon/eco_boundary.bc.csv`` maps known TSA codes to CBM eco
boundaries. The current table was checked by intersecting the public BCGW
``WHSE_ADMIN_BOUNDARIES.FADM_TSA`` polygons with the AAFC Terrestrial Ecozones
(2026-10-26). It records the dominant boundary and the overlap share in the notes.
The contract still allows one boundary per package, so a TSA that straddles a
boundary must be split or handled by a later multi-boundary extension; the table
marks those cases as ``split required``. MKRF is represented by the ``mkrf`` FMU
code in ``config/carbon/mkrf.yaml`` with the Pacific Maritime boundary.

Disturbance
~~~~~~~~~~~

``config/carbon/disturbance_map.bc.csv`` maps normalized WS4 treatment labels to
CBM default disturbance types. Matching is case-insensitive. Treatments that do
not remove biomass are marked ``removes_biomass = false`` and use a no-stock-change
CBM type. ``ct`` uses ``40% commercial thinning`` as an upper-bound proxy for a
40% basal-area removal from below; the actual merchantable-volume removal is
normally lower. ``mpb`` uses the 10% moderate default as an evergreen placeholder
and must be replaced with a severity-specific type when the instance supplies
one. Fertilization is deliberately **not** mapped: the current package has no
fertilized growth curve and no fertilizer life-cycle/N2O account, so mapping
``f1``-``f3`` to a no-op would be wrong. WS4 rejects those treatment labels until
that extension exists.

The thesis implementation (``UBC-FRESH/msc_jimmy_ke``) uses a 200 kg N/ha dose and
a growth response beginning 10 years after application. Its fertilization notebook
records per-hectare factors of approximately 17.14 kg CO2, 0.0557 kg CH4, and
20.00 kg N2O for one application, with 40.00/60.00 kg N2O for two/three
applications. Those are converted through a dynamic LCA (CH4/N2O residence times),
not a simple fixed GWP. A future FEMIC/WS4 adapter must carry both the fertilized
curve and these emission factors.

Land class
~~~~~~~~~~

``config/carbon/land_class.bc.csv`` declares the CBM-CFS3 UNFCCC land class by IFM
state: managed forest land is ``0`` (Forest Land remaining Forest Land) and
unmanaged forest land is ``16`` (Unmanaged Forest Land), following the definitions
in the CBM-CFS3 v1.2 User's Guide, Table 3-2. Nonforest area must be mapped
explicitly to its actual land-use class (cropland, grassland, wetland, settlement,
or other); there is no generic nonforest default. An unmapped IFM state is a hard
error.

Provenance and reproducibility
------------------------------

The manifest records:

- every upstream source and its hash;
- the producer version;
- the ``cbm_defaults`` version and hash;
- the table hashes;
- the package units and boundaries.

The consumer computes a package fingerprint over the manifest and table hashes.
A package is reproducible when re-exporting the same inputs produces the same
fingerprint. A run that uses a different ``cbm_defaults`` database must record
the mismatch.

Validation rules
----------------

FEMIC validation and the WS4 loader enforce the same contract:

- required tables and columns;
- unique declared keys;
- positive inventory area, non-negative ages and delays;
- land class in 0-22;
- classifier sets with the right number of values and defined values;
- every leading species in the species map;
- every yield track present, with non-negative volume;
- shares in 0-1 and summing to at most one;
- every track's eco boundary equal to the manifest boundary;
- declared disturbance types for inventory and treatment mappings;
- table hashes when present;
- the package fingerprint and the manifest boundaries.

``femic carbon validate <package>`` runs these producer-side checks and exits
non-zero on an area, classifier, or manifest mismatch. The public-safe
``tests/fixtures/carbon/tsa24_minimal`` package is the CI fixture.

Engine adapter and CBM4 readiness
---------------------------------

The package and the SIT tables are the stable contract; the carbon engine is replaceable.
The current runtime is ``libcbm==2.10.2`` with the bundled CBM defaults database
``1.2.9300.391`` (SHA-256
``4bd722d8825abeda3c9cf77247bbd4903824259e2fcc046d9a335336c8842155``). WS4 owns the
schedule-to-events/transitions step; FEMIC owns the static package. Neither side imports
CBM4 today.

The adapter boundary is:

- **Package** — schema ``0.1``, exact ``track_name`` join, CBM species names, units
  ``ha``/``m3/ha``/``tC``, and a manifest with source, table, and CBM-defaults hashes.
- **SIT tables** — classifiers, disturbance types, age classes, inventory, yield, events,
  and transitions. The compiler is engine-neutral in shape, even where the first driver
  consumes libcbm.
- **Driver** — turns SIT tables plus a schedule into pools, fluxes, accounts, and a
  manifest. ``libcbm`` is the first driver; a CBM4 driver would implement the same
  outputs and provenance.
- **Reporting** — ``carbon.*`` accounts, the block ledger, the optimizer objective, and
  the run report do not depend on a particular engine.

CBM4 status (2026-10-26)
~~~~~~~~~~~~~~~~~~~~~~~~

CBM4 is the Canadian Forest Service's next-generation, spatially explicit forest carbon
model. Public CFS material from May 2026 describes it as open-source with public
availability targeted for the latter half of 2026, and a CBM4 workshop was scheduled for
IBFRA 2026. No public CBM4 Python package, input schema, or release artifact is pinned in
this repository, so CBM4 is treated as **unreleased** until a public source and version
are verified.

The public ``cat-cfs`` organization currently exposes `libcbm_py
<https://github.com/cat-cfs/libcbm_py>`_, `cbm_defaults
<https://github.com/cat-cfs/cbm_defaults>`_, and `gcbmwalltowall
<https://github.com/cat-cfs/gcbmwalltowall>`_. ``gcbmwalltowall`` includes an external
``convert`` path from a prepared GCBM project to CBM4, but it is not a FEMIC runtime
dependency and is not used by this phase. The CBM4 status and timing are from the CFS
presentation at the EEA/JRC LULUCF Workshop (May 2026) and the IBFRA 2026 workshop
listing.

Migration triggers
~~~~~~~~~~~~~~~~~~

Revisit CBM4 when all of the following hold:

1. A public release is available with a versioned package and input contract.
2. A CBM4 driver can consume the SIT/package boundary (directly or through a documented
   adapter) and emit the same pool, flux, and account semantics.
3. A parity run on the TSA24 clipped fixture and the real TSA24 package passes the
   existing tolerance and replay checks.
4. The release license and platform support are acceptable for the lab environment.

What changes and what does not
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A CBM4 migration would change the driver, its version pin, its output mapping, and the
calibration/parameter provenance. It would **not** change the package schema, the exact
``track_name`` join, the WS4 event/transition compiler, the ``carbon.*`` account names,
the block ledger, the optimizer target interface, or the report contract.

Version-pin policy
~~~~~~~~~~~~~~~~~~

- ``libcbm`` is an optional extra, pinned exactly to ``2.10.2`` in FEMIC and WS4.
- The CBM defaults version and SHA-256 are recorded in every package and run manifest.
- An engine or defaults upgrade requires a new package fingerprint, a parity run, and a
  changelog entry; it is not a silent dependency refresh.
- CBM4 must not be added as a dependency before a public release is verified.

Platform watchlist
~~~~~~~~~~~~~~~~~~

- ``libcbm`` Linux/macOS wheels and the bundled CBM defaults database.
- Windows and Wine paths for GCBM ``moja.cli.exe`` and ``gcbmwalltowall``.
- CBM4 public repository, wheels, input schema, and CFS support policy.
- CBM-CFS3 archive tooling, kept only as a reference and not as a runtime dependency.

Open questions
--------------

1. Which CBM species default is acceptable for the BC interior hybrid spruce
   complex, and when should the package use a species-resolved curve instead of
   a softwood/hardwood share?
2. MKRF is a custom research-forest boundary near Maple Ridge; confirm its
   Pacific Maritime assignment before treating it as a TSA row.
3. Which retention and partial-harvest cases must the first version represent
   exactly rather than reject?
4. When CBM4 is public, does it accept this SIT-compatible package directly or
   require an adapter, and what is its spatial-input contract?

Related
-------

- ``planning/phase115_forest_carbon.md`` — phase plan and task map.
- WS4 ``docs/reference/carbon.rst`` — consumer-side loader contract.
- ``UBC-FRESH/ws3`` — reference implementation and parity oracle.
