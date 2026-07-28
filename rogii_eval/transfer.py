"""Leakage-safe cross-well TVT transfer primitives."""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass

from .data import WellFiles, iter_horizontal

FEATURES = ("X", "Y", "Z", "GR")


@dataclass(frozen=True)
class WellProfile:
    well: WellFiles
    center: dict[str, float]
    md_min: float
    md_span: float


def _finite(values: list[float]) -> list[float]:
    return [value for value in values if math.isfinite(value)]


def profile(well: WellFiles) -> WellProfile:
    values: dict[str, list[float]] = {name: [] for name in FEATURES}
    mds: list[float] = []
    for row in iter_horizontal(well):
        if math.isfinite(row["MD"]):
            mds.append(row["MD"])
        for name in FEATURES:
            if math.isfinite(row[name]):
                values[name].append(row[name])
    if not mds:
        raise ValueError(f"{well.well_id}: no finite MD")
    center = {
        name: sum(items) / len(items) if items else math.nan for name, items in values.items()
    }
    md_min = min(mds)
    return WellProfile(well, center, md_min, max(max(mds) - md_min, 1.0))


def training_scales(profiles: list[WellProfile]) -> dict[str, float]:
    """Return deterministic scales fitted exclusively on training wells."""
    scales: dict[str, float] = {}
    for name in FEATURES:
        values = _finite([item.center[name] for item in profiles])
        if len(values) < 2:
            scales[name] = 1.0
            continue
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        scales[name] = max(math.sqrt(variance), 1.0)
    return scales


def _distance(
    left: dict[str, float],
    right: dict[str, float],
    scales: dict[str, float],
    names: tuple[str, ...],
) -> float:
    terms = [
        ((left[name] - right[name]) / scales[name]) ** 2
        for name in names
        if math.isfinite(left[name]) and math.isfinite(right[name])
    ]
    return math.sqrt(sum(terms) / len(terms)) if terms else math.inf


def select_neighbors(
    validation: WellProfile, training: list[WellProfile], count: int
) -> tuple[list[WellProfile], list[dict[str, float | str]]]:
    """Select spatially nearest training wells; the validation target is never read."""
    scales = training_scales(training)
    ranked = sorted(
        training,
        key=lambda item: (
            _distance(validation.center, item.center, scales, ("X", "Y", "Z")),
            item.well.well_id,
        ),
    )
    selected = ranked[: max(1, min(count, len(ranked)))]
    diagnostics: list[dict[str, float | str]] = [
        {
            "well_id": item.well.well_id,
            "spatial_distance": _distance(validation.center, item.center, scales, ("X", "Y", "Z")),
            "gr_distance": _distance(validation.center, item.center, scales, ("GR",)),
        }
        for item in selected
    ]
    return selected, diagnostics


class TransferPredictor:
    """Predict TVT from rows belonging only to explicitly supplied neighbor wells."""

    def __init__(
        self,
        validation: WellProfile,
        neighbors: list[WellProfile],
        scales: dict[str, float],
    ) -> None:
        self.validation = validation
        self.scales = scales
        self.rows: list[tuple[WellProfile, list[dict[str, float]], list[float]]] = []
        for neighbor in neighbors:
            rows = sorted(iter_horizontal(neighbor.well), key=lambda row: row["MD"])
            relative_md = [(row["MD"] - neighbor.md_min) / neighbor.md_span for row in rows]
            self.rows.append((neighbor, rows, relative_md))

    def predict(self, row: dict[str, float]) -> tuple[float, dict[str, float | str]]:
        relative_md = (row["MD"] - self.validation.md_min) / self.validation.md_span
        candidates: list[tuple[float, float, str, float]] = []
        for neighbor, rows, positions in self.rows:
            index = bisect.bisect_left(positions, relative_md)
            for candidate_index in range(max(0, index - 2), min(len(rows), index + 3)):
                candidate = rows[candidate_index]
                feature_distance = _distance(row, candidate, self.scales, ("X", "Y", "Z", "GR"))
                md_distance = abs(positions[candidate_index] - relative_md)
                distance = feature_distance + md_distance
                candidates.append((distance, candidate["TVT"], neighbor.well.well_id, md_distance))
        if not candidates:
            return 0.0, {
                "source_well": "zero_fallback",
                "distance": math.inf,
                "relative_md_distance": math.inf,
            }
        distance, target, source, md_distance = min(candidates, key=lambda item: (item[0], item[2]))
        return target, {
            "source_well": source,
            "distance": distance,
            "relative_md_distance": md_distance,
        }


def continuity_predictions(rows: list[dict[str, float]]) -> list[float]:
    """Fill missing TVT_input from the nearest finite value in the same well."""
    valid = [
        (index, row["TVT_input"])
        for index, row in enumerate(rows)
        if math.isfinite(row["TVT_input"])
    ]
    if not valid:
        return [0.0] * len(rows)
    indices = [item[0] for item in valid]
    output: list[float] = []
    for index, row in enumerate(rows):
        if math.isfinite(row["TVT_input"]):
            output.append(row["TVT_input"])
            continue
        position = bisect.bisect_left(indices, index)
        options = valid[max(0, position - 1) : min(len(valid), position + 1)]
        output.append(min(options, key=lambda item: abs(item[0] - index))[1])
    return output
