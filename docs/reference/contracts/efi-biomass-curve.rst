EFI Biomass Curve (``femic.efi.biomass_curve.v1``)
==================================================

Purpose
-------

This contract carries published remote-sensing biomass yield curves and a declared carbon
fraction. It is a data and evaluation layer, not a new model fit and not a carbon inventory.

The pilot uses the national RSYC curves from Tompalski et al. (2025), derived from Landsat
time series, forest age, species composition, and aboveground biomass. The curve parameters
are published numeric values; no R package code is copied. The RSYC R package is GPL-3; the
paper is CC BY 4.0.

Equation
--------

For stand age ``age``:

``AGB = b1 * exp(-b4 * age) * (1 - exp(-b2 * age)) ** b3``

where:

- ``AGB`` is aboveground dry biomass in ``t_ha``;
- ``b1``, ``b2``, ``b3``, ``b4`` are published curve parameters;
- ``age`` is stand age in years.

The optional volume curve uses the same form and is kept in ``m3_ha``. Biomass and volume
are **not** additive; they are separate response families.

Carbon conversion
-----------------

Carbon is:

``carbon_t_c_ha = AGB_t_ha * carbon_fraction``

``carbon_fraction`` is mandatory in the curve record, and ``carbon_fraction_source`` must
name its source. The pilot uses **0.47**, from IPCC (2006) Guidelines for National
Greenhouse Gas Inventories, Vol. 4, Ch. 4, Table 4.3.

Boundary: this is aboveground live biomass carbon only. It excludes belowground biomass,
dead wood, litter, soil carbon, and harvested-product pools. It is not a CBM or WS4 carbon
inventory.

Document
--------

.. code-block:: json

   {
     "schema_version": "femic.efi.biomass_curve.v1",
     "source_id": "tompalski-et-al-2025-rsyc-national",
     "source_url": "https://doi.org/10.1093/forestry/cpaf067",
     "licence_id": "CC-BY-4.0",
     "curves": [
       {
         "curve_id": "rsyc-pseu-men-cariboo-basin",
         "species": "PSEU.MEN",
         "region": "Montane Cordillera",
         "ecodistrict": "Cariboo Basin",
         "age_min": 1,
         "age_max": 300,
         "carbon_fraction": 0.47,
         "carbon_fraction_source": "IPCC 2006 Guidelines, Vol. 4, Ch. 4, Table 4.3",
         "agb": {
           "model_id": "rsyc_agb_regional_ecodistrict_pseu_men_...",
           "model_version": "2025.1",
           "response": "agb",
           "unit": "t_ha",
           "b1": 135.742,
           "b2": 0.035627,
           "b3": 1.200684,
           "b4": 0.001018
         },
         "volume": {
           "model_id": "rsyc_volume_regional_ecodistrict_pseu_men_...",
           "model_version": "2025.1",
           "response": "volume",
           "unit": "m3_ha",
           "b1": 299.0254,
           "b2": 0.036353,
           "b3": 1.281213,
           "b4": 0.001238
         }
       }
     ]
   }

Pilot file
----------

``config/efi/biomass/rsyc_cariboo_pilot.json`` contains two published curves for the
Cariboo Basin ecodistrict:

- Douglas-fir (``PSEU.MEN``);
- lodgepole pine (``PINU.CON``).

Both have a paired RSYC volume curve for comparison. The age domain is 1–300 years.

CLI
---

.. code-block:: bash

   femic efi biomass-curve config/efi/biomass/rsyc_cariboo_pilot.json \
     --species PSEU.MEN --age 50 --json

Output includes ``agb_t_ha``, ``volume_m3_ha``, ``carbon_t_c_ha``, the carbon fraction and
source, and the published source/licence.

Comparison at the pilot ages
----------------------------

.. list-table::
   :header-rows: 1
   :widths: 18 10 14 14 14

   * - Species
     - Age
     - AGB t/ha
     - Volume m3/ha
     - Carbon tC/ha
   * - PSEU.MEN
     - 20
     - 59.2
     - 125.2
     - 27.8
   * - PSEU.MEN
     - 50
     - 103.4
     - 224.0
     - 48.6
   * - PSEU.MEN
     - 100
     - 118.4
     - 255.3
     - 55.7
   * - PINU.CON
     - 20
     - 43.8
     - 87.5
     - 20.6
   * - PINU.CON
     - 50
     - 70.8
     - 146.9
     - 33.3
   * - PINU.CON
     - 100
     - 81.6
     - 170.4
     - 38.4

The ratio is not a conversion factor; it is a comparison of two independently fitted
response curves with different units.

Limits
------

- The pilot is one ecodistrict and two species; it is not a BC-wide biomass map.
- RSYC curves are published regional/national models, not local FEMIC validation.
- The curve may decline at old ages; do not impose monotonicity beyond the source relationship.
- The carbon fraction is a declared planning value, not a species-specific measurement.
- Do not sum biomass and volume into the same account.
- This does not modify the P115 carbon package or CBM runtime.

Sources
-------

- Tompalski, P., Hermosilla, T., Baral, S.K., Wulder, M.A., White, J.C. (2025).
  National remote sensing-derived aboveground biomass yield curves for Canada.
  *Forestry: An International Journal of Forest Research*.
  https://doi.org/10.1093/forestry/cpaf067
- Tompalski, P., Wulder, M.A., White, J.C., Hermosilla, T., Riofrío, J., Kurz, W.A. (2024).
  Developing aboveground biomass yield curves for dominant boreal tree species from time
  series remote sensing data. *Forest Ecology and Management* 561, 121894.
  https://doi.org/10.1016/j.foreco.2024.121894
- IPCC (2006). Guidelines for National Greenhouse Gas Inventories, Vol. 4, Ch. 4,
  Table 4.3.

Cross-References
----------------

- :doc:`efi-model-card`
- :doc:`efi-application`
- :doc:`../api/femic-efi-biomass`
- :doc:`index`
