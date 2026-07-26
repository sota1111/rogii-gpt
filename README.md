# rogii-gpt

ROGII - Wellbore Geology Prediction experimentation repository.

## Reproducible local evaluation

The dependency-free `rogii_eval` package validates competition CSV schemas,
prevents well leakage during validation, records the `TVT_input` baseline, and
produces machine-readable screen/confirm reports:

```bash
python3 -m unittest discover -s tests -v
python3 -m rogii_eval.cli run \
  --data-dir data/train --mode screen --output reports/screen.json
python3 -m rogii_eval.cli run \
  --data-dir data/train --mode confirm --output reports/confirm.json \
  --champion-manifest reports/champion.json
```

See [docs/evaluation.md](docs/evaluation.md) for schemas, split semantics,
promotion/rollback rules, and the gates after local confirmation.

## Kaggle submission

The retained champion passes through finite `TVT_input` values and uses `0.0`
where the competition test rows hide that field. The standalone Kaggle script
uses only the Python standard library, does not depend on the working directory
or `__file__`, and runs with internet disabled:

```bash
python3 -c "from pathlib import Path; from rogii_eval.submission import build_tvt_input_submission; build_tvt_input_submission(Path('data/sample_submission.csv'), Path('data/test'), Path('submission.csv'))"
kaggle kernels push -p kaggle/kernel
```

See [docs/submission.md](docs/submission.md) for the screen/confirm contract and
the recorded kernel/submission result.
