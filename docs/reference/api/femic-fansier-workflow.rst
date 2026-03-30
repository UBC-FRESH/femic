femic.fansier_workflow
======================

The ``femic.fansier_workflow`` module composes FEMIC's tracked FAN$IER seams
into higher-level one-command workflows.

Current responsibilities include:

- running unattended FAN$IER batch extraction through
  :mod:`femic.fansier_runtime`; and
- immediately parsing the resulting long-report ``.txt`` files through
  :mod:`femic.fansier_reporting`.

This is the convenience composition layer over the two proven primitive seams:

- batch extraction; then
- normalization/parsing.

It should stay thin. If behavior changes are needed at the GUI-driving or
report-parsing boundaries, those belong in the runtime or reporting modules,
not in this wrapper.

Primary entry point
-------------------

- ``run_fansier_batch_and_parse()``

See also:

- :doc:`femic-fansier-runtime`
- :doc:`femic-fansier-reporting`
- :doc:`../../guides/btc-fansier-runtime-and-extraction`

.. automodule:: femic.fansier_workflow
   :members:
   :undoc-members:
   :show-inheritance:
