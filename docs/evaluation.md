# ROGII local evaluation protocol

This harness compares changes without mixing rows from the same well between fit
and validation. Raw competition data and credentials must stay outside Git.

## Data and schema

Point `--data-dir` at the competition `train/` directory. Every well must have:

- `<well>__horizontal_well.csv`: `MD,X,Y,Z,GR,TVT_input` and evaluation target `TVT`.
- `<well>__typewell.csv`: `TVT,GR,Geology`.

Readers reject missing/duplicate columns, non-finite required numeric values,
and missing pairs. Blank feature values are accepted because the supplied data
is sparse there; target `TVT` remains mandatory. Rows lacking `TVT_input` cannot
participate in that baseline, so they are skipped and counted as `skipped_rows`
in both baseline and candidate metrics.
Submissions must contain exactly `id,tvt`, in sample-submission order, with
unique ids and finite values.

## Two-stage gate

Run the same seed and implementation at both stages:

```bash
python3 -m rogii_eval.cli run \
  --data-dir /path/to/train --mode screen --seed 1975 \
  --output reports/screen.json

python3 -m rogii_eval.cli run \
  --data-dir /path/to/train --mode confirm --seed 1975 --folds 5 \
  --output reports/confirm.json --champion-manifest reports/champion.json
```

`screen` uses a stable hash-selected 12-well subset and a well-level holdout. It
is for fast schema, determinism, and direction checks only; it can never update
the champion. `confirm` performs literal leave-one-well-out: each available well
is evaluated once, and its complete `TVT` column is excluded from normalization,
neighbor selection, and prediction. Every fit/selection input comes from the
other wells. Both stages use the same predictor and configuration.

The report compares four methods on the same rows and with the same MAE/RMSE:

- current champion (`TVT_input`, with its documented zero fallback);
- constant zero fallback;
- same-well continuity (nearest finite `TVT_input` for missing rows);
- cross-well transfer candidate.

The transfer candidate normalizes X/Y/Z/GR using scales fitted on training wells,
selects spatially nearest training wells, maps relative MD between wells, then
chooses the closest local row using normalized X/Y/Z/GR plus relative-MD
distance. Missing features are omitted from that row's distance. With no usable
match it deterministically returns zero. One-well data is rejected because a
leak-free training set cannot be formed.

The JSON records the seed, exact split well ids, row/well counts, aggregate and
per-well metrics, selected-neighbor spatial/GR distances, source-row counts,
mean match distance, promotion decision, and a data fingerprint. The
`target_used_for_fit_or_selection: false` contract is regression-tested by
mutating a held-out target and proving selection and prediction are unchanged.
Run reports are ignored by Git; only compact experiment evidence is versioned.

## Champion and rollback rules

1. A candidate passes the local promotion threshold only after `confirm`, only
   when its MAE improves on the current champion by more than
   `--min-mae-improvement` (default `0.0`), and only when screen and confirm
   agree on direction.
2. `reports/champion.json` calls the winner a **local champion**. Promotion to a
   production/Kaggle champion additionally requires execution-environment
   compatibility and an actual Kaggle submission result.
3. If confirm fails or reverses the screen result, revert the candidate/model
   changes (not the evaluation harness). Keep a dated experiment note containing
   commit, seed, split, KPI, failure, and non-promotion reason.
4. If confirm passes, commit the manifest and then perform the execution
   compatibility check followed by Kaggle validation. A failure at either later
   gate leaves the manifest status local-only.

This issue establishes the harness; the transfer candidate is an evaluation
reference, not a claim about the final competition model.
An existing `kaggle_validated_champion` manifest is never overwritten by local
evaluation. Non-promotion keeps the evaluation code, JSON result, and dated
reason only; any integration of the candidate into `kaggle/kernel/submit.py`
must be reverted.
