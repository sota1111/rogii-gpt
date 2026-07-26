"""Strict readers for ROGII well-log and submission CSV files."""

from __future__ import annotations

import csv
import math
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

HORIZONTAL_REQUIRED = ("MD", "X", "Y", "Z", "GR", "TVT_input")
TYPEWELL_REQUIRED = ("TVT", "GR", "Geology")
SUBMISSION_COLUMNS = ("id", "tvt")
WELL_FILE = re.compile(r"^(?P<well>[0-9a-fA-F]+)__horizontal_well\.csv$")


class SchemaError(ValueError):
    """Raised when an input does not satisfy the competition schema."""


@dataclass(frozen=True)
class WellFiles:
    well_id: str
    horizontal: Path
    typewell: Path


def _header(path: Path) -> tuple[str, ...]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        try:
            return tuple(next(reader))
        except StopIteration as exc:
            raise SchemaError(f"{path}: empty CSV") from exc


def _require_columns(path: Path, required: tuple[str, ...]) -> tuple[str, ...]:
    columns = _header(path)
    missing = [name for name in required if name not in columns]
    if missing:
        raise SchemaError(f"{path}: missing columns: {', '.join(missing)}")
    if len(columns) != len(set(columns)):
        raise SchemaError(f"{path}: duplicate column names")
    return columns


def discover_wells(data_dir: Path, require_target: bool = True) -> list[WellFiles]:
    """Find paired horizontal/type-well files and validate their headers."""
    if not data_dir.is_dir():
        raise SchemaError(f"{data_dir}: data directory not found")
    wells: list[WellFiles] = []
    for horizontal in sorted(data_dir.glob("*__horizontal_well.csv")):
        match = WELL_FILE.match(horizontal.name)
        if not match:
            continue
        well_id = match.group("well").lower()
        typewell = data_dir / f"{well_id}__typewell.csv"
        if not typewell.is_file():
            raise SchemaError(f"{well_id}: paired type-well CSV not found")
        columns = _require_columns(horizontal, HORIZONTAL_REQUIRED)
        if require_target and "TVT" not in columns:
            raise SchemaError(f"{horizontal}: TVT target required for evaluation")
        _require_columns(typewell, TYPEWELL_REQUIRED)
        wells.append(WellFiles(well_id, horizontal, typewell))
    if not wells:
        raise SchemaError(f"{data_dir}: no horizontal well CSV files found")
    return wells


def iter_horizontal(well: WellFiles, require_target: bool = True) -> Iterator[dict[str, float]]:
    """Yield validated numeric horizontal-well rows."""
    numeric = list(HORIZONTAL_REQUIRED) + (["TVT"] if require_target else [])
    with well.horizontal.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise SchemaError(f"{well.horizontal}: missing header")
        for row_number, row in enumerate(reader, start=2):
            parsed: dict[str, float] = {}
            for name in numeric:
                raw = row.get(name, "")
                # Feature gaps genuinely occur in the supplied competition data.
                # Preserve them for model-specific handling; the target stays strict.
                if name != "TVT" and (raw is None or not raw.strip()):
                    parsed[name] = math.nan
                    continue
                try:
                    value = float(raw)
                except (TypeError, ValueError) as exc:
                    raise SchemaError(
                        f"{well.horizontal}:{row_number}: {name} is not numeric"
                    ) from exc
                if not math.isfinite(value):
                    raise SchemaError(
                        f"{well.horizontal}:{row_number}: {name} must be finite"
                    )
                parsed[name] = value
            yield parsed


def validate_typewell_rows(well: WellFiles) -> int:
    """Validate numeric TVT/GR values while allowing blank Geology labels."""
    count = 0
    with well.typewell.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=2):
            for name in ("TVT", "GR"):
                raw = row.get(name, "")
                if name == "GR" and (raw is None or not raw.strip()):
                    continue
                try:
                    value = float(raw)
                except (TypeError, ValueError) as exc:
                    raise SchemaError(
                        f"{well.typewell}:{row_number}: {name} is not numeric"
                    ) from exc
                if not math.isfinite(value):
                    raise SchemaError(
                        f"{well.typewell}:{row_number}: {name} must be finite"
                    )
            count += 1
    if count == 0:
        raise SchemaError(f"{well.typewell}: no data rows")
    return count


def validate_submission(path: Path, expected_ids: list[str] | None = None) -> int:
    """Require exactly id,tvt, unique non-empty ids, and finite predictions."""
    columns = _header(path)
    if columns != SUBMISSION_COLUMNS:
        raise SchemaError(f"{path}: columns must be exactly id,tvt (found {columns})")
    ids: list[str] = []
    seen: set[str] = set()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            row_id = (row.get("id") or "").strip()
            if not row_id:
                raise SchemaError(f"{path}:{row_number}: id is empty")
            if row_id in seen:
                raise SchemaError(f"{path}:{row_number}: duplicate id {row_id}")
            seen.add(row_id)
            ids.append(row_id)
            try:
                prediction = float(row.get("tvt", ""))
            except (TypeError, ValueError) as exc:
                raise SchemaError(f"{path}:{row_number}: tvt is not numeric") from exc
            if not math.isfinite(prediction):
                raise SchemaError(f"{path}:{row_number}: tvt must be finite")
    if expected_ids is not None and ids != expected_ids:
        raise SchemaError(f"{path}: ids/order do not match the sample submission")
    return len(ids)


def write_submission(
    output: Path, ids: list[str], predictions: list[float], sample: Path | None = None
) -> None:
    """Write a strict submission, optionally checking exact sample id order."""
    if len(ids) != len(predictions):
        raise SchemaError("ids and predictions have different lengths")
    expected_ids = read_submission_ids(sample) if sample else None
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(SUBMISSION_COLUMNS)
        writer.writerows(zip(ids, predictions))
    validate_submission(output, expected_ids)


def read_submission_ids(path: Path) -> list[str]:
    validate_submission(path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [row["id"].strip() for row in csv.DictReader(handle)]
