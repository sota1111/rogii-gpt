"""Well-grouped, deterministic evaluation and champion manifest logic."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .data import WellFiles, iter_horizontal, validate_typewell_rows
from .transfer import (
    TransferPredictor,
    WellProfile,
    continuity_predictions,
    profile,
    select_neighbors,
    training_scales,
)

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
    per_well: list[dict[str, object]]

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


def _evaluate_fold(
    train: list[WellFiles],
    validation: list[WellFiles],
    neighbor_count: int,
    profiles: dict[str, WellProfile],
) -> tuple[dict[str, list[tuple[float, float]]], list[dict[str, object]], int]:
    train_profiles = [profiles[well.well_id] for well in train]
    scales = training_scales(train_profiles)
    pairs: dict[str, list[tuple[float, float]]] = {
        "tvt_input": [],
        "zero": [],
        "same_well_continuity": [],
        "cross_well_transfer": [],
    }
    reports: list[dict[str, object]] = []
    skipped = 0
    for well in validation:
        validate_typewell_rows(well)
        validation_profile = profiles[well.well_id]
        neighbors, neighbor_diagnostics = select_neighbors(
            validation_profile, train_profiles, neighbor_count
        )
        predictor = TransferPredictor(validation_profile, neighbors, scales)
        rows = list(iter_horizontal(well))
        continuity = continuity_predictions(rows)
        well_pairs: dict[str, list[tuple[float, float]]] = {name: [] for name in pairs}
        source_counts: dict[str, int] = {}
        distances: list[float] = []
        for index, row in enumerate(rows):
            target = row["TVT"]
            champion = row["TVT_input"] if math.isfinite(row["TVT_input"]) else 0.0
            skipped += int(not math.isfinite(row["TVT_input"]))
            transfer, diagnostic = predictor.predict(row)
            source = str(diagnostic["source_well"])
            source_counts[source] = source_counts.get(source, 0) + 1
            if math.isfinite(float(diagnostic["distance"])):
                distances.append(float(diagnostic["distance"]))
            predictions = {
                "tvt_input": champion,
                "zero": 0.0,
                "same_well_continuity": continuity[index],
                "cross_well_transfer": transfer,
            }
            for name, prediction in predictions.items():
                pair = (prediction, target)
                pairs[name].append(pair)
                well_pairs[name].append(pair)
        reports.append(
            {
                "well_id": well.well_id,
                "training_wells": [item.well.well_id for item in train_profiles],
                "target_used_for_fit_or_selection": False,
                "neighbors": neighbor_diagnostics,
                "source_row_counts": source_counts,
                "mean_match_distance": sum(distances) / len(distances) if distances else None,
                "metrics": {
                    name: asdict(_score(items, 1, 0)) for name, items in well_pairs.items()
                },
            }
        )
    return pairs, reports, skipped


def evaluate(
    wells: list[WellFiles],
    mode: str,
    seed: int = SEED,
    screen_wells: int = 12,
    folds: int = 5,
    min_mae_improvement: float = 0.0,
    neighbor_count: int = 3,
) -> Evaluation:
    """Run a quick holdout or full leave-one-well-out evaluation."""
    ordered = stable_order(wells, seed)
    if len(ordered) < 2:
        raise ValueError("evaluation requires at least two wells")
    profiles = {well.well_id: profile(well) for well in wells}
    all_pairs: dict[str, list[tuple[float, float]]] = {
        "tvt_input": [],
        "zero": [],
        "same_well_continuity": [],
        "cross_well_transfer": [],
    }
    per_well: list[dict[str, object]] = []
    validation_ids: list[str] = []
    skipped_rows = 0

    if mode == "screen":
        sample = ordered[: min(len(ordered), max(2, screen_wells))]
        validation_count = max(1, len(sample) // 4)
        validation = sample[:validation_count]
        train = sample[validation_count:]
        fold_pairs, fold_reports, skipped = _evaluate_fold(
            train, validation, neighbor_count, profiles
        )
        for name, items in fold_pairs.items():
            all_pairs[name].extend(items)
        per_well.extend(fold_reports)
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
        fold_ids: list[list[str]] = []
        for validation_well in ordered:
            validation = [validation_well]
            train = [well for well in ordered if well.well_id != validation_well.well_id]
            fold_pairs, fold_reports, skipped = _evaluate_fold(
                train, validation, neighbor_count, profiles
            )
            for name, items in fold_pairs.items():
                all_pairs[name].extend(items)
            per_well.extend(fold_reports)
            skipped_rows += skipped
            validation_ids.extend(well.well_id for well in validation)
            fold_ids.append([well.well_id for well in validation])
        split = {
            "kind": "leave_one_well_out",
            "folds": len(ordered),
            "fold_validation_wells": fold_ids,
            "all_wells_evaluated_once": sorted(validation_ids)
            == sorted(well.well_id for well in wells),
        }
    else:
        raise ValueError("mode must be screen or confirm")

    scored = {
        name: _score(items, len(set(validation_ids)), skipped_rows)
        for name, items in all_pairs.items()
    }
    baseline_metrics = scored["tvt_input"]
    candidate_metrics = scored["cross_well_transfer"]
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
        baselines={
            "tvt_input": baseline_metrics,
            "zero": scored["zero"],
            "same_well_continuity": scored["same_well_continuity"],
        },
        candidate={
            "name": "cross_well_transfer",
            "metrics": asdict(candidate_metrics),
            "neighbor_count": neighbor_count,
            "normalization": "training-well standard scales; relative MD per well",
            "mae_improvement": improvement,
        },
        promoted=promoted,
        promotion_reason=reason,
        data_fingerprint=_fingerprint(wells),
        per_well=per_well,
    )


def write_result(result: Evaluation, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n")


def update_champion(result: Evaluation, manifest: Path) -> bool:
    """Update only from a successful confirm; bootstrap the baseline if needed."""
    if result.mode != "confirm":
        return False
    if manifest.exists():
        existing = json.loads(manifest.read_text())
        if existing.get("champion", {}).get("status") == "kaggle_validated_champion":
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
        "evaluation": {"kind": "leave_one_well_out", "mode": "confirm"},
        "champion": champion,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return True
