from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_feedback_application import validate_feedback_application  # noqa: E402


class FeedbackApplicationValidationTests(unittest.TestCase):
    def _item(self, target_layer: str = "case_plan") -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        (root / "design").mkdir()
        (root / "testcases").mkdir()
        (root / "manifest.json").write_text(
            json.dumps(
                {"pipeline_policy": {"feedback_application_receipt_required": True}}
            ),
            encoding="utf-8",
        )
        target = root / "testcases" / "case_plan.json"
        target.write_text('{"changed": true}\n', encoding="utf-8")
        after = hashlib.sha256(target.read_bytes()).hexdigest()
        feedback = {
            "project_code": "P",
            "work_item_id": "W",
            "feedback_items": [
                {"feedback_id": "DF-001", "target_layer": target_layer, "status": "applied"}
            ],
        }
        receipt = {
            "project_code": "P",
            "work_item_id": "W",
            "applications": [
                {
                    "feedback_id": "DF-001",
                    "target_layer": target_layer,
                    "artifacts": [
                        {
                            "path": "testcases/case_plan.json",
                            "before_sha256": "0" * 64,
                            "after_sha256": after,
                        }
                    ],
                }
            ],
        }
        (root / "design" / "design_feedback.json").write_text(
            json.dumps(feedback), encoding="utf-8"
        )
        (root / "design" / "feedback_application.json").write_text(
            json.dumps(receipt), encoding="utf-8"
        )
        return temporary, root

    def test_accepts_target_design_layer_with_current_hash(self) -> None:
        temporary, root = self._item()
        self.addCleanup(temporary.cleanup)
        result = validate_feedback_application(root)
        self.assertEqual(
            result,
            {"status": "verified", "application_count": 1, "artifact_count": 1},
        )

    def test_rejects_direct_testcase_write(self) -> None:
        temporary, root = self._item()
        self.addCleanup(temporary.cleanup)
        receipt_path = root / "design" / "feedback_application.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["applications"][0]["artifacts"][0]["path"] = "testcases/testcases_main.md"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "非法路径"):
            validate_feedback_application(root)

    def test_rejects_stale_after_hash(self) -> None:
        temporary, root = self._item()
        self.addCleanup(temporary.cleanup)
        (root / "testcases" / "case_plan.json").write_text("drift\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "链尾 after_sha256"):
            validate_feedback_application(root)

    def test_accepts_sequential_applications_to_same_artifact(self) -> None:
        temporary, root = self._item()
        self.addCleanup(temporary.cleanup)
        target = root / "testcases" / "case_plan.json"
        first_after = hashlib.sha256(target.read_bytes()).hexdigest()
        target.write_text('{"changed": "twice"}\n', encoding="utf-8")
        second_after = hashlib.sha256(target.read_bytes()).hexdigest()

        feedback_path = root / "design" / "design_feedback.json"
        feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
        feedback["feedback_items"].append(
            {"feedback_id": "DF-002", "target_layer": "case_plan", "status": "applied"}
        )
        feedback_path.write_text(json.dumps(feedback), encoding="utf-8")

        receipt_path = root / "design" / "feedback_application.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["applications"].append(
            {
                "feedback_id": "DF-002",
                "target_layer": "case_plan",
                "artifacts": [
                    {
                        "path": "testcases/case_plan.json",
                        "before_sha256": first_after,
                        "after_sha256": second_after,
                    }
                ],
            }
        )
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

        result = validate_feedback_application(root)
        self.assertEqual(result["application_count"], 2)
        self.assertEqual(result["artifact_count"], 2)

    def test_rejects_broken_sequential_application_hash_chain(self) -> None:
        temporary, root = self._item()
        self.addCleanup(temporary.cleanup)
        target = root / "testcases" / "case_plan.json"
        target.write_text('{"changed": "twice"}\n', encoding="utf-8")
        second_after = hashlib.sha256(target.read_bytes()).hexdigest()

        feedback_path = root / "design" / "design_feedback.json"
        feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
        feedback["feedback_items"].append(
            {"feedback_id": "DF-002", "target_layer": "case_plan", "status": "applied"}
        )
        feedback_path.write_text(json.dumps(feedback), encoding="utf-8")

        receipt_path = root / "design" / "feedback_application.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["applications"].append(
            {
                "feedback_id": "DF-002",
                "target_layer": "case_plan",
                "artifacts": [
                    {
                        "path": "testcases/case_plan.json",
                        "before_sha256": "f" * 64,
                        "after_sha256": second_after,
                    }
                ],
            }
        )
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "hash 链断裂"):
            validate_feedback_application(root)

    def test_rejects_non_hex_before_hash(self) -> None:
        temporary, root = self._item()
        self.addCleanup(temporary.cleanup)
        receipt_path = root / "design" / "feedback_application.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["applications"][0]["artifacts"][0]["before_sha256"] = "g" * 64
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "64 位 sha256"):
            validate_feedback_application(root)

    def test_rejects_applied_feedback_without_receipt(self) -> None:
        temporary, root = self._item()
        self.addCleanup(temporary.cleanup)
        feedback_path = root / "design" / "design_feedback.json"
        feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
        feedback["feedback_items"].append(
            {"feedback_id": "DF-002", "target_layer": "case_plan", "status": "applied"}
        )
        feedback_path.write_text(json.dumps(feedback), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "缺少回灌凭证"):
            validate_feedback_application(root)

    def test_required_policy_rejects_missing_receipt(self) -> None:
        temporary, root = self._item()
        self.addCleanup(temporary.cleanup)
        (root / "design" / "feedback_application.json").unlink()
        with self.assertRaisesRegex(ValueError, "policy 要求"):
            validate_feedback_application(root)

    def test_legacy_applied_feedback_without_policy_remains_compatible(self) -> None:
        temporary, root = self._item()
        self.addCleanup(temporary.cleanup)
        (root / "design" / "feedback_application.json").unlink()
        (root / "manifest.json").write_text("{}\n", encoding="utf-8")
        result = validate_feedback_application(root)
        self.assertEqual(result["status"], "legacy_compatible")


if __name__ == "__main__":
    unittest.main()
