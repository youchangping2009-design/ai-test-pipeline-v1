from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from harness.agent_loop import CasePlanAgentLoop  # noqa: E402
from harness.approval_service import CasePlanApprovalService  # noqa: E402
from harness.artifact_workspace import (  # noqa: E402
    ArtifactWorkspaceError,
    CasePlanArtifactWorkspace,
    file_hash,
)
from harness.audit import HarnessRunAuditor  # noqa: E402
from harness.hook_dispatcher import HookDispatcher  # noqa: E402
from harness.model_gateway import ModelTurnResult  # noqa: E402
from harness.state_store import HarnessStateError, atomic_write_json  # noqa: E402
from harness.telemetry import BudgetConfig  # noqa: E402


SOURCE_ITEM = ROOT / "tests" / "fixtures" / "runtime_work_item"


def action(
    action_id: str,
    action_type: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "action_type": action_type,
        "stage_id": "case_plan",
        "arguments": arguments,
        "expected_outcome": "test",
    }


class EchoCasePlanGateway:
    def next_action(self, request: dict[str, Any]) -> dict[str, Any]:
        turn = int(request["turn"])
        if turn == 1:
            return action(
                "ACT-READ",
                "read_artifact",
                {"path": "testcases/case_plan.json"},
            )
        if turn == 2:
            content = request["observations"][-1]["result"]["content"]
            return action(
                "ACT-PROPOSE",
                "propose_artifacts",
                {
                    "path": "testcases/case_plan.json",
                    "content": json.loads(content),
                },
            )
        if turn == 3:
            return action("ACT-VALIDATE", "run_stage_validation", {})
        return action("ACT-COMMIT", "commit_stage", {})


class InvalidRepairGateway:
    def next_action(self, request: dict[str, Any]) -> dict[str, Any]:
        turn = int(request["turn"])
        if turn % 2 == 1:
            return action(
                f"ACT-PROPOSE-{turn}",
                "propose_artifacts",
                {
                    "path": "testcases/case_plan.json",
                    "content": {"case_plans": []},
                },
            )
        return action(
            f"ACT-VALIDATE-{turn}",
            "run_stage_validation",
            {},
        )


class InvalidActionGateway:
    def next_action(self, request: dict[str, Any]) -> dict[str, Any]:
        return action(
            f"ACT-INVALID-{request['turn']}",
            "arbitrary_shell",
            {"command": "echo forbidden"},
        )


class UsageEchoCasePlanGateway:
    def __init__(self) -> None:
        self.delegate = EchoCasePlanGateway()

    def next_action(self, request: dict[str, Any]) -> ModelTurnResult:
        return ModelTurnResult(
            action=self.delegate.next_action(request),
            usage={
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
                "cost_usd": 0.001,
            },
            runtime={"provider": "unit-test", "model": "fixture-model"},
        )


class CasePlanAgentLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.item_root = Path(self.temporary.name) / "work_item"
        self._copy_case_plan_inputs(self.item_root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _pending_commit(self, run_id: str):
        loop = CasePlanAgentLoop(
            item_root=self.item_root,
            project_code="DEMO",
            work_item_id="WI-001",
            work_item_level="M",
            gateway=EchoCasePlanGateway(),
        )
        code, state = loop.run(run_id)
        self.assertEqual(code, 0)
        self.assertEqual(state["status"], "waiting_approval")
        run_dir = (
            self.item_root / ".generation" / "runs" / run_id
        )
        approval_path = next((run_dir / "approvals").glob("*.json"))
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        workspace = CasePlanArtifactWorkspace(
            item_root=self.item_root,
            run_dir=run_dir,
            work_item_level="M",
        )
        return (
            CasePlanApprovalService(self.item_root),
            workspace,
            approval_path,
            approval,
        )

    def test_workspace_rejects_path_traversal(self) -> None:
        workspace = CasePlanArtifactWorkspace(
            item_root=self.item_root,
            run_dir=Path(self.temporary.name) / "run-traversal",
            work_item_level="M",
        )
        with self.assertRaises(ArtifactWorkspaceError):
            workspace.read_artifact("../manifest.json")
        with self.assertRaises(ArtifactWorkspaceError):
            workspace.read_artifact("reviews/quality_report.json")

    def test_real_case_plan_candidate_passes_staging_validator(self) -> None:
        workspace = CasePlanArtifactWorkspace(
            item_root=self.item_root,
            run_dir=Path(self.temporary.name) / "run-validate",
            work_item_level="M",
        )
        payload = json.loads(
            (self.item_root / "testcases" / "case_plan.json").read_text(
                encoding="utf-8"
            )
        )
        workspace.propose_case_plan(payload)
        result = workspace.validate_candidate()
        self.assertTrue(result.passed)
        self.assertEqual(result.exit_code, 0)

    def test_commit_rejects_target_hash_drift(self) -> None:
        workspace = CasePlanArtifactWorkspace(
            item_root=self.item_root,
            run_dir=Path(self.temporary.name) / "run-drift",
            work_item_level="M",
        )
        payload = json.loads(
            (self.item_root / "testcases" / "case_plan.json").read_text(
                encoding="utf-8"
            )
        )
        workspace.propose_case_plan(payload)
        self.assertTrue(workspace.validate_candidate().passed)
        atomic_write_json(
            self.item_root / "testcases" / "case_plan.json",
            {"case_plans": [{"external": "change"}]},
        )
        with self.assertRaises(ArtifactWorkspaceError):
            workspace.commit_validated_candidate()

    def test_default_agent_loop_stages_and_requests_approval(self) -> None:
        target = self.item_root / "testcases" / "case_plan.json"
        before = target.read_bytes()
        loop = CasePlanAgentLoop(
            item_root=self.item_root,
            project_code="DEMO",
            work_item_id="WI-001",
            work_item_level="M",
            gateway=EchoCasePlanGateway(),
        )
        code, state = loop.run("RUN-STAGING")
        self.assertEqual(code, 0)
        self.assertEqual(state["status"], "waiting_approval")
        self.assertEqual(target.read_bytes(), before)
        approvals = list(
            (
                self.item_root
                / ".generation"
                / "runs"
                / "RUN-STAGING"
                / "approvals"
            ).glob("*.json")
        )
        self.assertEqual(len(approvals), 1)
        approval = json.loads(approvals[0].read_text(encoding="utf-8"))
        self.assertEqual(approval["status"], "pending")
        self.assertEqual(approval["requested_action"], "commit_stage")
        telemetry = json.loads(
            (
                self.item_root
                / ".generation"
                / "runs"
                / "RUN-STAGING"
                / "telemetry.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(telemetry["model_calls"], 4)
        self.assertFalse(telemetry["usage_complete"])
        audit_code, report = HarnessRunAuditor(self.item_root).audit(
            "RUN-STAGING"
        )
        self.assertEqual(audit_code, 0)
        self.assertTrue(report["passed"])

    def test_explicit_commit_completes_with_backup(self) -> None:
        target = self.item_root / "testcases" / "case_plan.json"
        before_hash = file_hash(target)
        loop = CasePlanAgentLoop(
            item_root=self.item_root,
            project_code="DEMO",
            work_item_id="WI-001",
            work_item_level="M",
            gateway=EchoCasePlanGateway(),
        )
        code, waiting = loop.run("RUN-COMMIT")
        self.assertEqual(code, 0)
        self.assertEqual(waiting["status"], "waiting_approval")
        approval_path = next(
            (
                self.item_root
                / ".generation"
                / "runs"
                / "RUN-COMMIT"
                / "approvals"
            ).glob("*.json")
        )
        pending = json.loads(approval_path.read_text(encoding="utf-8"))
        service = CasePlanApprovalService(self.item_root)
        state, approval = service.approve(
            run_id="RUN-COMMIT",
            approval_id=pending["approval_id"],
            candidate_hash=pending["candidate_hash"],
            approved_by="unit-test",
        )
        self.assertEqual(state["status"], "completed")
        self.assertEqual(approval["status"], "approved")
        backup = (
            self.item_root
            / ".generation"
            / "runs"
            / "RUN-COMMIT"
            / "backups"
            / "testcases"
            / "case_plan.json"
        )
        self.assertTrue(backup.exists())
        self.assertEqual(file_hash(backup), before_hash)
        self.assertEqual(
            json.loads(target.read_text(encoding="utf-8")),
            json.loads(backup.read_text(encoding="utf-8")),
        )
        invalidations = json.loads(
            (
                self.item_root
                / ".generation"
                / "runs"
                / "RUN-COMMIT"
                / "downstream_invalidations.json"
            ).read_text(encoding="utf-8")
        )
        self.assertIn("testcases", invalidations["invalidated_stages"])
        self.assertIn("strict_gate", invalidations["invalidated_stages"])
        audit_code, report = HarnessRunAuditor(self.item_root).audit(
            "RUN-COMMIT"
        )
        self.assertEqual(audit_code, 0)
        self.assertTrue(report["passed"])

    def test_recover_prepared_commit_rolls_back_to_pending(self) -> None:
        target = self.item_root / "testcases" / "case_plan.json"
        before = target.read_bytes()
        service, workspace, _, approval = self._pending_commit(
            "RUN-RECOVER-PREPARED"
        )
        workspace.prepare_commit(
            approval_id=approval["approval_id"],
            approved_by="unit-test",
        )
        state, recovered_approval, transaction = service.recover(
            run_id="RUN-RECOVER-PREPARED"
        )
        self.assertEqual(transaction["status"], "rolled_back")
        self.assertEqual(recovered_approval["status"], "pending")
        self.assertEqual(state["status"], "waiting_approval")
        self.assertEqual(target.read_bytes(), before)
        audit_code, report = HarnessRunAuditor(self.item_root).audit(
            "RUN-RECOVER-PREPARED"
        )
        self.assertEqual(audit_code, 0, report["errors"])

    def test_reject_requires_unfinished_commit_recovery_first(self) -> None:
        service, workspace, _, approval = self._pending_commit(
            "RUN-REJECT-UNFINISHED"
        )
        workspace.prepare_commit(
            approval_id=approval["approval_id"],
            approved_by="unit-test",
        )
        with self.assertRaisesRegex(
            HarnessStateError,
            "recover-case-plan",
        ):
            service.reject(
                run_id="RUN-REJECT-UNFINISHED",
                approval_id=approval["approval_id"],
                rejected_by="unit-test",
                reason="must recover first",
            )

    def test_approve_retries_after_rolled_back_recovery(self) -> None:
        service, workspace, _, approval = self._pending_commit(
            "RUN-RETRY-COMMIT"
        )
        workspace.prepare_commit(
            approval_id=approval["approval_id"],
            approved_by="first-attempt",
        )
        service.recover(run_id="RUN-RETRY-COMMIT")
        state, resolved = service.approve(
            run_id="RUN-RETRY-COMMIT",
            approval_id=approval["approval_id"],
            candidate_hash=approval["candidate_hash"],
            approved_by="second-attempt",
        )
        self.assertEqual(state["status"], "completed")
        self.assertEqual(resolved["resolved_by"], "second-attempt")
        transaction = workspace.read_commit_transaction()
        self.assertEqual(transaction["status"], "committed")
        self.assertEqual(transaction["attempt"], 2)

    def test_recover_committing_restores_partially_replaced_target(self) -> None:
        target = self.item_root / "testcases" / "case_plan.json"
        before = target.read_bytes()
        service, workspace, _, approval = self._pending_commit(
            "RUN-RECOVER-COMMITTING"
        )
        transaction = workspace.prepare_commit(
            approval_id=approval["approval_id"],
            approved_by="unit-test",
        )
        transaction["status"] = "committing"
        workspace._write_commit_transaction(transaction)
        target.write_text("partially replaced", encoding="utf-8")
        self.assertNotEqual(file_hash(target), transaction["expected_target_hash"])
        _, recovered_approval, transaction = service.recover(
            run_id="RUN-RECOVER-COMMITTING"
        )
        self.assertEqual(transaction["status"], "rolled_back")
        self.assertEqual(recovered_approval["status"], "pending")
        self.assertEqual(target.read_bytes(), before)

    def test_recover_committed_transaction_finalizes_metadata_idempotently(
        self,
    ) -> None:
        service, workspace, _, approval = self._pending_commit(
            "RUN-RECOVER-COMMITTED"
        )
        transaction = workspace.prepare_commit(
            approval_id=approval["approval_id"],
            approved_by="unit-test",
        )
        workspace.apply_commit(transaction)
        audit_code, _ = HarnessRunAuditor(self.item_root).audit(
            "RUN-RECOVER-COMMITTED"
        )
        self.assertEqual(audit_code, 1)
        state, recovered_approval, transaction = service.recover(
            run_id="RUN-RECOVER-COMMITTED"
        )
        self.assertEqual(transaction["status"], "committed")
        self.assertEqual(recovered_approval["status"], "approved")
        self.assertEqual(state["status"], "completed")
        state, recovered_approval, _ = service.recover(
            run_id="RUN-RECOVER-COMMITTED"
        )
        self.assertEqual(state["status"], "completed")
        events = (
            workspace.run_dir / "events.jsonl"
        ).read_text(encoding="utf-8")
        self.assertEqual(events.count('"event_type": "run_completed"'), 1)
        audit_code, report = HarnessRunAuditor(self.item_root).audit(
            "RUN-RECOVER-COMMITTED"
        )
        self.assertEqual(audit_code, 0, report["errors"])

    def test_recovery_refuses_missing_case_plan_backup(self) -> None:
        service, workspace, _, approval = self._pending_commit(
            "RUN-RECOVER-NO-BACKUP"
        )
        transaction = workspace.prepare_commit(
            approval_id=approval["approval_id"],
            approved_by="unit-test",
        )
        transaction["status"] = "committing"
        workspace._write_commit_transaction(transaction)
        Path(transaction["backup_path"]).unlink()
        with self.assertRaisesRegex(
            ArtifactWorkspaceError,
            "缺少回滚备份",
        ):
            service.recover(run_id="RUN-RECOVER-NO-BACKUP")

    def test_recovery_refuses_tampered_backup_before_restore(self) -> None:
        target = self.item_root / "testcases" / "case_plan.json"
        service, workspace, _, approval = self._pending_commit(
            "RUN-RECOVER-BACKUP-DRIFT"
        )
        transaction = workspace.prepare_commit(
            approval_id=approval["approval_id"],
            approved_by="unit-test",
        )
        transaction["status"] = "committing"
        workspace._write_commit_transaction(transaction)
        target.write_text("partial target", encoding="utf-8")
        Path(transaction["backup_path"]).write_text(
            "tampered backup",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            ArtifactWorkspaceError,
            "回滚备份 hash 不一致",
        ):
            service.recover(run_id="RUN-RECOVER-BACKUP-DRIFT")
        self.assertEqual(target.read_text(encoding="utf-8"), "partial target")

    def test_recovery_refuses_committed_target_drift(self) -> None:
        service, workspace, _, approval = self._pending_commit(
            "RUN-RECOVER-TARGET-DRIFT"
        )
        transaction = workspace.prepare_commit(
            approval_id=approval["approval_id"],
            approved_by="unit-test",
        )
        workspace.apply_commit(transaction)
        workspace.target_path.write_text("drift", encoding="utf-8")
        with self.assertRaisesRegex(
            HarnessStateError,
            "正式 Case Plan hash 已漂移",
        ):
            service.recover(run_id="RUN-RECOVER-TARGET-DRIFT")

    def test_approval_rejects_wrong_candidate_hash(self) -> None:
        target = self.item_root / "testcases" / "case_plan.json"
        before = target.read_bytes()
        loop = CasePlanAgentLoop(
            item_root=self.item_root,
            project_code="DEMO",
            work_item_id="WI-001",
            work_item_level="M",
            gateway=EchoCasePlanGateway(),
        )
        loop.run("RUN-WRONG-HASH")
        approval_path = next(
            (
                self.item_root
                / ".generation"
                / "runs"
                / "RUN-WRONG-HASH"
                / "approvals"
            ).glob("*.json")
        )
        pending = json.loads(approval_path.read_text(encoding="utf-8"))
        service = CasePlanApprovalService(self.item_root)
        with self.assertRaises(HarnessStateError):
            service.approve(
                run_id="RUN-WRONG-HASH",
                approval_id=pending["approval_id"],
                candidate_hash="wrong-hash",
                approved_by="unit-test",
            )
        self.assertEqual(target.read_bytes(), before)

    def test_budget_stops_before_over_budget_action(self) -> None:
        loop = CasePlanAgentLoop(
            item_root=self.item_root,
            project_code="DEMO",
            work_item_id="WI-001",
            work_item_level="M",
            gateway=UsageEchoCasePlanGateway(),
            budget=BudgetConfig(
                max_model_calls=8,
                max_total_tokens=50,
            ),
        )
        code, state = loop.run("RUN-TOKEN-BUDGET")
        self.assertEqual(code, 0)
        self.assertEqual(state["status"], "waiting_approval")
        telemetry = json.loads(
            (
                self.item_root
                / ".generation"
                / "runs"
                / "RUN-TOKEN-BUDGET"
                / "telemetry.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(telemetry["stop_reason"], "token_budget_exhausted")
        self.assertEqual(telemetry["model_calls"], 1)
        self.assertEqual(telemetry["action_counts"], {})

    def test_reject_approval_cancels_run_without_commit(self) -> None:
        target = self.item_root / "testcases" / "case_plan.json"
        before = target.read_bytes()
        loop = CasePlanAgentLoop(
            item_root=self.item_root,
            project_code="DEMO",
            work_item_id="WI-001",
            work_item_level="M",
            gateway=EchoCasePlanGateway(),
        )
        loop.run("RUN-REJECT")
        approval_path = next(
            (
                self.item_root
                / ".generation"
                / "runs"
                / "RUN-REJECT"
                / "approvals"
            ).glob("*.json")
        )
        pending = json.loads(approval_path.read_text(encoding="utf-8"))
        state, approval = CasePlanApprovalService(self.item_root).reject(
            run_id="RUN-REJECT",
            approval_id=pending["approval_id"],
            rejected_by="unit-test",
            reason="候选需要产品确认",
        )
        self.assertEqual(state["status"], "cancelled")
        self.assertEqual(approval["status"], "rejected")
        self.assertEqual(target.read_bytes(), before)
        audit_code, _ = HarnessRunAuditor(self.item_root).audit("RUN-REJECT")
        self.assertEqual(audit_code, 0)

    def test_approval_requested_and_resolved_hooks_are_dispatched(self) -> None:
        hook_root = Path(self.temporary.name) / "hook_repo"
        handlers = hook_root / "scripts" / "hooks"
        handlers.mkdir(parents=True)
        (handlers / "echo.py").write_text(
            "import json, sys\n"
            "request = json.load(sys.stdin)\n"
            "print(json.dumps({'event': request['event']}))\n",
            encoding="utf-8",
        )
        config_path = hook_root / "config" / "harness_hooks.json"
        config_path.parent.mkdir(parents=True)
        hooks = []
        for hook_id, event in (
            ("approval-requested", "approval_requested"),
            ("approval-resolved", "approval_resolved"),
        ):
            hooks.append(
                {
                    "hook_id": hook_id,
                    "enabled": True,
                    "event": event,
                    "stages": ["case_plan"],
                    "handler": "scripts/hooks/echo.py",
                    "failure_policy": "warn",
                    "timeout_seconds": 5,
                    "max_output_chars": 4096,
                }
            )
        config_path.write_text(
            json.dumps({"schema_version": "1.0.0", "hooks": hooks}),
            encoding="utf-8",
        )
        dispatcher = HookDispatcher(
            repository_root=hook_root,
            config_path=config_path,
        )
        loop = CasePlanAgentLoop(
            item_root=self.item_root,
            project_code="DEMO",
            work_item_id="WI-001",
            work_item_level="M",
            gateway=EchoCasePlanGateway(),
            hooks=dispatcher,
        )
        loop.run("RUN-APPROVAL-HOOKS")
        run_dir = (
            self.item_root
            / ".generation"
            / "runs"
            / "RUN-APPROVAL-HOOKS"
        )
        approval_path = next((run_dir / "approvals").glob("*.json"))
        pending = json.loads(approval_path.read_text(encoding="utf-8"))
        requested = list(
            (run_dir / "hooks").glob("approval-requested-*.json")
        )
        self.assertEqual(len(requested), 1)
        CasePlanApprovalService(
            self.item_root,
            hooks=dispatcher,
        ).reject(
            run_id="RUN-APPROVAL-HOOKS",
            approval_id=pending["approval_id"],
            rejected_by="unit-test",
            reason="仅验证 Hook",
        )
        resolved = list(
            (run_dir / "hooks").glob("approval-resolved-*.json")
        )
        self.assertEqual(len(resolved), 1)
        audit_code, report = HarnessRunAuditor(self.item_root).audit(
            "RUN-APPROVAL-HOOKS"
        )
        self.assertEqual(audit_code, 0)
        self.assertEqual(report["counts"]["hooks"], 2)

    def test_audit_detects_tampered_event_sequence(self) -> None:
        loop = CasePlanAgentLoop(
            item_root=self.item_root,
            project_code="DEMO",
            work_item_id="WI-001",
            work_item_level="M",
            gateway=EchoCasePlanGateway(),
        )
        loop.run("RUN-AUDIT-TAMPER")
        events_path = (
            self.item_root
            / ".generation"
            / "runs"
            / "RUN-AUDIT-TAMPER"
            / "events.jsonl"
        )
        lines = events_path.read_text(encoding="utf-8").splitlines()
        first = json.loads(lines[0])
        first["sequence"] = 99
        lines[0] = json.dumps(first)
        events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        audit_code, report = HarnessRunAuditor(self.item_root).audit(
            "RUN-AUDIT-TAMPER"
        )
        self.assertEqual(audit_code, 1)
        self.assertFalse(report["passed"])
        self.assertTrue(
            any("sequence" in error for error in report["errors"])
        )

    def test_audit_detects_missing_action_document(self) -> None:
        loop = CasePlanAgentLoop(
            item_root=self.item_root,
            project_code="DEMO",
            work_item_id="WI-001",
            work_item_level="M",
            gateway=EchoCasePlanGateway(),
        )
        loop.run("RUN-ACTION-LINKAGE")
        run_dir = (
            self.item_root
            / ".generation"
            / "runs"
            / "RUN-ACTION-LINKAGE"
        )
        next((run_dir / "actions").glob("*.json")).unlink()
        audit_code, report = HarnessRunAuditor(self.item_root).audit(
            "RUN-ACTION-LINKAGE"
        )
        self.assertEqual(audit_code, 1)
        self.assertTrue(
            any("action_linkage" in error for error in report["errors"])
        )

    def test_repair_budget_exhaustion_requests_approval(self) -> None:
        loop = CasePlanAgentLoop(
            item_root=self.item_root,
            project_code="DEMO",
            work_item_id="WI-001",
            work_item_level="M",
            gateway=InvalidRepairGateway(),
            max_repairs=2,
        )
        code, state = loop.run("RUN-REPAIR-EXHAUSTED")
        self.assertEqual(code, 0)
        self.assertEqual(state["status"], "waiting_approval")
        agent_state = json.loads(
            (
                self.item_root
                / ".generation"
                / "runs"
                / "RUN-REPAIR-EXHAUSTED"
                / "agent_state.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(agent_state["failed_validations"], 3)
        self.assertEqual(agent_state["repair_rounds_used"], 2)

    def test_turn_budget_exhaustion_requests_approval(self) -> None:
        loop = CasePlanAgentLoop(
            item_root=self.item_root,
            project_code="DEMO",
            work_item_id="WI-001",
            work_item_level="M",
            gateway=InvalidActionGateway(),
            max_turns=2,
        )
        code, state = loop.run("RUN-TURN-EXHAUSTED")
        self.assertEqual(code, 0)
        self.assertEqual(state["status"], "waiting_approval")
        approvals = list(
            (
                self.item_root
                / ".generation"
                / "runs"
                / "RUN-TURN-EXHAUSTED"
                / "approvals"
            ).glob("*.json")
        )
        approval = json.loads(approvals[0].read_text(encoding="utf-8"))
        self.assertEqual(
            approval["requested_action"],
            "turn_budget_exhausted",
        )

    @staticmethod
    def _copy_case_plan_inputs(item_root: Path) -> None:
        paths = [
            "manifest.json",
            "acceptance/testability_gate.json",
            "acceptance/acceptance_examples.json",
            "design/verification_responsibility_map.json",
            "testcases/case_plan.json",
        ]
        for relative_path in paths:
            source = SOURCE_ITEM / relative_path
            target = item_root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        manifest_path = item_root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["project_code"] = "DEMO"
        manifest["work_item_id"] = "WI-001"
        manifest.setdefault("pipeline_policy", {})[
            "requirement_approval_required"
        ] = False
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
