femic.fansier_runtime
=====================

The ``femic.fansier_runtime`` module owns FEMIC's tracked FAN$IER GUI-automation
runtime seam on Windows.

Use this module when you need to:

- launch FAN$IER from a clean session;
- open the Batch form without a preloaded main-window regime;
- load `.rgm` and optional `.dis` files;
- drive broad product/age selections using FAN$IER's own checked-list
  context-menu actions;
- and harvest deterministic manifests around unattended batch outputs.

Why this module exists
----------------------

FAN$IER's broad unattended batch extraction surface turned out to be real, but
the stable implementation path was not generic UIA checkbox poking. The key
runtime seam is FAN$IER's own checked-list context menu (`Check All` /
`Uncheck All`) combined with the batch-form calculations label.

That means the code here owns:

- Windows-only process/bootstrap logic for ``Fansier.exe``;
- batch-form synchronization against the live calculations label;
- tracked manifest writing for unattended runs; and
- the public helper surface used by the CLI.

Current scope
-------------

The first tracked runtime surface focuses on launching and running unattended
batch extraction, not on downstream normalization of FAN$IER report text into
tabular FEMIC artifacts. Output parsing is a follow-on concern.

.. automodule:: femic.fansier_runtime
   :members:
   :undoc-members:
   :show-inheritance:
