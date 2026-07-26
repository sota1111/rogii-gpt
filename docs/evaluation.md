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
the champion. `confirm` independently evaluates every available training well
exactly once with grouped OOF folds. Any fitted state is learned only from the
other wells. Both stages report MAE and RMSE for the `TVT_input` passthrough
baseline and a deliberately simple mean-bias candidate.

The JSON records the seed, exact split well ids, fold parameters, row/well
counts, metrics, promotion decision, and a data fingerprint. Run reports are
ignored by Git; only the compact champion manifest is versioned.

## Champion and rollback rules

1. A candidate may become champion only after `confirm`, only when its MAE
   strictly improves on the recorded baseline/champion threshold, and only when
   screen and confirm agree on direction.
2. `reports/champion.json` calls the winner a **local champion**. Promotion to a
   production/Kaggle champion additionally requires execution-environment
   compatibility and an actual Kaggle submission result.
3. If confirm fails or reverses the screen result, revert the candidate/model
   changes (not the evaluation harness). Keep a dated experiment note containing
   commit, seed, split, KPI, failure, and non-promotion reason.
4. If confirm passes, commit the manifest and then perform the execution
   compatibility check followed by Kaggle validation. A failure at either later
   gate leaves the manifest status local-only.

This issue establishes the harness; the included bias candidate is a leakage
test and reference comparison, not a claim about the final competition model.
