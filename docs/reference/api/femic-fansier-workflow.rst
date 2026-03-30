femic.fansier_workflow
======================

The ``femic.fansier_workflow`` module composes FEMIC's tracked FAN$IER seams
into higher-level one-command workflows.

Current responsibilities include:

- running unattended FAN$IER batch extraction through
  :mod:`femic.fansier_runtime`; and
- immediately parsing the resulting long-report ``.txt`` files through
  :mod:`femic.fansier_reporting`.

Primary entry point
-------------------

- ``run_fansier_batch_and_parse()``

.. automodule:: femic.fansier_workflow
   :members:
   :undoc-members:
   :show-inheritance:
