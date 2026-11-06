``femic.efi.biomass`` Module
============================

The :mod:`femic.efi.biomass` module loads published RSYC biomass and volume curves,
evaluates the nonlinear form, checks the age domain, and applies a declared carbon
fraction.

Use this page when you need an independently selectable biomass curve, a paired volume
curve, or an aboveground-biomass carbon conversion.

Start Here If...
----------------

Use this page first if you are trying to:

- load a ``femic.efi.biomass_curve.v1`` document;
- select a species/ecodistrict curve;
- evaluate aboveground biomass, volume, or carbon at a stand age; or
- verify that a carbon fraction and its source travel with the curve.

Typical Usage
-------------

.. code-block:: python

   from femic.efi.biomass import load_biomass_curves

   family = load_biomass_curves("config/efi/biomass/rsyc_cariboo_pilot.json")
   curve = family.select_one(species="PSEU.MEN")
   print(curve.agb_t_ha(50))
   print(curve.volume_m3_ha(50))
   print(curve.carbon_t_c_ha(50))

Key Entry Surfaces
------------------

- :func:`load_biomass_curves`
  Load and validate a curve family.
- :class:`BiomassCurveFamily`
  Select curves by species, region, or ecodistrict.
- :class:`BiomassCurve`
  One curve with ``agb_t_ha``, ``volume_m3_ha``, and ``carbon_t_c_ha``.
- :class:`RSYCCurve`
  The published equation parameters and response unit.

Cross-References
----------------

- :doc:`../contracts/efi-biomass-curve`
- :doc:`femic-efi-application`
- :doc:`../contracts/index`

.. automodule:: femic.efi.biomass
   :members:
   :show-inheritance:
