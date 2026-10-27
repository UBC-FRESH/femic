Carbon package workflow
========================================

This is the producer-side entry point for FEMIC's forest carbon lane. It connects the
static package, the public fertilization response, the HWP assumptions, the GCBM bridge,
and the WS4 consumer path. The detailed pages remain the authority; this page is the map.

Start here
----------

.. list-table::
   :header-rows: 1
   :widths: 24 42 34

   * - If you are
     - Read
     - Why
   * - An analyst building a study
     - This page, then :doc:`carbon-export`
     - Build and validate the package that WS4 consumes.
   * - A developer or reviewer
     - :doc:`../reference/contracts/carbon-domain`, then this page
     - The schema, join key, crosswalk, and engine boundary.
   * - A researcher or policy analyst
     - :doc:`hwp-lifecycle`, :doc:`fertilization-audit`, and :doc:`gcbm-export`
     - The assumptions, the emissions accounts, and the bridge boundary.
   * - An LLM agent
     - This page, ``docs/llms.txt``, and ``AGENTS.md``
     - The stable source map before changing the carbon lane.

Data flow
---------

.. code-block:: text

   public instance bundle + checkpoint
                |
                v
   FEMIC carbon export-package
   (static classifiers, inventory, yield, crosswalks, boundaries)
                |
                v
   femic carbon validate
                |
                v
   WS4 package loader -> SIT compiler -> libcbm -> carbon accounts
                                              |
                                              +-> HWP lifecycle (public config)
                                              +-> optimizer block ledger
                                              +-> system targets

   FEMIC export gcbm is a separate walltowall bridge; it is not a WS4 runtime dependency.

What belongs where
------------------

.. list-table::
   :header-rows: 1
   :widths: 28 34 38

   * - Surface
     - Owner
     - What it means
   * - Static package
     - FEMIC
     - Species/eco/disturbance crosswalks, initial inventory, merchantable yield,
       boundaries, provenance, and hashes.
   * - Schedule and events
     - WS4
     - The annual treatment chain, block area, and the exact event offsets.
   * - Engine
     - WS4
     - libcbm behind the driver protocol; a replaceable engine, not a package field.
   * - HWP assumptions
     - FEMIC publishes; WS4 applies
     - Public half-life, split, utilization, and displacement config in
       ``config/carbon/hwp.bc.yaml``.
   * - GCBM project and results
     - FEMIC exports; WS4 reads
     - A separate spatially explicit bridge and tabular reader, not a parity oracle.

Stable page map
---------------

.. list-table::
   :header-rows: 1
   :widths: 36 64

   * - Question
     - Page
   * - What is the package schema and join contract?
     - :doc:`../reference/contracts/carbon-domain`
   * - How do I export and validate a package?
     - :doc:`carbon-export`
   * - What are the public fertilization response and emissions factors?
     - :doc:`fertilization-audit`
   * - How are HWP products, decay, displacement, and EOL emissions counted?
     - :doc:`hwp-lifecycle`
   * - How do I prepare a GCBM walltowall project?
     - :doc:`gcbm-export`
   * - How does WS4 consume the package and optimize carbon?
     - `WS4 carbon reference <https://ubc-fresh.github.io/ws4/reference/carbon.html>`_
   * - How do I run a carbon study end to end?
     - `WS4 carbon how-to <https://ubc-fresh.github.io/ws4/howto/run-carbon.html>`_

Production evidence
-------------------

The production package ids and validation status for TSA08, TSA16, TSA40, and TSA41 are
recorded in the producer note ``notes/reports/p120-multi-boundary.md`` and the
`WS4 consumer report
<https://github.com/UBC-FRESH/ws4/blob/main/notes/reports/p120-multi-boundary.md>`_.
The key producer facts are:

- all four packages validate against the public CBM defaults hash
  ``4bd722d8825abeda3c9cf77247bbd4903824259e2fcc046d9a335336c8842155``;
- each package carries multiple eco boundaries where the TSA straddles them, with
  per-row inventory shares for the WS4 split;
- the TSA08/16/40/41 compiled-matrix and full-landscape schedules are WS4 evidence, not
  a FEMIC carbon-engine claim; and
- GCBM bridge runs check format and readiness only. They do not establish numerical
  equality with libcbm.

Boundaries
----------

- FEMIC does not run a carbon engine for every WS4 schedule.
- FEMIC does not own the WS4 treatment transition or the optimizer ledger.
- The HWP config is a public scenario input, not a calibrated parameter estimate.
- GCBM is not a runtime dependency and is not a parity target.
- CBM4 is unreleased; the package/SIT boundary is the migration seam.

Related
-------

- `WS4 carbon reference <https://ubc-fresh.github.io/ws4/reference/carbon.html>`_
- `WS4 carbon how-to <https://ubc-fresh.github.io/ws4/howto/run-carbon.html>`_
- `fresh-yan <https://github.com/UBC-FRESH/fresh-yan>`_ — public corrected accounting,
  curve generation, HWP grid, and records.
- `yan-yancun-masc-thesis-paper <https://github.com/UBC-FRESH/yan-yancun-masc-thesis-paper>`_
  — manuscript method and evidence.
