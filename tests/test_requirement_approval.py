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

from cleanup_derived_artifacts import MINIMAL_DERIVED_PATHS  # noqa: E402
from create_work_item import build_manifest  # noqa: E402
from harness.audit import HarnessRunAuditor  # noqa: E402
from harness.approval_service import RequirementApprovalService  # noqa: E402
from harness.generation_workspace import PUBLISH_FILES  # noqa: E402
from harness.orchestrator import DeterministicOrchestrator  # noqa: E402
from harness.requirement_approval import (  # noqa: E402
    RECEIPT_RELATIVE_PATH,
    validate_requirement_approval,
)
from harness.stage_registry import StageSpec  # noqa: E402
from harness.state_store import HarnessStateError, StateStore  # noqa: E402


ALL_LEVELS = frozenset({"S", "M", "L"})


def no_commands(
    _item_root: Path,
    _project_code: str,
    _work_item_id: str,
    _work_item_level: str,
    _strict: bool,
) -> list[list[str]]:
    return []


class RequirementApprovalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.item_root = Path(self.temporary.name) / "work_item"
        inputs = self.item_root / "inputs"
        images = inputs / "images"
        images.mkdir(parents=True)
        self.manifest = {
            "project_code": "DEMO",
            "work_item_id": "WI-001",
            "title": "审批测试",
            "requirement_version": "v1",
            "work_item_level": "S",
            "created_at": "2026-08-06T00:00:00+00:00",
            "status": "initialized",
            "pipeline_policy": {
                "requirement_intake_required": True,
                "requirement_approval_required": True,
                "testpoints_required": True,
            },
            "artifacts": {
                "inputs": "inputs/",
                "requirement_summary": "inputs/requirement_summary.md",
                "source_manifest": "inputs/source_manifest.json",
                "requirement_approval": RECEIPT_RELATIVE_PATH,
                "structured_prd": "structured_prd/structured_prd.json",
                "testcases": "testcases/testcases.md",
                "reviews": "reviews/review_record.md",
            },
        }
        self._write_manifest()
        (inputs / "requirement_summary.md").write_text(
            "# 已整理需求\n\n- 真实内容\n", encoding="utf-8"
        )
        (inputs / "source_manifest.json").write_text(
            json.dumps(
                {
                    "project_code": "DEMO",
                    "work_item_id": "WI-001",
                    "manifest_type": "requirement_source_manifest",
                    "summary_artifact": "inputs/requirement_summary.md",
                    "sources": [
                        {
                            "source_id": "SRC-001",
                            "source_type": "local_file",
                            "location": "inputs/images/01.png",
                            "access_status": "available",
                            "consumed": True,
                        }
                    ],
                    "unresolved_sources": [],
                }
            ),
            encoding="utf-8",
        )
        (images / "01.png").write_bytes(b"raw-image-v1")
        self.plan = [
            StageSpec(
                "requirement_intake",
                "validation",
                ALL_LEVELS,
                ("inputs/requirement_summary.md", "inputs/source_manifest.json"),
                no_commands,
            ),
            StageSpec(
                "evidence",
                "checkpoint",
                ALL_LEVELS,
                ("inputs/images/01.png",),
                no_commands,
            ),
        ]
        self.orchestrator = DeterministicOrchestrator(
            item_root=self.item_root,
            project_code="DEMO",
            work_item_id="WI-001",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_manifest(self) -> None:
        self.item_root.mkdir(parents=True, exist_ok=True)
        (self.item_root / "manifest.json").write_text(
            json.dumps(self.manifest), encoding="utf-8"
        )

    def _patch_plan(self):
        return (
            patch("harness.orchestrator.resolve_stage_plan", return_value=self.plan),
            patch(
                "harness.orchestrator.stage_ids",
                return_value=["requirement_intake", "evidence"],
            ),
        )

    def _start_waiting(self, run_id: str = "RUN-APPROVAL") -> dict:
        plan_patch, ids_patch = self._patch_plan()
        with plan_patch, ids_patch:
            code, state = self.orchestrator.start(
                run_id=run_id,
                work_item_level="S",
                strict=True,
                stop_at="evidence",
            )
        self.assertEqual(code, 0)
        self.assertEqual(state["status"], "waiting_approval")
        self.assertEqual(state["current_stage"], "requirement_intake")
        self.assertEqual(state["stages"][0]["status"], "waiting_approval")
        self.assertEqual(state["stages"][1]["attempts"], 0)
        return state

    def test_waiting_approval_blocks_resume_and_persists_bound_receipt(self) -> None:
        self._start_waiting()
        receipt = json.loads(
            (self.item_root / RECEIPT_RELATIVE_PATH).read_text(encoding="utf-8")
        )
        self.assertEqual(receipt["status"], "pending")
        self.assertEqual(receipt["run_id"], "RUN-APPROVAL")
        for key in (
            "approval_id",
            "requirement_summary_sha256",
            "source_manifest_sha256",
            "raw_inputs_fingerprint",
            "requirement_version",
        ):
            self.assertTrue(receipt[key])
        plan_patch, ids_patch = self._patch_plan()
        with plan_patch, ids_patch:
            with self.assertRaisesRegex(HarnessStateError, "pending"):
                self.orchestrator.resume(run_id="RUN-APPROVAL")

    def test_approve_allows_resume_and_repeated_approve_is_idempotent(self) -> None:
        self._start_waiting()
        service = RequirementApprovalService(self.item_root)
        state, receipt = service.approve(
            run_id="RUN-APPROVAL",
            reviewed_by="qa.owner",
            note="需求范围已核对",
        )
        self.assertEqual(state["status"], "paused")
        self.assertEqual(receipt["status"], "approved")
        first_reviewed_at = receipt["reviewed_at"]
        _, repeated = service.approve(
            run_id="RUN-APPROVAL",
            reviewed_by="qa.owner",
            note="需求范围已核对",
        )
        self.assertEqual(repeated["reviewed_at"], first_reviewed_at)
        with self.assertRaisesRegex(HarnessStateError, "冲突"):
            service.reject(
                run_id="RUN-APPROVAL",
                reviewed_by="qa.owner",
                note="冲突拒绝",
            )
        plan_patch, ids_patch = self._patch_plan()
        with plan_patch, ids_patch:
            code, completed = self.orchestrator.resume(run_id="RUN-APPROVAL")
        self.assertEqual(code, 0)
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["stages"][1]["attempts"], 1)

    def test_cancel_after_approval_remains_auditable(self) -> None:
        self._start_waiting()
        RequirementApprovalService(self.item_root).approve(
            run_id="RUN-APPROVAL",
            reviewed_by="qa.owner",
            note="需求范围已核对",
        )

        cancelled = self.orchestrator.cancel(run_id="RUN-APPROVAL")
        self.assertEqual(cancelled["status"], "cancelled")
        audit_code, report = HarnessRunAuditor(self.item_root).audit(
            "RUN-APPROVAL"
        )
        self.assertEqual(audit_code, 0, report["errors"])

    def test_runtime_manifest_changes_do_not_invalidate_approved_checkpoint(self) -> None:
        self._start_waiting()
        service = RequirementApprovalService(self.item_root)
        _, receipt = service.approve(
            run_id="RUN-APPROVAL",
            reviewed_by="qa.owner",
            note="需求内容已确认",
        )
        approved_at = receipt["reviewed_at"]
        self.manifest["status"] = "pipeline_running"
        self.manifest["quality_gate"] = {
            "enabled": False,
            "mode": "soft",
            "rollout_source": "runtime_update",
        }
        self.manifest["runtime_metadata"] = {
            "last_stage": "requirement_intake",
            "updated_at": "2026-08-06T10:00:00+00:00",
        }
        self._write_manifest()

        plan_patch, ids_patch = self._patch_plan()
        with plan_patch, ids_patch:
            code, completed = self.orchestrator.resume(
                run_id="RUN-APPROVAL",
                stop_at="evidence",
            )

        self.assertEqual(code, 0)
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["stages"][0]["attempts"], 1)
        persisted = json.loads(
            (self.item_root / RECEIPT_RELATIVE_PATH).read_text(encoding="utf-8")
        )
        self.assertEqual(persisted["status"], "approved")
        self.assertEqual(persisted["reviewed_at"], approved_at)
        audit_code, report = HarnessRunAuditor(self.item_root).audit(
            "RUN-APPROVAL"
        )
        self.assertEqual(audit_code, 0, report["errors"])

    def test_reject_is_terminal_and_reviewer_is_required(self) -> None:
        self._start_waiting()
        service = RequirementApprovalService(self.item_root)
        with self.assertRaisesRegex(HarnessStateError, "reviewed_by"):
            service.reject(
                run_id="RUN-APPROVAL",
                reviewed_by="",
                note="范围不清晰",
            )
        state, receipt = service.reject(
            run_id="RUN-APPROVAL",
            reviewed_by="qa.owner",
            note="范围不清晰",
        )
        self.assertEqual(state["status"], "cancelled")
        self.assertEqual(receipt["status"], "rejected")
        with self.assertRaises(HarnessStateError):
            self.orchestrator.resume(run_id="RUN-APPROVAL")

    def test_ci_cannot_self_approve(self) -> None:
        self._start_waiting()
        with patch.dict("os.environ", {"CI": "true"}):
            with self.assertRaisesRegex(HarnessStateError, "CI 环境不得自批准"):
                RequirementApprovalService(self.item_root).approve(
                    run_id="RUN-APPROVAL",
                    reviewed_by="ci-bot",
                    note="自动批准",
                )

    def test_any_bound_content_drift_invalidates_approval_and_checkpoint(self) -> None:
        for relative_path, content in (
            ("inputs/requirement_summary.md", "# changed\n"),
            ("inputs/source_manifest.json", '{"changed": true}\n'),
            ("inputs/images/01.png", b"raw-image-v2"),
            ("manifest.json", {"requirement_version": "v2"}),
        ):
            with self.subTest(relative_path=relative_path):
                self.tearDown()
                self.setUp()
                self._start_waiting()
                RequirementApprovalService(self.item_root).approve(
                    run_id="RUN-APPROVAL",
                    reviewed_by="qa.owner",
                    note="通过",
                )
                path = self.item_root / relative_path
                if relative_path == "manifest.json":
                    self.manifest.update(content)
                    self._write_manifest()
                elif isinstance(content, bytes):
                    path.write_bytes(content)
                else:
                    path.write_text(content, encoding="utf-8")
                plan_patch, ids_patch = self._patch_plan()
                with plan_patch, ids_patch:
                    with self.assertRaisesRegex(HarnessStateError, "漂移"):
                        self.orchestrator.resume(run_id="RUN-APPROVAL")
                state = StateStore(self.item_root).load("RUN-APPROVAL")
                self.assertEqual(state["status"], "waiting_approval")
                self.assertEqual(state["stages"][0]["status"], "waiting_approval")
                self.assertEqual(state["stages"][1]["status"], "pending")
                receipt = json.loads(
                    (self.item_root / RECEIPT_RELATIVE_PATH).read_text(encoding="utf-8")
                )
                self.assertEqual(receipt["status"], "pending")
                audit_code, report = HarnessRunAuditor(self.item_root).audit(
                    "RUN-APPROVAL"
                )
                self.assertEqual(audit_code, 0, report["errors"])

    def test_recover_completes_receipt_event_and_state_idempotently(self) -> None:
        self._start_waiting()
        service = RequirementApprovalService(self.item_root)
        state, receipt = service.approve(
            run_id="RUN-APPROVAL",
            reviewed_by="qa.owner",
            note="通过",
        )
        approved_at = receipt["reviewed_at"]
        self.manifest["status"] = "runtime_updated_after_approval"
        self.manifest["runtime_metadata"] = {"last_stage": "evidence"}
        self._write_manifest()
        store = StateStore(self.item_root)
        state["status"] = "waiting_approval"
        state["current_stage"] = "requirement_intake"
        state["stages"][0]["status"] = "waiting_approval"
        store.save(state)
        events_path = store.run_dir("RUN-APPROVAL") / "events.jsonl"
        events = [
            json.loads(line)
            for line in events_path.read_text(encoding="utf-8").splitlines()
        ]
        events = [
            event
            for event in events
            if event["event_type"] != "approval_resolved"
        ]
        for index, event in enumerate(events, start=1):
            event["sequence"] = index
        events_path.write_text(
            "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
            encoding="utf-8",
        )
        recovered_state, recovered_receipt = service.recover(
            run_id="RUN-APPROVAL"
        )
        self.assertEqual(recovered_state["status"], "paused")
        self.assertEqual(recovered_receipt["status"], "approved")
        repeated_state, _ = service.recover(run_id="RUN-APPROVAL")
        self.assertEqual(repeated_state["status"], "paused")
        final_events = [
            json.loads(line)
            for line in events_path.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(
            sum(
                event["event_type"] == "approval_resolved"
                for event in final_events
            ),
            1,
        )
        plan_patch, ids_patch = self._patch_plan()
        with plan_patch, ids_patch:
            code, completed = self.orchestrator.resume(
                run_id="RUN-APPROVAL",
                stop_at="evidence",
            )
        self.assertEqual(code, 0)
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["stages"][0]["attempts"], 1)
        final_receipt = json.loads(
            (self.item_root / RECEIPT_RELATIVE_PATH).read_text(encoding="utf-8")
        )
        self.assertEqual(final_receipt["reviewed_at"], approved_at)
        audit_code, report = HarnessRunAuditor(self.item_root).audit(
            "RUN-APPROVAL"
        )
        self.assertEqual(audit_code, 0, report["errors"])

    def test_strict_policy_compatibility_and_binding_validation(self) -> None:
        legacy_manifest = dict(self.manifest)
        legacy_manifest["pipeline_policy"] = {
            "requirement_intake_required": True,
            "testpoints_required": True,
        }
        self.assertEqual(
            validate_requirement_approval(self.item_root, legacy_manifest), []
        )
        errors = validate_requirement_approval(self.item_root, self.manifest)
        self.assertTrue(any("requirement_approval.json" in error for error in errors))
        self._start_waiting()
        RequirementApprovalService(self.item_root).approve(
            run_id="RUN-APPROVAL",
            reviewed_by="qa.owner",
            note="通过",
        )
        self.assertEqual(
            validate_requirement_approval(self.item_root, self.manifest), []
        )
        (self.item_root / "inputs" / "images" / "01.png").write_bytes(b"drift")
        errors = validate_requirement_approval(self.item_root, self.manifest)
        self.assertTrue(any("fingerprint" in error for error in errors))

    def test_audit_detects_missing_event_state_mismatch_and_hash_drift(self) -> None:
        self._start_waiting()
        code, report = HarnessRunAuditor(self.item_root).audit("RUN-APPROVAL")
        self.assertEqual(code, 0, report["errors"])
        events_path = (
            self.item_root
            / ".generation/runs/RUN-APPROVAL/events.jsonl"
        )
        events = [
            json.loads(line)
            for line in events_path.read_text(encoding="utf-8").splitlines()
        ]
        events = [
            event
            for event in events
            if event["event_type"] != "approval_requested"
        ]
        for index, event in enumerate(events, start=1):
            event["sequence"] = index
        events_path.write_text(
            "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
            encoding="utf-8",
        )
        code, report = HarnessRunAuditor(self.item_root).audit("RUN-APPROVAL")
        self.assertEqual(code, 1)
        self.assertTrue(any("requirement_approval" in error for error in report["errors"]))
        RequirementApprovalService(self.item_root).recover(run_id="RUN-APPROVAL")
        store = StateStore(self.item_root)
        mismatched = store.load("RUN-APPROVAL")
        mismatched["status"] = "paused"
        store.save(mismatched)
        code, report = HarnessRunAuditor(self.item_root).audit("RUN-APPROVAL")
        self.assertEqual(code, 1)
        self.assertTrue(
            any("run state 不一致" in error for error in report["errors"])
        )
        RequirementApprovalService(self.item_root).recover(run_id="RUN-APPROVAL")
        (self.item_root / "inputs" / "images" / "01.png").write_bytes(b"drift")
        code, report = HarnessRunAuditor(self.item_root).audit("RUN-APPROVAL")
        self.assertEqual(code, 1)
        self.assertTrue(
            any(
                "hash/fingerprint/run 已漂移" in error
                for error in report["errors"]
            )
        )

    def test_cleanup_and_generation_cannot_remove_or_publish_receipt(self) -> None:
        self.assertNotIn(RECEIPT_RELATIVE_PATH, MINIMAL_DERIVED_PATHS)
        self.assertNotIn(RECEIPT_RELATIVE_PATH, PUBLISH_FILES)

    def test_new_manifest_defaults_to_required_and_declares_receipt(self) -> None:
        manifest = json.loads(
            build_manifest("DEMO", "WI-NEW", "title", "v1", "M")
        )
        self.assertIs(
            manifest["pipeline_policy"]["requirement_approval_required"],
            True,
        )
        self.assertEqual(
            manifest["artifacts"]["requirement_approval"],
            RECEIPT_RELATIVE_PATH,
        )


if __name__ == "__main__":
    unittest.main()
