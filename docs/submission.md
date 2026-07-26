# Kaggle champion submission

SOT-1977 packages the retained `tvt_input` local champion as a standalone
Kaggle script. For test rows where the competition withholds `TVT_input`, the
previously submitted zero baseline remains the explicit fallback.

## Execution contract

- Read the unique `sample_submission.csv` below `/kaggle/input`.
- Resolve each sample ID as `<well-id>_<zero-based horizontal-row-index>`.
- Write exactly `id,tvt` in sample order, with unique IDs and finite numeric TVT.
- Use no network access, package installation, working-directory assumption, or
  `__file__`.

## Verification and result

### Screen

- Generated 14,151 rows from the downloaded competition test fixture.
- Exact sample ID order and row count were retained.
- All IDs are unique and all TVT values are numeric and finite.
- The output has exactly `id,tvt`; its SHA-256 is
  `7a20b373f00d0d219db2d8e39f7c326fde98b93a5d812b227c70d6bf98fc1d57`.

### Confirm

The standalone source was executed twice from an unrelated temporary working
directory, without `__file__`, network access, or third-party packages. Both
runs produced the same artifact hash. Kaggle then ran the committed source as
kernel `sota1111/rogii-gpt-cli-baseline`, version 2, with status `COMPLETE`; the
downloaded kernel output independently passed the same schema and ordering
checks and had the same hash.

### Submission

- Champion source commit: `d0dec26`
- Kernel: `sota1111/rogii-gpt-cli-baseline`, version 2
- Submission ID: `54996914`
- Message: `SOT-1977 rogii-gpt tvt_input champion`
- Status: `COMPLETE`
- Public score: `11551.955`
- Public rank at 2026-07-26 09:15 UTC: `5714 / 5719`

The submission proves execution compatibility but ties the previously recorded
zero-baseline score and is not a competitive improvement. The retained
`tvt_input`/zero-fallback implementation is therefore promoted only from
`local_champion` to `kaggle_validated_champion`; it does not claim a score
improvement. Future work must address the rows whose `TVT_input` is withheld.
