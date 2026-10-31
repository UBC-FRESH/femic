# Nonlinear regional volume candidate

Experimental polynomial volume model on log `Lhmean` and log `CC2m`.

Terms:

```text
log(volume) = b0 + b1*log(Lhmean) + b2*log(CC2m)
              + b3*log(Lhmean)^2 + b4*log(CC2m)^2
              + b5*log(Lhmean)*log(CC2m)
```

This is not a standard `femic.inventory.als.model.v1` card because FEMIC's model
reader supports only linear predictors.  It is packaged as an experimental
specification with `volume_poly2.json` and the application script.

Results:

- external TSA 23 holdout RMSE 42.09 m3/ha
- cross-region leave-one-TSA-out average RMSE ~35.5 m3/ha
- full-grid volume cells 4,745,557; mean 170.84 m3/ha
- coverage/status unchanged from the linear regional bundle

Use it as an experimental candidate, not a published card.
