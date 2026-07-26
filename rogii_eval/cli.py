"""Command-line interface for ROGII evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .data import discover_wells, validate_submission
from .evaluate import SEED, evaluate, update_champion, write_result


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="rogii-eval")
    commands = root.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run screen or confirm evaluation")
    run.add_argument("--data-dir", type=Path, required=True)
    run.add_argument("--mode", choices=("screen", "confirm"), required=True)
    run.add_argument("--seed", type=int, default=SEED)
    run.add_argument("--screen-wells", type=int, default=12)
    run.add_argument("--folds", type=int, default=5)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--champion-manifest", type=Path)
    validate = commands.add_parser("validate-submission")
    validate.add_argument("path", type=Path)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "validate-submission":
        rows = validate_submission(args.path)
        print(f"valid submission: {rows} rows")
        return 0
    wells = discover_wells(args.data_dir)
    result = evaluate(
        wells,
        args.mode,
        seed=args.seed,
        screen_wells=args.screen_wells,
        folds=args.folds,
    )
    write_result(result, args.output)
    updated = (
        update_champion(result, args.champion_manifest) if args.champion_manifest else False
    )
    baseline = result.baselines["tvt_input"]
    candidate = result.candidate["metrics"]
    print(
        f"{result.mode}: wells={baseline.wells} rows={baseline.rows} "
        f"tvt_input_mae={baseline.mae:.6f} tvt_input_rmse={baseline.rmse:.6f} "
        f"candidate_mae={candidate['mae']:.6f} promoted={result.promoted} "
        f"manifest_updated={updated}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
