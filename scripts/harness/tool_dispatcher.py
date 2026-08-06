from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from harness.artifact_workspace import (
    TARGET_RELATIVE_PATH,
    ArtifactWorkspaceError,
    CasePlanArtifactWorkspace,
)
from harness.contracts import ContractError, validate_named
from harness.state_store import StateStore, atomic_write_json, utc_now


class ActionDispatchError(RuntimeError):
    """Raised when a Model Action violates the restricted tool contract."""


@dataclass
class CasePlanToolDispatcher:
    workspace: CasePlanArtifactWorkspace
    store: StateStore
    state: dict[str, Any]

    def dispatch(self, action: dict[str, Any], turn: int) -> dict[str, Any]:
        try:
            validate_named(action, "harness_model_action.schema.json")
        except ContractError as exc:
            raise ActionDispatchError(str(exc)) from exc
        if action.get("stage_id") != "case_plan":
            raise ActionDispatchError("P3 只允许 stage_id=case_plan")
        action_type = str(action["action_type"])
        arguments = action.get("arguments")
        if not isinstance(arguments, dict):
            raise ActionDispatchError("Model Action arguments 必须是 object")

        handlers = {
            "read_artifact": self._read_artifact,
            "search_inputs": self._search_inputs,
            "propose_artifacts": self._propose_artifacts,
            "run_stage_validation": self._run_stage_validation,
            "commit_stage": self._commit_stage,
            "request_approval": self._request_approval,
            "finish_stage": self._finish_stage,
        }
        if action_type not in handlers:
            raise ActionDispatchError(f"不允许的 action_type: {action_type}")
        return handlers[action_type](arguments, turn)

    def _read_artifact(
        self,
        arguments: dict[str, Any],
        _turn: int,
    ) -> dict[str, Any]:
        path = self._required_string(arguments, "path")
        result = self.workspace.read_artifact(path)
        return self._observation("read_artifact", result)

    def _search_inputs(
        self,
        arguments: dict[str, Any],
        _turn: int,
    ) -> dict[str, Any]:
        query = self._required_string(arguments, "query")
        max_results = arguments.get("max_results", 20)
        if not isinstance(max_results, int) or not 1 <= max_results <= 50:
            raise ActionDispatchError("search_inputs.max_results 必须在 1..50")
        results = self.workspace.search_inputs(query, max_results=max_results)
        return self._observation(
            "search_inputs",
            {"query": query, "matches": results},
        )

    def _propose_artifacts(
        self,
        arguments: dict[str, Any],
        _turn: int,
    ) -> dict[str, Any]:
        path = self._required_string(arguments, "path")
        if path != TARGET_RELATIVE_PATH:
            raise ActionDispatchError(
                f"P3 只允许 propose {TARGET_RELATIVE_PATH}，实际: {path}"
            )
        if "content" not in arguments:
            raise ActionDispatchError("propose_artifacts 缺少 content")
        result = self.workspace.propose_case_plan(arguments["content"])
        self.store.append_event(
            self.state,
            "artifact_staged",
            "case_plan",
            {
                "path": result["path"],
                "candidate_hash": result["candidate_hash"],
            },
        )
        return self._observation("propose_artifacts", result)

    def _run_stage_validation(
        self,
        _arguments: dict[str, Any],
        _turn: int,
    ) -> dict[str, Any]:
        self.store.append_event(
            self.state,
            "stage_validation_started",
            "case_plan",
            {},
        )
        result = self.workspace.validate_candidate()
        payload = {
            "passed": result.passed,
            "attempt": result.attempt,
            "exit_code": result.exit_code,
            "log_path": result.log_path,
            "diagnostic_path": result.diagnostic_path,
            "diagnostics": list(result.diagnostics),
        }
        self.store.append_event(
            self.state,
            "stage_validation_completed",
            "case_plan",
            {
                "passed": result.passed,
                "attempt": result.attempt,
                "exit_code": result.exit_code,
                "diagnostic_count": len(result.diagnostics),
            },
        )
        return self._observation("run_stage_validation", payload)

    def _commit_stage(
        self,
        _arguments: dict[str, Any],
        turn: int,
    ) -> dict[str, Any]:
        approval = self._write_approval(
            turn=turn,
            status="pending",
            reason="正式 Case Plan 提交需要独立 approve-case-plan 审批。",
            requested_action="commit_stage",
            resolved_by=None,
        )
        return self._observation(
            "commit_stage",
            {
                "committed": False,
                "approval": approval,
                "stop": True,
                "run_status": "waiting_approval",
            },
            ok=False,
        )

    def _request_approval(
        self,
        arguments: dict[str, Any],
        turn: int,
    ) -> dict[str, Any]:
        reason = self._required_string(arguments, "reason")
        requested_action = str(
            arguments.get("requested_action", "manual_decision")
        )
        if requested_action not in {
            "commit_stage",
            "manual_decision",
            "repair_exhausted",
            "turn_budget_exhausted",
            "budget_exhausted",
        }:
            raise ActionDispatchError(
                f"不允许的 requested_action: {requested_action}"
            )
        approval = self._write_approval(
            turn=turn,
            status="pending",
            reason=reason,
            requested_action=requested_action,
            resolved_by=None,
            options=arguments.get("options"),
            recommended_option=arguments.get("recommended_option"),
        )
        return self._observation(
            "request_approval",
            {
                "approval": approval,
                "stop": True,
                "run_status": "waiting_approval",
            },
        )

    def _finish_stage(
        self,
        _arguments: dict[str, Any],
        _turn: int,
    ) -> dict[str, Any]:
        raise ActionDispatchError(
            "case_plan stage 只能在 commit_stage 或 request_approval 后结束"
        )

    def write_automatic_approval(
        self,
        *,
        turn: int,
        reason: str,
        requested_action: str,
    ) -> dict[str, Any]:
        return self._write_approval(
            turn=turn,
            status="pending",
            reason=reason,
            requested_action=requested_action,
            resolved_by=None,
        )

    def _write_approval(
        self,
        *,
        turn: int,
        status: str,
        reason: str,
        requested_action: str,
        resolved_by: str | None,
        options: Any = None,
        recommended_option: Any = None,
    ) -> dict[str, Any]:
        normalized_options = (
            options
            if isinstance(options, list)
            and len(options) >= 2
            and all(isinstance(item, str) and item.strip() for item in options)
            else ["approve", "reject"]
        )
        normalized_recommended = (
            recommended_option
            if isinstance(recommended_option, str)
            and recommended_option in normalized_options
            else normalized_options[0]
        )
        binding = self.workspace.approval_binding()
        approval = {
            "approval_id": (
                f"{self.state['run_id']}-case-plan-turn-{turn}"
            ),
            "run_id": self.state["run_id"],
            "stage_id": "case_plan",
            "status": status,
            "reason": reason,
            "options": normalized_options,
            "recommended_option": normalized_recommended,
            "affected_truth_sources": [TARGET_RELATIVE_PATH],
            "requested_action": requested_action,
            **binding,
            "requested_at": utc_now(),
            "resolved_at": utc_now() if status != "pending" else None,
            "resolved_by": resolved_by,
        }
        validate_named(approval, "harness_approval.schema.json")
        path = (
            self.store.run_dir(str(self.state["run_id"]))
            / "approvals"
            / f"{approval['approval_id']}.json"
        )
        atomic_write_json(path, approval)
        self.store.append_event(
            self.state,
            "approval_requested",
            "case_plan",
            {
                "approval_id": approval["approval_id"],
                "status": approval["status"],
                "requested_action": requested_action,
            },
        )
        return approval

    @staticmethod
    def _required_string(arguments: dict[str, Any], key: str) -> str:
        value = arguments.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ActionDispatchError(f"Action 缺少非空字符串参数: {key}")
        return value.strip()

    @staticmethod
    def _observation(
        action_type: str,
        result: dict[str, Any],
        ok: bool = True,
    ) -> dict[str, Any]:
        return {
            "ok": ok,
            "action_type": action_type,
            "result": result,
        }

