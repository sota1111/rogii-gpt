"""Kaggle entry point for the retained TVT-input/zero-fallback champion.

This file is intentionally standalone: Kaggle scripts run with internet disabled,
without installing this repository, and may execute the source without defining
``__file__``.
"""

import csv
import math
from pathlib import Path

INPUT_ROOT = Path("/kaggle/input")
OUTPUT_PATH = Path("/kaggle/working/submission.csv")


def find_unique(name):
    matches = list(INPUT_ROOT.rglob(name))
    if len(matches) != 1:
        raise RuntimeError(f"Expected one {name}, found {len(matches)}: {matches}")
    return matches[0]


def generate_submission():
    sample_path = find_unique("sample_submission.csv")
    horizontal_paths = sorted(INPUT_ROOT.rglob("*__horizontal_well.csv"))
    if not horizontal_paths:
        raise RuntimeError("No horizontal-well CSV files found under /kaggle/input")

    predictions = {}
    for horizontal_path in horizontal_paths:
        well_id = horizontal_path.name.removesuffix("__horizontal_well.csv")
        with horizontal_path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source)
            if not reader.fieldnames or "TVT_input" not in reader.fieldnames:
                raise RuntimeError(f"{horizontal_path}: missing TVT_input column")
            for index, row in enumerate(reader):
                raw = (row.get("TVT_input") or "").strip()
                value = float(raw) if raw else 0.0
                if not math.isfinite(value):
                    raise RuntimeError(
                        f"{horizontal_path}:{index + 2}: non-finite TVT_input"
                    )
                predictions[f"{well_id}_{index}"] = value

    seen = set()
    count = 0
    with sample_path.open(newline="", encoding="utf-8-sig") as source, OUTPUT_PATH.open(
        "w", newline="", encoding="utf-8"
    ) as target:
        reader = csv.DictReader(source)
        if reader.fieldnames != ["id", "tvt"]:
            raise RuntimeError(
                f"{sample_path}: expected columns ['id', 'tvt'], found {reader.fieldnames}"
            )
        writer = csv.writer(target, lineterminator="\n")
        writer.writerow(["id", "tvt"])
        for row_number, row in enumerate(reader, start=2):
            row_id = (row.get("id") or "").strip()
            if not row_id or row_id in seen:
                raise RuntimeError(f"{sample_path}:{row_number}: invalid or duplicate id")
            if row_id not in predictions:
                raise RuntimeError(f"{sample_path}:{row_number}: no prediction for {row_id}")
            seen.add(row_id)
            writer.writerow([row_id, format(predictions[row_id], ".10g")])
            count += 1

    print(f"Wrote {count} rows to {OUTPUT_PATH}")


generate_submission()
