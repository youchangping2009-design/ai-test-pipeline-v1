from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from manage_feedback_application import prepare_application, record_application  # noqa: E402
from validate_feedback_application import validate_feedback_application  # noqa: E402


class ManageFeedbackApplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.item_root = Path(self.temporary.name)
        (self.item_root / "design").mkdir()
        (self.item_root / "testcases").mkdir()
        (self.item_root / "manifest.json").write_text(
            json.dumps(
                {"pipeline_policy": {"feedback_application_receipt_required": True}}
            ),
            encoding="utf-8",
        )
        (self.item_root / "design" / "design_feedback.json").write_text(
            json.dumps(
                {
                    "project_code": "P",
                    "work_item_id": "W",
                    "feedback_items": [
                        {
                            "feedback_id": "DF-001",
                            "target_layer": "case_plan",
                            "status": "accepted",
                            "finding": "明确可验证行为",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.json_target = self.item_root / "testcases" / "case_plan.json"
        self.md_target = self.item_root / "testcases" / "case_plan.md"
        self.json_target.write_text('{"version": 1}\n', encoding="utf-8")
        self.md_target.write_text("# version 1\n", encoding="utf-8")

    def test_prepare_then_record_captures_real_hashes_and_applies(self) -> None:
        snapshot = prepare_application(self.item_root, "DF-001")
        self.json_target.write_text('{"version": 2}\n', encoding="utf-8")
        self.md_target.write_text("# version 2\n", encoding="utf-8")
        receipt = record_application(self.item_root, "DF-001")

        self.assertTrue(snapshot.is_file())
        self.assertTrue(receipt.is_file())
        feedback = json.loads(
            (self.item_root / "design" / "design_feedback.json").read_text(encoding="utf-8")
        )
        self.assertEqual(feedback["feedback_items"][0]["status"], "applied")
        result = validate_feedback_application(self.item_root)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["artifact_count"], 2)

    def test_prepare_rejects_testcase_output_path(self) -> None:
        with self.assertRaisesRegex(ValueError, "不属于 case_plan"):
            prepare_application(
                self.item_root,
                "DF-001",
                ["testcases/testcases_main.md"],
            )

    def test_record_rejects_no_design_change(self) -> None:
        prepare_application(self.item_root, "DF-001")
        with self.assertRaisesRegex(ValueError, "没有发生变化"):
            record_application(self.item_root, "DF-001")

    def test_record_rejects_feedback_drift(self) -> None:
        prepare_application(self.item_root, "DF-001")
        feedback_path = self.item_root / "design" / "design_feedback.json"
        feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
        feedback["feedback_items"][0]["finding"] = "prepare 后被改写"
        feedback_path.write_text(json.dumps(feedback), encoding="utf-8")
        self.json_target.write_text('{"version": 2}\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "内容在 prepare 后发生漂移"):
            record_application(self.item_root, "DF-001")

    def test_record_is_idempotent_after_receipt_first_interruption(self) -> None:
        prepare_application(self.item_root, "DF-001")
        self.json_target.write_text('{"version": 2}\n', encoding="utf-8")
        self.md_target.write_text("# version 2\n", encoding="utf-8")
        record_application(self.item_root, "DF-001")
        feedback_path = self.item_root / "design" / "design_feedback.json"
        feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
        feedback["feedback_items"][0]["status"] = "accepted"
        feedback_path.write_text(json.dumps(feedback), encoding="utf-8")

        record_application(self.item_root, "DF-001")
        recovered = json.loads(feedback_path.read_text(encoding="utf-8"))
        self.assertEqual(recovered["feedback_items"][0]["status"], "applied")


if __name__ == "__main__":
    unittest.main()
