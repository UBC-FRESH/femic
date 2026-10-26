# Chapman Creek flood pilot — data audit

Date: 2026-10-26
Status: P118.1 audit; no flood model or response surface run.
Parent issue: #383
Branch: `feature/p118-flood-pilot`

## Candidate

**Chapman Creek**, Sunshine Coast, BC. The creek supplies the Chapman water
system and is the strongest bounded pilot candidate for the coastal
rain/rain-on-snow regime.

This is a **Sunshine Coast pilot**. It is not a GNN North Island result.

## Pilot envelope

A broad audit bbox in BC Albers was used to test LidarBC coverage:

- `1155000, 488000, 1180000, 507000` (EPSG:3005).
- Approximate Chapman Creek gauge location: `1165959, 498894`.
- The final domain must use the FWA watershed polygon, not this bbox.

## LiDAR coverage

A LidarBC discovery run for the broad bbox returned:

- **397 tiles**
- **90 DEM** tiles
- **84 DSM** tiles
- **223 point-cloud** tiles
- acquisition year **2024**
- 1 m DEM/DSM products
- warning: no DSM layer 2 tile intersects the broad bbox

The discovery manifest is local at
`/tmp/opencode/chapman_lidar_selection.json`; it is not committed. The final
selection must be clipped to the FWA watershed and reviewed for tile
completeness and vertical datum.

Source: https://lidar.gov.bc.ca/pages/download-discovery

## WSC and SCRD gauge record

Historical Water Survey of Canada stations:

| Station | Name | Period | Drainage area | Notes |
| --- | --- | --- | ---: | --- |
| 08GA046 | Chapman Creek near Wilson Creek | 1962–1970 | 71.5 km² | historical |
| 08GA060 | Chapman Creek above Sechelt diversion | 1971–1988 | 64.5 km² | historical |
| 08GA078 | Chapman Creek below Sechelt diversion | 1993–2003 | 64.5 km² | historical |

Sources:

- https://wateroffice.ec.gc.ca/station_metadata/reference_index_e.html?stnNum=08GA056
- https://wateroffice.ec.gc.ca/report/data_availability_e.html?parameter_type=Flow&station=08GA078&type=historical
- UBC Chapman Creek discharge summary:
  https://blogs.ubc.ca/mstaats8/methods-2/data-collection

The public WSC record is **discontinuous** and ends in 2003. The SCRD currently
monitors Chapman Creek and Soames Creek for water-system operations; the current
data are not a confirmed public daily series. The pilot cannot treat the
historical WSC record as a continuous 2021 baseline.

Evidence that current monitoring is a critical operational input:

- SCRD RFP 2637007, Calibration Services for Hydrometric Stations (2026):
  https://scrd.ca/wp-content/uploads/2026/05/2637007-RFP-Calibration-Services-for-Hydrometric-Stations.pdf
- The RFP states the monitoring network supports systems serving about 32,000
  residents, with the Chapman system supplying up to 90% of the Regional
  District water.

## Receptor and flood evidence

Receptor: the **Chapman Creek water intake / Chapman water system**. Public
sources describe the Chapman system as supplying roughly 22,000–32,000 residents
and about 76% of the Sunshine Coast population.

Flood evidence:

- November 2021 atmospheric river caused highway, road, culvert, and creek
  damage on the Sunshine Coast, including Chapman Creek and nearby Clack
  Creek/Day Road.
- The Chapman water intake had to be cleared repeatedly during the event.
- BC Highway Flood Recovery — Sunshine Coast:
  https://www2.gov.bc.ca/gov/content/transportation-projects/bc-highway-flood-recovery/2021-flood-road-recovery-projects-sunshine-coast
- Coast Reporter, one year after the atmospheric river:
  https://www.coastreporter.net/local-news/one-year-later-atmospheric-river-repairs-still-under-way-on-the-coast-6107658

This is event evidence, not a quantified flood-frequency record or a damage
curve.

## Required domain layers

Draft `femic.hydrology.domain.v1` layers:

- `watershed`: FWA watershed polygon for Chapman Creek.
- `stream`: FWA stream network, reviewed for positional quality.
- `road`: DRA/FTEN or reviewed road network, including crossings and culverts
  where available.
- `dem`: LidarBC DEM at native 1 m resolution.
- `receptor`: Chapman intake / water-system infrastructure and downstream
  community receptor.
- `gauge`: WSC historical stations and the current SCRD monitoring record, if
  shareable.
- optional `land_cover`, `soil`, `climate`, and `hru` layers.

The final domain must record CRS, resolution, licence, checksum, source, and
provenance. No private or Indigenous data may be committed without governance.

## Missing data

- A continuous current public gauge series, or a governed SCRD series.
- Exact FWA watershed/stream and DRA road layers with licence/provenance.
- Culvert and road-crossing inventory.
- Flood extent/depth observations for November 2021 or later events.
- Receptor capacity/damage curve or a documented screening alternative.
- Hydrologist review of the model card/response surface.
- A reviewed WS4 block/fragment → FEMIC watershed/receptor crosswalk.

## Decision

Do **not** build a response surface, run a WS4 flood screen, or claim a
regulatory flood result from this audit. The next step is to acquire the FWA,
DRA, receptor, and gauge layers and review the domain with a hydrologist.

