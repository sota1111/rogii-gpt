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
