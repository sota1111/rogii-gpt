from __future__ import annotations

import csv
import math
import tempfile
import unittest
from pathlib import Path

from rogii_eval.data import discover_wells, iter_horizontal
from rogii_eval.evaluate import evaluate, update_champion
from rogii_eval.transfer import TransferPredictor, profile, select_neighbors, training_scales


class EvaluateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for index in range(8):
            well = f"{index:08x}"
            with (self.root / f"{well}__horizontal_well.csv").open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["MD", "X", "Y", "Z", "TVT", "GR", "TVT_input"])
                for row in range(3):
                    target = index * 10 + row
                    writer.writerow([row, 1, 2, 3, target, 100, target - 2])
            with (self.root / f"{well}__typewell.csv").open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["TVT", "GR", "Geology"])
                writer.writerow([1, 100, ""])
        self.wells = discover_wells(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_screen_is_deterministic_and_cannot_promote(self) -> None:
        first = evaluate(self.wells, "screen", seed=42, screen_wells=8)
        second = evaluate(self.wells, "screen", seed=42, screen_wells=8)
        self.assertEqual(first.split, second.split)
        self.assertEqual(first.baselines, second.baselines)
        self.assertFalse(first.promoted)

    def test_confirm_is_leave_one_well_out_and_records_all_baselines(self) -> None:
        result = evaluate(self.wells, "confirm", seed=42, folds=4)
        self.assertTrue(result.split["all_wells_evaluated_once"])
        self.assertEqual(result.split["kind"], "leave_one_well_out")
        self.assertEqual(result.baselines["tvt_input"].wells, 8)
        self.assertEqual(result.baselines["tvt_input"].mae, 2.0)
        self.assertEqual(result.baselines["tvt_input"].skipped_rows, 0)
        self.assertIn("zero", result.baselines)
        self.assertIn("same_well_continuity", result.baselines)
        self.assertEqual(len(result.per_well), 8)
        for report in result.per_well:
            self.assertFalse(report["target_used_for_fit_or_selection"])
            self.assertNotIn(report["well_id"], report["training_wells"])

    def test_screen_never_updates_manifest(self) -> None:
        result = evaluate(self.wells, "screen")
        self.assertFalse(update_champion(result, self.root / "champion.json"))

    def test_confirm_replaces_unverified_baseline_manifest(self) -> None:
        result = evaluate(self.wells, "confirm")
        manifest = self.root / "champion.json"
        manifest.write_text('{"champion":{"status":"unverified_baseline"}}')
        self.assertTrue(update_champion(result, manifest))
        self.assertNotIn("unverified_baseline", manifest.read_text())

    def test_validation_targets_cannot_change_fit_selection_or_predictions(self) -> None:
        validation = profile(self.wells[0])
        training = [profile(well) for well in self.wells[1:]]
        neighbors, diagnostics = select_neighbors(validation, training, 3)
        predictor = TransferPredictor(validation, neighbors, training_scales(training))
        row = next(iter(iter_horizontal(self.wells[0])))
        prediction, source = predictor.predict(row)
        path = self.wells[0].horizontal
        text = path.read_text()
        path.write_text(text.replace(",0,100,", ",999999,100,", 1))
        changed = profile(self.wells[0])
        changed_neighbors, changed_diagnostics = select_neighbors(changed, training, 3)
        changed_prediction, changed_source = TransferPredictor(
            changed, changed_neighbors, training_scales(training)
        ).predict(row)
        self.assertEqual(diagnostics, changed_diagnostics)
        self.assertEqual(prediction, changed_prediction)
        self.assertEqual(source, changed_source)

    def test_nan_features_and_end_rows_have_finite_fallback(self) -> None:
        path = self.wells[0].horizontal
        lines = path.read_text().splitlines()
        fields = lines[-1].split(",")
        for index in (1, 2, 3, 5):
            fields[index] = ""
        lines[-1] = ",".join(fields)
        path.write_text("\n".join(lines) + "\n")
        result = evaluate(self.wells, "screen", seed=42, screen_wells=8)
        self.assertTrue(math.isfinite(result.candidate["metrics"]["mae"]))

    def test_single_well_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least two wells"):
            evaluate(self.wells[:1], "screen")


if __name__ == "__main__":
    unittest.main()
