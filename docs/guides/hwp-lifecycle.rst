Harvested wood product lifecycle
========================================

FEMIC owns the public HWP parameter set and the producer-side provenance. WS4 owns the
run-time product ledger. This page explains the assumptions, the equations, and the
boundary between the two repositories.

The parameter file is ``config/carbon/hwp.bc.yaml``. It is a scenario input, not a
calibrated estimate of the single true half-life or displacement factor. A study should
run a range over plausible values and report the range.

Public assumptions
------------------

The default file records the corrected public accounting used in the UBC-FRESH
forest-sector carbon work:

- utilization rate: **0.85** of merchantable carbon becomes utilized product;
- utilized fibre split: **50% paper**, **50% solid wood**;
- paper half-life: **2 years**;
- solid-wood half-life: a scenario parameter (the public config uses 100 years as a
  representative value);
- solid-wood displacement factor: a scenario parameter (the public config uses 1.0
  tC avoided per tC product);
- paper displacement factor: **0** tC avoided per tC product;
- decay convention: exact per-period survival ``2 ** (-period_length / half_life)``;
- end-of-life convention: product decay is emitted to the atmosphere.

The full scenario grid in the public ``fresh-yan`` records varies solid-wood half-life and
displacement factor. The thesis and ``fresh-yan`` are the method references; the config
file is the stable input surface.

Accounting
----------

For one period, WS4 reads the merchantable carbon that a disturbance transfers to the
product pool and computes:

.. code-block:: text

   inflow      = merchantable carbon transferred × utilization_rate
   solid_in    = inflow × proportion_solid_wood
   paper_in    = inflow × (1 - proportion_solid_wood)
   solid_t     = solid_{t-1} × survival_solid + solid_in
   paper_t     = paper_{t-1} × survival_paper + paper_in
   survival    = 2 ** (-period_length / half_life)
   decay       = solid_{t-1} × (1 - survival_solid)
               + paper_{t-1} × (1 - survival_paper)
   displacement = (solid_in × df_solid + paper_in × df_paper) × credit
   system       = ecosystem + solid_t + paper_t
   net emission = (ecosystem_{t-1} - ecosystem_t)
                + (HWP_{t-1} - HWP_t)
                - displacement

The carbon terms are in ``tC`` and are converted to ``tCO2e`` with 44/12. The identity
telescopes to ``ecosystem_start - ecosystem_end - HWP_end - sum(displacement)``, so the
product transfer is counted once and HWP decay is not double-counted as a second
ecosystem emission.

What the model does not represent
---------------------------------

- Landfill and inert long-lived product pools are not separate pools in this first
  version; product decay is immediate end-of-life emission.
- The paper/solid split is a public scenario assumption, not a mill-level product
  allocation.
- Displacement is a credit on product inflow. It is not a market model and does not
  establish that the displaced material would otherwise have been produced.
- The HWP parameters are uncertain. A single run is a scenario, not a confidence
  interval.

Run it in WS4
-------------

WS4 consumes the same public config:

.. code-block:: bash

   ws4 carbon \
     --dataset output/ws4/tsa24/compiled \
     --package output/carbon/tsa24 \
     --schedule schedules/baseline.csv \
     --hwp-config config/carbon/hwp.bc.yaml \
     --out out/carbon/tsa24-hwp

   ws4 optimize \
     --dataset output/ws4/tsa24/compiled \
     --targets targets/tsa24-system.yaml \
     --carbon-package output/carbon/tsa24 \
     --carbon-hwp config/carbon/hwp.bc.yaml \
     --out out/ws4/tsa24-system-search

The run adds product, end-of-life, displacement, and whole-system accounts to
``carbon_accounts.csv``. Examples of system targets are ``carbon.system.total`` (maximum
stock) and ``carbon.co2e.system.emissions.cumulative`` (minimum net emissions). See the
WS4 ``docs/reference/carbon`` page for the full account list.

Curve relationship
------------------

The HWP ledger is separate from the carbon yield curves. The curves supply ecosystem and
merchantable-carbon trajectories per track; the HWP ledger turns the harvest inflow into
product pools and emissions. WS4 can compile both from the same package and dataset, but
the exact optimizer path remains the block-level libcbm ledger.

Related
-------

- ``docs/guides/carbon-export.rst`` — package export and validation.
- ``docs/reference/contracts/carbon-domain.rst`` — package contract.
- WS4 ``docs/reference/carbon`` — consumer runtime and account list.
- WS4 ``docs/howto/run-carbon`` — task walkthrough.
- `fresh-yan <https://github.com/UBC-FRESH/fresh-yan>`_ — corrected accounting, curve
  generation, HWP grid, and records.
- `yan-yancun-masc-thesis-paper <https://github.com/UBC-FRESH/yan-yancun-masc-thesis-paper>`_
  — manuscript method and evidence.
