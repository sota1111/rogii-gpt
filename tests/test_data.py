from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from rogii_eval.data import (
    SchemaError,
    discover_wells,
    validate_submission,
    write_submission,
)


def write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


class DataTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_discovers_and_validates_pair(self) -> None:
        write_csv(
            self.root / "abcdef01__horizontal_well.csv",
            ["MD", "X", "Y", "Z", "TVT", "GR", "TVT_input"],
            [[1, 2, 3, 4, 5, 6, 7]],
        )
        write_csv(
            self.root / "abcdef01__typewell.csv",
            ["TVT", "GR", "Geology"],
            [[1, 2, "sand"]],
        )
        self.assertEqual(discover_wells(self.root)[0].well_id, "abcdef01")

    def test_rejects_missing_schema_column(self) -> None:
        write_csv(
            self.root / "abcdef01__horizontal_well.csv",
            ["MD", "X", "Y", "Z", "TVT", "TVT_input"],
            [[1, 2, 3, 4, 5, 7]],
        )
        write_csv(
            self.root / "abcdef01__typewell.csv",
            ["TVT", "GR", "Geology"],
            [[1, 2, ""]],
        )
        with self.assertRaisesRegex(SchemaError, "GR"):
            discover_wells(self.root)

    def test_allows_missing_gr_but_not_missing_target(self) -> None:
        write_csv(
            self.root / "abcdef01__horizontal_well.csv",
            ["MD", "X", "Y", "Z", "TVT", "GR", "TVT_input"],
            [[1, 2, 3, 4, 5, "", 7]],
        )
        write_csv(
            self.root / "abcdef01__typewell.csv",
            ["TVT", "GR", "Geology"],
            [[1, "", ""]],
        )
        self.assertEqual(len(discover_wells(self.root)), 1)

    def test_submission_round_trip_and_duplicate_rejection(self) -> None:
        output = self.root / "submission.csv"
        write_submission(output, ["a_0", "b_0"], [1.25, 2.5])
        self.assertEqual(validate_submission(output), 2)
        write_csv(output, ["id", "tvt"], [["a", 1], ["a", 2]])
        with self.assertRaisesRegex(SchemaError, "duplicate id"):
            validate_submission(output)

    def test_submission_requires_exact_columns(self) -> None:
        output = self.root / "submission.csv"
        write_csv(output, ["index", "id", "tvt"], [[0, "a", 1]])
        with self.assertRaisesRegex(SchemaError, "exactly id,tvt"):
            validate_submission(output)


if __name__ == "__main__":
    unittest.main()
