WBI AOI Instance Set (Phase 113)
================================

Purpose
-------

Phase 113 (``UBC-FRESH/femic#316``) delivers the five WBI birds AOI
management-unit instances — TSAs **08, 16, 24, 40, 41** — as standard
deployment-instance repos consumed by the
`WBI birds engine <https://github.com/UBC-FRESH/wbi-birds>`_.

The five repos:

- ``UBC-FRESH/femic-tsa08-instance``
- ``UBC-FRESH/femic-tsa16-instance``
- ``UBC-FRESH/femic-tsa24-instance``
- ``UBC-FRESH/femic-tsa40-instance``
- ``UBC-FRESH/femic-tsa41-instance``

Each is wired into FEMIC as an ``external/`` git submodule.

Structure (per instance)
------------------------

Standard deployment-instance layout (see :doc:`deployment-instances` and
:doc:`case-onboarding`):

- ``config/`` — ``run_profile.tsa<code>.yaml``, ``tipsy/tsa<code>.yaml``,
  ``rebuild.spec.yaml``, ``rebuild.allowlist.yaml``,
  ``patchworks.runtime.windows.yaml``
- ``workflows/freshforge/tsa<code>_model_build_workflow.yaml``
- ``docs/`` — Sphinx site following :doc:`sphinx-template-baseline`,
  published to GitHub Pages by ``.github/workflows/docs-pages.yml``
- ``README.md``, ``QUICKSTART.md``, ``ROADMAP.md``, ``CHANGE_LOG.md``
- ``data/``, ``output/``, ``models/``, ``runbooks/``, ``evidence/``

Data lane
---------

Fresh public data only:

- **VRI 2025** (``VEG_COMP_LYR_R1_POLY_2025`` and
  ``VEG_COMP_VDYP7_INPUT_POLY_AND_LAYER_2025``), resolved via
  ``femic data bcdc-resolve``; direct zips under
  ``https://pub.data.gov.bc.ca/datasets/02dba161-fdb7-48ae-a4bb-bd6ef017c36d/current/``
  (an AOI-scoped WFS fetch is available as an alternative — see
  :doc:`bc-data-catalogue-discovery`).
- **FADM TSA boundaries** and **SiteProd** from ``external/femic-public-data``
  (see :doc:`public-data-mirror-runbook`).

Repo creation / publication flow (maintainer)
---------------------------------------------

The bootstrap follows the split-repo pattern in
:doc:`github-datalad-arbutus-pattern` and the publish recipe in
:doc:`public-data-mirror-runbook`:

1. ``gh repo create UBC-FRESH/femic-tsa<code>-instance --public``
2. ``datalad create <path>`` (dataset id + git-annex)
3. ``femic instance init --instance-root <path> --no-download-bc-vri``
4. Layer the standard structure (config overlays, docs, runbooks).
5. Create the Arbutus bucket ``ubc-fresh-femic-tsa<code>-instance`` and:

   .. code-block:: bash

      git annex initremote arbutus-s3 type=S3 encryption=none \
        bucket=ubc-fresh-femic-tsa<code>-instance public=yes \
        publicurl=https://object-arbutus.cloud.computecanada.ca/ubc-fresh-femic-tsa<code>-instance \
        host=object-arbutus.cloud.computecanada.ca protocol=https port=443 \
        requeststyle=path autoenable=true chunk=1GiB storageclass=STANDARD

6. ``git config remote.origin.datalad-publish-depends arbutus-s3``; push
   ``main`` and ``git-annex``.
7. Enable Pages: ``gh api repos/UBC-FRESH/femic-tsa<code>-instance/pages -X POST
   -f build_type=workflow``.
8. Wire the submodule: ``git submodule add <url>
   external/femic-tsa<code>-instance``.

Per-MU model-build graphs
-------------------------

Each instance owns its graph at
``workflows/freshforge/tsa<code>_model_build_workflow.yaml``:

.. code-block:: console

   freshforge plan external/femic-tsa<code>-instance/workflows/freshforge/tsa<code>_model_build_workflow.yaml
   freshforge run  external/femic-tsa<code>-instance/workflows/freshforge/tsa<code>_model_build_workflow.yaml \
     --workdir runtime/freshforge --namespace tsa<code>/model-build --json

Node chain: ``validate_case`` -> ``geospatial_preflight`` -> ``compile_upstream``
-> ``btc_post_tipsy`` -> ``export_woodstock`` -> ``ws3_bridge``; the final step
delivers ``output/ws3/tsa<code>.{lan,are,yld,act,trn}`` for the WBI engine.

Verification
------------

.. code-block:: bash

   femic prep validate-case --run-config config/run_profile.tsa<code>.yaml
   sphinx-build -b html docs docs/_build/html -W

Plan: ``planning/phase113_wbi_aoi_model_build.md``.
