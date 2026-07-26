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

Pending SOT-1977 screen, independent clean-environment confirm, and Kaggle
kernel submission.
