"""Well-grouped, deterministic evaluation and champion manifest logic."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .data import WellFiles, iter_horizontal, validate_typewell_rows

SEED = 1975


@dataclass(frozen=True)
class Metrics:
    mae: float
    rmse: float
    rows: int
    wells: int
    skipped_rows: int


@dataclass(frozen=True)
class Evaluation:
    mode: str
    seed: int
    split: dict[str, object]
    baselines: dict[str, Metrics]
    candidate: dict[str, object]
    promoted: bool
    promotion_reason: str
    data_fingerprint: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def stable_order(wells: list[WellFiles], seed: int) -> list[WellFiles]:
    return sorted(
        wells,
        key=lambda well: hashlib.sha256(f"{seed}:{well.well_id}".encode()).hexdigest(),
    )


def _fingerprint(wells: list[WellFiles]) -> str:
    digest = hashlib.sha256()
    for well in sorted(wells, key=lambda item: item.well_id):
        digest.update(well.well_id.encode())
        digest.update(str(well.horizontal.stat().st_size).encode())
        digest.update(str(well.typewell.stat().st_size).encode())
    return digest.hexdigest()


def _score(pairs: list[tuple[float, float]], wells: int, skipped_rows: int) -> Metrics:
    if not pairs:
        raise ValueError("cannot score zero rows")
    errors = [prediction - target for prediction, target in pairs]
    return Metrics(
        mae=sum(abs(error) for error in errors) / len(errors),
        rmse=math.sqrt(sum(error * error for error in errors) / len(errors)),
        rows=len(errors),
        wells=wells,
        skipped_rows=skipped_rows,
    )


def _mean_residual(wells: list[WellFiles]) -> float:
    total = 0.0
    rows = 0
    for well in wells:
        for row in iter_horizontal(well):
            if not math.isfinite(row["TVT_input"]):
                continue
            total += row["TVT"] - row["TVT_input"]
            rows += 1
    if not rows:
        raise ValueError("training split contains zero rows")
    return total / rows


def _evaluate_fold(train: list[WellFiles], validation: list[WellFiles]) -> tuple[
    list[tuple[float, float]], list[tuple[float, float]], float, int
]:
    # This deliberately simple candidate proves fitted state comes only from other wells.
    bias = _mean_residual(train)
    baseline: list[tuple[float, float]] = []
    candidate: list[tuple[float, float]] = []
    skipped = 0
    for well in validation:
        validate_typewell_rows(well)
        for row in iter_horizontal(well):
            if not math.isfinite(row["TVT_input"]):
                skipped += 1
                continue
            baseline.append((row["TVT_input"], row["TVT"]))
            candidate.append((row["TVT_input"] + bias, row["TVT"]))
    return baseline, candidate, bias, skipped


def evaluate(
    wells: list[WellFiles],
    mode: str,
    seed: int = SEED,
    screen_wells: int = 12,
    folds: int = 5,
    min_mae_improvement: float = 0.0,
) -> Evaluation:
    """Run quick fixed holdout (screen) or full well-grouped OOF (confirm)."""
    ordered = stable_order(wells, seed)
    if len(ordered) < 2:
        raise ValueError("evaluation requires at least two wells")
    baseline_pairs: list[tuple[float, float]] = []
    candidate_pairs: list[tuple[float, float]] = []
    biases: list[float] = []
    validation_ids: list[str] = []
    skipped_rows = 0

    if mode == "screen":
        sample = ordered[: min(len(ordered), max(2, screen_wells))]
        validation_count = max(1, len(sample) // 4)
        validation = sample[:validation_count]
        train = sample[validation_count:]
        baseline, candidate, bias, skipped = _evaluate_fold(train, validation)
        baseline_pairs.extend(baseline)
        candidate_pairs.extend(candidate)
        biases.append(bias)
        skipped_rows += skipped
        validation_ids.extend(well.well_id for well in validation)
        split: dict[str, object] = {
            "kind": "fixed_well_holdout",
            "available_wells": len(wells),
            "screen_wells": [well.well_id for well in sample],
            "train_wells": [well.well_id for well in train],
            "validation_wells": validation_ids,
        }
    elif mode == "confirm":
        actual_folds = min(max(2, folds), len(ordered))
        fold_ids: list[list[str]] = []
        for fold in range(actual_folds):
            validation = ordered[fold::actual_folds]
            validation_set = {well.well_id for well in validation}
            train = [well for well in ordered if well.well_id not in validation_set]
            baseline, candidate, bias, skipped = _evaluate_fold(train, validation)
            baseline_pairs.extend(baseline)
            candidate_pairs.extend(candidate)
            biases.append(bias)
            skipped_rows += skipped
            validation_ids.extend(well.well_id for well in validation)
            fold_ids.append([well.well_id for well in validation])
        split = {
            "kind": "grouped_oof",
            "folds": actual_folds,
            "fold_validation_wells": fold_ids,
            "all_wells_evaluated_once": sorted(validation_ids)
            == sorted(well.well_id for well in wells),
        }
    else:
        raise ValueError("mode must be screen or confirm")

    baseline_metrics = _score(baseline_pairs, len(set(validation_ids)), skipped_rows)
    candidate_metrics = _score(candidate_pairs, len(set(validation_ids)), skipped_rows)
    improvement = baseline_metrics.mae - candidate_metrics.mae
    promoted = mode == "confirm" and improvement > min_mae_improvement
    if mode != "confirm":
        reason = "screen results cannot promote a champion"
    elif promoted:
        reason = f"candidate MAE improved by {improvement:.12g}"
    else:
        reason = f"candidate MAE improvement {improvement:.12g} did not exceed threshold"
    return Evaluation(
        mode=mode,
        seed=seed,
        split=split,
        baselines={"tvt_input": baseline_metrics},
        candidate={
            "name": "mean_bias_corrected_tvt_input",
            "metrics": asdict(candidate_metrics),
            "fold_biases": biases,
            "mae_improvement": improvement,
        },
        promoted=promoted,
        promotion_reason=reason,
        data_fingerprint=_fingerprint(wells),
    )


def write_result(result: Evaluation, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n")


def update_champion(result: Evaluation, manifest: Path) -> bool:
    """Update only from a successful confirm; bootstrap the baseline if needed."""
    if result.mode != "confirm":
        return False
    baseline = asdict(result.baselines["tvt_input"])
    if result.promoted:
        champion = {
            "model": result.candidate["name"],
            "metrics": result.candidate["metrics"],
            "status": "local_champion",
            "requires": ["exec_compatibility", "kaggle_validation"],
        }
    else:
        if manifest.exists():
            existing = json.loads(manifest.read_text())
            status = existing.get("champion", {}).get("status")
            if status != "unverified_baseline":
                return False
        champion = {
            "model": "tvt_input",
            "metrics": baseline,
            "status": "local_champion",
            "requires": ["exec_compatibility", "kaggle_validation"],
        }
    payload = {
        "schema_version": 1,
        "seed": result.seed,
        "data_fingerprint": result.data_fingerprint,
        "evaluation": {"kind": "grouped_oof", "mode": "confirm"},
        "champion": champion,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return True
