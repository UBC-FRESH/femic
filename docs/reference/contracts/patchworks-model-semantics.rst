Patchworks Model Semantics
==========================

This page defines the repo-wide semantic contract for Patchworks-facing FEMIC
models.

Use it when you need the shortest correct answer to any of these questions:

- what ``managed`` / ``unmanaged`` means in Patchworks;
- what ``natural`` / ``treated`` origin means;
- how retention is allowed to change state;
- whether curve-family availability can be used as an IFM proxy; or
- what validation is required before declaring a rebuilt model sane.

Core separation of concerns
---------------------------

FEMIC keeps three concepts separate:

- IFM / treatment eligibility:
  ``managed`` or ``unmanaged``
- origin / curve provenance:
  ``natural`` or ``treated``
- retention / partial inoperability:
  an explicit area reallocation or factor, not a curve-family label

These concepts must not be collapsed into one another.

IFM contract
------------

In Patchworks, ``managed`` and ``unmanaged`` mean treatment eligibility only:

- ``managed`` area is treatment-eligible in that period;
- ``unmanaged`` area is treatment-ineligible in that period.

This is the operational meaning that matters when scheduling or applying
treatments.

Origin contract
---------------

``natural`` and ``treated`` origin describe curve provenance only:

- natural-origin area belongs on the untreated / VDYP-style curve lane;
- treated-origin area belongs on the treated / plantation / TIPSY-style curve
  lane.

Origin does not, by itself, determine whether an area is treatment-eligible.

Forbidden shortcuts
-------------------

Agents and exporters must not infer any of the following:

- ``managed = treated``
- ``unmanaged = natural``
- first-growth curve availability implies unmanaged state
- plantation-curve availability implies managed state
- ``hasfg`` or similar curve-family presence is an acceptable proxy for IFM

If a model needs both IFM and origin, publish both explicitly.

Retention contract
------------------

Retention is orthogonal to origin.

Allowed behavior:

- retention may move area from ``managed`` to ``unmanaged``;
- retention may reduce treatment-eligible area; and
- retained area keeps its existing origin unless the model explicitly changes
  it for another documented reason.

Disallowed behavior:

- retention should not silently relabel natural-origin area as treated-origin;
- retention should not silently relabel treated-origin area as natural-origin.

Validation contract
-------------------

After a Patchworks-facing rebuild, FEMIC must validate more than successful XML
generation or Matrix Builder completion.

Minimum sanity checks:

- inspect rebuilt runtime outputs that correspond to the changed contract;
- compare published species-share source tables against runtime ``indsp.*``
  feature/product outputs for representative runs; and
- explain any all-zero emitted family from source inputs rather than from
  hidden state conflation.

Signal rules:

- nonzero source share + zero runtime signal = fail
- zero source share + zero runtime signal = acceptable, but report it
- zero source share + nonzero runtime signal = fail

Related pages
-------------

- :doc:`../patchworks-export`
- :doc:`stage-boundaries-and-canonical-artifacts`
- :doc:`../../guides/vscode-coding-agent-onboarding`