The P114 producer and WS4 P57 consumer are merged; the missing piece is the
pilot data and review, not more model code.

## P118.2 tail remediation

The P114.9 validation finding was addressed before any pilot response surface:
the stationary GEV now uses a shape-bounded fallback when the unconstrained MLE
falls outside `[-0.5, 0.5]`, records `fit_strategy`, and warns. The Squamish
validation GEV is usable again under the same tail screen, with LP3 retained as
a comparison.

This does not remove the Chapman data gaps. The pilot still needs the public
FWA/DRA/receptor/gauge layers, a reviewed crosswalk, and hydrologist review.

## P118.3 public-layer acquisition

The acquisition script `scripts/acquire_chapman_public.py` writes bulk public
GeoJSON to the ignored `runtime/p118_chapman/` directory and records provenance
there. No bulk public data is tracked.

Real acquisition on 2026-10-26:

| Layer | Features | Bytes | CRS | BBOX (EPSG:3005) |
| --- | ---: | ---: | --- | --- |
| FWA watersheds (`900-127577%`) | 288 | 1,677,590 | EPSG:3005 | 1164341.6, 494054.6, 1176347.2, 513103.7 |
| FWA streams | 24 | 269,441 | EPSG:3005 | 1163230.3, 493177.2, 1171265.6, 501297.7 |
| DRA roads | 492 | 741,287 | EPSG:3005 | 1162907.8, 492863.4, 1171239.9, 501087.5 |
| WSC gauges | 3 | 1,334 | EPSG:4326 | -123.7206, 49.4419, -123.7108, 49.4822 |

The watershed code-prefix union is **6,917.1 ha**. The WSC station metadata
reports **6,902.0 ha** for 08GA046 (near Wilson Creek), **6,306.0 ha** for
08GA060 (above the Sechelt diversion), and **6,258.0 ha** for 08GA078 (below the
diversion). The union is therefore **0.2% larger** than the 08GA046 drainage
area; the smaller upstream/diversion stations are consistent with the diversion
and must not be treated as the same catchment. The local watershed polygon is
not the catchment.

The DRA layer contains road sections, not a culvert or road-stream crossing
inventory. The WSC stations are historical and discontinuous. The DEM, receptor,
current public gauge series, culvert inventory, reviewed crosswalk, and
hydrologist review remain gaps.

Reproduce:

```shell
python scripts/acquire_chapman_public.py \
  --output-root runtime/p118_chapman --timeout 120
```

Offline tests mock the HTTP responses; the public run above is the provenance
evidence.


## P118.4 watershed and LidarBC audit

The domain-audit script `scripts/audit_chapman_domain.py` unions the 288 FWA
polygons and intersects them with the local LidarBC selection. Real audit:

| Product | Tiles | Covered ha | Uncovered ha | Years | Vertical datum missing |
| --- | ---: | ---: | ---: | --- | ---: |
| DEM | 90 | 6,790.5 | 126.6 | 2019, 2020, 2024 | 90 |
| DSM | 84 | 6,672.8 | 244.3 | 2020, 2024 | 84 |
| Point cloud | 223 | 3,751.7 | 3,165.4 | 2019, 2020, 2024 | 0 |

The union is valid, 6,917.1 ha, and matches 08GA046 within 0.2%. DEM coverage
leaves about 126.6 ha (1.8%) uncovered, and every selected DEM/DSM tile lacks a
recorded vertical datum. All selected tiles use UTM zone 10; a domain DEM mosaic
must record the native projection and the vertical-datum decision.

The receptor, current public gauge, culvert inventory, hydrologist review, and
reviewed WS4 crosswalk remain gaps. No flood model or screen was run.

## P118.5 domain assembly decisions

The machine-readable plan is `planning/chapman_domain_plan.json`. It is marked
**blocked**, not ready.

- **Proposed CRS:** EPSG:32610 (UTM zone 10N), because every selected LidarBC
  DEM/DSM tile is native 1 m UTM10. FWA/DRA/WSC vectors would be reprojected
  from EPSG:3005/EPSG:4326 with a documented transformation. Using EPSG:3005
  instead would require resampling the DEM. This is proposed, pending
  geospatial review.
- **Vertical datum:** unresolved. Every selected DEM/DSM tile has
  `vertical_datum=null`. The domain is blocked until LidarBC metadata or a
  reviewed local control check resolves it.
- **Watershed:** dissolve the 288 FWA parts into one polygon. The 6,917.1 ha
  union matches 08GA046 (6,902 ha) within 0.2%; the ~861 ha local polygon is not
  the catchment. 08GA060/08GA078 are smaller diversion stations.
- **DEM:** 90 tiles cover 6,790.5 ha with a 126.6 ha edge gap. Do not download
  or mosaic until the vertical-datum decision is resolved.
- **Receptor:** missing. Candidate is the Chapman Creek water-system intake/WTP;
  a reviewed point/geometry and capacity or damage assumption are required.
- **Crosswalk:** missing. Required fields are one of `fragment_id`/`block_id`,
  plus `unit_id`, `watershed_id`, `receptor_id`, `source`, and `review_status`.
  No watershed inference from block centroids.

Other blockers: no current public/govened gauge series, no culvert inventory, no
hydrologist review, and no reviewed WS4 crosswalk. No flood model or claim was
produced.
