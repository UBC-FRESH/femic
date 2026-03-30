Known Limitations and Human-in-the-Loop Boundaries
===================================================

TIPSY Boundary
--------------

- BatchTIPSY/BTC remains an external proprietary runtime boundary.
- FEMIC now supports a tracked unattended BTC `/TSR` seam on Windows through
  the live user-overlay ``TimberSupply.rpt`` path.
- The external-boundary caveat is now about the proprietary Windows tool and
  its report/runtime quirks, not about a hard requirement for routine manual
  button-clicking in the supported FEMIC path.
- For unattended BTC work, the supported FEMIC seam is the live `/TSR`
  user-overlay report path. BTC `/No_GUI` is not a supported FEMIC workflow.

FAN$IER Boundary
----------------

- FAN$IER automation is now real, but it remains Windows GUI automation around
  a proprietary application, not a native CLI/runtime contract.
- FEMIC can launch unattended batch extraction and parse the resulting reports,
  but this seam should still be treated as a fragile external runtime boundary.

Data Vendor/Format Constraints
------------------------------

- Some BC datasets are delivered in formats that require special extraction
  or conversion tooling.
- Dataset vintages can change fields and behavior; source validation is required
  before swapping vintages in production workflows.

Modeling Limitations
--------------------

- Small-area units can break stratification assumptions tuned for large TSAs.
- SI signal may appear weak without careful split/merge and fit controls.
- Species-wise managed trajectories may require explicit tuning when vendor
  outputs are inconsistent with scenario intent.

Documentation Scope Boundary
----------------------------

- Published Sphinx docs are user/developer guides and reference contracts.
- Large proprietary PDFs and ad hoc source material are stored under
  ``reference/`` and are not republished through Sphinx pages.
