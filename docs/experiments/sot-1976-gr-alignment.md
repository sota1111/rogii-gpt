# SOT-1976 — type-well GR alignment experiment

## Decision

**Not promoted.** The fixed `TVT_input` baseline has zero error on every row
where it is populated. A bounded type-well GR alignment therefore cannot
strictly improve it. The experimental model code was reverted as required; the
versioned champion manifest remains unchanged and continues to identify
`tvt_input` as the local champion.

## Candidate fixed before evaluation

- Name: `typewell_gr_robust_shift`
- Inputs: horizontal-well `GR` and `TVT_input`; paired type-well `GR` and `TVT`
- Alignment: choose one constant TVT shift per well by minimizing median
  absolute GR interpolation error
- Search grid: `[-12.0, 12.0]`, step `0.5`
- Alignment sample: at most 256 evenly spaced valid horizontal GR points
- Tie break: smallest absolute shift, then lowest signed shift
- Prediction: `TVT_input + selected_shift`
- Missing `TVT_input`: skipped under the unchanged SOT-1975 KPI contract
- Seed and stable well order: `1975`

No horizontal-well target `TVT` was used to select a shift. Complexity, search
range, loss, and sampling limit were fixed before screen or confirm.

## Reproducible results

Data source: the locally available competition train set, 773 paired wells.
Data fingerprint from the SOT-1975 champion manifest:
`c7c598e03bd10bbaf998f026a856ac84b444b76fb2df2dd0ce024b93e8f6fac4`.

| Stage | Wells | Scored rows | Skipped rows | TVT_input MAE / RMSE | Candidate MAE / RMSE | MAE improvement |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| screen | fixed 12 | 19,891 | 56,085 | 0.000000 / 0.000000 | 1.658036 / 3.520764 | -1.658036 |
| confirm | all 773 | 1,308,266 | 3,783,989 | 0.000000 / 0.000000 | 0.921000 / 2.178443 | -0.921000 |

The screen report was executed twice with identical JSON output
(`sha256:81f4e8ccb4f604a9e029c49fa8bdc643ecf93a419fbffb630f67c6292e7aa3f8`).
The confirm report hash was
`sha256:6ade06d6deb494635528e0f0b503870fcfec8d907aedc2079f35cfccc1ef0189`.
Selected shifts stayed within the pre-fixed physical bound; no prediction was
NaN. Screen shifts ranged from 0.0 to 9.0 TVT units. Confirm shifts ranged from
-12.0 to 12.0, with median 0.0.

## Gate outcome

- Screen direction: fail (candidate is worse than `TVT_input`).
- Independent confirm direction: fail (candidate is worse than `TVT_input`).
- Promotion: no; screen alone cannot promote and confirm does not improve MAE.
- Rollback: candidate implementation removed; only this experiment record is
  retained.
- Manifest: deliberately unchanged, so implementation, documentation, and
  `reports/champion.json` agree that `tvt_input` remains the local champion.
- Exec/Kaggle gate: not entered. SOT-1977 must not treat this failed candidate
  as the champion.
