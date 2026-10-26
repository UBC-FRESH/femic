Fertilization Response and Emissions Audit
==========================================

FEMIC exposes the public fertilization response and the thesis emissions factors as
first-class carbon-lane functions. No proprietary input data is required.

Public response data
--------------------

``config/carbon/tipsy/FertRespMOF.txt`` is the BC TIPSY MOF default fertilization
response table. It provides percent total-volume gain by species, site index, and
fertilization age for FDC, SS, SW, PLI, and FDI. FEMIC parses the table and applies the
default 80% effectiveness over a 10-year response.

The response is applied to an existing yield curve with
``femic.carbon.fertilized_curve``: the curve is unchanged before the response age and
then ramps to the tabulated percent gain over 10 years. This is the producer-side curve
transform; it does not require a private TIPSY curve file.

Emissions audit
---------------

``config/carbon/fertilization.bc.yaml`` records the public thesis assumptions:

- dose: **200 kg N/ha**
- response: **10 years**, **80% effectiveness**
- factors per fertilized hectare per action: CO2 **17.13779467 kg**, CH4
  **0.055734646 kg**
- N2O: **20.00206748 kg** for one application, **40.00206748** for two,
  **60.00206748** for three
- audit GWP100: CH4 **27.9**, N2O **273.0**

The thesis uses a dynamic LCA for CH4/N2O. The audit uses fixed IPCC AR6 GWP100 values
so the result is reproducible and comparable; it does not claim to reproduce the
dynamic LCA.

Run the audit on a compiled dataset and a schedule:

.. code-block:: bash

   femic carbon fertilization-audit \
     --dataset output/ws4/tsa24/compiled \
     --schedule schedules/fertilization.csv \
     --fertilization-config config/carbon/fertilization.bc.yaml \
     --out output/carbon/fertilization-audit

The schedule uses ``block_id,treatment,offset`` with treatments ``f1``, ``f2``, and
``f3``. The output is ``fertilization_accounts.csv`` with:

- ``fertilization.area_ha``
- ``fertilization.dose_kg_n``
- ``fertilization.co2_t``
- ``fertilization.ch4_t``
- ``fertilization.n2o_t``
- ``fertilization.co2e_t``

and ``fertilization_manifest.json``.

Current boundary
----------------

The audit is producer-side: it does not alter the libcbm pool accounts, the block
ledger, or the optimizer objective. Wiring the public TIPSY response into the compiled
dataset/optimizer is a separate runtime task; the response curve and emissions factors
are already materialized and tested.

References
----------

- BC TIPSY ``FertRespMOF.txt`` (public response table; copied from the archived FEMIC
  BTC install).
- Jinming Ke MSc thesis code: https://github.com/UBC-FRESH/msc_jimmy_ke
