"""Offline screening gate for Kaggle submission candidates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path


def discover_sample(input_root: Path) -> Path:
    """Find the single sample submission exactly as the Kaggle kernel does."""
    matches = sorted(input_root.rglob("sample_submission.csv"))
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one sample_submission.csv, found {len(matches)}"
        )
    return matches[0]


def _read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        return columns, list(reader)


def screen_candidate(input_root: Path, candidate_path: Path) -> dict[str, object]:
    """Validate a candidate against the discovered sample and return evidence."""
    checks: dict[str, bool] = {}
    reasons: list[str] = []
    sample_path: Path | None = None
    sample_rows: list[dict[str, str]] = []
    candidate_rows: list[dict[str, str]] = []

    try:
        sample_path = discover_sample(input_root)
        checks["unique_sample_discovered"] = True
    except ValueError as exc:
        checks["unique_sample_discovered"] = False
        reasons.append(str(exc))

    if sample_path is not None:
        sample_columns, sample_rows = _read_rows(sample_path)
        checks["sample_schema"] = sample_columns == ["id", "tvt"]
        if not checks["sample_schema"]:
            reasons.append(f"sample columns are {sample_columns!r}, expected ['id', 'tvt']")

    candidate_columns, candidate_rows = _read_rows(candidate_path)
    checks["candidate_schema"] = candidate_columns == ["id", "tvt"]
    if not checks["candidate_schema"]:
        reasons.append(
            f"candidate columns are {candidate_columns!r}, expected ['id', 'tvt']"
        )

    sample_ids = [row.get("id", "").strip() for row in sample_rows]
    candidate_ids = [row.get("id", "").strip() for row in candidate_rows]
    checks["row_count"] = len(candidate_rows) == len(sample_rows)
    checks["ids_match_sample_order"] = candidate_ids == sample_ids
    checks["ids_nonempty_unique"] = bool(candidate_ids) and all(candidate_ids) and len(
        set(candidate_ids)
    ) == len(candidate_ids)

    numeric_finite = True
    for row in candidate_rows:
        raw = row.get("tvt", "").strip()
        try:
            numeric_finite = numeric_finite and bool(raw) and math.isfinite(float(raw))
        except ValueError:
            numeric_finite = False
    checks["tvt_numeric_finite_nonmissing"] = numeric_finite

    labels = {
        "row_count": "candidate row count differs from sample",
        "ids_match_sample_order": "candidate ids differ from sample order",
        "ids_nonempty_unique": "candidate ids are empty or duplicated",
        "tvt_numeric_finite_nonmissing": "candidate tvt contains missing/non-numeric/non-finite values",
    }
    for name, label in labels.items():
        if not checks[name]:
            reasons.append(label)

    passed = all(checks.values())
    return {
        "schema_version": 1,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "gate": "screen",
        "status": "passed" if passed else "rejected",
        "promotion_eligible": passed,
        "next_gate": "confirm" if passed else None,
        "checks": checks,
        "evidence": {
            "sample_path": str(sample_path) if sample_path else None,
            "candidate_path": str(candidate_path),
            "sample_rows": len(sample_rows),
            "candidate_rows": len(candidate_rows),
            "candidate_sha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
        },
        "reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = screen_candidate(args.input_root, args.candidate)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"{report['status']}: {args.report}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
