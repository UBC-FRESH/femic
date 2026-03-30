femic.fansier_reporting
=======================

The ``femic.fansier_reporting`` module owns FEMIC's structured parsing layer
for FAN$IER batch text outputs.

Current responsibilities include:

- parsing one FAN$IER long-report ``.txt`` file into normalized row groups;
- normalizing machine-hostile scalar values such as:
  - comma-formatted numerics;
  - ``∞``; and
  - ``n/a``;
- preserving file-derived batch metadata such as regime, discount profile,
  selected product, and selected harvest age; and
- aggregating a directory of FAN$IER reports into FEMIC-owned CSV tables for:
  - ``calculation_summary``;
  - ``harvest_summary``;
  - ``cost_lines``;
  - ``product_price_factors``; and
  - ``benefit_lines``.

This is the parsing half of the tracked FAN$IER seam. In operator terms, it is
what turns the long-report text lane into FEMIC-owned normalized tables that
downstream economics code can consume without having to understand FAN$IER's
report layout directly.

Primary entry points
--------------------

- ``parse_fansier_batch_report()``
- ``parse_fansier_batch_output_dir()``

See also:

- :doc:`femic-fansier-runtime`
- :doc:`femic-fansier-workflow`
- :doc:`../../guides/btc-fansier-runtime-and-extraction`

.. automodule:: femic.fansier_reporting
   :members:
   :undoc-members:
   :show-inheritance:
