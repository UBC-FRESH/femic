``femic.instance_bootstrap`` Module
===================================

The :mod:`femic.instance_bootstrap` module owns FEMIC's filesystem-first
deployment-instance scaffold. It creates the canonical instance directory
layout, writes packaged template files, and optionally downloads the standard
BC-wide VRI datasets that many new deployment instances start from.

If you are debugging why ``femic instance init`` created or skipped certain
files, where the template payload actually comes from, or how FEMIC expects a
new instance workspace to be laid out on disk, this is the first module to
read. In practice it owns:

- the canonical instance directory skeleton
- packaged template-file extraction from ``femic.resources.instance``
- optional BC VRI download/extract behavior
- the typed result payload returned to the CLI after bootstrap

Start Here If...
----------------

Use this page first if you are trying to:

- understand what ``femic instance init`` actually writes into a new instance
- inspect which template files are packaged with FEMIC and where they land
- debug overwrite-versus-skip behavior during instance bootstrap
- trace the optional BC VRI download/extract path

Typical maintenance path:

1. Start with :func:`bootstrap_instance_workspace` for the overall workflow.
2. Read ``INSTANCE_DIRS`` and ``INSTANCE_TEMPLATE_FILES`` when the question is
   about the expected on-disk instance layout.
3. Inspect ``BC_VRI_DOWNLOADS`` if the issue is about dataset URLs or extract
   locations.

Typical Usage
-------------

The common operator-facing call is:

.. code-block:: bash

   femic instance init --instance-root instances/reference --no-download-bc-vri

The matching Python entrypoint is:

.. code-block:: python

   from pathlib import Path
   from femic.instance_bootstrap import bootstrap_instance_workspace

   result = bootstrap_instance_workspace(
       instance_root=Path("instances/reference"),
       overwrite=False,
       include_bc_vri_download=False,
   )

How This Fits Into The Pipeline
-------------------------------

This module sits at the very start of a deployment-instance lifecycle:

1. a user or maintainer runs ``femic instance init``
2. this module creates the canonical instance workspace skeleton
3. downstream commands such as ``prep validate-case``, ``run``, and
   ``instance rebuild`` rely on that layout being present

That means this module owns the *initial filesystem contract* for instances,
not the later runtime semantics. Once the instance exists, path resolution and
workflow behavior move into :mod:`femic.instance_context`,
:mod:`femic.pipeline.io`, and the guide/runbook layers.

Key Entry Surfaces
------------------

The highest-value entrypoints in this module are:

- :func:`bootstrap_instance_workspace`
  Create the instance workspace, write templates, and optionally fetch BC VRI
  archives.
- :class:`DatasetDownloadSpec`
  Typed download rule for one optional bootstrap dataset.
- :class:`InstanceInitResult`
  Result payload summarizing which dirs/files were created, skipped, or
  downloaded.

Filesystem Contracts
--------------------

The most important runtime contracts in this module are:

- instance bootstraps create the canonical directories in ``INSTANCE_DIRS``
- template files are copied from packaged resources named in
  ``INSTANCE_TEMPLATE_FILES``
- existing files are skipped unless ``overwrite=True``
- optional BC VRI downloads are written under ``data/downloads`` and extracted
  into ``data/bc/vri/2024``
- the CLI can summarize created/skipped/downloaded artifacts because this
  module returns a structured :class:`InstanceInitResult`

These rules matter because later deployment-instance docs and validation logic
assume the bootstrap shape produced here.

Failure Seams To Watch
----------------------

The common failure boundaries in this module are:

- stale packaged templates
  if docs or runtime assumptions drift from the packaged instance resources,
  new instances will start from the wrong contract
- overwrite confusion
  existing files are intentionally skipped by default, which can surprise users
  expecting a refresh in place
- dataset download/extract failures
  URL, network, or zip-extract issues can leave the optional BC VRI path only
  partially initialized

Cross-References
----------------

Guides and references that pair especially closely with this module:

- :doc:`../../guides/deployment-instances`
- :doc:`../../guides/case-onboarding`
- :doc:`../../guides/developer-environment-bootstrap`
- :doc:`../cli`

Related API pages:

- :doc:`femic-instance-context`
- :doc:`femic-pipeline-io`

.. toctree::
   :hidden:

   generated/femic.instance_bootstrap

.. automodule:: femic.instance_bootstrap
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
