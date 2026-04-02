Patchworks Export Contract
==========================

``femic export patchworks`` writes two artifacts:

- ``forestmodel.xml``
- ``fragments/fragments.shp`` (plus shapefile sidecars)

Terminology:

- A fragment shapefile row is one stand-fragment record.
- In this exporter, ``BLOCK`` is one-to-one with fragment rows (one fragment per
  block id).

ForestModel XML requirements
----------------------------

The exporter now enforces these required structure elements before writing XML:

- Root tag: ``ForestModel``
- Root attributes: ``horizon``, ``year``, ``match``
- ``<input>`` node with attributes: ``block``, ``area``, ``age``
- ``<output>`` node
- ``<define field="AU" column="AU">``
- ``<define field="IFM" column="IFM">``
- ``<define field="ORIGIN" column="ORIGIN">``
- ``<define field="RETENTION" column="Number(column('RETENTION'))">``
- ``<define field="treatment">``
- A ``unity`` curve with at least one point
- At least one ``<treatment label="CC" ...>``
- Every ``<attribute><curve idref="...">`` must reference an existing ``<curve id="...">``

Species-wise yield curves
-------------------------

For each AU/IFM species proportion curve, FEMIC now also emits a derived
species-yield curve:

- unmanaged: ``feature.Yield.unmanaged.<SPP>``
- managed: ``feature.Yield.managed.<SPP>`` and ``product.Yield.managed.<SPP>``

For CC treatment consequences, managed product attributes now also include:

- total harvested volume: ``product.HarvestedVolume.managed.Total.CC``
- species harvested volume: ``product.HarvestedVolume.managed.<SPP>.CC``

Derived species-yield points are computed as:

``TotalVolume(age) * SpeciesProportion(age)``

where species proportions are evaluated at each total-curve age using constant or
piecewise-linear interpolation of the source species-proportion curve.

To reduce XML size/noise, serializer output trims redundant far-left and far-right
points when a curve starts/ends with repeated y-values; Patchworks extends
terminal points horizontally by default.

Curve IDs are emitted as readable tokens (for example
``managed_total_<au_token>_<id>``, ``managed_prop_<SPP>_<au_token>_<id>``,
``au_<au_token>_managed_yield_<SPP>``) while remaining unique within the XML
file.

In these readable surfaces, ``<au_token>`` means the deterministic
Patchworks-safe AU token derived from ``stratum_code`` + ``si_level`` (for
example ``CWHvm_HW_FDC_H``). Operator characters such as ``+`` and ``-`` are
sanitized because Patchworks parses account labels as expressions rather than
free-text strings. When the same readable AU token would otherwise collide
across FMU/code targets, FEMIC prefixes the case code to keep the label
unique. The underlying compatibility field/normalizer still uses legacy
``tsa`` naming in parts of the runtime.

CC treatment minimum age is now resolved per AU as:

``CMAI(managed_total_curve) - 20``

where CMAI is the age with maximum mean annual increment
(``managed_volume(age) / age``) on the managed total-yield curve. The result is
clamped to ``[0, --cc-max-age]``.

Seral-stage attributes (optional)
---------------------------------

When ``--seral-stage-config`` is provided, the exporter emits per-AU binary
seral curves and binds these attributes:

- ``feature.Seral.regenerating``
- ``feature.Seral.young``
- ``feature.Seral.immature``
- ``feature.Seral.mature``
- ``feature.Seral.overmature``
- ``feature.Seral.<au_token>.regenerating``
- ``feature.Seral.<au_token>.young``
- ``feature.Seral.<au_token>.immature``
- ``feature.Seral.<au_token>.mature``
- ``feature.Seral.<au_token>.overmature``
- CC-treatment consequence area accounts by stage/AU:
  ``product.Seral.area.<stage>.<au_token>.CC``

The global ``feature.Seral.<stage>`` labels remain in place for compatibility
and summary surfaces. The AU-specific ``feature.Seral.<au_token>.<stage>``
labels are the per-AU inventory-state surface.

Default boundaries are derived per AU from managed total-yield CMAI and peak
yield age:

- regenerating: ``0-5``
- young: ``6-25``
- immature: ``26-CMAI`` (CMAI floor of 25 applied for ordering stability)
- mature: ``CMAI+1`` to ``min(peak_yield_age, 200)``
- overmature: ``mature_upper+1`` and older

