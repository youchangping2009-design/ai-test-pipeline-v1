from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from generate_regeneration_bundle import build_existing_bundle
from harness.artifact_workspace import ArtifactWorkspaceError
from harness.contracts import ContractError, validate_named
from harness.generation_workspace import (
    ControlledGenerationError,
    ControlledGenerationWorkspace,
)
from harness.hook_dispatcher import HookDispatchResult, HookDispatcher
from harness.model_gateway import ModelGateway, ModelGatewayError, ModelTurnResult
from harness.parallel_reviewer_runtime import ParallelReviewerRuntime
from harness.role_workspace import (
    ROLE_BY_STAGE,
    ROLE_SPECS,
    MultiRoleArtifactWorkspace,
    RoleSpec,
)
from harness.stage_registry import ROOT, StageSpec
from harness.state_store import (
    HarnessStateError,
    StateStore,
    atomic_write_json,
    fingerprint_files,
    utc_now,
)
from harness.telemetry import BudgetConfig, RunTelemetry, finalize_persisted_telemetry


MAX_ROLE_TURNS = 8
MAX_ROLE_REPAIRS = 2
ROLE_ACTIONS = [
    "read_artifact",
    "search_inputs",
    "propose_artifacts",
    "run_stage_validation",
    "finish_stage",
    "request_approval",
]


def _no_commands(
    _item_root: Path,
    _project_code: str,
    _work_item_id: str,
    _work_item_level: str,
    _strict: bool,
) -> list[list[str]]:
    return []


