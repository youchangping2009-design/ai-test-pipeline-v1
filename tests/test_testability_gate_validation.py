from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_DIR = ROOT / "skills" / "testability-gate" / "scripts"
if str(VALIDATOR_DIR) not in sys.path:
    sys.path.insert(0, str(VALIDATOR_DIR))

from validate_testability_gate import validate_gate  # noqa: E402


class TestabilityGateValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.structured_prd = {
            "requirement_info": {
                "explicit_rules": [
                    {
                        "rule_id": "REQ-001",
                        "rule_text": "保存后状态必须变为已生效。",
                    }
                ]
            },
            "modules": [],
        }
        self.gate = {
            "items": [
                {
                    "gate_id": "TG-001",
                    "source_rule_id": "REQ-001",
                    "source_text": "保存后状态必须变为已生效。",
                    "classification": "product_behavior",
                    "testability": "testable",
                    "decision": "generate_acceptance_example",
                    "reason": "可观察保存后的状态。",
                    "confidence": "confirmed",
                }
            ]
        }

    def test_source_text_matches_structured_rule(self) -> None:
        self.assertEqual(validate_gate(self.gate, self.structured_prd), [])

    def test_source_text_drift_is_rejected(self) -> None:
        self.gate["items"][0]["source_text"] = "保存后状态可能变为已生效。"

        errors = validate_gate(self.gate, self.structured_prd)

        self.assertTrue(any("source_text 与 structured_prd" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
