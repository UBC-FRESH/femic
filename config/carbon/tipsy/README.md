# TIPSY fertilization response tables

`FertRespMOF.txt` is the public BC TIPSY MOF default fertilization response table
(percent total-volume gain by species, site index, and fertilization age, with the
default 80% effectiveness over 10 years). It was copied from the archived FEMIC BTC
install; the source is the BC TIPSY distribution.

SHA-256: `2e579683fc933d8cab79b44a4e477349d743d9e8dd8432c20a0064157fb741cf`

FEMIC parses it in `femic.carbon.load_tipsy_fertilization_response` and applies it with
`femic.carbon.fertilized_curve`. It is a public input, not a private curve artifact.
