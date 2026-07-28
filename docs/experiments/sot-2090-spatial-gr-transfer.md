# SOT-2090 spatial/GR cross-well TVT transfer selection

## Decision

`sot_2089_spatial_md_nearest` is the single local promotion candidate. It
remains substantially better than the retained Kaggle champion under the fixed
SOT-2089 split, while the three new weighted/local variants were rejected at
screen. The Kaggle-validated `tvt_input` champion remains active until the
separate execution/submission gate in SOT-2091 succeeds.

## Fixed evaluation contract

- Seed: `1975`
- Data fingerprint:
  `c7c598e03bd10bbaf998f026a856ac84b444b76fb2df2dd0ce024b93e8f6fac4`
- Screen: the fixed 12-well subset from SOT-2089
- Confirm: literal leave-one-well-out over all 773 wells
- Promotion gates: positive MAE improvement, no well regression over 25%,
  finite outputs for every row, and runtime below 7,200 seconds

## Screen

| Candidate | MAE | RMSE | Fallback rate | Decision |
| --- | ---: | ---: | ---: | --- |
| `sot_2089_spatial_md_nearest` | 442.430 | 529.318 | 0.000 | confirm |
| `spatial_gr_weighted` | 2302.971 | 4782.704 | 0.179 | reject |
| `spatial_z_md_local` | 2299.540 | 4782.404 | 0.179 | reject |
| `gr_local` | 2377.324 | 4794.558 | 0.179 | reject |

Only the lowest-MAE screen candidate proceeded to confirm.

## Confirm

- Candidate MAE / RMSE: `59.543084 / 124.713394`
- Current champion MAE / RMSE: `8579.426386 / 9967.274248`
- MAE improvement: `8519.883302`
- Scored rows: `5,092,255`
- Finite output: `100%`
- Fallback rate: `0%`
- Wells worse than the current champion: `0`
- Runtime: `141.23s`

All local promotion thresholds passed. `reports/champion.json` records the
candidate and its remaining `exec_compatibility` and `kaggle_validation`
requirements without replacing the current Kaggle-validated champion early.

The complete machine-readable screen ranking, configurations, fixed split,
thresholds, confirm metrics, and decision are in
`sot-2090-spatial-gr-transfer.json` (SHA-256
`d92d4869e92d5672187b8ee66de056785595d471dd98b958bb0d3f0e532ed9d8`).
