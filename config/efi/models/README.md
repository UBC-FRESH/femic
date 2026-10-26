# Published EFI model cards

These cards are metadata records for two published ALS-derived inventory
models. They are not FEMIC-trained models, and they do not carry the authors'
model objects or coefficients.

| Card | Attribute | Region | Species | Validation |
| --- | --- | --- | --- | --- |
| `als_loreys_height_cwh_2015.json` | Lorey's mean height | CWH, northern Vancouver Island, BC | Cw, Hw, Hm | RMSE 2.88 m; bias 0.05 m; 140 plots; 10-fold CV repeated 5 times |
| `als_site_index_loblolly_seus_2019.json` | Site index | Southeastern USA | Loblolly pine (*Pinus taeda*) | RMSE 3.8 m; bias -0.28 m; 75 FIA plots; base age 25 |

## Sources

- White, J.C., Tompalski, P., Coops, N.C., et al. (2015). Comparing ALS and
  image-based point cloud metrics and modelled forest inventory attributes in
  a complex coastal forest environment. *Forests*, 6(10), 3704-3732.
  https://doi.org/10.3390/f6103704. Open access under CC BY 4.0.
- Gopalakrishnan, R., Kauffman, J.S., Fagan, M.E., et al. (2019). Creating
  landscape-scale site index maps for the southeastern US is possible with
  airborne LiDAR and Landsat imagery. *Forests*, 10(3), 234.
  https://doi.org/10.3390/f10030234. Open access under CC BY 4.0.

## How to use these cards

The cards record the target, predictors, training region/species, validation
design and accuracy, applicability domain, and licence. FEMIC's
`annotate_attribute_table` helper can attach this metadata to an attribute
table. A consumer should reject or flag rows whose region, species, age, or
height falls outside the card's applicability domain.

These are not validation certificates for a FEMIC instance. They are published
claims, dated to their source. Do not apply a card outside its stated domain,
and do not treat its accuracy as a local accuracy estimate.

The cards are metadata-only because the published models are Random Forests or
a height-plus-Landsat workflow, not the linear form accepted by
`femic.efi.coefficients.v1`. Do not invent linear coefficients to force them
through the application engine.
