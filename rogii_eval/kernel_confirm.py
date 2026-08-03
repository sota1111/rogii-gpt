"""Confirm the screened candidate under the standalone Kaggle execution contract."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from rogii_eval.candidate_screen import screen_candidate


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _submission_values(path: Path) -> list[tuple[str, float]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [(row["id"], float(row["tvt"])) for row in csv.DictReader(handle)]


def confirm_kernel(
    kernel_dir: Path, input_root: Path, screened_candidate: Path
) -> dict[str, object]:
    """Run the exact kernel source twice and return fail-closed confirm evidence."""
    source = kernel_dir / "submit.py"
    metadata_path = kernel_dir / "kernel-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    screen = screen_candidate(input_root, screened_candidate)
    checks = {
        "screen_passed": screen["status"] == "passed" and screen["next_gate"] == "confirm",
        "standalone_source": metadata.get("code_file") == source.name and source.is_file(),
        "internet_disabled": metadata.get("enable_internet") is False,
        "dependencies_empty": all(
            not metadata.get(key)
            for key in ("dataset_sources", "kernel_sources", "model_sources")
        ),
        "competition_source_declared": metadata.get("competition_sources")
        == ["rogii-wellbore-geology-prediction"],
    }
    runs: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for run_number in (1, 2):
            output = root / f"run-{run_number}" / "submission.csv"
            output.parent.mkdir()
            environment = os.environ.copy()
            environment.update(
                KAGGLE_INPUT_ROOT=str(input_root.resolve()),
                KAGGLE_OUTPUT_PATH=str(output.resolve()),
                PYTHONNOUSERSITE="1",
            )
            command = [
                sys.executable,
                "-I",
                "-c",
                "import sys; source=open(sys.argv[1], encoding='utf-8').read(); "
                "exec(compile(source, sys.argv[1], 'exec'), {'__name__':'__main__'})",
                str(source.resolve()),
            ]
            completed = subprocess.run(
                command,
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            run_screen = screen_candidate(input_root, output) if output.is_file() else None
            runs.append(
                {
                    "run": run_number,
                    "exit_code": completed.returncode,
                    "stdout": completed.stdout.strip(),
                    "stderr": completed.stderr.strip(),
                    "output_sha256": _sha256(output) if output.is_file() else None,
                    "output_values": _submission_values(output) if output.is_file() else None,
                    "output_screen_status": run_screen["status"] if run_screen else "missing",
                }
            )
    checks["both_runs_exit_zero"] = all(run["exit_code"] == 0 for run in runs)
    checks["both_outputs_pass_schema"] = all(
        run["output_screen_status"] == "passed" for run in runs
    )
    output_hashes = {run["output_sha256"] for run in runs}
    checks["deterministic_output"] = len(output_hashes) == 1 and None not in output_hashes
    generated_runs = [run for run in runs if run["output_sha256"] is not None]
    checks["matches_screened_candidate"] = bool(generated_runs) and all(
        run["output_values"] == _submission_values(screened_candidate)
        for run in generated_runs
    )
    passed = all(checks.values())
    return {
        "schema_version": 1,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "gate": "confirm",
        "status": "passed" if passed else "rejected",
        "promotion_eligible": passed,
        "checks": checks,
        "artifact": {
            "kernel_id": metadata.get("id"),
            "source": str(source),
            "source_sha256": _sha256(source),
            "metadata_sha256": _sha256(metadata_path),
            "submission_sha256": next(iter(output_hashes)) if len(output_hashes) == 1 else None,
            "output": "submission.csv",
            "wrapper_contract": "kernel/version/output",
        },
        "runs": runs,
        "kaggle_submission_performed": False,
        "reasons": [] if passed else [name for name, value in checks.items() if not value],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel-dir", type=Path, required=True)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--screened-candidate", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = confirm_kernel(args.kernel_dir, args.input_root, args.screened_candidate)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"{report['status']}: {args.report}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
