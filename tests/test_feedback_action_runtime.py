from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from harness.feedback_action_runtime import (  # noqa: E402
    FeedbackActionDispatchError,
    FeedbackApplicationActionRuntime,
)
from harness.audit import HarnessRunAuditor  # noqa: E402
from harness.state_store import StateStore  # noqa: E402
from harness.stage_registry import resolve_stage_plan  # noqa: E402
from validate_feedback_action_journal import (  # noqa: E402
    request_sha256,
    validate_feedback_action_journal,
)


class FeedbackActionRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.item_root = Path(self.temporary.name)
        (self.item_root / "design").mkdir()
        (self.item_root / "testcases").mkdir()
        (self.item_root / "manifest.json").write_text(
            json.dumps(
                {
                    "project_code": "P",
                    "work_item_id": "W",
                    "pipeline_policy": {
                        "feedback_application_receipt_required": True,
                        "feedback_action_journal_required": True,
                        "feedback_action_execution_identity_required": True,
                    }
                }
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
                            "finding": "补强已批准需求断言",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.case_plan = self.item_root / "testcases" / "case_plan.json"
        self.case_plan.write_text('{"version": 1}\n', encoding="utf-8")
        (self.item_root / "testcases" / "case_plan.md").write_text(
            "# version 1\n", encoding="utf-8"
        )
        self.run_id = "RUN-FEEDBACK-001"
        StateStore(self.item_root).create(
            run_id=self.run_id,
            project_code="P",
            work_item_id="W",
            work_item_level="M",
            strict=True,
            stop_at="review",
            stages=resolve_stage_plan("M"),
            mode="agent",
        )
        self.runtime = FeedbackApplicationActionRuntime(
            item_root=self.item_root,
            run_id=self.run_id,
            actor="qa-owner",
            provider="unit-test-provider",
        )

    @staticmethod
    def action(action_type: str, arguments: dict) -> dict:
        return {
            "action_id": f"ACT-{action_type}",
            "action_type": action_type,
            "stage_id": "design_feedback_application",
            "feedback_id": "DF-001",
            "arguments": arguments,
            "expected_outcome": "完成受限反馈动作",
        }

    def test_restricted_lifecycle_applies_only_after_record(self) -> None:
        prepared = self.runtime.dispatch(
            self.action("prepare_feedback_application", {})
        )
        self.assertEqual(prepared["result"]["status"], "prepared")

        proposed = self.runtime.dispatch(
            self.action(
                "propose_feedback_design_artifacts",
                {"artifacts": {"testcases/case_plan.json": {"version": 2}}},
            )
        )
        self.assertEqual(proposed["result"]["paths"], ["testcases/case_plan.json"])
        feedback_before_record = json.loads(
            (self.item_root / "design" / "design_feedback.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            feedback_before_record["feedback_items"][0]["status"], "accepted"
        )

        recorded = self.runtime.dispatch(
            self.action("record_feedback_application", {})
        )
        self.assertEqual(recorded["result"]["status"], "applied")
        audit = validate_feedback_action_journal(self.item_root)
        self.assertEqual(
            audit,
            {
                "status": "verified",
                "actions": 3,
                "feedbacks": 1,
                "failed_actions": 0,
                "execution_identity_status": "verified",
                "run_ids": [self.run_id],
                "actors": ["qa-owner"],
                "providers": ["unit-test-provider"],
                "actions_by_run": {self.run_id: 3},
            },
        )

    def test_journal_binds_run_actor_and_provider(self) -> None:
        action = self.action("prepare_feedback_application", {})
        self.runtime.dispatch(action)
        action_dir = (
            self.item_root / ".generation" / "feedback_applications" / "actions"
        )
        intent = json.loads(
            (action_dir / f"{action['action_id']}.intent.json").read_text(
                encoding="utf-8"
            )
        )
        result = json.loads(
            (action_dir / f"{action['action_id']}.result.json").read_text(
                encoding="utf-8"
            )
        )
        expected = {
            "run_id": self.run_id,
            "actor": "qa-owner",
            "provider": "unit-test-provider",
        }
        self.assertEqual(intent["schema_version"], "1.1.0")
        self.assertEqual(intent["execution_context"], expected)
        self.assertEqual(result["execution_context"], expected)

    def test_harness_run_audit_counts_bound_feedback_actions(self) -> None:
        self.runtime.dispatch(self.action("prepare_feedback_application", {}))
        self.runtime.dispatch(
            self.action(
                "propose_feedback_design_artifacts",
                {"artifacts": {"testcases/case_plan.json": {"version": 2}}},
            )
        )
        self.runtime.dispatch(self.action("record_feedback_application", {}))

        code, report = HarnessRunAuditor(self.item_root).audit(self.run_id)
        self.assertEqual(code, 0, report["errors"])
        self.assertIn("feedback_action_journal", report["checks"])
        self.assertEqual(report["counts"]["feedback_actions"], 3)

    def test_action_id_cannot_be_reused_by_another_actor(self) -> None:
        action = self.action("prepare_feedback_application", {})
        self.runtime.dispatch(action)
        other = FeedbackApplicationActionRuntime(
            item_root=self.item_root,
            run_id=self.run_id,
            actor="another-actor",
            provider="unit-test-provider",
        )
        with self.assertRaisesRegex(
            FeedbackActionDispatchError, "action_id 已绑定不同请求"
        ):
            other.dispatch(action)

    def test_rejects_missing_or_mismatched_harness_run(self) -> None:
        missing = FeedbackApplicationActionRuntime(
            item_root=self.item_root,
            run_id="RUN-MISSING",
            actor="qa-owner",
            provider="unit-test-provider",
        )
        with self.assertRaisesRegex(FeedbackActionDispatchError, "执行上下文无效"):
            missing.dispatch(self.action("prepare_feedback_application", {}))

        StateStore(self.item_root).create(
            run_id="RUN-OTHER-WORK-ITEM",
            project_code="P",
            work_item_id="OTHER",
            work_item_level="M",
            strict=True,
            stop_at="review",
            stages=resolve_stage_plan("M"),
            mode="agent",
        )
        mismatched = FeedbackApplicationActionRuntime(
            item_root=self.item_root,
            run_id="RUN-OTHER-WORK-ITEM",
            actor="qa-owner",
            provider="unit-test-provider",
        )
        with self.assertRaisesRegex(FeedbackActionDispatchError, "work_item_id"):
            mismatched.dispatch(self.action("prepare_feedback_application", {}))

    def test_completed_action_is_idempotent_by_action_id(self) -> None:
        action = self.action("prepare_feedback_application", {})
        first = self.runtime.dispatch(action)
        second = self.runtime.dispatch(action)
        self.assertEqual(first, second)
        action_dir = (
            self.item_root / ".generation" / "feedback_applications" / "actions"
        )
        self.assertEqual(len(list(action_dir.glob("*.intent.json"))), 1)
        self.assertEqual(len(list(action_dir.glob("*.result.json"))), 1)

    def test_reuses_unfinished_intent_to_recover_prepare(self) -> None:
        action = self.action("prepare_feedback_application", {})
        self.runtime.dispatch(action)
        result_path = (
            self.item_root
            / ".generation"
            / "feedback_applications"
            / "actions"
            / f"{action['action_id']}.result.json"
        )
        result_path.unlink()

        recovered = self.runtime.dispatch(action)
        self.assertEqual(recovered["result"]["status"], "prepared")
        self.assertTrue(result_path.is_file())

    def test_rejects_action_id_reuse_with_different_request(self) -> None:
        action = self.action("prepare_feedback_application", {})
        self.runtime.dispatch(action)
        conflict = self.action(
            "prepare_feedback_application", {"targets": ["testcases/case_plan.json"]}
        )
        with self.assertRaisesRegex(
            FeedbackActionDispatchError, "action_id 已绑定不同请求"
        ):
            self.runtime.dispatch(conflict)

    def test_audit_rejects_unfinished_intent(self) -> None:
        action = self.action("prepare_feedback_application", {})
        self.runtime.dispatch(action)
        result_path = (
            self.item_root
            / ".generation"
            / "feedback_applications"
            / "actions"
            / f"{action['action_id']}.result.json"
        )
        result_path.unlink()
        with self.assertRaisesRegex(ValueError, "未完成"):
            validate_feedback_action_journal(self.item_root)

    def test_failed_action_has_terminal_result_and_can_be_replaced(self) -> None:
        failed = self.action(
            "propose_feedback_design_artifacts",
            {"artifacts": {"testcases/case_plan.json": {"version": 2}}},
        )
        with self.assertRaises(FeedbackActionDispatchError):
            self.runtime.dispatch(failed)
        action_dir = (
            self.item_root / ".generation" / "feedback_applications" / "actions"
        )
        self.assertTrue((action_dir / f"{failed['action_id']}.result.json").is_file())

        prepare = self.action("prepare_feedback_application", {})
        prepare["action_id"] = "ACT-PREPARE-RETRY"
        self.runtime.dispatch(prepare)
        proposed = self.action(
            "propose_feedback_design_artifacts",
            {"artifacts": {"testcases/case_plan.json": {"version": 2}}},
        )
        proposed["action_id"] = "ACT-PROPOSE-RETRY"
        self.runtime.dispatch(proposed)
        record = self.action("record_feedback_application", {})
        record["action_id"] = "ACT-RECORD-RETRY"
        self.runtime.dispatch(record)

        audit = validate_feedback_action_journal(self.item_root)
        self.assertEqual(audit["failed_actions"], 1)

    def test_audit_rejects_tampered_result_binding(self) -> None:
        action = self.action("prepare_feedback_application", {})
        self.runtime.dispatch(action)
        result_path = (
            self.item_root
            / ".generation"
            / "feedback_applications"
            / "actions"
            / f"{action['action_id']}.result.json"
        )
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["request_sha256"] = "0" * 64
        result_path.write_text(json.dumps(result), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "request hash"):
            validate_feedback_action_journal(self.item_root)

    def test_audit_rejects_tampered_execution_identity(self) -> None:
        action = self.action("prepare_feedback_application", {})
        self.runtime.dispatch(action)
        result_path = (
            self.item_root
            / ".generation"
            / "feedback_applications"
            / "actions"
            / f"{action['action_id']}.result.json"
        )
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["execution_context"]["actor"] = "tampered-actor"
        result_path.write_text(json.dumps(result), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "execution_context"):
            validate_feedback_action_journal(self.item_root)

    def test_audit_rejects_one_feedback_spanning_multiple_runs(self) -> None:
        self.runtime.dispatch(self.action("prepare_feedback_application", {}))
        second_run_id = "RUN-FEEDBACK-002"
        StateStore(self.item_root).create(
            run_id=second_run_id,
            project_code="P",
            work_item_id="W",
            work_item_level="M",
            strict=True,
            stop_at="review",
            stages=resolve_stage_plan("M"),
            mode="agent",
        )
        second_runtime = FeedbackApplicationActionRuntime(
            item_root=self.item_root,
            run_id=second_run_id,
            actor="reviewer",
            provider="manual-review",
        )
        propose = self.action(
            "propose_feedback_design_artifacts",
            {"artifacts": {"testcases/case_plan.json": {"version": 2}}},
        )
        propose["action_id"] = "ACT-PROPOSE-SECOND-RUN"
        second_runtime.dispatch(propose)
        record = self.action("record_feedback_application", {})
        record["action_id"] = "ACT-RECORD-SECOND-RUN"
        second_runtime.dispatch(record)
        with self.assertRaisesRegex(ValueError, "跨 Harness run"):
            validate_feedback_action_journal(self.item_root)

    def test_required_policy_rejects_applied_feedback_without_journal(self) -> None:
        feedback_path = self.item_root / "design" / "design_feedback.json"
        feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
        feedback["feedback_items"][0]["status"] = "applied"
        feedback_path.write_text(json.dumps(feedback), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "要求 applied feedback"):
            validate_feedback_action_journal(self.item_root)

    def test_legacy_applied_feedback_without_journal_is_compatible(self) -> None:
        manifest_path = self.item_root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["pipeline_policy"].pop("feedback_action_journal_required")
        manifest["pipeline_policy"].pop(
            "feedback_action_execution_identity_required"
        )
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        feedback_path = self.item_root / "design" / "design_feedback.json"
        feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
        feedback["feedback_items"][0]["status"] = "applied"
        feedback_path.write_text(json.dumps(feedback), encoding="utf-8")

        result = validate_feedback_action_journal(self.item_root)
        self.assertEqual(result["status"], "legacy_compatible")

    def test_legacy_v1_failed_journal_remains_readable(self) -> None:
        manifest_path = self.item_root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        action = self.action("propose_feedback_design_artifacts", {})
        action_dir = (
            self.item_root / ".generation" / "feedback_applications" / "actions"
        )
        action_dir.mkdir(parents=True, exist_ok=True)
        request_hash = request_sha256(action)
        intent = {
            "schema_version": "1.0.0",
            "record_type": "intent",
            "action_id": action["action_id"],
            "request_sha256": request_hash,
            "action": action,
            "recorded_at": "2026-09-22T00:00:00+00:00",
        }
        result = {
            "schema_version": "1.0.0",
            "record_type": "result",
            "action_id": action["action_id"],
            "request_sha256": request_hash,
            "observation": {
                "ok": False,
                "action_type": action["action_type"],
                "result": {"error": "legacy failure"},
            },
            "recorded_at": "2026-09-22T00:00:01+00:00",
        }
        (action_dir / f"{action['action_id']}.intent.json").write_text(
            json.dumps(intent), encoding="utf-8"
        )
        (action_dir / f"{action['action_id']}.result.json").write_text(
            json.dumps(result), encoding="utf-8"
        )

        with self.assertRaisesRegex(ValueError, "要求 action 绑定执行身份"):
            validate_feedback_action_journal(self.item_root)

        manifest["pipeline_policy"].pop(
            "feedback_action_execution_identity_required"
        )
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        audit = validate_feedback_action_journal(self.item_root)
        self.assertEqual(audit["status"], "legacy_compatible")
        self.assertEqual(audit["execution_identity_status"], "legacy_compatible")

    def test_rejects_direct_feedback_status_write(self) -> None:
        self.runtime.dispatch(self.action("prepare_feedback_application", {}))
        with self.assertRaisesRegex(
            FeedbackActionDispatchError, "未被 prepare 冻结"
        ):
            self.runtime.dispatch(
                self.action(
                    "propose_feedback_design_artifacts",
                    {
                        "artifacts": {
                            "design/design_feedback.json": {
                                "feedback_items": [{"status": "applied"}]
                            }
                        }
                    },
                )
            )

    def test_rejects_testcase_output_write(self) -> None:
        self.runtime.dispatch(self.action("prepare_feedback_application", {}))
        with self.assertRaisesRegex(
            FeedbackActionDispatchError, "未被 prepare 冻结"
        ):
            self.runtime.dispatch(
                self.action(
                    "propose_feedback_design_artifacts",
                    {"artifacts": {"testcases/testcases_main.md": "forbidden"}},
                )
            )

    def test_rejects_propose_before_prepare(self) -> None:
        with self.assertRaises(FeedbackActionDispatchError):
            self.runtime.dispatch(
                self.action(
                    "propose_feedback_design_artifacts",
                    {"artifacts": {"testcases/case_plan.json": {"version": 2}}},
                )
            )

    def test_schema_rejects_arbitrary_shell(self) -> None:
        with self.assertRaises(FeedbackActionDispatchError):
            self.runtime.dispatch(self.action("arbitrary_shell", {"command": "true"}))


if __name__ == "__main__":
    unittest.main()
