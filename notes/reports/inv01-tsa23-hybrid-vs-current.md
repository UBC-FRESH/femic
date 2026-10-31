# INV-01 hybrid versus current TSA 23 inventory

## Surface comparison

| Attribute | Current cells | Hybrid cells | Current mean | Hybrid mean |
| --- | ---: | ---: | ---: | ---: |
| Height | 6,573,196 | 6,573,196 | 16.09 m | 16.09 m |
| BA | 2,942,755 | 7,479,672 | 23.87 m2/ha | 23.83 m2/ha |
| Volume | 2,942,755 | 4,745,557 | 139.33 m3/ha | 170.84 m3/ha |

Joint BA/volume coverage rises from **1,839 km2 (14.9%)** to **2,913 km2
(23.6%)**.

## Overlap differences

For cells present in both surfaces:

| Attribute | Common cells | Mean difference | MAE | RMSE | Range |
| --- | ---: | ---: | ---: | ---: | --- |
| BA | 2,909,489 | -1.24 m2/ha | 3.75 | 4.66 | -15.65 to +8.29 |
| Volume | 2,942,755 | -1.20 m3/ha | 9.74 | 12.45 | -48.82 to +20.60 |

New hybrid-only cells:

- BA: 4,570,183 cells, mean 24.55 m2/ha
- Volume: 1,802,802 cells, mean 224.24 m3/ha

There are 33,266 current BA cells not covered by the hybrid candidate; their
mean is 17.35 m2/ha.  The volume candidate covers every current volume cell.

## Decision

The hybrid bundle is now the **default experimental inventory root** for the
TSA 23 instance:

```text
config/inventory/experimental.yaml
config/inventory/models/experimental/
```

It materially expands BA/volume coverage and produces a higher mean volume on
the newly covered high-biomass cells.  It does **not** replace the published
cards or become an operational inventory: the external check is four clustered
plots and cross-region volume RMSE remains 16-67 m3/ha.

Height remains on the current card.  The published TSA 23 cards remain
unchanged.
