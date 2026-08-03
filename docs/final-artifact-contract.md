# Final candidate artifact contract (SOT-2374)

The machine-readable source of truth is
[`docs/experiments/sot-2374-final-artifact.json`](experiments/sot-2374-final-artifact.json).
The parent run must read its `decision.new_artifact` value and may submit only
when it is `true`, every value in `checks` except
`kaggle_submission_performed` is `true`, and
`kaggle_submission_performed` is `false`.

The selected candidate is the retained `tvt_input` champion with its documented
zero fallback. SOT-2372 passed the offline screen and SOT-2373 passed two
deterministic standalone executions. Their reports, the candidate output, the
kernel source, and kernel metadata are bound to the final decision by SHA-256.

This cycle has a new artifact because the confirmed standalone source hash
`f225cd21...1bafd` differs from the previous submission source hash
`a66d28e5...d3a56`. The artifact remains compatible with the control-plane
`kernel/version/output` wrapper contract and writes `submission.csv`.

No model/candidate implementation was rejected, so there is no code to revert.
No Kaggle kernel push or competition submission was performed by SOT-2374.
