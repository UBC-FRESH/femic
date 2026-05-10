Diagnostics Interpretation Playbook
===================================

This page defines operational checks for the three key diagnostic plot families.

Strata Diagnostics (``strata-*.png``)
-------------------------------------

Healthy signals:

- Top strata capture expected cumulative area coverage.
- Relative abundance bars are non-empty and interpretable.
- SI violin/scatter distributions show plausible ecological structure.

Red flags:

- Near-empty abundance in retained strata.
- Extreme SI spikes isolated to tiny samples.
- Missing or collapsed strata labels inconsistent with run settings.

VDYP Fit Diagnostics (``vdyp_fitdiag_*.png``)
---------------------------------------------

Healthy signals:

- Smoothed curve tracks binned median trend.
- For AU-level first-growth synthesis, the default accepted direct-fit family
  is ``smoothed_bin_pchip`` rather than the older NLLS-first approach.
- SI levels show coherent ordering when signal exists.
- Tail handling avoids unrealistic late-age collapse/oscillation.

Red flags:

- Outlier-driven overfit (for example impossible young-age volumes).
- Inverted SI dominance where ecological signal should be monotonic.
- Apparent fit to sparse/noisy bins without fallback/merge behavior.
- Unexplained reversion to an older NLLS-oriented first-growth fit when the
  canonical AU-level default should be ``smoothed_bin_pchip``.

TIPSY vs VDYP Overlays (``tipsy_vdyp_*.png``)
---------------------------------------------

Healthy signals:

- Managed and untreated curves are scenario-coherent AU-by-AU.
- Relative magnitudes and timing match intended silviculture assumptions.

Red flags:

- Managed trajectories nonsensically underperforming/overshooting without
  explicit scenario rationale.
- Strong discontinuities that point to handoff parse or unit mismatch issues.

Escalation Path
---------------

1. Validate input data and stratification assumptions.
2. Validate VDYP fit settings and bin collapse behavior.
3. Validate TIPSY DAT fixed-width alignment and species/FIZ compatibility.
4. Re-run targeted units with deterministic run IDs and preserved diagnostics.
