FEMIC
=====

Forest Estate Modelling Integration Core (FEMIC) documentation.

Start with :doc:`guides/carbon-overview` for the carbon lane, or
:doc:`reference/contracts/index` for the operational contracts. The guides are the
task paths; the contracts are the shortest source of truth.

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Question
     - Start here
   * - How do I build a carbon package for WS4?
     - :doc:`guides/carbon-overview`, then :doc:`guides/carbon-export`
   * - How are HWP half-life and displacement counted?
     - :doc:`guides/hwp-lifecycle`
   * - How do I prepare a GCBM project?
     - :doc:`guides/gcbm-export`
   * - What are the runtime and data invariants?
     - :doc:`reference/contracts/index`

.. toctree::
   :maxdepth: 2
   :caption: Guides

   guides/index

.. toctree::
   :maxdepth: 2
   :caption: Sample Models

   sample-models/index

.. toctree::
   :maxdepth: 2
   :caption: Reference

   reference/contracts/index
   reference/api/index
   reference/cli
   reference/patchworks-export
   reference/woodstock-export
   reference/run-config
   reference/nemora-task-map
   reference/nemora-upstream-candidates
