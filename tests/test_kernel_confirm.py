from pathlib import Path
import tempfile
import unittest

from rogii_eval.kernel_confirm import confirm_kernel


ROOT = Path(__file__).parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "candidate_screen"
KERNEL_INPUT = Path(__file__).parent / "fixtures" / "kernel_confirm" / "input"


class KernelConfirmTests(unittest.TestCase):
    def test_screened_candidate_passes_standalone_contract_twice(self) -> None:
        report = confirm_kernel(
            ROOT / "kaggle" / "kernel",
            KERNEL_INPUT,
            FIXTURE / "candidate.csv",
        )
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["promotion_eligible"])
        self.assertTrue(all(report["checks"].values()))
        self.assertEqual(report["artifact"]["output"], "submission.csv")
        self.assertEqual(report["artifact"]["wrapper_contract"], "kernel/version/output")
        self.assertFalse(report["kaggle_submission_performed"])

    def test_confirm_rejects_a_kernel_output_that_differs_from_screen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "candidate.csv"
            candidate.write_text("id,tvt\nwell-a_0,1\nwell-a_1,2\nwell-b_0,3\n")
            report = confirm_kernel(
                ROOT / "kaggle" / "kernel", KERNEL_INPUT, candidate
            )
        self.assertEqual(report["status"], "rejected")
        self.assertFalse(report["checks"]["matches_screened_candidate"])


if __name__ == "__main__":
    unittest.main()
