# Offline candidate screen (SOT-2372)

The `screen` gate validates a generated submission before any Kaggle execution.
It discovers exactly one `sample_submission.csv`, then requires exact `id,tvt`
columns, equal row count, non-empty unique IDs in sample order, and finite,
numeric, non-missing `tvt` values. Any failed check sets `promotion_eligible` to
false and prevents the `confirm` gate.

Run the checked-in fixture and write reproducible JSON evidence:

```bash
python3 -m rogii_eval.candidate_screen \
  --input-root tests/fixtures/candidate_screen/input \
  --candidate tests/fixtures/candidate_screen/candidate.csv \
  --report docs/experiments/sot-2372-candidate-screen.json
```

The valid fixture is generated-equivalent to the retained candidate's execution
contract: `build_tvt_input_submission` reads horizontal-well inputs in the same
way as `kaggle/kernel/submit.py`, preserves sample order, applies the documented
zero fallback, and writes `submission.csv`. The integration test generates that
artifact and sends it through the screen gate. Invalid fixtures cover duplicate
IDs, reordered IDs, row-count mismatch, incorrect schema, and non-finite TVT.

Passing screen only makes the candidate eligible for the separate confirm gate;
it is not evidence of a Kaggle submission. No candidate source was changed by
this evaluation, so no candidate revert was necessary.
