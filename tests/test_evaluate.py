from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from rogii_eval.data import discover_wells
from rogii_eval.evaluate import evaluate, update_champion


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

    def test_confirm_is_grouped_oof_and_updates_manifest(self) -> None:
        result = evaluate(self.wells, "confirm", seed=42, folds=4)
        self.assertTrue(result.split["all_wells_evaluated_once"])
        self.assertEqual(result.baselines["tvt_input"].wells, 8)
        self.assertEqual(result.baselines["tvt_input"].mae, 2.0)
        self.assertEqual(result.baselines["tvt_input"].skipped_rows, 0)
        self.assertAlmostEqual(result.candidate["metrics"]["mae"], 0.0)
        manifest = self.root / "champion.json"
        self.assertTrue(update_champion(result, manifest))
        self.assertIn('"status": "local_champion"', manifest.read_text())

    def test_screen_never_updates_manifest(self) -> None:
        result = evaluate(self.wells, "screen")
        self.assertFalse(update_champion(result, self.root / "champion.json"))

    def test_confirm_replaces_unverified_baseline_manifest(self) -> None:
        result = evaluate(self.wells, "confirm")
        manifest = self.root / "champion.json"
        manifest.write_text('{"champion":{"status":"unverified_baseline"}}')
        self.assertTrue(update_champion(result, manifest))
        self.assertNotIn("unverified_baseline", manifest.read_text())


if __name__ == "__main__":
    unittest.main()
