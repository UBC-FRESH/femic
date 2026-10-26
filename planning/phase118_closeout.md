# P118 close-out: Chapman Creek flood pilot

Date: 2026-10-26
Status: **closed — data-blocked**
Parent issue: #383
Branch: `feature/p118-flood-pilot`

## Outcome

P118 completed the public-data audit, public-layer acquisition, DEM metadata and
mosaic work, FEMIC-native terrain/stream audit, and historical WSC gauge
backcast. It did **not** produce a current flood-frequency baseline, a flood
response surface, or a regulatory flood map.

## Delivered

- P118.1 Chapman public-data audit and pilot-domain plan.
- P118.2 bounded-shape GEV tail fallback and fit-strategy metadata (producer
  hardening; merged `70fb82a`).
- P118.3 public FWA watershed/stream, DRA road, and WSC gauge acquisition with
  provenance and checksums.
- P118.4 watershed-union and LidarBC coverage audit.
- P118.5 domain assembly plan and blocked-decision record.
- P118.6 LidarBC DEM compound-CRS audit and receptor candidate record.
- P118.7 clipped native 1 m DEM mosaic and coverage manifest.
- P118.8 domain defensibility decision.
- P118.9 FEMIC-native terrain/stream audit.
- P118.10 historical WSC gauge-frequency backcast and record decision.

## Quantitative evidence

- Watershed union: 288 FWA parts, 6,917.1 ha; matches WSC 08GA046 within 0.2%.
- DEM mosaic: 4,985.9 ha valid inside the watershed; 1,931.2 ha unfilled gap.
- Vertical coverage: 1,621.6 ha CGVD2013-known (32.5%); 3,347.5 ha covered only
  by 2D tiles with unknown vertical datum (67.1%).
- Mixed-mosaic terrain: slope max 45,466.8%; not usable.
- CGVD2013-only subset: 1,620.6 ha, slope max 838.8%, mean 31.31%.
- D8 stream candidates: 21.17 ha at threshold 500; FWA overlap Jaccard 0.00046.
- Historical gauge 100-year GEV/LP3:
  - 08GA046: 445.7/336.0 m3/s (11 values, constrained GEV);
  - 08GA060: 106.1/105.6 m3/s (18 values);
  - 08GA078: 93.6/95.7 m3/s (11 values).
- Records are sequential, overlap only in 1970, gap 1988–1992, and end in 2003.

## What is not claimed

- No current flood-frequency baseline.
- No pooled three-station record.
- No flood map, design flood, or regulatory determination.
- No WS4/FHOPS flood screen using Chapman geography.

## Unblock inputs

1. Current public or governed gauge series, or explicit acceptance of a
   historical-only frequency result.
2. Vertical metadata for the 9 older 2D DEM tiles, or a consistent CGVD2013 DEM.
3. Closure or explicit bounding of the 1,931.2 ha DEM coverage gap.
4. Reviewed Chapman intake/WTP receptor geometry and capacity/damage assumption.
5. Culvert/road-stream crossing inventory.
6. Reviewed WS4 block/fragment crosswalk.
7. Hydrologist review of the record discontinuities, diversion, and model card.

Only items that use non-public or licence-restricted data require a governance
decision. The public WSC/LidarBC/FWA/DRA work is complete and does not.

## Recommendation

Close P118 as data-blocked. The next engineering work should be WS4/FHOPS
consumer integration against the existing pinned response-bundle contracts, or
a new pilot watershed with a continuous public gauge and reviewed receptor. Do
not build a flood model from the current Chapman DEM.

No flood model or regulatory claim was produced.
