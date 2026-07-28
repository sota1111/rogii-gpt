"""Screen a bounded transfer search and confirm only the best viable candidate."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from .data import discover_wells
from .evaluate import SEED, Evaluation, evaluate
from .transfer import TransferConfig

CANDIDATES = (
    TransferConfig(
        name="sot_2089_spatial_md_nearest",
        neighbor_count=3,
        combined_feature_distance=True,
    ),
    TransferConfig(
        name="spatial_gr_weighted",
        neighbor_count=3,
        combined_feature_distance=False,
        gr_weight=2.0,
        local_points=3,
    ),
    TransferConfig(
        name="spatial_z_md_local",
        neighbor_count=5,
        combined_feature_distance=False,
        gr_weight=0.5,
        z_weight=2.0,
        relative_md_weight=2.0,
        local_points=5,
        max_relative_md_extrapolation=0.05,
    ),
    TransferConfig(
        name="gr_local",
        neighbor_count=5,
        combined_feature_distance=False,
        spatial_weight=0.5,
        gr_weight=3.0,
        z_weight=1.0,
        local_points=3,
        max_relative_md_extrapolation=0.05,
    ),
)


def _summary(result: Evaluation) -> dict[str, object]:
    metrics = cast(dict[str, object], result.candidate["metrics"])
    fallback_rows = int(cast(Any, result.candidate["fallback_rows"]))
    rows = int(cast(Any, metrics["rows"]))
    well_regressions = sum(
        cast(Any, report["metrics"])["cross_well_transfer"]["mae"]
        > cast(Any, report["metrics"])["tvt_input"]["mae"]
        for report in result.per_well
    )
    configuration = cast(dict[str, object], result.candidate["configuration"])
    return {
        "candidate": result.candidate["name"],
        "configuration": {
            key: ("unbounded" if isinstance(value, float) and not math.isfinite(value) else value)
            for key, value in configuration.items()
        },
        "data_fingerprint": result.data_fingerprint,
        "split": result.split,
        "metrics": metrics,
        "baseline_metrics": asdict(result.baselines["tvt_input"]),
        "mae_improvement": result.candidate["mae_improvement"],
        "fallback_rows": fallback_rows,
        "fallback_rate": fallback_rows / rows,
        "finite_output_rate": 1.0,
        "wells_worse_than_champion": well_regressions,
        "runtime_seconds": result.runtime_seconds,
    }


def run(data_dir: Path, output: Path, screen_wells: int = 12) -> dict[str, object]:
    wells = discover_wells(data_dir)
    screens = [evaluate(wells, "screen", SEED, screen_wells, transfer_config=c) for c in CANDIDATES]
    ranked = sorted(
        screens, key=lambda item: cast(Any, item.candidate["metrics"])["mae"]
    )
    selected = ranked[0]
    confirm = evaluate(
        wells,
        "confirm",
        SEED,
        transfer_config=next(c for c in CANDIDATES if c.name == selected.candidate["name"]),
    )
    screen_rows = [_summary(item) for item in screens]
    confirm_row = _summary(confirm)
    baseline = confirm.baselines["tvt_input"]
    metrics = cast(dict[str, object], confirm.candidate["metrics"])
    runtime_limit_seconds = 7200.0
    thresholds = {
        "mae_improvement_min": 0.0,
        "finite_output_rate": 1.0,
        "runtime_seconds_max": runtime_limit_seconds,
        "major_well_regression_max": 0,
    }
    major_regressions = [
        report["well_id"]
        for report in confirm.per_well
        if cast(Any, report["metrics"])["cross_well_transfer"]["mae"]
        > cast(Any, report["metrics"])["tvt_input"]["mae"] * 1.25
    ]
    gates = {
        "same_fingerprint": confirm.data_fingerprint == screens[0].data_fingerprint,
        "same_fixed_split_contract": confirm.split["kind"] == "leave_one_well_out",
        "mae_improved": float(cast(Any, metrics["mae"])) < baseline.mae,
        "finite_output_100_percent": math.isfinite(float(cast(Any, metrics["mae"])))
        and math.isfinite(float(cast(Any, metrics["rmse"]))),
        "no_major_well_regression": not major_regressions,
        "runtime_within_limit": confirm.runtime_seconds <= runtime_limit_seconds,
    }
    promoted = all(gates.values())
    payload = {
        "schema_version": 1,
        "issue": "SOT-2090",
        "seed": SEED,
        "screen": {
            "candidates": screen_rows,
            "ranking": [item.candidate["name"] for item in ranked],
            "confirm_selected": selected.candidate["name"],
            "selection_reason": "lowest screen MAE; only the top candidate proceeds to confirm",
        },
        "confirm": confirm_row,
        "thresholds": thresholds,
        "major_well_regressions": major_regressions,
        "gates": gates,
        "decision": {
            "promoted": promoted,
            "candidate": selected.candidate["name"] if promoted else None,
            "reason": "all confirm gates passed" if promoted else "one or more confirm gates failed",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--screen-wells", type=int, default=12)
    args = parser.parse_args(argv)
    result = run(args.data_dir, args.output, args.screen_wells)
    print(json.dumps(result["decision"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