class MultiRoleAgentRuntime:
    def __init__(
        self,
        *,
        item_root: Path,
        project_code: str,
        work_item_id: str,
        work_item_level: str,
        gateway: ModelGateway,
        max_turns_per_role: int = MAX_ROLE_TURNS,
        max_repairs_per_role: int = MAX_ROLE_REPAIRS,
        budget: BudgetConfig | None = None,
        hooks: HookDispatcher | None = None,
        parallel_reviewers: bool = False,
        max_turns_per_reviewer: int = 4,
        max_repairs_per_reviewer: int = MAX_ROLE_REPAIRS,
        reviewer_timeout_seconds: int = 120,
    ) -> None:
        if not 1 <= max_turns_per_role <= MAX_ROLE_TURNS:
            raise HarnessStateError(
                f"max_turns_per_role 必须在 1..{MAX_ROLE_TURNS}"
            )
        if not 0 <= max_repairs_per_role <= MAX_ROLE_REPAIRS:
            raise HarnessStateError(
                f"max_repairs_per_role 必须在 0..{MAX_ROLE_REPAIRS}"
            )
        self.item_root = item_root
        self.project_code = project_code
        self.work_item_id = work_item_id
        self.work_item_level = work_item_level.upper()
        self.gateway = gateway
        self.max_turns_per_role = max_turns_per_role
        self.max_repairs_per_role = max_repairs_per_role
        self.budget = budget or BudgetConfig(
            max_model_calls=max_turns_per_role * len(ROLE_SPECS)
        )
        self.hooks = hooks or HookDispatcher()
        self.parallel_reviewers = parallel_reviewers
        self.max_turns_per_reviewer = max_turns_per_reviewer
        self.max_repairs_per_reviewer = max_repairs_per_reviewer
        self.reviewer_timeout_seconds = reviewer_timeout_seconds
        self.store = StateStore(item_root)

    def run(
        self,
        *,
        run_id: str,
        force_unlock: bool = False,
    ) -> tuple[int, dict[str, Any]]:
        stages = [
            StageSpec(
                stage_id=spec.stage_id,
                kind="agent",
                levels=frozenset({"S", "M", "L"}),
                required_files=("manifest.json",),
                command_factory=_no_commands,
            )
            for spec in ROLE_SPECS
        ]
        with self.store.lock(run_id, force=force_unlock):
            state = self.store.create(
                run_id=run_id,
                project_code=self.project_code,
                work_item_id=self.work_item_id,
                work_item_level=self.work_item_level,
                strict=True,
                stop_at=ROLE_SPECS[-1].stage_id,
                stages=stages,
                mode="multi_role",
            )
            state["status"] = "running"
            self.store.save(state)
            self.store.append_event(
                state,
                "run_started",
                None,
                {"mode": "multi_role", "roles": len(ROLE_SPECS)},
            )
            base_bundle = self._prepare_base_bundle(run_id)
            workspace = MultiRoleArtifactWorkspace(
                item_root=self.item_root,
                run_dir=self.store.run_dir(run_id),
                project_code=self.project_code,
                work_item_id=self.work_item_id,
                work_item_level=self.work_item_level,
                base_bundle=base_bundle,
            )
            role_state = self._initial_role_state(run_id)
            self._write_role_state(run_id, role_state)
            telemetry = RunTelemetry(
                run_id=run_id,
                run_dir=self.store.run_dir(run_id),
                budget=self.budget,
            )
            telemetry.write()

            for role_index, spec in enumerate(ROLE_SPECS):
                if spec.stage_id == "case_reviewer" and self.parallel_reviewers:
                    result = self._run_parallel_reviewers(
                        state=state,
                        role_state=role_state,
                        role_index=role_index,
                        spec=spec,
                        workspace=workspace,
                        telemetry=telemetry,
                    )
                else:
                    result = self._run_role(
                        state=state,
                        role_state=role_state,
                        role_index=role_index,
                        spec=spec,
                        workspace=workspace,
                        telemetry=telemetry,
                    )
                if result is not None:
                    return 0, result

            raise HarnessStateError("多角色 Runtime 未产生最终审批")

    def approve(
        self,
        *,
        run_id: str,
        approval_id: str,
        candidate_hash: str,
        approved_by: str,
        force_unlock: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not approved_by.strip():
            raise HarnessStateError("approved_by 不能为空")
        with self.store.lock(run_id, force=force_unlock):
            state, approval, approval_path = self._load_pending_approval(
                run_id,
                approval_id,
            )
            if approval["requested_action"] != "publish_generation":
                raise HarnessStateError("该 approval 不允许发布多角色候选")
            if approval.get("candidate_hash") != candidate_hash:
                raise HarnessStateError("candidate_hash 与 approval 绑定值不一致")
            workspace = self._generation_workspace(run_id, state)
            binding = workspace.approval_binding()
            for key in (
                "candidate_hash",
                "expected_target_hash",
                "expected_upstream_fingerprint",
            ):
                if approval.get(key) != binding.get(key):
                    raise ControlledGenerationError(
                        f"approval 绑定的 {key} 已漂移"
                    )
            transaction = workspace.publish(
                formal_validator=lambda: self._formal_strict_validator(state)
            )
            approval["status"] = "approved"
            approval["resolved_at"] = utc_now()
            approval["resolved_by"] = approved_by.strip()
            validate_named(approval, "harness_approval.schema.json")
            atomic_write_json(approval_path, approval)
            final_record = self._stage_record(state, "asset_formatter")
            final_record["status"] = "succeeded"
            final_record["completed_at"] = utc_now()
            final_record["last_exit_code"] = 0
            state["status"] = "completed"
            state["current_stage"] = None
            state["last_error"] = None
            self.store.save(state)
            role_state = self._load_role_state(run_id)
            role_state["current_role"] = None
            for role in role_state["roles"]:
                if role["stage_id"] == "asset_formatter":
                    role["status"] = "succeeded"
            self._write_role_state(run_id, role_state)
            self.store.append_event(
                state,
                "approval_resolved",
                "asset_formatter",
                {
                    "approval_id": approval_id,
                    "status": "approved",
                    "resolved_by": approval["resolved_by"],
                },
            )
            self._dispatch_hook(
                state,
                "approval_resolved",
                "asset_formatter",
                {
                    "approval_id": approval_id,
                    "status": "approved",
                    "requested_action": "publish_generation",
                },
            )
            self.store.append_event(
                state,
                "generation_publish_completed",
                "asset_formatter",
                {
                    "approval_id": approval_id,
                    "transaction_id": transaction["transaction_id"],
                },
            )
            self.store.append_event(
                state,
                "stage_succeeded",
                "asset_formatter",
                {"mode": "multi_role"},
            )
            self.store.append_event(
                state,
                "run_completed",
                None,
                {"mode": "multi_role"},
            )
            finalize_persisted_telemetry(
                run_dir=self.store.run_dir(run_id),
                state=state,
                status="completed",
                stop_reason=None,
            )
            return state, approval

    def reject(
        self,
        *,
        run_id: str,
        approval_id: str,
        rejected_by: str,
        reason: str,
        force_unlock: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not rejected_by.strip() or not reason.strip():
            raise HarnessStateError("rejected_by 和 reason 不能为空")
        with self.store.lock(run_id, force=force_unlock):
            state, approval, approval_path = self._load_pending_approval(
                run_id,
                approval_id,
            )
            approval["status"] = "rejected"
            approval["resolved_at"] = utc_now()
            approval["resolved_by"] = rejected_by.strip()
            approval["resolution_note"] = reason.strip()
            validate_named(approval, "harness_approval.schema.json")
            atomic_write_json(approval_path, approval)
            current_stage = str(
                state.get("current_stage")
                or approval.get("stage_id")
                or "asset_formatter"
            )
            record = self._stage_record(state, current_stage)
            record["status"] = "skipped"
            record["completed_at"] = utc_now()
            state["status"] = "cancelled"
            state["current_stage"] = None
            state["last_error"] = None
            self.store.save(state)
            role_state = self._load_role_state(run_id)
            role_state["current_role"] = None
            for role in role_state["roles"]:
                if role["stage_id"] == current_stage:
                    role["status"] = "skipped"
            self._write_role_state(run_id, role_state)
            self.store.append_event(
                state,
                "approval_resolved",
                current_stage,
                {
                    "approval_id": approval_id,
                    "status": "rejected",
                    "resolved_by": approval["resolved_by"],
                },
            )
            self._dispatch_hook(
                state,
                "approval_resolved",
                current_stage,
                {
                    "approval_id": approval_id,
                    "status": "rejected",
                    "requested_action": approval["requested_action"],
                },
            )
            self.store.append_event(
                state,
                "run_cancelled",
                current_stage,
                {"reason": "multi_role_approval_rejected"},
            )
            finalize_persisted_telemetry(
                run_dir=self.store.run_dir(run_id),
                state=state,
                status="cancelled",
                stop_reason="approval_rejected",
            )
            return state, approval

    def recover(
        self,
        *,
        run_id: str,
        recovered_by: str,
        reason: str,
        force_unlock: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not recovered_by.strip() or not reason.strip():
            raise HarnessStateError("recovered_by 和 reason 不能为空")
        with self.store.lock(run_id, force=force_unlock):
            state = self.store.load(run_id)
            if state.get("mode") != "multi_role":
                raise HarnessStateError(
                    "recover-roles 只支持 multi_role run"
                )
            run_dir = self.store.run_dir(run_id)
            recovery_path = run_dir / "multi_role_recovery.json"
            recovery: dict[str, Any] | None = None
            if recovery_path.is_file():
                recovery = json.loads(
                    recovery_path.read_text(encoding="utf-8")
                )
                validate_named(
                    recovery,
                    "harness_multi_role_recovery.schema.json",
                )
                if (
                    recovery["status"] == "completed"
                    and state.get("status") == "cancelled"
                ):
                    return state, recovery
            if recovery is None and state.get("status") != "running":
                raise HarnessStateError(
                    "只有异常遗留为 running 的 multi_role run 可以恢复"
                )
            if recovery is not None and state.get("status") not in {
                "running",
                "cancelled",
            }:
                raise HarnessStateError(
                    "恢复记录与 run 状态不一致，拒绝继续"
                )

            pending = self._pending_approvals(run_dir)
            if pending:
                raise HarnessStateError(
                    "run 存在 pending approval，必须使用 "
                    "approve-roles 或 reject-roles 处理"
                )
            transaction_path = run_dir / "publish_transaction.json"
            if transaction_path.is_file():
                transaction = json.loads(
                    transaction_path.read_text(encoding="utf-8")
                )
                if transaction.get("status") != "rolled_back":
                    raise HarnessStateError(
                        "run 存在发布 transaction，必须先执行 "
                        "recover-generation"
                    )

            now = utc_now()
            if recovery is None:
                recovery = {
                    "schema_version": "1.0.0",
                    "recovery_id": f"{run_id}-multi-role-recovery",
                    "run_id": run_id,
                    "status": "recovering",
                    "original_run_status": "running",
                    "original_current_stage": state.get("current_stage"),
                    "recovered_by": recovered_by.strip(),
                    "reason": reason.strip(),
                    "created_at": now,
                    "updated_at": now,
                    "recovered_at": None,
                    "skipped_stages": [],
                    "preserved_paths": self._recovery_evidence_paths(run_dir),
                    "parallel_review_status": self._parallel_review_status(
                        run_dir
                    ),
                }
                validate_named(
                    recovery,
                    "harness_multi_role_recovery.schema.json",
                )
                atomic_write_json(recovery_path, recovery)

            role_state_path = run_dir / "role_runtime_state.json"
            if role_state_path.is_file():
                role_state = self._load_role_state(run_id)
            else:
                role_state = self._initial_role_state(run_id)
            skipped_stages: list[str] = []
            for stage_record in state["stages"]:
                if stage_record["status"] == "succeeded":
                    continue
                stage_record["status"] = "skipped"
                stage_record["completed_at"] = (
                    stage_record.get("completed_at") or now
                )
                skipped_stages.append(str(stage_record["stage_id"]))
            stage_statuses = {
                str(record["stage_id"]): record["status"]
                for record in state["stages"]
            }
            for role_record in role_state["roles"]:
                role_record["status"] = (
                    "succeeded"
                    if stage_statuses.get(role_record["stage_id"])
                    == "succeeded"
                    else "skipped"
                )
            role_state["current_role"] = None
            if not skipped_stages and recovery.get("skipped_stages"):
                skipped_stages = list(recovery["skipped_stages"])
            state["status"] = "cancelled"
            state["current_stage"] = None
            state["last_error"] = None
            self.store.save(state)
            self._write_role_state(run_id, role_state)
            self._append_event_once(
                state,
                "multi_role_run_recovered",
                recovery.get("original_current_stage"),
                {
                    "recovery_id": recovery["recovery_id"],
                    "recovered_by": recovery["recovered_by"],
                    "reason": recovery["reason"],
                    "skipped_stages": skipped_stages,
                },
            )
            self._append_event_once(
                state,
                "run_cancelled",
                recovery.get("original_current_stage"),
                {"reason": "multi_role_crash_recovered"},
            )
            telemetry_path = run_dir / "telemetry.json"
            if telemetry_path.is_file():
                finalize_persisted_telemetry(
                    run_dir=run_dir,
                    state=state,
                    status="cancelled",
                    stop_reason="multi_role_crash_recovered",
                )
            else:
                telemetry = RunTelemetry(
                    run_id=run_id,
                    run_dir=run_dir,
                    budget=self.budget,
                )
                telemetry.finalize(
                    state=state,
                    status="cancelled",
                    stop_reason="multi_role_crash_recovered",
                )
            recovery["status"] = "completed"
            recovery["updated_at"] = utc_now()
            recovery["recovered_at"] = recovery["updated_at"]
            recovery["skipped_stages"] = skipped_stages
            validate_named(
                recovery,
                "harness_multi_role_recovery.schema.json",
            )
            atomic_write_json(recovery_path, recovery)
            return state, recovery

    @staticmethod
    def _pending_approvals(run_dir: Path) -> list[str]:
        approvals_root = run_dir / "approvals"
        if not approvals_root.is_dir():
            return []
        pending: list[str] = []
        for path in sorted(approvals_root.glob("*.json")):
            approval = json.loads(path.read_text(encoding="utf-8"))
            validate_named(approval, "harness_approval.schema.json")
            if approval.get("status") == "pending":
                pending.append(str(approval.get("approval_id")))
        return pending

    @staticmethod
    def _recovery_evidence_paths(run_dir: Path) -> list[str]:
        candidates = (
            "actions",
            "diagnostics",
            "logs",
            "parallel_review",
            "role_runtime_state.json",
            "role_workspace.json",
            "role_workspace",
        )
        return [
            path
            for path in candidates
            if (run_dir / path).exists()
        ]

    @staticmethod
    def _parallel_review_status(run_dir: Path) -> str | None:
        root = run_dir / "parallel_review"
        if not root.exists():
            return None
        runtime_path = root / "runtime_state.json"
        if not runtime_path.is_file():
            return "partial"
        try:
            payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return "unreadable"
        return str(payload.get("status") or "unknown")

    def _append_event_once(
        self,
        state: dict[str, Any],
        event_type: str,
        stage_id: str | None,
        payload: dict[str, Any],
    ) -> None:
        events_path = self.store.run_dir(str(state["run_id"])) / "events.jsonl"
        if events_path.is_file():
            for line in events_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = json.loads(line)
                if event.get("event_type") == event_type:
                    return
        self.store.append_event(state, event_type, stage_id, payload)

    def _run_role(
        self,
        *,
        state: dict[str, Any],
        role_state: dict[str, Any],
        role_index: int,
        spec: RoleSpec,
        workspace: MultiRoleArtifactWorkspace,
        telemetry: RunTelemetry,
    ) -> dict[str, Any] | None:
        record = self._stage_record(state, spec.stage_id)
        role_record = role_state["roles"][role_index]
        record["status"] = "running"
        record["attempts"] = 1
        record["started_at"] = utc_now()
        record["input_fingerprint"] = self._role_input_fingerprint(spec, workspace)
        state["current_stage"] = spec.stage_id
        role_record["status"] = "running"
        role_state["current_role"] = spec.stage_id
        self.store.save(state)
        self._write_role_state(str(state["run_id"]), role_state)
        self.store.append_event(
            state,
            "stage_started",
            spec.stage_id,
            {"mode": "multi_role", "role_id": spec.role_id},
        )

        observations: list[dict[str, Any]] = []
        failed_validations = 0
        for turn in range(1, self.max_turns_per_role + 1):
            budget_reason = telemetry.before_model_call()
            if budget_reason:
                approval = self._write_manual_approval(
                    state,
                    spec,
                    turn,
                    f"{spec.role_id} 预算停止: {budget_reason}",
                    "budget_exhausted",
                )
                return self._pause(
                    state,
                    role_state,
                    role_record,
                    record,
                    spec,
                    approval,
                    telemetry,
                    budget_reason,
                )
            self.store.append_event(
                state,
                "agent_turn_started",
                spec.stage_id,
                {
                    "turn": turn,
                    "max_turns": self.max_turns_per_role,
                    "repair_rounds_used": max(0, failed_validations - 1),
                },
            )
            request = self._build_request(
                state=state,
                spec=spec,
                turn=turn,
                observations=observations,
                failed_validations=failed_validations,
            )
            call_started = time.monotonic()
            turn_result: ModelTurnResult | None = None
            try:
                raw_result = self.gateway.next_action(request)
                turn_result = (
                    raw_result
                    if isinstance(raw_result, ModelTurnResult)
                    else ModelTurnResult(action=raw_result)
                )
                budget_reason = telemetry.record_model_call(
                    duration_ms=int((time.monotonic() - call_started) * 1000),
                    result=turn_result,
                )
                telemetry.write()
                if budget_reason:
                    approval = self._write_manual_approval(
                        state,
                        spec,
                        turn,
                        f"{spec.role_id} 预算停止: {budget_reason}",
                        "budget_exhausted",
                    )
                    return self._pause(
                        state,
                        role_state,
                        role_record,
                        record,
                        spec,
                        approval,
                        telemetry,
                        budget_reason,
                    )
                action = turn_result.action
                validate_named(action, "harness_model_action.schema.json")
                action_path = (
                    self.store.run_dir(str(state["run_id"]))
                    / "actions"
                    / f"{role_index + 1:02d}-{spec.stage_id}-turn-{turn}.json"
                )
                atomic_write_json(action_path, action)
                self.store.append_event(
                    state,
                    "agent_action_received",
                    spec.stage_id,
                    {
                        "turn": turn,
                        "action_id": action.get("action_id"),
                        "action_type": action.get("action_type"),
                    },
                )
                telemetry.record_action(str(action.get("action_type", "")))
                observation = self._dispatch_action(
                    state,
                    spec,
                    workspace,
                    action,
                    turn,
                )
            except (
                ModelGatewayError,
                ContractError,
                ArtifactWorkspaceError,
                ControlledGenerationError,
                subprocess.TimeoutExpired,
            ) as exc:
                if turn_result is None:
                    telemetry.record_model_call(
                        duration_ms=int((time.monotonic() - call_started) * 1000),
                        result=None,
                    )
                observation = {
                    "ok": False,
                    "action_type": "invalid_action",
                    "result": {
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                }
            observations.append(observation)
            role_record["turns_used"] = turn
            self._write_role_state(str(state["run_id"]), role_state)
            self.store.append_event(
                state,
                "agent_observation",
                spec.stage_id,
                self._observation_payload(turn, observation),
            )
            result = observation.get("result", {})
            action_type = observation.get("action_type")
            if action_type == "run_stage_validation":
                passed = bool(result.get("passed"))
                telemetry.record_validation(
                    passed=passed,
                    diagnostic_count=len(result.get("diagnostics", [])),
                )
                if not passed:
                    failed_validations += 1
                    role_record["repair_rounds_used"] = max(
                        0,
                        failed_validations - 1,
                    )
                    if failed_validations >= self.max_repairs_per_role + 1:
                        approval = self._write_manual_approval(
                            state,
                            spec,
                            turn,
                            f"{spec.role_id} Validator repair 已耗尽。",
                            "repair_exhausted",
                        )
                        return self._pause(
                            state,
                            role_state,
                            role_record,
                            record,
                            spec,
                            approval,
                            telemetry,
                            "repair_budget_exhausted",
                        )
                    hook = self._dispatch_hook(
                        state,
                        "repair_requested",
                        spec.stage_id,
                        {
                            "failed_validations": failed_validations,
                            "repair_rounds_used": role_record[
                                "repair_rounds_used"
                            ],
                        },
                    )
                    if hook.blocking_failure:
                        approval = self._write_manual_approval(
                            state,
                            spec,
                            turn,
                            "repair_requested Hook 阻止自动回修。",
                            "manual_decision",
                        )
                        return self._pause(
                            state,
                            role_state,
                            role_record,
                            record,
                            spec,
                            approval,
                            telemetry,
                            "repair_hook_blocked",
                        )
            if bool(result.get("stop")):
                if result.get("run_status") == "role_succeeded":
                    fingerprint = workspace.assert_role_validated(spec)
                    record["status"] = "succeeded"
                    record["completed_at"] = utc_now()
                    record["last_exit_code"] = 0
                    role_record["status"] = "succeeded"
                    role_record["validated_fingerprint"] = fingerprint
                    self.store.append_event(
                        state,
                        "stage_succeeded",
                        spec.stage_id,
                        {"mode": "multi_role", "role_id": spec.role_id},
                    )
                    if spec.stage_id == "asset_formatter":
                        approval = self._write_publish_approval(state, workspace)
                        return self._pause(
                            state,
                            role_state,
                            role_record,
                            record,
                            spec,
                            approval,
                            telemetry,
                            "publish_approval_required",
                        )
                    state["current_stage"] = None
                    self.store.save(state)
                    self._write_role_state(str(state["run_id"]), role_state)
                    return None
                approval = result.get("approval")
                return self._pause(
                    state,
                    role_state,
                    role_record,
                    record,
                    spec,
                    approval if isinstance(approval, dict) else None,
                    telemetry,
                    "manual_approval_required",
                )
            telemetry.write()

        approval = self._write_manual_approval(
            state,
            spec,
            self.max_turns_per_role,
            f"{spec.role_id} 已耗尽 {self.max_turns_per_role} 个 turn。",
            "turn_budget_exhausted",
        )
        return self._pause(
            state,
            role_state,
            role_record,
            record,
            spec,
            approval,
            telemetry,
            "turn_budget_exhausted",
        )

    def _run_parallel_reviewers(
        self,
        *,
        state: dict[str, Any],
        role_state: dict[str, Any],
        role_index: int,
        spec: RoleSpec,
        workspace: MultiRoleArtifactWorkspace,
        telemetry: RunTelemetry,
    ) -> dict[str, Any] | None:
        record = self._stage_record(state, spec.stage_id)
        role_record = role_state["roles"][role_index]
        record["status"] = "running"
        record["attempts"] = 1
        record["started_at"] = utc_now()
        record["input_fingerprint"] = self._role_input_fingerprint(spec, workspace)
        state["current_stage"] = spec.stage_id
        role_record["status"] = "running"
        role_state["current_role"] = spec.stage_id
        self.store.save(state)
        self._write_role_state(str(state["run_id"]), role_state)
        self.store.append_event(
            state,
            "stage_started",
            spec.stage_id,
            {
                "mode": "multi_role",
                "role_id": spec.role_id,
                "parallel_reviewers": True,
            },
        )
        parallel = ParallelReviewerRuntime(
            run_id=str(state["run_id"]),
            run_dir=self.store.run_dir(str(state["run_id"])),
            gateway=self.gateway,
            workspace=workspace,
            telemetry=telemetry,
            append_event=lambda event_type, payload: self.store.append_event(
                state,
                event_type,
                spec.stage_id,
                payload,
            ),
            max_turns_per_reviewer=self.max_turns_per_reviewer,
            max_repairs_per_reviewer=self.max_repairs_per_reviewer,
            reviewer_timeout_seconds=self.reviewer_timeout_seconds,
        )
        result = parallel.execute()
        runtime_state = result["runtime_state"]
        role_record["turns_used"] = sum(
            reviewer["turns_used"] for reviewer in runtime_state["reviewers"]
        )
        role_record["repair_rounds_used"] = sum(
            reviewer["repair_rounds_used"] for reviewer in runtime_state["reviewers"]
        )
        if not result["succeeded"]:
            approval = self._write_manual_approval(
                state,
                spec,
                max(1, role_record["turns_used"]),
                "并行 Reviewer 未通过 3/3 barrier 或聚合后 Review Gate；"
                "不得进入 Formatter，仅允许拒绝本轮。",
                "manual_decision",
                reject_only=True,
                affected_truth_sources=[],
            )
            return self._pause(
                state,
                role_state,
                role_record,
                record,
                spec,
                approval,
                telemetry,
                str(result["stop_reason"]),
            )
        record["status"] = "succeeded"
        record["completed_at"] = utc_now()
        record["last_exit_code"] = 0
        role_record["status"] = "succeeded"
        role_record["validated_fingerprint"] = result["validated_fingerprint"]
        self.store.append_event(
            state,
            "stage_succeeded",
            spec.stage_id,
            {
                "mode": "multi_role",
                "role_id": spec.role_id,
                "parallel_reviewers": True,
                "bundle_hash": result["bundle"]["bundle_hash"],
            },
        )
        state["current_stage"] = None
        self.store.save(state)
        self._write_role_state(str(state["run_id"]), role_state)
        return None

    def _dispatch_action(
        self,
        state: dict[str, Any],
        spec: RoleSpec,
        workspace: MultiRoleArtifactWorkspace,
        action: dict[str, Any],
        turn: int,
    ) -> dict[str, Any]:
        if action.get("stage_id") != spec.stage_id:
            raise ArtifactWorkspaceError(
                f"当前只允许 stage_id={spec.stage_id}"
            )
        action_type = str(action.get("action_type"))
        if action_type not in ROLE_ACTIONS:
            raise ArtifactWorkspaceError(
                f"{spec.stage_id} 不允许 action_type={action_type}"
            )
        arguments = action.get("arguments")
        if not isinstance(arguments, dict):
            raise ArtifactWorkspaceError("Action arguments 必须是 object")
        if action_type == "read_artifact":
            result = workspace.read_artifact(
                spec,
                self._required_string(arguments, "path"),
            )
        elif action_type == "search_inputs":
            max_results = arguments.get("max_results", 20)
            if not isinstance(max_results, int) or not 1 <= max_results <= 50:
                raise ArtifactWorkspaceError("max_results 必须在 1..50")
            result = {
                "matches": workspace.search_inputs(
                    spec,
                    self._required_string(arguments, "query"),
                    max_results=max_results,
                )
            }
        elif action_type == "propose_artifacts":
            result = workspace.propose_artifacts(
                spec,
                arguments.get("artifacts"),
            )
            self.store.append_event(
                state,
                "artifact_staged",
                spec.stage_id,
                result,
            )
        elif action_type == "run_stage_validation":
            validation = workspace.validate_role(spec)
            result = {
                "passed": validation.passed,
                "attempt": validation.attempt,
                "exit_code": validation.exit_code,
                "log_path": validation.log_path,
                "diagnostic_path": validation.diagnostic_path,
                "diagnostics": list(validation.diagnostics),
            }
        elif action_type == "finish_stage":
            workspace.assert_role_validated(spec)
            result = {"stop": True, "run_status": "role_succeeded"}
        else:
            reason = self._required_string(arguments, "reason")
            approval = self._write_manual_approval(
                state,
                spec,
                turn,
                reason,
                "manual_decision",
            )
            result = {
                "stop": True,
                "run_status": "waiting_approval",
                "approval": approval,
            }
        return {"ok": True, "action_type": action_type, "result": result}

    def _build_request(
        self,
        *,
        state: dict[str, Any],
        spec: RoleSpec,
        turn: int,
        observations: list[dict[str, Any]],
        failed_validations: int,
    ) -> dict[str, Any]:
        return {
            "protocol_version": "1.0.0",
            "run_id": state["run_id"],
            "mode": "multi_role",
            "role_id": spec.role_id,
            "stage_id": spec.stage_id,
            "skill_path": spec.skill_path,
            "turn": turn,
            "max_turns": self.max_turns_per_role,
            "repair_rounds_used": max(0, failed_validations - 1),
            "max_repair_rounds": self.max_repairs_per_role,
            "budget": self.budget.__dict__,
            "allowed_actions": ROLE_ACTIONS,
            "readable_prefixes": list(spec.readable_prefixes),
            "readable_paths": list(spec.readable_paths),
            "writable_paths": list(spec.writable_paths),
            "work_item": {
                "project_code": self.project_code,
                "work_item_id": self.work_item_id,
                "work_item_level": self.work_item_level,
            },
            "constraints": [
                "只返回一个符合 Harness Model Action Schema 的 JSON object",
                "不得请求 shell、网络或工作项外文件",
                "只能写当前角色 writable_paths，且只写 role staging",
                "Validator 结果高于模型判断",
                "Reviewer 不得重写 testcase，Formatter 不得写真源",
            ],
            "observations": observations,
        }

    def _prepare_base_bundle(self, run_id: str) -> dict[str, Any]:
        output_dir = f".generation/runs/{run_id}/role_tasks"
        command = [
            sys.executable,
            str(ROOT / "scripts" / "prepare_regeneration_run.py"),
            "--project-code",
            self.project_code,
            "--work-item-id",
            self.work_item_id,
            "--work-item-level",
            self.work_item_level,
            "--output-dir-name",
            output_dir,
        ]
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        if result.returncode != 0:
            raise HarnessStateError(
                "生成多角色任务清单失败: "
                + ((result.stdout or "") + (result.stderr or ""))[-2000:]
            )
        manifest_path = (
            self.store.run_dir(run_id) / "role_tasks" / "run_manifest.json"
        )
        run_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return build_existing_bundle(self.item_root, run_manifest)

    def _initial_role_state(self, run_id: str) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "role_order": [spec.stage_id for spec in ROLE_SPECS],
            "current_role": None,
            "roles": [
                {
                    "role_id": spec.role_id,
                    "stage_id": spec.stage_id,
                    "skill_path": spec.skill_path,
                    "status": "pending",
                    "turns_used": 0,
                    "repair_rounds_used": 0,
                    "writable_paths": list(spec.writable_paths),
                    "validated_fingerprint": None,
                }
                for spec in ROLE_SPECS
            ],
            "staged_paths": [],
            "updated_at": utc_now(),
        }

    def _write_role_state(
        self,
        run_id: str,
        role_state: dict[str, Any],
    ) -> None:
        workspace_path = self.store.run_dir(run_id) / "role_workspace.json"
        if workspace_path.exists():
            workspace = json.loads(workspace_path.read_text(encoding="utf-8"))
            role_state["staged_paths"] = list(workspace.get("staged_paths", []))
        role_state["updated_at"] = utc_now()
        validate_named(role_state, "harness_role_runtime.schema.json")
        atomic_write_json(
            self.store.run_dir(run_id) / "role_runtime_state.json",
            role_state,
        )

    def _load_role_state(self, run_id: str) -> dict[str, Any]:
        path = self.store.run_dir(run_id) / "role_runtime_state.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        validate_named(payload, "harness_role_runtime.schema.json")
        return payload

    def _write_manual_approval(
        self,
        state: dict[str, Any],
        spec: RoleSpec,
        turn: int,
        reason: str,
        requested_action: str,
        reject_only: bool = False,
        affected_truth_sources: list[str] | None = None,
    ) -> dict[str, Any]:
        approval = {
            "approval_id": (
                f"{state['run_id']}-{spec.stage_id}-turn-{turn}"
            ),
            "run_id": state["run_id"],
            "stage_id": spec.stage_id,
            "status": "pending",
            "reason": reason,
            "options": (
                ["reject", "cancel_run"]
                if reject_only
                else ["continue_after_review", "reject"]
            ),
            "recommended_option": "reject",
            "affected_truth_sources": (
                list(spec.writable_paths)
                if affected_truth_sources is None
                else affected_truth_sources
            ),
            "requested_action": requested_action,
            "expected_target_hash": None,
            "expected_upstream_fingerprint": None,
            "candidate_hash": None,
            "requested_at": utc_now(),
            "resolved_at": None,
            "resolved_by": None,
            "resolution_note": None,
        }
        return self._persist_approval(state, approval)

    def _write_publish_approval(
        self,
        state: dict[str, Any],
        workspace: MultiRoleArtifactWorkspace,
    ) -> dict[str, Any]:
        generation = workspace.generation_workspace()
        candidate = generation.verify_candidate()
        approval = {
            "approval_id": f"{state['run_id']}-multi-role-publish",
            "run_id": state["run_id"],
            "stage_id": "asset_formatter",
            "status": "pending",
            "reason": (
                "四角色 staging 已完成，最终候选通过隔离 strict；"
                f"发布将替换 {len(candidate['files'])} 个正式资产文件。"
            ),
            "options": ["approve_publish", "reject_publish"],
            "recommended_option": "approve_publish",
            "affected_truth_sources": [
                entry["path"] for entry in candidate["files"]
            ],
            "requested_action": "publish_generation",
            "expected_target_hash": candidate["expected_target_hash"],
            "expected_upstream_fingerprint": candidate[
                "expected_upstream_fingerprint"
            ],
            "candidate_hash": candidate["candidate_hash"],
            "requested_at": utc_now(),
            "resolved_at": None,
            "resolved_by": None,
            "resolution_note": None,
        }
        return self._persist_approval(state, approval)

    def _persist_approval(
        self,
        state: dict[str, Any],
        approval: dict[str, Any],
    ) -> dict[str, Any]:
        validate_named(approval, "harness_approval.schema.json")
        path = (
            self.store.run_dir(str(state["run_id"]))
            / "approvals"
            / f"{approval['approval_id']}.json"
        )
        atomic_write_json(path, approval)
        self.store.append_event(
            state,
            "approval_requested",
            str(approval["stage_id"]),
            {
                "approval_id": approval["approval_id"],
                "requested_action": approval["requested_action"],
                "candidate_hash": approval.get("candidate_hash"),
            },
        )
        return approval

    def _pause(
        self,
        state: dict[str, Any],
        role_state: dict[str, Any],
        role_record: dict[str, Any],
        stage_record: dict[str, Any],
        spec: RoleSpec,
        approval: dict[str, Any] | None,
        telemetry: RunTelemetry,
        stop_reason: str,
    ) -> dict[str, Any]:
        stage_record["status"] = "waiting_approval"
        stage_record["completed_at"] = utc_now()
        role_record["status"] = "waiting_approval"
        role_state["current_role"] = spec.stage_id
        state["status"] = "waiting_approval"
        state["current_stage"] = spec.stage_id
        state["last_error"] = None
        self.store.save(state)
        self._write_role_state(str(state["run_id"]), role_state)
        self.store.append_event(
            state,
            "run_paused",
            spec.stage_id,
            {
                "reason": stop_reason,
                "approval_id": approval.get("approval_id") if approval else None,
            },
        )
        self._dispatch_hook(
            state,
            "approval_requested",
            spec.stage_id,
            {
                "approval_id": approval.get("approval_id") if approval else None,
                "requested_action": (
                    approval.get("requested_action") if approval else None
                ),
            },
        )
        telemetry.finalize(
            state=state,
            status="waiting_approval",
            stop_reason=stop_reason,
        )
        return state

    def _load_pending_approval(
        self,
        run_id: str,
        approval_id: str,
    ) -> tuple[dict[str, Any], dict[str, Any], Path]:
        state = self.store.load(run_id)
        if state["mode"] != "multi_role" or state["status"] != "waiting_approval":
            raise HarnessStateError(
                "只有 waiting_approval 的 multi_role run 可处理审批"
            )
        path = (
            self.store.run_dir(run_id)
            / "approvals"
            / f"{approval_id}.json"
        )
        if not path.is_file():
            raise HarnessStateError(f"approval 不存在: {approval_id}")
        approval = json.loads(path.read_text(encoding="utf-8"))
        validate_named(approval, "harness_approval.schema.json")
        if approval["run_id"] != run_id or approval["status"] != "pending":
            raise HarnessStateError("approval run/status 不匹配")
        return state, approval, path

    def _generation_workspace(
        self,
        run_id: str,
        state: dict[str, Any],
    ) -> ControlledGenerationWorkspace:
        return ControlledGenerationWorkspace(
            item_root=self.item_root,
            run_dir=self.store.run_dir(run_id),
            project_code=self.project_code,
            work_item_id=self.work_item_id,
            work_item_level=str(state["work_item_level"]),
        )

    def _formal_strict_validator(
        self,
        state: dict[str, Any],
    ) -> tuple[bool, str]:
        command = [
            sys.executable,
            str(ROOT / "scripts" / "validate_work_item.py"),
            "--project-code",
            self.project_code,
            "--work-item-id",
            self.work_item_id,
            "--work-item-level",
            str(state["work_item_level"]),
            "--strict",
            "--skip-code-reviews",
        ]
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
        )
        output = (result.stdout or "") + (
            ("\n" + result.stderr) if result.stderr else ""
        )
        return result.returncode == 0, output

    def _role_input_fingerprint(
        self,
        spec: RoleSpec,
        workspace: MultiRoleArtifactWorkspace,
    ) -> str:
        readable = []
        for path in workspace.staging_root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(workspace.staging_root).as_posix()
            if workspace._is_readable(spec, relative):
                readable.append(relative)
        return fingerprint_files(workspace.staging_root, tuple(sorted(readable)))

    def _dispatch_hook(
        self,
        state: dict[str, Any],
        event: str,
        stage_id: str,
        payload: dict[str, Any],
    ) -> HookDispatchResult:
        return self.hooks.dispatch(
            event=event,
            state=state,
            run_dir=self.store.run_dir(str(state["run_id"])),
            stage_id=stage_id,
            payload=payload,
            event_callback=lambda event_type, event_payload: self.store.append_event(
                state,
                event_type,
                stage_id,
                event_payload,
            ),
        )

    @staticmethod
    def _required_string(arguments: dict[str, Any], key: str) -> str:
        value = arguments.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ArtifactWorkspaceError(f"Action 缺少非空字符串参数: {key}")
        return value.strip()

    @staticmethod
    def _stage_record(
        state: dict[str, Any],
        stage_id: str,
    ) -> dict[str, Any]:
        for record in state["stages"]:
            if record["stage_id"] == stage_id:
                return record
        raise HarnessStateError(f"run 不包含 stage: {stage_id}")

    @staticmethod
    def _observation_payload(
        turn: int,
        observation: dict[str, Any],
    ) -> dict[str, Any]:
        result = observation.get("result", {})
        return {
            "turn": turn,
            "ok": bool(observation.get("ok")),
            "action_type": observation.get("action_type"),
            "passed": result.get("passed") if isinstance(result, dict) else None,
            "stop": result.get("stop") if isinstance(result, dict) else None,
            "error_type": (
                result.get("error_type") if isinstance(result, dict) else None
            ),
        }
