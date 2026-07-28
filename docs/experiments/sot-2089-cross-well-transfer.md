# SOT-2089 leakage-safe cross-well transfer evaluation

## Configuration

- Data fingerprint: `c7c598e03bd10bbaf998f026a856ac84b444b76fb2df2dd0ce024b93e8f6fac4`
- Seed: `1975`
- Neighbors: `3`
- Screen: stable 12-well sample, 3 held-out wells
- Confirm: all 773 wells, literal leave-one-well-out
- Rows scored in confirm: 5,092,255

The screen and confirm commands use the same predictor and normalization. The
held-out well's TVT is read only after prediction for scoring; its well ID is
absent from every recorded training-well and source-well list.

## Results

| Method | Screen MAE / RMSE | Confirm MAE / RMSE |
| --- | ---: | ---: |
| Current champion (`TVT_input`, zero fallback) | 8022.756 / 9526.709 | 8579.426 / 9967.274 |
| Zero | 11255.337 / 11256.711 | 11503.644 / 11521.432 |
| Same-well continuity | 4.246 / 6.858 | 8.320 / 13.715 |
| Cross-well transfer | 442.430 / 529.318 | 59.543 / 124.713 |

The cross-well candidate clears the configured local threshold against the
current champion in both stages, but same-well continuity is materially better.
This issue therefore does not change the Kaggle submission or the retained
`kaggle_validated_champion`; SOT-2090 owns candidate selection and Kaggle exec
compatibility.

## Machine-readable artifacts

- `sot-2089-cross-well-screen.json` — complete screen result.
- `sot-2089-cross-well-confirm.json.gz` — complete confirm result, including
  per-well metrics, neighbor diagnostics, source counts, and match distances.

The compressed confirm artifact SHA-256 is
`7e759c66173ab1f49d5c20ef36af3ded9b11ac2e2a01ca1b26729c087d5802f1`.

## Promotion and rollback

Promotion requires confirm MAE to beat the current champion by more than
`--min-mae-improvement`, followed by Kaggle execution compatibility and actual
submission validation. If confirm does not clear the threshold, or a later gate
fails, revert candidate integration from `kaggle/kernel/submit.py` while keeping
the evaluation code, artifacts, and this reason. No submission integration was
made in SOT-2089, so there is no candidate implementation to revert.
