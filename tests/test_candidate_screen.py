from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from rogii_eval.candidate_screen import discover_sample, screen_candidate
from rogii_eval.submission import build_tvt_input_submission


FIXTURE = Path(__file__).parent / "fixtures" / "candidate_screen"


def write_candidate(path: Path, rows: list[list[object]], columns=None) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns or ["id", "tvt"])
        writer.writerows(rows)


class CandidateScreenTests(unittest.TestCase):
    def test_valid_fixture_passes_and_records_fingerprint(self) -> None:
        report = screen_candidate(FIXTURE / "input", FIXTURE / "candidate.csv")
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["promotion_eligible"])
        self.assertEqual(report["next_gate"], "confirm")
        self.assertEqual(report["evidence"]["candidate_rows"], 3)
        self.assertEqual(len(report["evidence"]["candidate_sha256"]), 64)
        self.assertTrue(all(report["checks"].values()))

    def test_existing_candidate_exec_output_passes_screen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "submission.csv"
            rows = build_tvt_input_submission(
                FIXTURE / "input" / "competition" / "sample_submission.csv",
                FIXTURE / "test",
                output,
            )
            report = screen_candidate(FIXTURE / "input", output)
        self.assertEqual(rows, 3)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["next_gate"], "confirm")

    def test_duplicate_sample_discovery_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("a", "b"):
                target = root / name
                target.mkdir()
                (target / "sample_submission.csv").write_text("id,tvt\na,0\n")
            with self.assertRaisesRegex(ValueError, "exactly one"):
                discover_sample(root)

    def test_schema_row_ids_and_values_fail_closed(self) -> None:
        cases = [
            ([['well-a_0', 1], ['well-a_0', 2], ['well-b_0', 3]], None, "ids_nonempty_unique"),
            ([['well-a_1', 1], ['well-a_0', 2], ['well-b_0', 3]], None, "ids_match_sample_order"),
            ([['well-a_0', 1]], None, "row_count"),
            ([['well-a_0', 'NaN'], ['well-a_1', 2], ['well-b_0', 3]], None, "tvt_numeric_finite_nonmissing"),
            ([['well-a_0', 1], ['well-a_1', 2], ['well-b_0', 3]], ["id", "prediction"], "candidate_schema"),
        ]
        for rows, columns, failed_check in cases:
            with self.subTest(failed_check=failed_check), tempfile.TemporaryDirectory() as directory:
                candidate = Path(directory) / "candidate.csv"
                write_candidate(candidate, rows, columns)
                report = screen_candidate(FIXTURE / "input", candidate)
                self.assertEqual(report["status"], "rejected")
                self.assertFalse(report["promotion_eligible"])
                self.assertIsNone(report["next_gate"])
                self.assertFalse(report["checks"][failed_check])


if __name__ == "__main__":
    unittest.main()
