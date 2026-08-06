from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from harness.artifact_workspace import (
    ArtifactWorkspaceError,
    CasePlanArtifactWorkspace,
)
from harness.contracts import ContractError, validate_named
from harness.hook_dispatcher import HookDispatchResult, HookDispatcher
from harness.model_gateway import ModelGateway, ModelGatewayError, ModelTurnResult
from harness.stage_registry import StageSpec
from harness.state_store import (
    HarnessStateError,
    StateStore,
    atomic_write_json,
    fingerprint_files,
    utc_now,
)
from harness.tool_dispatcher import (
    ActionDispatchError,
    CasePlanToolDispatcher,
)
from harness.telemetry import BudgetConfig, RunTelemetry


MAX_AGENT_TURNS = 8
MAX_REPAIR_ROUNDS = 2
ALLOWED_ACTIONS = [
    "read_artifact",
    "search_inputs",
    "propose_artifacts",
    "run_stage_validation",
    "commit_stage",
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


class CasePlanAgentLoop:
    def __init__(
        self,
        *,
        item_root: Path,
        project_code: str,
        work_item_id: str,
        work_item_level: str,
        gateway: ModelGateway,
        max_turns: int = MAX_AGENT_TURNS,
        max_repairs: int = MAX_REPAIR_ROUNDS,
        budget: BudgetConfig | None = None,
        hooks: HookDispatcher | None = None,
    ) -> None:
        if not 1 <= max_turns <= MAX_AGENT_TURNS:
            raise HarnessStateError(
                f"max_turns 必须在 1..{MAX_AGENT_TURNS}"
            )
        if not 0 <= max_repairs <= MAX_REPAIR_ROUNDS:
            raise HarnessStateError(
                f"max_repairs 必须在 0..{MAX_REPAIR_ROUNDS}"
            )
        self.item_root = item_root
        self.project_code = project_code
        self.work_item_id = work_item_id
        self.work_item_level = work_item_level.upper()
        self.gateway = gateway
        self.max_turns = max_turns
        self.max_repairs = max_repairs
        self.budget = budget or BudgetConfig(max_model_calls=max_turns)
        self.hooks = hooks or HookDispatcher()
        self.store = StateStore(item_root)

    def run(
        self,
        run_id: str,
        force_unlock: bool = False,
    ) -> tuple[int, dict[str, Any]]:
        upstream_paths = self._upstream_paths()
        missing_upstream = [
            path for path in upstream_paths if not (self.item_root / path).is_file()
        ]
        if missing_upstream:
            raise HarnessStateError(
                "Case Plan Agent 缺少上游产物: " + ", ".join(missing_upstream)
            )
        stage = StageSpec(
            stage_id="case_plan",
            kind="agent",
            levels=frozenset({"S", "M", "L"}),
            required_files=upstream_paths,
            command_factory=_no_commands,
        )
        with self.store.lock(run_id, force=force_unlock):
            state = self.store.create(
                run_id=run_id,
                project_code=self.project_code,
                work_item_id=self.work_item_id,
                work_item_level=self.work_item_level,
                strict=True,
                stop_at="case_plan",
                stages=[stage],
                mode="agent",
            )
            record = state["stages"][0]
            record["status"] = "running"
            record["attempts"] = 1
            record["started_at"] = utc_now()
            record["input_fingerprint"] = fingerprint_files(
                self.item_root,
                upstream_paths,
            )
            state["status"] = "running"
            state["current_stage"] = "case_plan"
            self.store.save(state)
            self.store.append_event(state, "run_started", None, {"mode": "agent"})
            self.store.append_event(
                state,
                "stage_started",
                "case_plan",
                {"attempt": 1, "mode": "agent"},
            )

            workspace = CasePlanArtifactWorkspace(
                item_root=self.item_root,
                run_dir=self.store.run_dir(run_id),
                work_item_level=self.work_item_level,
            )
            dispatcher = CasePlanToolDispatcher(
                workspace=workspace,
                store=self.store,
                state=state,
            )
            observations: list[dict[str, Any]] = []
            failed_validations = 0
            telemetry = RunTelemetry(
                run_id=run_id,
                run_dir=self.store.run_dir(run_id),
                budget=self.budget,
            )
            telemetry.write()

            for turn in range(1, self.max_turns + 1):
                budget_reason = telemetry.before_model_call()
                if budget_reason:
                    return 0, self._stop_for_budget(
                        state=state,
                        dispatcher=dispatcher,
                        telemetry=telemetry,
                        turn=max(1, turn - 1),
                        reason=budget_reason,
                    )
                self.store.append_event(
                    state,
                    "agent_turn_started",
                    "case_plan",
                    {
                        "turn": turn,
                        "max_turns": self.max_turns,
                        "repair_rounds_used": max(0, failed_validations - 1),
                    },
                )
                request = self._build_request(
                    state=state,
                    turn=turn,
                    observations=observations,
                    failed_validations=failed_validations,
                )
                call_started: float | None = None
                turn_result: ModelTurnResult | None = None
                try:
                    call_started = time.monotonic()
                    raw_result = self.gateway.next_action(request)
                    call_duration_ms = int(
                        (time.monotonic() - call_started) * 1000
                    )
                    turn_result = (
                        raw_result
                        if isinstance(raw_result, ModelTurnResult)
                        else ModelTurnResult(action=raw_result)
                    )
                    budget_reason = telemetry.record_model_call(
                        duration_ms=call_duration_ms,
                        result=turn_result,
                    )
                    telemetry.write()
                    if budget_reason:
                        return 0, self._stop_for_budget(
                            state=state,
                            dispatcher=dispatcher,
                            telemetry=telemetry,
                            turn=turn,
                            reason=budget_reason,
                        )
                    action = turn_result.action
                    validate_named(
                        action,
                        "harness_model_action.schema.json",
                    )
                    action_path = (
                        self.store.run_dir(run_id)
                        / "actions"
                        / f"turn-{turn}.json"
                    )
                    atomic_write_json(action_path, action)
                    self.store.append_event(
                        state,
                        "agent_action_received",
                        "case_plan",
                        {
                            "turn": turn,
                            "action_id": action.get("action_id"),
                            "action_type": action.get("action_type"),
                        },
                    )
                    telemetry.record_action(str(action.get("action_type", "")))
                    observation = dispatcher.dispatch(action, turn)
                except (
                    ModelGatewayError,
                    ContractError,
                    ActionDispatchError,
                    ArtifactWorkspaceError,
                ) as exc:
                    if call_started is not None and turn_result is None:
                        telemetry.record_model_call(
                            duration_ms=int(
                                (time.monotonic() - call_started) * 1000
                            ),
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
                self._persist_agent_state(
                    run_id=run_id,
                    turn=turn,
                    failed_validations=failed_validations,
                    observations=observations,
                )
                self.store.append_event(
                    state,
                    "agent_observation",
                    "case_plan",
                    self._observation_event_payload(turn, observation),
                )

                if observation.get("action_type") == "run_stage_validation":
                    result = observation.get("result", {})
                    telemetry.record_validation(
                        passed=bool(result.get("passed")),
                        diagnostic_count=len(result.get("diagnostics", [])),
                    )
                    if not bool(result.get("passed")):
                        failed_validations += 1
                        self._persist_agent_state(
                            run_id=run_id,
                            turn=turn,
                            failed_validations=failed_validations,
                            observations=observations,
                        )
                        if failed_validations >= self.max_repairs + 1:
                            self.store.append_event(
                                state,
                                "repair_budget_exhausted",
                                "case_plan",
                                {
                                    "failed_validations": failed_validations,
                                    "max_repairs": self.max_repairs,
                                },
                            )
                            approval = dispatcher.write_automatic_approval(
                                turn=turn,
                                reason=(
                                    "Case Plan Validator 连续失败，"
                                    f"已耗尽 {self.max_repairs} 轮 repair。"
                                ),
                                requested_action="repair_exhausted",
                            )
                            return 0, self._mark_waiting_approval(
                                state,
                                approval,
                                telemetry,
                                "repair_budget_exhausted",
                            )
                        repair_hook = self._dispatch_hook(
                            state=state,
                            event="repair_requested",
                            stage_id="case_plan",
                            payload={
                                "failed_validations": failed_validations,
                                "repair_rounds_used": max(
                                    0,
                                    failed_validations - 1,
                                ),
                            },
                        )
                        if repair_hook.blocking_failure:
                            approval = dispatcher.write_automatic_approval(
                                turn=turn,
                                reason=(
                                    "repair_requested Hook 阻止自动回修: "
                                    f"{repair_hook.blocking_failure['hook_id']}"
                                ),
                                requested_action="manual_decision",
                            )
                            return 0, self._mark_waiting_approval(
                                state,
                                approval,
                                telemetry,
                                "repair_hook_blocked",
                            )
                telemetry.write()
                self.store.append_event(
                    state,
                    "telemetry_updated",
                    "case_plan",
                    {
                        "turn": turn,
                        "model_calls": telemetry.model_calls,
                        "total_tokens": telemetry.total_tokens,
                        "cost_usd": telemetry.cost_usd,
                    },
                )

                result = observation.get("result", {})
                if bool(result.get("stop")):
                    if result.get("run_status") == "completed":
                        return 0, self._mark_completed(state, telemetry)
                    approval = result.get("approval")
                    return 0, self._mark_waiting_approval(
                        state,
                        approval if isinstance(approval, dict) else None,
                        telemetry,
                        "approval_required",
                    )

            self.store.append_event(
                state,
                "turn_budget_exhausted",
                "case_plan",
                {"max_turns": self.max_turns},
            )
            approval = dispatcher.write_automatic_approval(
                turn=self.max_turns,
                reason=f"Case Plan Agent 已耗尽 {self.max_turns} 个 turn。",
                requested_action="turn_budget_exhausted",
            )
            return 0, self._mark_waiting_approval(
                state,
                approval,
                telemetry,
                "turn_budget_exhausted",
            )

    def _build_request(
        self,
        *,
        state: dict[str, Any],
        turn: int,
        observations: list[dict[str, Any]],
        failed_validations: int,
    ) -> dict[str, Any]:
        return {
            "protocol_version": "1.0.0",
            "run_id": state["run_id"],
            "stage_id": "case_plan",
            "turn": turn,
            "max_turns": self.max_turns,
            "repair_rounds_used": max(0, failed_validations - 1),
            "max_repair_rounds": self.max_repairs,
            "budget": self.budget.__dict__,
            "allowed_actions": ALLOWED_ACTIONS,
            "target_artifact": "testcases/case_plan.json",
            "work_item": {
                "project_code": self.project_code,
                "work_item_id": self.work_item_id,
                "work_item_level": self.work_item_level,
            },
            "constraints": [
                "只返回一个符合 Harness Model Action Schema 的 JSON object",
                "不得请求 shell、网络或工作项外文件",
                "候选只能写入 testcases/case_plan.json staging",
                "Validator 结果高于模型判断",
                "不确定业务规则时必须 request_approval",
            ],
            "observations": observations,
        }

    def _persist_agent_state(
        self,
        *,
        run_id: str,
        turn: int,
        failed_validations: int,
        observations: list[dict[str, Any]],
    ) -> None:
        atomic_write_json(
            self.store.run_dir(run_id) / "agent_state.json",
            {
                "schema_version": "1.0.0",
                "stage_id": "case_plan",
                "turns_used": turn,
                "failed_validations": failed_validations,
                "repair_rounds_used": max(0, failed_validations - 1),
                "max_turns": self.max_turns,
                "max_repair_rounds": self.max_repairs,
                "observations": observations,
                "updated_at": utc_now(),
            },
        )

    def _mark_waiting_approval(
        self,
        state: dict[str, Any],
        approval: dict[str, Any] | None,
        telemetry: RunTelemetry,
        stop_reason: str,
    ) -> dict[str, Any]:
        record = state["stages"][0]
        record["status"] = "waiting_approval"
        record["completed_at"] = utc_now()
        state["status"] = "waiting_approval"
        state["current_stage"] = None
        state["last_error"] = None
        self.store.save(state)
        self.store.append_event(
            state,
            "run_paused",
            "case_plan",
            {
                "reason": "approval_required",
                "approval_id": approval.get("approval_id") if approval else None,
            },
        )
        self._dispatch_hook(
            state=state,
            event="approval_requested",
            stage_id="case_plan",
            payload={
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

    def _dispatch_hook(
        self,
        *,
        state: dict[str, Any],
        event: str,
        stage_id: str | None,
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

    def _mark_completed(
        self,
        state: dict[str, Any],
        telemetry: RunTelemetry,
    ) -> dict[str, Any]:
        record = state["stages"][0]
        record["status"] = "succeeded"
        record["completed_at"] = utc_now()
        record["last_exit_code"] = 0
        state["status"] = "completed"
        state["current_stage"] = None
        state["last_error"] = None
        self.store.save(state)
        self.store.append_event(
            state,
            "stage_succeeded",
            "case_plan",
            {"mode": "agent"},
        )
        self.store.append_event(state, "run_completed", None, {"mode": "agent"})
        telemetry.finalize(
            state=state,
            status="completed",
            stop_reason=None,
        )
        return state

    def _stop_for_budget(
        self,
        *,
        state: dict[str, Any],
        dispatcher: CasePlanToolDispatcher,
        telemetry: RunTelemetry,
        turn: int,
        reason: str,
    ) -> dict[str, Any]:
        self.store.append_event(
            state,
            "budget_exhausted",
            "case_plan",
            {
                "reason": reason,
                "model_calls": telemetry.model_calls,
                "total_tokens": telemetry.total_tokens,
                "cost_usd": telemetry.cost_usd,
            },
        )
        approval = dispatcher.write_automatic_approval(
            turn=turn,
            reason=f"Case Plan Agent 预算停止: {reason}",
            requested_action="budget_exhausted",
        )
        return self._mark_waiting_approval(
            state,
            approval,
            telemetry,
            reason,
        )

    def _upstream_paths(self) -> tuple[str, ...]:
        paths = ["acceptance/testability_gate.json"]
        if self.work_item_level in {"M", "L"}:
            paths.append("acceptance/acceptance_examples.json")
        if self.work_item_level == "L":
            paths.append("design/verification_responsibility_map.json")
        return tuple(paths)

    @staticmethod
    def _observation_event_payload(
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

