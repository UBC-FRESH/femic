North Island Instance Pair
==========================

The North Island work has two deliberately related but independent public
instance datasets:

.. list-table::
   :header-rows: 1

   * - Repository
     - Boundary
     - Primary use
   * - `UBC-FRESH/femic-tsa48-instance <https://github.com/UBC-FRESH/femic-tsa48-instance>`_
     - full TSA 48
     - AAC/THLB benchmark, part accounting, NICC-share reference
   * - `UBC-FRESH/femic-northisland-instance <https://github.com/UBC-FRESH/femic-northisland-instance>`_
     - TSA 48 ∩ NICC + K3Z
     - NICC/MSFM planning, NICF expansion

Shared inputs, separate runtimes
--------------------------------

Both instances consume the same public BC inventory and FEMIC/VDYP export lane.
They do not share a compiled matrix, a run directory, or a web service.

The full model carries ``part = nicc`` / ``part = outside`` and ``k3z`` block
flags. Its first-decade NICC harvest is the current reference for NICC target
calibration: **≈214,544 m3/yr** (17.19% of the full AAC).

The NICC model uses the district + K3Z boundary directly. It does not import the
full-TSA runtime.

Use them together or separately
-------------------------------

Use the full TSA 48 instance for questions about the published AAC/THLB, the
NICC/outside split, or the NICC harvest reference. Use the NICC instance for
district-scale planning, targets, and the proposed 8,000 ha NICF expansion.

Either repository can be used alone. A change in one is not automatically a
change in the other; record shared assumptions in both
``notes/reference/related-instances.md`` files.
