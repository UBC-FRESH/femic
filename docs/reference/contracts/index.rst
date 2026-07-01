Technical Contracts
===================

This section is FEMIC's compact technical contract surface.

Use it when you need a fast answer about repo invariants, runtime prerequisites,
path resolution, stage boundaries, canonical artifacts, or restart behavior.

This is intentionally **not** a separate agent-only documentation universe. The
pages here live in the same Sphinx tree as the narrative Guides and API
Reference, and they link back to those deeper pages instead of duplicating them
wholesale.

How to use this section
-----------------------

- Start here when you need the shortest source-of-truth answer for an
  operational seam.
- Follow the linked Guides when you need the full runbook or interpretation
  detail.
- Follow the linked API pages when the question is really about code ownership
  or callable behavior rather than workflow contract.

Contract Pages
--------------

.. toctree::
   :maxdepth: 1

   patchworks-model-semantics
   repo-runtime-invariants
   instance-and-data-roots
   instance-extension-boundaries
   stage-boundaries-and-canonical-artifacts
   recovery-and-external-runtime-boundaries
