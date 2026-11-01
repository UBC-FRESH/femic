# ADR 0001: BA-only default for the INV-01 TSA 23 pilot

Status: accepted

Date: 2026-11-01

## Context

The INV-01 TSA 23 default inventory previously contained height and BA, with
volume withheld.  Independent validation on the strict 38-plot set produced:

- BA: 36 in-range plots, RMSE 8.86 m2/ha.
- Height: 19 in-range plots, RMSE 2.54 m; TSA 23 strict 6 plots, RMSE 4.18 m.
- Volume: 28 in-range plots, RMSE 67.02 m3/ha; no independent TSA 23 volume
  plot in range.

The height card's 0.688 m figure was LOOCV on 14 plots, not independent
validation.

## Decision

The default TSA 23 product contains BA only.  Height and volume remain published
cards but require an explicit card path or the research configuration.  Volume
is not an operational product.

## Consequences

- The default config is smaller and only exposes an attribute with an
  independent check.
- Users needing height or volume must opt in explicitly and accept the stated
  limitations.
- The pilot remains non-operational; the 38-plot strict set is small and TSA 23
  has only 7 independent plots.
- Future work needs more recent high-biomass validation, not another fit on the
  same population.
