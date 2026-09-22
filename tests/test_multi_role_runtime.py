from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from harness.artifact_workspace import ArtifactWorkspaceError, file_hash  # noqa: E402
from harness.audit import HarnessRunAuditor  # noqa: E402
from harness.generation_workspace import ControlledGenerationError  # noqa: E402
from harness.model_gateway import ModelTurnResult  # noqa: E402
from harness.multi_role_runtime import MultiRoleAgentRuntime  # noqa: E402
from harness.role_workspace import (  # noqa: E402
    ROLE_BY_STAGE,
    ROLE_SPECS,
    MultiRoleArtifactWorkspace,
)
from harness.telemetry import BudgetConfig  # noqa: E402
from harness.state_store import HarnessStateError, atomic_write_json  # noqa: E402


SOURCE_ITEM = ROOT / "tests" / "fixtures" / "runtime_work_item"


def role_action(
    request: dict,
    action_type: str,
    arguments: dict,
) -> dict:
    return {
        "action_id": f"{request['stage_id']}-{request['turn']}-{action_type}",
        "action_type": action_type,
        "stage_id": request["stage_id"],
        "arguments": arguments,
        "expected_outcome": "unit test",
    }


class EchoRoleGateway:
    targets = {
        "prd_structurer": "structured_prd/structured_prd.json",
        "case_generator": "testcases/testcases_main.md",
        "case_reviewer": "reviews/review_record.md",
        "asset_formatter": "feishu_ready.md",
    }

    def next_action(self, request: dict) -> ModelTurnResult:
        turn = int(request["turn"])
        stage_id = request["stage_id"]
        target = self.targets[stage_id]
        if stage_id == "prd_structurer" and turn == 1:
            action = role_action(
                request,
                "read_artifact",
                {"path": "structured_prd/structured_prd.md"},
            )
        elif stage_id == "prd_structurer" and turn == 2:
            action = role_action(
                request,
                "read_artifact",
                {"path": "structured_prd/structured_prd.json"},
            )
        elif stage_id == "prd_structurer" and turn == 3:
            markdown = request["observations"][-2]["result"]["content"]
            json_content = request["observations"][-1]["result"]["content"]
            action = role_action(
                request,
                "propose_artifacts",
                {
                    "artifacts": {
                        "structured_prd/structured_prd.md": markdown,
                        "structured_prd/structured_prd.json": json_content,
                    }
                },
            )
        elif stage_id == "prd_structurer" and turn == 4:
            action = role_action(request, "run_stage_validation", {})
        elif stage_id == "prd_structurer":
            action = role_action(request, "finish_stage", {})
        elif turn == 1:
            action = role_action(request, "read_artifact", {"path": target})
        elif turn == 2:
            content = request["observations"][-1]["result"]["content"]
            action = role_action(
                request,
                "propose_artifacts",
                {"artifacts": {target: content}},
            )
        elif turn == 3:
            action = role_action(request, "run_stage_validation", {})
        else:
            action = role_action(request, "finish_stage", {})
        return ModelTurnResult(
            action=action,
            usage={
                "input_tokens": 1,
                "output_tokens": 1,
                "total_tokens": 2,
                "cost_usd": 0.0,
            },
            runtime={"provider": "unit-test", "model": "echo-role"},
        )


class ReadOnlyGateway:
    def next_action(self, request: dict) -> ModelTurnResult:
        return ModelTurnResult(
            action=role_action(
                request,
                "read_artifact",
                {"path": "structured_prd/structured_prd.json"},
            ),
            usage={
                "input_tokens": 1,
                "output_tokens": 1,
                "total_tokens": 2,
                "cost_usd": 0.0,
            },
            runtime={"provider": "unit-test", "model": "read-only"},
        )


class InvalidPRDGateway:
    def next_action(self, request: dict) -> ModelTurnResult:
        turn = int(request["turn"])
        if turn % 2:
            action = role_action(
                request,
                "propose_artifacts",
                {
                    "artifacts": {
                        "structured_prd/structured_prd.md": "# invalid\n",
                        "structured_prd/structured_prd.json": {},
                    }
                },
            )
        else:
            action = role_action(request, "run_stage_validation", {})
        return ModelTurnResult(
            action=action,
            usage={
                "input_tokens": 1,
                "output_tokens": 1,
                "total_tokens": 2,
                "cost_usd": 0.0,
            },
            runtime={"provider": "unit-test", "model": "invalid-prd"},
        )