YAML supports optional per-AU stage overrides:

.. code-block:: yaml

   default:
     mature:
       max_age: min_peak_or_200
   au_overrides:
     "985501000":
       mature:
         max_age: 170
       overmature:
         min_age: 171

Recognized token values for ``min_age``/``max_age`` are:
``cmai``, ``cmai_plus_1``, ``peak_yield_age``, ``min_peak_or_200``,
``mature_plus_1``.

Retention modulator (optional per fragment)
--------------------------------------------

The exporter now supports a per-fragment retention scalar:

- ``RETENTION = 0.0``: no retained area
- ``RETENTION = 1.0``: fully retained fragment area
- intermediate values: partial retained area

Current export behavior:

- fragments carry a numeric ``RETENTION`` field
- managed select statements emit:
  ``<retention factor="RETENTION">``
- the retained share is reassigned to ``IFM='unmanaged'``
- ``ORIGIN`` is left unchanged on the retained portion

This keeps retention orthogonal to both:

- ``IFM`` as the managed/unmanaged regime field, and
- ``ORIGIN`` as the natural/planted composition field

When ``RETENTION = 0.0`` everywhere, retention wiring is present but behavior is
unchanged relative to the pre-retention model.

Point formatting policy:

- ``x``: integer age strings when integral (default case)
- ``y`` for volume-yield curves (``managed_total_*``, ``unmanaged_total_*``,
  ``au_*_..._yield_*``): rounded to 1 decimal place
- ``y`` for normalized/proportion curves: rounded to at most 5 decimals

Fragments shapefile requirements
--------------------------------

The exporter validates these required fields before writing:

- ``BLOCK``: integer block ID (non-negative). A block may have one row
  (one stand-fragment per block)
- ``AREA_HA``: numeric area in hectares (strictly positive)
- ``F_AGE``: numeric forest age (non-negative)
- ``AU``: numeric analysis-unit ID (non-negative)
- ``IFM``: management mode, one of ``managed`` or ``unmanaged``
- ``ORIGIN``: stand origin state, one of ``natural`` or ``planted``
- ``RETENTION``: retention factor in ``[0.0, 1.0]``
- ``TSA``: legacy case/FMU code label field retained for compatibility
- ``geometry``: non-null, non-empty geometry

Managed/unmanaged assignment:

- Each fragment row is assigned a single IFM value:
  ``managed`` or ``unmanaged``.
- Priority/order for IFM assignment:
  ``thlb`` (0/1), then ``thlb_fact`` (>0), then ``thlb_area`` (>0), then
  ``thlb_raw`` (>0).
- If no THLB signal is present, exporter defaults to ``managed``.
- You can override the source column with ``--ifm-source-col``.
- ``--ifm-threshold <value>`` marks stands as managed when source value exceeds
  the threshold.
- ``--ifm-target-managed-share <share>`` marks top-N stands as managed to hit the
  requested stand-count share.
- ``--ifm-threshold`` and ``--ifm-target-managed-share`` are mutually exclusive.

The fragments dataset must also carry a CRS.

CLI usage
---------

Basic usage:

.. code-block:: bash

   PYTHONPATH=src python -m femic export patchworks --tsa k3z

Useful overrides:

- ``--bundle-dir``: alternate bundle source (``au_table.csv``, ``curve_table.csv``, ``curve_points_table.csv``)
- ``--checkpoint``: alternate stand checkpoint feather (must include geometry,
  legacy ``TSA`` case code field, AU, and age)
- ``--output-dir``: export destination
- ``--start-year``, ``--horizon-years``, ``--cc-min-age``, ``--cc-max-age``,
  ``--cc-transition-ifm``, ``--fragments-crs``, ``--seral-stage-config``
- ``--ifm-source-col``, ``--ifm-threshold``, ``--ifm-target-managed-share``

Transition note:

- By default, CC tracks do not write an IFM transition assignment.
- If ``--cc-transition-ifm unmanaged`` is provided, CC treatment writes
  ``<transition><assign field="IFM" value="'unmanaged'"/></transition>``.
- ``--cc-transition-ifm managed`` is accepted but omitted from XML because it is
  redundant within managed-only select statements.
