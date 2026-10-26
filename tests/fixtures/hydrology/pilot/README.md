# P114.9 Public Gauge Pilot Fixture

This bounded fixture contains derived annual maximum daily discharge values for
three public Water Survey of Canada gauges. It is used only to exercise the
P114.9 gauge backcast and close-out reporting paths.

## Sources

- Environment and Climate Change Canada, Water Survey of Canada, Hydrometric
  Data, `hydrometric-annual-statistics` collection:
  - Carnation Creek at the Mouth (`08HB048`), coastal rain-dominated regime.
  - Coldwater River near Brookmere (`08LG048`), interior snow-transient regime.
  - Squamish River near Brackendale (`08GA022`), coastal mountain
    rain-on-snow regime.
- API: https://api.weather.gc.ca/
- Licence: Open Government Licence - Canada.
- Retrieved: 2026-10-25.

Only the annual maximum daily discharge, its date, and the source symbol are
retained. No daily series, private data, Indigenous data, or licence-restricted
data are included. Gauge metadata and API URLs are recorded in `gauges.json`.

## Known Gaps

- Missing annual maxima: Carnation Creek 2018; Coldwater River 2021; Squamish
  River 1926-1954, 1996, 2019-2020.
- Some annual maxima carry an `Estimated` or other source symbol. The backcast
  reports these symbols and treats them as a quality caveat.
- This is a gauge-frequency backcast, not a full watershed pilot. Public LiDAR,
  harvest/road disturbance ledgers, downstream receptor capacity, and process
  model inputs were not assembled in P114.9.
- The fixture is not a regulatory flood-frequency product and must not be used
  for design-flood or floodplain mapping.