class CrashRoleGateway:
    def next_action(self, request: dict) -> ModelTurnResult:
        raise RuntimeError(
            f"simulated crash in {request['stage_id']}"
        )


class MultiRoleRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.item_root = Path(self.temporary.name) / "work_item"
        shutil.copytree(
            SOURCE_ITEM,
            self.item_root,
            ignore=lambda _directory, names: {".generation"}.intersection(names),
        )
        manifest_path = self.item_root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.setdefault("pipeline_policy", {})[
            "requirement_approval_required"
        ] = False
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (self.item_root / "inputs" / "requirement_approval.json").unlink(
            missing_ok=True
        )
        feishu_ready_path = self.item_root / "feishu_ready.md"
        if not feishu_ready_path.exists():
            feishu_ready_path.write_text("# Feishu Ready\n", encoding="utf-8")
        self.run_dir = (
            self.item_root / ".generation" / "runs" / "RUN-ROLE-TEST"
        )
        self.base_bundle = self._build_base_bundle()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _build_base_bundle(self) -> dict:
        prefix = "assets/projects/FIXTURE/work_items/FIXTURE-RUNTIME-001/"
        artifacts: dict[str, str] = {}
        allowed_prefixes = (
            "analysis/",
            "evidence/",
            "image_evidence/",
            "structured_prd/",
            "coverage/",
            "acceptance/",
            "design/",
            "testcases/",
            "traceability/",
            "reviews/",
        )
        allowed_files = {
            "inputs/requirement_summary.md",
            "inputs/source_manifest.json",
            "feishu_ready.md",
        }
        for path in sorted(
            candidate for candidate in self.item_root.rglob("*") if candidate.is_file()
        ):
            relative = path.relative_to(self.item_root).as_posix()
            if relative.startswith(".generation/"):
                continue
            if relative in allowed_files or relative.startswith(allowed_prefixes):
                artifacts[prefix + relative] = path.read_text(encoding="utf-8")
        return {
            "provider": "existing",
            "work_item_level": "M",
            "cleanup_targets": list(artifacts),
            "artifacts": artifacts,
        }

    def _workspace(self) -> MultiRoleArtifactWorkspace:
        return MultiRoleArtifactWorkspace(
            item_root=self.item_root,
            run_dir=self.run_dir,
            project_code="FIXTURE",
            work_item_id="FIXTURE-RUNTIME-001",
            work_item_level="M",
            base_bundle=self.base_bundle,
        )

    def _runtime(
        self,
        gateway,
        budget=None,
        *,
        parallel_reviewers: bool = False,
    ) -> MultiRoleAgentRuntime:
        return MultiRoleAgentRuntime(
            item_root=self.item_root,
            project_code="FIXTURE",
            work_item_id="FIXTURE-RUNTIME-001",
            work_item_level="M",
            gateway=gateway,
            budget=budget,
            parallel_reviewers=parallel_reviewers,
        )

    def _create_serial_crash(self) -> MultiRoleAgentRuntime:
        runtime = self._runtime(CrashRoleGateway())
        with patch.object(
            runtime,
            "_prepare_base_bundle",
            return_value=self.base_bundle,
        ):
            with self.assertRaisesRegex(RuntimeError, "simulated crash"):
                runtime.run(run_id="RUN-ROLE-TEST")
        state = runtime.store.load("RUN-ROLE-TEST")
        self.assertEqual(state["status"], "running")
        return runtime

    def test_role_order_and_write_boundaries_are_fixed(self) -> None:
        self.assertEqual(
            [spec.stage_id for spec in ROLE_SPECS],
            [
                "prd_structurer",
                "case_generator",
                "case_reviewer",
                "asset_formatter",
            ],
        )
        workspace = self._workspace()
        reviewer = ROLE_BY_STAGE["case_reviewer"]
        formatter = ROLE_BY_STAGE["asset_formatter"]
        with self.assertRaises(ArtifactWorkspaceError):
            workspace.propose_artifacts(
                reviewer,
                {"testcases/testcases_main.md": "forbidden"},
            )
        with self.assertRaises(ArtifactWorkspaceError):
            workspace.propose_artifacts(
                formatter,
                {"structured_prd/structured_prd.json": {}},
            )
        with self.assertRaises(ArtifactWorkspaceError):
            workspace.read_artifact(
                ROLE_BY_STAGE["prd_structurer"],
                "../manifest.json",
            )
        workspace.propose_artifacts(
            ROLE_BY_STAGE["prd_structurer"],
            {"structured_prd/structured_prd.json": {}},
        )
        with self.assertRaisesRegex(ArtifactWorkspaceError, "同步提交"):
            workspace.validate_role(ROLE_BY_STAGE["prd_structurer"])

    def test_recover_crashed_role_is_idempotent_and_auditable(self) -> None:
        runtime = self._create_serial_crash()
        state, recovery = runtime.recover(
            run_id="RUN-ROLE-TEST",
            recovered_by="unit-test",
            reason="simulated process crash",
        )
        self.assertEqual(state["status"], "cancelled")
        self.assertEqual(recovery["status"], "completed")
        self.assertEqual(
            [stage["status"] for stage in state["stages"]],
            ["skipped", "skipped", "skipped", "skipped"],
        )
        state, repeated = runtime.recover(
            run_id="RUN-ROLE-TEST",
            recovered_by="ignored-on-repeat",
            reason="idempotent retry",
        )
        self.assertEqual(state["status"], "cancelled")
        self.assertEqual(repeated["recovery_id"], recovery["recovery_id"])
        events = [
            json.loads(line)
            for line in (self.run_dir / "events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        self.assertEqual(
            sum(
                event["event_type"] == "multi_role_run_recovered"
                for event in events
            ),
            1,
        )
        audit_code, report = HarnessRunAuditor(self.item_root).audit(
            "RUN-ROLE-TEST"
        )
        self.assertEqual(audit_code, 0, report["errors"])

    def test_recover_preserves_partial_parallel_reviewer_evidence(self) -> None:
        runtime = self._runtime(
            EchoRoleGateway(),
            parallel_reviewers=True,
        )

        def succeed_role(**kwargs):
            state = kwargs["state"]
            role_state = kwargs["role_state"]
            role_index = kwargs["role_index"]
            spec = kwargs["spec"]
            state["stages"][role_index]["status"] = "succeeded"
            role_state["roles"][role_index]["status"] = "succeeded"
            runtime.store.save(state)
            runtime._write_role_state("RUN-ROLE-TEST", role_state)
            runtime.store.append_event(
                state,
                "stage_succeeded",
                spec.stage_id,
                {"mode": "multi_role", "fixture": True},
            )
            return None

        def crash_parallel():
            partial = (
                self.run_dir
                / "parallel_review"
                / "evidence"
                / "actions"
            )
            partial.mkdir(parents=True)
            (partial / "partial.txt").write_text(
                "preserved",
                encoding="utf-8",
            )
            raise RuntimeError("parallel reviewer crash")

        with patch.object(
            runtime,
            "_prepare_base_bundle",
            return_value=self.base_bundle,
        ), patch.object(
            runtime,
            "_run_role",
            side_effect=succeed_role,
        ), patch(
            "harness.multi_role_runtime.ParallelReviewerRuntime.execute",
            side_effect=crash_parallel,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "parallel reviewer crash",
            ):
                runtime.run(run_id="RUN-ROLE-TEST")
        state, recovery = runtime.recover(
            run_id="RUN-ROLE-TEST",
            recovered_by="unit-test",
            reason="parallel crash",
        )
        self.assertEqual(
            [stage["status"] for stage in state["stages"]],
            ["succeeded", "succeeded", "skipped", "skipped"],
        )
        self.assertEqual(recovery["parallel_review_status"], "partial")
        self.assertIn("parallel_review", recovery["preserved_paths"])
        self.assertTrue(
            (
                self.run_dir
                / "parallel_review"
                / "evidence"
                / "actions"
                / "partial.txt"
            ).is_file()
        )
        audit_code, report = HarnessRunAuditor(self.item_root).audit(
            "RUN-ROLE-TEST"
        )
        self.assertEqual(audit_code, 0, report["errors"])

    def test_recover_refuses_pending_approval(self) -> None:
        runtime = self._create_serial_crash()
        approval = {
            "approval_id": "APPROVAL-PENDING",
            "run_id": "RUN-ROLE-TEST",
            "stage_id": "prd_structurer",
            "status": "pending",
            "reason": "manual decision",
            "options": ["continue_after_review", "reject"],
            "recommended_option": "reject",
            "affected_truth_sources": [],
            "requested_action": "manual_decision",
            "expected_target_hash": None,
            "expected_upstream_fingerprint": None,
            "candidate_hash": None,
            "requested_at": "2026-08-06T00:00:00+00:00",
            "resolved_at": None,
            "resolved_by": None,
            "resolution_note": None,
        }
        atomic_write_json(
            self.run_dir / "approvals" / "APPROVAL-PENDING.json",
            approval,
        )
        with self.assertRaisesRegex(
            HarnessStateError,
            "approve-roles 或 reject-roles",
        ):
            runtime.recover(
                run_id="RUN-ROLE-TEST",
                recovered_by="unit-test",
                reason="must not bypass approval",
            )

    def test_recover_refuses_unfinished_publish_transaction(self) -> None:
        runtime = self._create_serial_crash()
        atomic_write_json(
            self.run_dir / "publish_transaction.json",
            {"status": "publishing"},
        )
        with self.assertRaisesRegex(
            HarnessStateError,
            "recover-generation",
        ):
            runtime.recover(
                run_id="RUN-ROLE-TEST",
                recovered_by="unit-test",
                reason="must recover publish first",
            )

    def test_recover_refuses_active_process_lock(self) -> None:
        runtime = self._create_serial_crash()
        with runtime.store.lock("LOCK-HOLDER"):
            with self.assertRaises(HarnessStateError):
                runtime.recover(
                    run_id="RUN-ROLE-TEST",
                    recovered_by="unit-test",
                    reason="active lock",
                    force_unlock=True,
                )

    def test_recover_accepts_confirmed_stale_lock(self) -> None:
        runtime = self._create_serial_crash()
        atomic_write_json(
            self.item_root
            / ".generation"
            / "runs"
            / "pipeline.lock",
            {
                "run_id": "DEAD-RUN",
                "pid": 99999999,
                "token": "stale-token",
                "created_at": "2026-08-06T00:00:00+00:00",
            },
        )
        state, _ = runtime.recover(
            run_id="RUN-ROLE-TEST",
            recovered_by="unit-test",
            reason="stale lock",
            force_unlock=True,
        )
        self.assertEqual(state["status"], "cancelled")

    def test_audit_detects_tampered_recovery_record(self) -> None:
        runtime = self._create_serial_crash()
        runtime.recover(
            run_id="RUN-ROLE-TEST",
            recovered_by="unit-test",
            reason="tamper test",
        )
        recovery_path = self.run_dir / "multi_role_recovery.json"
        recovery = json.loads(recovery_path.read_text(encoding="utf-8"))
        recovery["skipped_stages"] = []
        atomic_write_json(recovery_path, recovery)
        audit_code, report = HarnessRunAuditor(self.item_root).audit(
            "RUN-ROLE-TEST"
        )
        self.assertEqual(audit_code, 1)
        self.assertTrue(
            any(
                "skipped_stages" in error
                for error in report["errors"]
            )
        )

    def test_validated_role_rejects_staging_drift(self) -> None:
        workspace = self._workspace()
        spec = ROLE_BY_STAGE["prd_structurer"]
        content = json.loads(
            (
                self.item_root
                / "structured_prd"
                / "structured_prd.json"
            ).read_text(encoding="utf-8")
        )
        workspace.propose_artifacts(
            spec,
            {
                "structured_prd/structured_prd.md": (
                    self.item_root
                    / "structured_prd"
                    / "structured_prd.md"
                ).read_text(encoding="utf-8"),
                "structured_prd/structured_prd.json": content,
            },
        )
        self.assertTrue(workspace.validate_role(spec).passed)
        (
            workspace.staging_root
            / "structured_prd"
            / "structured_prd.json"
        ).write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ArtifactWorkspaceError, "漂移"):
            workspace.assert_role_validated(spec)

    def test_full_runtime_enforces_drift_and_publishes_after_approval(self) -> None:
        case_plan_path = self.item_root / "testcases" / "case_plan.json"
        before_case_plan = file_hash(
            case_plan_path
        )
        case_plan_content = case_plan_path.read_bytes()
        before_testcases = file_hash(
            self.item_root / "testcases" / "testcases_main.md"
        )
        runtime = self._runtime(EchoRoleGateway())
        with patch.object(
            runtime,
            "_prepare_base_bundle",
            return_value=self.base_bundle,
        ):
            code, state = runtime.run(run_id="RUN-ROLE-TEST")
        self.assertEqual(code, 0)
        self.assertEqual(state["status"], "waiting_approval")
        self.assertEqual(
            [record["status"] for record in state["stages"]],
            ["succeeded", "succeeded", "succeeded", "waiting_approval"],
        )
        approval_id = "RUN-ROLE-TEST-multi-role-publish"
        approval = json.loads(
            (
                self.run_dir / "approvals" / f"{approval_id}.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(approval["requested_action"], "publish_generation")
        self.assertTrue((self.run_dir / "generation_candidate.json").is_file())
        self.assertEqual(HarnessRunAuditor(self.item_root).audit("RUN-ROLE-TEST")[0], 0)
        case_plan_path.write_text('{"external": "drift"}\n', encoding="utf-8")
        with patch.object(
            runtime,
            "_formal_strict_validator",
            return_value=(True, "fixture strict passed"),
        ):
            with self.assertRaises(ControlledGenerationError):
                runtime.approve(
                    run_id="RUN-ROLE-TEST",
                    approval_id=approval_id,
                    candidate_hash=approval["candidate_hash"],
                    approved_by="unit-test",
                )
        case_plan_path.write_bytes(case_plan_content)
        with patch.object(
            runtime,
            "_formal_strict_validator",
            return_value=(True, "fixture strict passed"),
        ):
            state, approval = runtime.approve(
                run_id="RUN-ROLE-TEST",
                approval_id=approval_id,
                candidate_hash=approval["candidate_hash"],
                approved_by="unit-test",
            )
        self.assertEqual(state["status"], "completed")
        self.assertEqual(approval["status"], "approved")
        role_state = json.loads(
            (self.run_dir / "role_runtime_state.json").read_text(encoding="utf-8")
        )
        self.assertIsNone(role_state["current_role"])
        self.assertEqual(role_state["roles"][-1]["status"], "succeeded")
        transaction = json.loads(
            (self.run_dir / "publish_transaction.json").read_text(encoding="utf-8")
        )
        self.assertEqual(transaction["status"], "committed")
        self.assertEqual(
            file_hash(self.item_root / "testcases" / "case_plan.json"),
            before_case_plan,
        )
        self.assertEqual(
            file_hash(self.item_root / "testcases" / "testcases_main.md"),
            before_testcases,
        )
        self.assertEqual(HarnessRunAuditor(self.item_root).audit("RUN-ROLE-TEST")[0], 0)

    def test_budget_exhaustion_pauses_current_role(self) -> None:
        runtime = self._runtime(
            ReadOnlyGateway(),
            budget=BudgetConfig(max_model_calls=1, require_usage=True),
        )
        with patch.object(
            runtime,
            "_prepare_base_bundle",
            return_value=self.base_bundle,
        ):
            code, state = runtime.run(run_id="RUN-ROLE-TEST")
        self.assertEqual(code, 0)
        self.assertEqual(state["status"], "waiting_approval")
        self.assertEqual(state["current_stage"], "prd_structurer")
        approvals = list((self.run_dir / "approvals").glob("*.json"))
        self.assertEqual(len(approvals), 1)
        approval = json.loads(approvals[0].read_text(encoding="utf-8"))
        self.assertEqual(approval["requested_action"], "budget_exhausted")
        state, approval = runtime.reject(
            run_id="RUN-ROLE-TEST",
            approval_id=approval["approval_id"],
            rejected_by="unit-test",
            reason="budget dry run",
        )
        self.assertEqual(state["status"], "cancelled")
        self.assertEqual(approval["status"], "rejected")
        self.assertEqual(HarnessRunAuditor(self.item_root).audit("RUN-ROLE-TEST")[0], 0)

    def test_repair_budget_exhaustion_requests_approval(self) -> None:
        runtime = MultiRoleAgentRuntime(
            item_root=self.item_root,
            project_code="FIXTURE",
            work_item_id="FIXTURE-RUNTIME-001",
            work_item_level="M",
            gateway=InvalidPRDGateway(),
            max_repairs_per_role=1,
        )
        with patch.object(
            runtime,
            "_prepare_base_bundle",
            return_value=self.base_bundle,
        ):
            code, state = runtime.run(run_id="RUN-ROLE-TEST")
        self.assertEqual(code, 0)
        self.assertEqual(state["status"], "waiting_approval")
        role_state = json.loads(
            (self.run_dir / "role_runtime_state.json").read_text(encoding="utf-8")
        )
        self.assertEqual(role_state["roles"][0]["repair_rounds_used"], 1)
        approval_path = next((self.run_dir / "approvals").glob("*.json"))
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
        self.assertEqual(approval["requested_action"], "repair_exhausted")
        self.assertEqual(HarnessRunAuditor(self.item_root).audit("RUN-ROLE-TEST")[0], 0)


if __name__ == "__main__":
    unittest.main()
