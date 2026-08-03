# Kaggle kernel execution confirm (SOT-2373)

The confirm gate consumes only a candidate that already passed the SOT-2372
screen. It executes the exact standalone kernel source twice in isolated Python
mode from an unrelated working directory, without `__file__`, user site
packages, network access, or undeclared Kaggle sources. Both outputs must exit
zero, pass the submission schema screen, be byte-identical, and match the
screened candidate fingerprint.

Run the checked-in contract fixture:

```bash
python3 -m rogii_eval.kernel_confirm \
  --kernel-dir kaggle/kernel \
  --input-root tests/fixtures/kernel_confirm/input \
  --screened-candidate tests/fixtures/candidate_screen/candidate.csv \
  --report docs/experiments/sot-2373-kernel-confirm.json
```

`submit.py` retains `/kaggle/input` and `/kaggle/working/submission.csv` as its
defaults. The environment overrides are only a local equivalent of those two
Kaggle mount points. The confirmed artifact contract is the kernel metadata ID
plus an immutable version and output name (`kernel/version/submission.csv`),
which is the contract accepted by the control-plane submit wrapper.

This gate does not push a kernel or submit to Kaggle. A rejected confirm is not
eligible for promotion; its reasons remain in the JSON report and no candidate
source is retained as a promoted artifact.
