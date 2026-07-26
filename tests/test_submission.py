from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from rogii_eval.data import SchemaError, validate_submission
from rogii_eval.submission import build_tvt_input_submission


def write_csv(path: Path, columns: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)


class SubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.test_dir = self.root / "test"
        write_csv(
            self.test_dir / "abcd1234__horizontal_well.csv",
            ["MD", "X", "Y", "Z", "GR", "TVT_input"],
            [[1, 2, 3, 4, 5, 101.25], [2, 3, 4, 5, 6, ""]],
        )
        self.sample = self.root / "sample_submission.csv"
        write_csv(
            self.sample,
            ["id", "tvt"],
            [["abcd1234_1", 0], ["abcd1234_0", 0]],
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_build_preserves_sample_order_and_uses_zero_fallback(self) -> None:
        output = self.root / "submission.csv"
        self.assertEqual(
            build_tvt_input_submission(self.sample, self.test_dir, output), 2
        )
        with output.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            rows,
            [
                {"id": "abcd1234_1", "tvt": "0.0"},
                {"id": "abcd1234_0", "tvt": "101.25"},
            ],
        )
        self.assertEqual(validate_submission(output, ["abcd1234_1", "abcd1234_0"]), 2)

    def test_missing_sample_id_is_rejected(self) -> None:
        write_csv(self.sample, ["id", "tvt"], [["missing_0", 0]])
        with self.assertRaisesRegex(SchemaError, "no horizontal-well row"):
            build_tvt_input_submission(
                self.sample, self.test_dir, self.root / "submission.csv"
            )
