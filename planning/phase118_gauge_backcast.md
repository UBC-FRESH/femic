# P118.10 Chapman WSC gauge backcast

Date: 2026-10-26
Status: historical gauge-frequency only; **not a current flood baseline**
Parent issue: #383

## Data

Public Water Survey of Canada annual maximum daily discharge:

| Station | Period | Values | Drainage area | Estimated maxima |
| --- | --- | ---: | ---: | ---: |
| 08GA046 | 1960–1970 | 11 | 69.02 km² | 3 |
| 08GA060 | 1970–1987 | 18 | 63.06 km² | 3 |
| 08GA078 | 1993–2003 | 11 | 62.58 km² | 4 |

Records are sequential, not overlapping, except for 1970, which appears in both
08GA046 and 08GA060. Gaps: 1988–1992 and 2004–present. 08GA060 is above the
Sechelt diversion; 08GA078 is below it. The three stations are not one
continuous series.

## Fits

Bounded-shape GEV and LP3, 100 bootstrap samples:

| Station | GEV 100-year | LP3 100-year | GEV strategy |
| --- | ---: | ---: | --- |
| 08GA046 | 445.7 m³/s | 336.0 m³/s | constrained |
| 08GA060 | 106.1 m³/s | 105.6 m³/s | mle |
| 08GA078 | 93.6 m³/s | 95.7 m³/s | mle |

Observed maxima were 193.0, 91.6, and 70.5 m³/s respectively. All three fits
have at least 11 annual maxima but fewer than 30; tail estimates are fragile.
No split-sample stability check was possible because each record is shorter
than 20 values after the early/late split requirement.

## Decision

**Status: `historical_gauge_frequency_only`.**

Defensible for:
- historical single-station GEV/LP3 screening;
- method development and record-length sensitivity.

Not defensible for:
- a current flood-frequency baseline;
- pooling the three stations without diversion/nonstationarity review;
- a regulatory flood map or design flood.

A current/govened gauge series, diversion review, and hydrologist review are
required before operational use. The DEM/receptor path remains separately
data-blocked.

No flood map or regulatory claim was produced.
