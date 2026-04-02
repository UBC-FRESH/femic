Woodstock Compatibility Export
==============================

``femic export woodstock`` writes four CSV artifacts:

- ``woodstock_yields.csv``: long-form yield points by FMU/code, AU, IFM, and
  age (the CLI flag still uses the legacy ``--tsa`` name)
- ``woodstock_areas.csv``: stand-level area/age/AU assignments
- ``woodstock_actions.csv``: baseline clearcut action metadata by AU
- ``woodstock_transitions.csv``: baseline post-action AU/IFM transitions

CLI usage
---------

Basic usage:

.. code-block:: bash

   PYTHONPATH=src python -m femic export woodstock --tsa k3z

Useful overrides:

- ``--bundle-dir``: alternate bundle source (``au_table.csv``, ``curve_table.csv``,
  ``curve_points_table.csv``)
- ``--checkpoint``: alternate stand checkpoint feather
- ``--output-dir``: export destination
- ``--cc-min-age`` and ``--cc-max-age``: clearcut action age window for
  ``woodstock_actions.csv``
- ``--fragments-crs``: CRS for geometry-derived area processing
