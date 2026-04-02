``femic.cli.main`` Module
=========================

The :mod:`femic.cli.main` module is the main operator-facing entry surface for
FEMIC. It defines the top-level ``femic`` Typer application, wires all
subcommands, and translates CLI options into the lower-level workflow,
pipeline, export, rebuild, and Patchworks runtime calls.

If you are trying to understand how a user-facing command reaches the rest of
the codebase, this is the first module to read. In practice it owns:

- top-level command and subcommand registration
- shared CLI option declarations
- instance-root resolution and operator-facing path defaults
- command-level handoff into the legacy workflow layer
- command-level handoff into Patchworks, export, rebuild, and evidence helpers

Start Here If...
----------------

Use this page first if you are trying to:

- add a new ``femic`` subcommand
- understand which function powers an existing CLI command
- trace how run profiles, instance roots, and external-data paths are resolved
- debug whether a failure belongs to the CLI layer or to the lower-level
  workflow/runtime helpers

Typical navigation path:

1. Find the Typer app or command decorator for the subcommand you care about.
2. Read the command function body to see which lower-level helper it calls.
3. Jump from there into the relevant module:
   - :mod:`femic.workflows.legacy`
   - :mod:`femic.pipeline.io`
   - :mod:`femic.patchworks_runtime`
   - :mod:`femic.rebuild_runner`
   - :mod:`femic.release_packaging`

Typical Usage
-------------

For operator-driven work, the CLI is usually the narrowest stable entrypoint:

.. code-block:: bash

   femic prep validate-case --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml
   femic run --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml --run-id k3z_docs_example
   femic tsa btc-post-tipsy --instance-root external/femic-k3z-instance --run-config config/run_profile.k3z.yaml --tsa k3z --run-id k3z_docs_example

When you are extending the CLI itself, the common maintenance pattern is:

.. code-block:: python

   from femic.cli.main import app, export_app

   # Existing sub-apps are registered near the bottom of the module.
   app.add_typer(export_app, name="export")

Command Structure
-----------------

The module defines one root Typer app and several sub-apps:

- ``app``: top-level ``femic`` command
- ``prep_app``: input preparation and preflight commands
- ``vdyp_app``: VDYP execution and reporting commands
- ``tsa_app``: legacy-named FMU/code stage commands, especially BTC/post-TIPSY
  resume
- ``tipsy_app``: TIPSY/BTC config, report-template, and runtime helpers
- ``export_app``: Patchworks, Woodstock, dual-export, and release packaging
- ``patchworks_app``: proprietary Patchworks runtime helpers
- ``instance_app``: instance bootstrap, rebuild, evidence, and ws3 smoke tools

Those sub-apps are attached near the end of the module with ``app.add_typer``.
That is the quickest place to orient yourself if you need the full command tree.

Common Entry Surfaces
---------------------

The highest-value command functions in this module are:

- :func:`run_all`
  - top-level end-to-end run entrypoint
- :func:`prep_validate_case`
  - case/runtime prerequisite validation
- :func:`prep_geospatial_preflight`
  - geospatial toolchain and dataset readiness checks
- :func:`tsa_btc_post_tipsy`
  - resume path after unattended BTC output refresh
- :func:`export_patchworks`
  - Patchworks package generation
- :func:`patchworks_preflight`
  - Patchworks runtime dependency checks
- :func:`patchworks_matrix_build`
  - Matrix Builder execution
- :func:`instance_rebuild`
  - rebuild-spec-driven validation and execution

These functions are good first rewrite targets because they sit at the seams
that operators and coding agents hit most often.

Shared Option Model
-------------------

One reason this module is large is that it centralizes a lot of reusable Typer
``Option`` definitions instead of scattering them across subcommands. That is
the right tradeoff for consistency, but it means this file contains both:

- structural command wiring, and
- a large constant surface for shared CLI options

When reading the file, it helps to treat those as two layers:

1. option declarations and reusable defaults
2. the actual command implementations

The shared option layer is where many important runtime contracts become
visible, including:

- default instance-relative paths
- run-id/log-dir conventions
- Patchworks runtime config defaults
- export/output directory conventions
- rebuild-spec and baseline diff inputs

Pipeline Role and Boundaries
----------------------------

This module does **not** implement the heavy modeling logic itself. Its job is
to:

- validate and normalize operator input
- resolve instance/runtime context
- choose the right lower-level helper
- render operator-facing output and failures cleanly

In other words, if a bug is about:

- command names
- option wiring
- instance-root handling
- which helper gets called
- user-facing error/report formatting

then ``femic.cli.main`` is probably the right place to investigate.

If the bug is about:

- actual Stage 00 / 01a / 01b behavior
- TIPSY/VDYP internals
- SiteProd handling
- Patchworks XML/fragments synthesis

then this module is usually just the entry seam, not the real owner.


.. toctree::
   :hidden:

   generated/femic.cli.main

Cross-References
----------------

Guides that pair especially closely with this module:

- :doc:`../../guides/pipeline-overview`
- :doc:`../../guides/stage-01a-vdyp-tipsy-input`
- :doc:`../../guides/stage-01b-post-tipsy`
- :doc:`../../guides/geospatial-runtime-bootstrap`
- :doc:`../../guides/cross-platform-runtime-smoke`

Related API pages:

- :doc:`generated/femic.pipeline.io`
- :doc:`generated/femic.patchworks_runtime`
- :doc:`generated/femic.workflows.legacy`

.. automodule:: femic.cli.main
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
