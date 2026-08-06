from __future__ import annotations

from pathlib import Path
from typing import Any

from harness.approval_service import RequirementApprovalService
from harness.hook_dispatcher import HookDispatchResult, HookDispatcher
from harness.stage_registry import StageSpec, resolve_stage_plan, stage_ids
from harness.stage_runner import StageRunner, write_diagnostics
from harness.state_store import (
    HarnessStateError,
    StateStore,
    fingerprint_files,
    utc_now,
)


class DeterministicOrchestrator:
    def __init__(
        self,
        item_root: Path,
        project_code: str,
        work_item_id: str,
        runner: StageRunner | None = None,
        hooks: HookDispatcher | None = None,
    ) -> None:
        self.item_root = item_root
        self.project_code = project_code
        self.work_item_id = work_item_id
        self.store = StateStore(item_root)
        self.runner = runner or StageRunner()
        self.hooks = hooks or HookDispatcher()
        self.requirement_approval = RequirementApprovalService(
            item_root,
            hooks=self.hooks,
        )

    def start(
        self,
        run_id: str,
        work_item_level: str,
        strict: bool,
        stop_at: str,
        force_unlock: bool = False,
    ) -> tuple[int, dict[str, Any]]:
        plan = resolve_stage_plan(work_item_level)
        self._validate_stop_at(stop_at, work_item_level)
        with self.store.lock(run_id, force=force_unlock):
            state = self.store.create(
                run_id=run_id,
                project_code=self.project_code,
                work_item_id=self.work_item_id,
                work_item_level=work_item_level,
                strict=strict,
                stop_at=stop_at,
                stages=plan,
            )
            state["status"] = "running"
            self.store.save(state)
            self.store.append_event(state, "run_started", None, {})
            return self._execute(state, plan)

    def resume(
        self,
        run_id: str | None = None,
        stop_at: str | None = None,
        force_unlock: bool = False,
    ) -> tuple[int, dict[str, Any]]:
        resolved_run_id = run_id or self.store.current_run_id()
        with self.store.lock(resolved_run_id, force=force_unlock):
            state = self.store.load(resolved_run_id)
            self.requirement_approval.guard_resume(state=state)
            if state["status"] == "completed":
                return 0, state
            if state["status"] == "cancelled":
                raise HarnessStateError("cancelled run 不能恢复")
            if state["status"] == "failed":
                hook_result = self._dispatch_hook(
                    state=state,
                    event="repair_requested",
                    stage_id=(
                        str(state["last_error"].get("stage_id"))
                        if isinstance(state.get("last_error"), dict)
                        else None
                    ),
                    payload={"last_error": state.get("last_error")},
                )
                if hook_result.blocking_failure:
                    return 1, self._mark_hook_failure(
                        state,
                        hook_result.blocking_failure,
                    )
            plan = resolve_stage_plan(str(state["work_item_level"]))
            if stop_at is not None:
                self._validate_stop_at(stop_at, str(state["work_item_level"]))
                state["stop_at"] = stop_at
            elif state["status"] == "paused":
                state["stop_at"] = plan[-1].stage_id
            state["status"] = "running"
            state["last_error"] = None
            self.store.save(state)
            self.store.set_current(resolved_run_id)
            self.store.append_event(state, "run_resumed", None, {})
            return self._execute(state, plan)

    def cancel(
        self,
        run_id: str | None = None,
        force_unlock: bool = False,
    ) -> dict[str, Any]:
        resolved_run_id = run_id or self.store.current_run_id()
        with self.store.lock(resolved_run_id, force=force_unlock):
            state = self.store.load(resolved_run_id)
            if state["status"] == "completed":
                raise HarnessStateError("completed run 不能取消")
            state["status"] = "cancelled"
            state["current_stage"] = None
            self.store.save(state)
            self.store.append_event(state, "run_cancelled", None, {})
            return state

    def status(self, run_id: str | None = None) -> dict[str, Any]:
        resolved_run_id = run_id or self.store.current_run_id()
        return self.store.load(resolved_run_id)

    def _execute(
        self,
        state: dict[str, Any],
        plan: list[StageSpec],
    ) -> tuple[int, dict[str, Any]]:
        stage_records = {
            str(record["stage_id"]): record
            for record in state["stages"]
        }
        run_dir = self.store.run_dir(str(state["run_id"]))
        stop_at = str(state["stop_at"])

        for index, stage in enumerate(plan):
            record = stage_records[stage.stage_id]
            fingerprint = self._stage_fingerprint(state, stage)
            normalized_approval_checkpoint = False
            if (
                stage.stage_id == "requirement_intake"
                and self.requirement_approval.policy_required()
                and record["status"] == "succeeded"
                and record["input_fingerprint"] != fingerprint
            ):
                record["input_fingerprint"] = fingerprint
                self.store.save(state)
                normalized_approval_checkpoint = True
            if (
                record["status"] == "succeeded"
                and record["input_fingerprint"] == fingerprint
            ):
                self.store.append_event(
                    state,
                    "stage_skipped",
                    stage.stage_id,
                    {
                        "reason": (
                            "canonical_approval_checkpoint_normalized"
                            if normalized_approval_checkpoint
                            else "idempotent_checkpoint"
                        )
                    },
                )
                continue
            if record["status"] == "succeeded":
                self._invalidate_from(state, index)
                self.store.append_event(
                    state,
                    "stages_invalidated",
                    stage.stage_id,
                    {"reason": "input_fingerprint_changed"},
                )

            state["status"] = "running"
            state["current_stage"] = stage.stage_id
            record["status"] = "running"
            record["attempts"] += 1
            record["started_at"] = utc_now()
            record["completed_at"] = None
            record["last_exit_code"] = None
            self.store.save(state)
            self.store.append_event(
                state,
                "stage_started",
                stage.stage_id,
                {"attempt": record["attempts"]},
            )
            pre_hook = self._dispatch_hook(
                state=state,
                event="pre_stage",
                stage_id=stage.stage_id,
                payload={"attempt": record["attempts"]},
            )
            if pre_hook.blocking_failure:
                record["status"] = "failed"
                record["completed_at"] = utc_now()
                return 1, self._mark_hook_failure(
                    state,
                    pre_hook.blocking_failure,
                )

            execution = self.runner.run(
                stage=stage,
                item_root=self.item_root,
                run_dir=run_dir,
                project_code=self.project_code,
                work_item_id=self.work_item_id,
                work_item_level=str(state["work_item_level"]),
                strict=bool(state["strict"]),
                attempt=int(record["attempts"]),
                event_callback=lambda event_type, payload: self.store.append_event(
                    state,
                    event_type,
                    stage.stage_id,
                    payload,
                ),
            )
            record["input_fingerprint"] = fingerprint
            record["completed_at"] = utc_now()
            record["last_exit_code"] = execution.exit_code
            record["log_path"] = execution.log_path

            if not execution.succeeded:
                record["status"] = "failed"
                diagnostic_path = write_diagnostics(
                    run_dir,
                    stage.stage_id,
                    int(record["attempts"]),
                    execution.diagnostics,
                )
                responsible_stages = sorted(
                    {
                        str(diagnostic["stage_id"])
                        for diagnostic in execution.diagnostics
                    }
                )
                state["status"] = "failed"
                state["last_error"] = {
                    "stage_id": stage.stage_id,
                    "exit_code": execution.exit_code,
                    "log_path": execution.log_path,
                    "diagnostic_path": diagnostic_path,
                    "diagnostic_count": len(execution.diagnostics),
                    "responsible_stages": responsible_stages,
                }
                self.store.save(state)
                self.store.append_event(
                    state,
                    "stage_failed",
                    stage.stage_id,
                    state["last_error"],
                )
                self._dispatch_hook(
                    state=state,
                    event="fail_stage",
                    stage_id=stage.stage_id,
                    payload={
                        "attempt": record["attempts"],
                        "last_error": state["last_error"],
                    },
                )
                self.store.append_event(
                    state,
                    "run_failed",
                    stage.stage_id,
                    state["last_error"],
                )
                return execution.exit_code or 1, state

            record["status"] = "succeeded"
            state["last_error"] = None
            self.store.save(state)
            self.store.append_event(
                state,
                "stage_succeeded",
                stage.stage_id,
                {"attempt": record["attempts"]},
            )
            post_hook = self._dispatch_hook(
                state=state,
                event="post_stage",
                stage_id=stage.stage_id,
                payload={
                    "attempt": record["attempts"],
                    "exit_code": execution.exit_code,
                },
            )
            if post_hook.blocking_failure:
                record["status"] = "failed"
                return 1, self._mark_hook_failure(
                    state,
                    post_hook.blocking_failure,
                )

            if (
                stage.stage_id == "requirement_intake"
                and self.requirement_approval.policy_required()
            ):
                self.requirement_approval.request(
                    state=state,
                    record=record,
                )
                return 0, state

            if stage.stage_id == stop_at and index < len(plan) - 1:
                state["status"] = "paused"
                state["current_stage"] = None
                self.store.save(state)
                self.store.append_event(
                    state,
                    "run_paused",
                    stage.stage_id,
                    {"reason": "stop_at_reached"},
                )
                return 0, state

        state["status"] = "completed"
        state["current_stage"] = None
        state["last_error"] = None
        self.store.save(state)
        self.store.append_event(state, "run_completed", None, {})
        return 0, state

    def _stage_fingerprint(
        self,
        state: dict[str, Any],
        stage: StageSpec,
    ) -> str:
        if (
            stage.stage_id == "requirement_intake"
            and self.requirement_approval.policy_required()
        ):
            return self.requirement_approval.checkpoint_fingerprint(
                str(state["run_id"])
            )
        return fingerprint_files(self.item_root, stage.required_files)

    def _invalidate_from(self, state: dict[str, Any], index: int) -> None:
        for record in state["stages"][index:]:
            record["status"] = "pending"
            record["input_fingerprint"] = ""
            record["started_at"] = None
            record["completed_at"] = None
            record["last_exit_code"] = None
            record["log_path"] = None
        self.store.save(state)

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

    def _mark_hook_failure(
        self,
        state: dict[str, Any],
        execution: dict[str, Any],
    ) -> dict[str, Any]:
        state["status"] = "failed"
        state["current_stage"] = None
        state["last_error"] = {
            "stage_id": execution["stage_id"],
            "exit_code": execution["exit_code"] or 1,
            "error_type": "hook_failure",
            "execution_id": execution["execution_id"],
            "hook_id": execution["hook_id"],
            "hook_event": execution["event"],
            "error": execution["error"],
        }
        self.store.save(state)
        self.store.append_event(
            state,
            "run_failed",
            execution["stage_id"],
            state["last_error"],
        )
        return state

    @staticmethod
    def _validate_stop_at(stop_at: str, work_item_level: str) -> None:
        allowed = stage_ids(work_item_level)
        if stop_at not in allowed:
            raise HarnessStateError(
                f"stop_at={stop_at} 不属于 {work_item_level} 档阶段，允许值: {', '.join(allowed)}"
            )

