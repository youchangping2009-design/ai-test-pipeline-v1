from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_evals  # noqa: E402
from harness.contracts import validate_named  # noqa: E402
from run_eval_suite import (  # noqa: E402
    DEFAULT_CONFIG,
    DEFAULT_GOLDEN_BASELINE,
    baseline_snapshot,
    compare_baseline,
    read_json,
    run_suite,
)


def fake_fixture(fixture_id: str, passed: bool = True) -> dict[str, object]:
    return {
        "fixture_id": fixture_id,
        "passed": passed,
        "duration_ms": 1,
        "check_count": 2,
        "expected_failure_checks": 1,
        "fingerprint": "a" * 64,
        "output_tail": [],
    }


class EvalSuiteTests(unittest.TestCase):
    def test_tiers_are_ordered_and_golden_covers_regression(self) -> None:
        config = read_json(DEFAULT_CONFIG)
        tiers = config["tiers"]
        smoke = set(tiers["smoke"]["fixtures"])
        regression = set(tiers["regression"]["fixtures"])
        golden = set(tiers["golden"]["fixtures"])
        self.assertTrue(smoke < regression)
        self.assertEqual(regression, golden)
        self.assertGreaterEqual(len(regression), 5)
        for command in tiers["golden"]["commands"]:
            rendered = " ".join(command["argv"])
            self.assertNotIn("validate_work_item.py", rendered)
            self.assertNotIn("assets/projects/", rendered)

    def test_smoke_tier_passes_and_matches_report_contract(self) -> None:
        report = run_suite("smoke")
        self.assertTrue(report["passed"])
        self.assertEqual(report["metrics"]["fixture_count"], 3)
        self.assertGreater(report["metrics"]["check_count"], 0)
        self.assertGreater(report["metrics"]["expected_failure_checks"], 0)
        validate_named(report, "eval_suite_report.schema.json")

    def test_element_notation_negative_fixture_is_part_of_eval(self) -> None:
        self.assertEqual(run_evals.run_fixture("ELEMENT_NOTATION"), 0)

    def test_baseline_diff_detects_metric_and_fixture_drift(self) -> None:
        metrics = {
            "fixture_count": 1,
            "check_count": 2,
            "expected_failure_checks": 1,
            "command_count": 0,
        }
        current = baseline_snapshot("1.0.0", "golden", metrics, [fake_fixture("A")])
        expected = json.loads(json.dumps(current))
        expected["metrics"]["check_count"] = 3
        expected["fixture_fingerprints"]["A"] = "b" * 64
        differences = compare_baseline(current, expected)
        self.assertTrue(any("metrics.check_count" in item for item in differences))
        self.assertTrue(any("fixture_fingerprints.A" in item for item in differences))

    def test_missing_baseline_fails_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing.json"
            with patch("run_eval_suite.run_fixture", side_effect=lambda item: fake_fixture(item)):
                report = run_suite("smoke", baseline_path=missing)
        self.assertFalse(report["passed"])
        self.assertEqual(report["baseline"]["status"], "missing")

    def test_failed_eval_cannot_update_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            baseline = Path(temporary) / "baseline.json"
            with patch(
                "run_eval_suite.run_fixture",
                side_effect=lambda item: fake_fixture(item, passed=False),
            ):
                with self.assertRaisesRegex(ValueError, "禁止更新 baseline"):
                    run_suite("smoke", baseline_path=baseline, update_baseline=True)
            self.assertFalse(baseline.exists())

    def test_committed_golden_baseline_matches_current_suite(self) -> None:
        self.assertTrue(DEFAULT_GOLDEN_BASELINE.exists())
        config = read_json(DEFAULT_CONFIG)
        baseline = read_json(DEFAULT_GOLDEN_BASELINE)
        fixture_ids = config["tiers"]["golden"]["fixtures"]
        self.assertEqual(fixture_ids, list(baseline["fixture_fingerprints"]))
        self.assertEqual(baseline["metrics"]["fixture_count"], len(fixture_ids))
        for fingerprint in baseline["fixture_fingerprints"].values():
            self.assertRegex(fingerprint, r"^[a-f0-9]{64}$")
        self.assertEqual(
            baseline["metrics"]["command_count"],
            len(config["tiers"]["golden"]["commands"]),
        )


if __name__ == "__main__":
    unittest.main()
