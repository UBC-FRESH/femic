# P79.6 TFL 6 LidarBC Pilot

Phase: P79.6 / `#217`
Status: complete
Parent: P79 / `#211`
Branch: `feature/p79-lidar-pipeline`
Instance context: `external/femic-tfl6-instance`

## Purpose

Pilot the package-level LidarBC terrain workflow against a bounded TFL 6 use
case and record whether it can support TFL 6-style steep-slope review and
stream-evidence screening. This is a pilot, not a TFL 6 model-input promotion.

## Bounded AOI

- AOI: `881700,627500,882700,628500` in EPSG:3005.
- Area: 100 ha (1 km x 1 km).
- AOI is fully inside:
  - the TFL 6 boundary;
  - LidarBC 1:2,500 DEM tiles `lidarbc:5:76205` and `lidarbc:5:77294`;
  - public CDED tile `092l12_e` used by the TFL 6 Phase 9D lane.
- The AOI contains forested VRI polygon `23339458`, so it is land rather than
  the coastal/ocean AOI rejected during the first pilot attempt.

## Commands Run

```bash
femic lidar discover \
  --bbox 881700,627500,882700,628500 \
  --product dem \
  --instance-root external/femic-tfl6-instance \
  --manifest-path runtime/dem/p79_6_lidarbc_pilot/selection.json

femic lidar materialize \
  --selection-manifest external/femic-tfl6-instance/runtime/dem/p79_6_lidarbc_pilot/selection.json \
  --instance-root external/femic-tfl6-instance \
  --output-root runtime/dem/p79_6_lidarbc_pilot/data
```

Analysis used the package APIs directly:

- LidarBC and CDED DEMs were mosaicked/reprojected to the same EPSG:3005 AOI
  grid (1 m LidarBC, 25 m CDED).
- Percent slope was derived with `femic.lidar.terrain.derive_slope_percent`.
- Stream candidates were derived with
  `femic.lidar.hydrography.derive_stream_candidates` and compared with the
  TFL 6-clipped FWA stream network.

## Results

Metrics: `planning/phase79_p79_6_tfl6_pilot_metrics.json`,
`planning/phase79_p79_6_tfl6_slope_thresholds.csv`, and
`planning/phase79_p79_6_tfl6_stream_thresholds.csv`.

### Discovery and materialization

- Discovery returned 3 DEM tiles for the 1 km AOI: two 1:2,500 layer-5 tiles and
  one larger 1:20,000 layer-6 tile.
- Materialization verified 3/3 tiles, 60.0 MiB total, in 7.18 s.
- Peak resident memory observed during materialization: about 187 MB.
- Reprojecting the layer-6 tile to the 1:2,500 comparison grid would add no
  useful detail; the pilot used the layer-5 tiles only.

### Steep-slope comparison

| Metric | LidarBC 1 m | CDED 25 m comparison grid |
| --- | ---: | ---: |
| Mean slope | 23.95% | 15.77% |
| Median slope | 19.46% | 15.03% |
| P90 slope | 41.98% | 24.76% |
| Max slope | 681.39% | 36.16% |
| Pixels >= 60% | 3.95% | 0.00% |
| Pixels >= 70% | 2.88% | 0.00% |
| Pixels >= 80% | 2.29% | 0.00% |
| Pixels >= 90% | 1.89% | 0.00% |
| Steep >= 70% area | 2.88 ha | 0.00 ha |

LidarBC raises the median slope by 4.43 percentage points and the mean by 8.19
percentage points relative to CDED over the same AOI. The LidarBC surface
contains 2.88 ha of >=70% slope that the coarse CDED surface does not resolve.

The TFL 6 Phase 9D AOI-level rule (`>=75%` of valid pixels at `>=70%` slope)
does not trigger on either surface at this AOI. This does not invalidate the
TFL 6 Step 220 proxy: the accepted rule is applied per fragment, not to a 1 km
AOI. It does show that LidarBC and CDED produce materially different steep-area
evidence and that a fragment-level rerun is required before changing Step 220.

### Stream-candidate comparison

FWA reference area in the AOI was 0.10 ha. Candidate performance was poor:

| Accumulation threshold | Candidate area | Precision | Recall | F1 |
| ---: | ---: | ---: | ---: | ---: |
| 5,000 | 1.18 ha | 0.25% | 3.00% | 0.47% |
| 20,000 | 0.52 ha | 0.52% | 2.70% | 0.87% |
| 50,000 | 0.33 ha | 0.78% | 2.60% | 1.20% |
| 100,000 | 0.19 ha | 0.70% | 1.30% | 0.91% |

The workflow runs and emits the full review manifest/caveat report, but the D8
candidates do not align with FWA at this AOI. They are not ready for TFL 6
riparian or stream-evidence use without additional review and method work.

### Storage and runtime

- Materialized tiles: 61 MiB on disk; 60.0 MiB reported by the manifest.
- Layer-5 tiles only: 13.5 MiB.
- Processed AOI DEM/slope GeoTIFFs: 6.6 MiB.
- Stream-candidate output bundle: about 1.1 MiB.
- Pilot analysis script: 63.3 s including the CDED download and four stream
  threshold runs.
- Full-TFL6 DEM planning estimate: 652 selected DEM tiles x about 20 MiB/tile
  is roughly 13 GiB before point clouds. This reinforces the DataLad/Arbutus
  annex requirement and rules out a full provincial mirror.

## Findings Against TFL 6 Needs

1. **Steep-slope evidence:** LidarBC is usable and materially sharper than
   CDED. It should be evaluated at TFL 6 fragment scale before any Step 220
   rule change.
2. **Stream evidence:** the package workflow works mechanically, but the
   current D8/FWA agreement is too low for riparian evidence. Treat stream
   candidates as review-only and do not promote them.
3. **Storage:** full TFL 6 DEM coverage is a multi-GiB annex workload; bounded
   AOIs and partial materialization are required.
4. **No core assumptions:** the pilot did not add TFL 6 thresholds or paths to
   FEMIC core.

## Follow-Up List

1. TFL 6 instance: rerun LidarBC slope against Step 210 fragment geometry and
   compare fragment-level Step 220 outcomes against the locked CDED proxy.
2. TFL 6 instance: decide whether LidarBC slope should replace, supplement, or
   remain a sensitivity check for the CDED Step 220 rule.
3. FEMIC P79.7: evaluate canopy/CHM and precision products before using
   LidarBC for operability evidence.
4. Stream candidates: test larger AOIs, alternate conditioning/thresholds, and
   FWA-buffered comparison before any riparian use.
5. DataLad: annex bounded tile sets under the instance Arbutus remote; keep
   manifests and small QA artifacts in git.

## Caveats

- The AOI is a single 1 km pilot, not a TFL 6-wide sample.
- CDED was reprojected from EPSG:4269 to a 25 m EPSG:3005 comparison grid.
- The Step 220 rule was evaluated at AOI level, not fragment level.
- Stream candidates are screening-only and require field/FWA review.
- No private WFP LiDAR, DTSM, ITI, LEFI, or Patchworks terrain data was used.
