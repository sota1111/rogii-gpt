"""Generate the retained TVT-input champion submission without third-party packages."""

from __future__ import annotations

import csv
import math
from pathlib import Path

from .data import SchemaError, validate_submission, write_submission


def build_tvt_input_submission(
    sample_path: Path, test_dir: Path, output_path: Path
) -> int:
    """Write predictions in sample order, using TVT_input with a zero fallback."""
    predictions_by_id: dict[str, float] = {}
    for horizontal in sorted(test_dir.glob("*__horizontal_well.csv")):
        well_id = horizontal.name.removesuffix("__horizontal_well.csv")
        with horizontal.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "TVT_input" not in reader.fieldnames:
                raise SchemaError(f"{horizontal}: missing TVT_input column")
            for index, row in enumerate(reader):
                raw = (row.get("TVT_input") or "").strip()
                value = float(raw) if raw else 0.0
                if not math.isfinite(value):
                    raise SchemaError(f"{horizontal}:{index + 2}: TVT_input must be finite")
                predictions_by_id[f"{well_id}_{index}"] = value

    ids: list[str] = []
    predictions: list[float] = []
    with sample_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["id", "tvt"]:
            raise SchemaError(f"{sample_path}: columns must be exactly id,tvt")
        for row_number, row in enumerate(reader, start=2):
            row_id = (row.get("id") or "").strip()
            if row_id not in predictions_by_id:
                raise SchemaError(
                    f"{sample_path}:{row_number}: no horizontal-well row for id {row_id}"
                )
            ids.append(row_id)
            predictions.append(predictions_by_id[row_id])

    write_submission(output_path, ids, predictions, sample_path)
    return validate_submission(output_path, ids)
