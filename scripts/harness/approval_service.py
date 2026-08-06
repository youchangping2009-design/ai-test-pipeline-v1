from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness.artifact_workspace import (
    ArtifactWorkspaceError,
    CasePlanArtifactWorkspace,
    file_hash,
)
from harness.contracts import validate_named
from harness.hook_dispatcher import HookDispatcher
from harness.requirement_approval import RequirementApprovalService
from harness.state_store import HarnessStateError, StateStore, atomic_write_json, utc_now
from harness.telemetry import finalize_persisted_telemetry


class CasePlanApprovalService:
    def __init__(
        self,
        item_root: Path,
        hooks: HookDispatcher | None = None,
    ) -> None:
        self.item_root = item_root
        self.store = StateStore(item_root)
        self.hooks = hooks or HookDispatcher()

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
        if not candidate_hash.strip():
            raise HarnessStateError("candidate_hash 不能为空")
        if not approval_id or any(
            character
            not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
            for character in approval_id
        ):
            raise HarnessStateError(f"非法 approval_id: {approval_id!r}")

        with self.store.lock(run_id, force=force_unlock):
            state = self.store.load(run_id)
            if state["mode"] != "agent" or state["status"] != "waiting_approval":
                raise HarnessStateError(
                    "只有 waiting_approval 的 agent run 可以审批提交"
                )
            approval_path = (
                self.store.run_dir(run_id)
                / "approvals"
                / f"{approval_id}.json"
            )
            if not approval_path.is_file():
                raise HarnessStateError(f"approval 不存在: {approval_id}")
            approval = json.loads(approval_path.read_text(encoding="utf-8"))
            validate_named(approval, "harness_approval.schema.json")
            if approval["run_id"] != run_id or approval["stage_id"] != "case_plan":
                raise HarnessStateError("approval 与当前 run/stage 不匹配")
            if approval["status"] != "pending":
                raise HarnessStateError(
                    f"approval 状态不是 pending: {approval['status']}"
                )
            if approval["requested_action"] != "commit_stage":
                raise HarnessStateError("该 approval 不允许提交 Case Plan")
            if candidate_hash != approval.get("candidate_hash"):
                raise HarnessStateError("candidate_hash 与 approval 绑定值不一致")

            workspace = CasePlanArtifactWorkspace(
                item_root=self.item_root,
                run_dir=self.store.run_dir(run_id),
                work_item_level=str(state["work_item_level"]),
            )
            existing_transaction = workspace.read_commit_transaction()
            if existing_transaction is not None:
                if existing_transaction["approval_id"] != approval_id:
                    raise HarnessStateError(
                        "Case Plan transaction 与 approval 不匹配"
                    )
                if existing_transaction["candidate_hash"] != candidate_hash:
                    raise HarnessStateError(
                        "Case Plan transaction candidate hash 不匹配"
                    )
                if existing_transaction["status"] == "committed":
                    return self._finalize_committed(
                        state=state,
                        approval=approval,
                        approval_path=approval_path,
                        workspace=workspace,
                        transaction=existing_transaction,
                    )
                if existing_transaction["status"] in {
                    "prepared",
                    "committing",
                }:
                    raise HarnessStateError(
                        "存在未恢复的 Case Plan transaction，"
                        "请先执行 recover-case-plan"
                    )
            binding = workspace.approval_binding()
            for key in (
                "expected_target_hash",
                "expected_upstream_fingerprint",
                "candidate_hash",
            ):
                if approval.get(key) != binding.get(key):
                    raise ArtifactWorkspaceError(
                        f"approval 绑定的 {key} 已漂移，拒绝提交"
                    )
            workspace.assert_commit_ready()
            transaction = workspace.prepare_commit(
                approval_id=approval_id,
                approved_by=approved_by.strip(),
            )
            try:
                workspace.apply_commit(transaction)
            except Exception:
                persisted = workspace.read_commit_transaction()
                if persisted is not None and persisted["status"] in {
                    "prepared",
                    "committing",
                }:
                    workspace.rollback_unfinished_commit()
                raise
            committed = workspace.read_commit_transaction()
            assert committed is not None
            return self._finalize_committed(
                state=state,
                approval=approval,
                approval_path=approval_path,
                workspace=workspace,
                transaction=committed,
            )

    def recover(
        self,
        *,
        run_id: str,
        force_unlock: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        with self.store.lock(run_id, force=force_unlock):
            state = self.store.load(run_id)
            if state["mode"] != "agent":
                raise HarnessStateError(
                    "recover-case-plan 只支持 agent run"
                )
            workspace = CasePlanArtifactWorkspace(
                item_root=self.item_root,
                run_dir=self.store.run_dir(run_id),
                work_item_level=str(state["work_item_level"]),
            )
            transaction = workspace.read_commit_transaction()
            if transaction is None:
                raise HarnessStateError(
                    "Case Plan commit transaction 不存在"
                )
            approval_path = (
                self.store.run_dir(run_id)
                / "approvals"
                / f"{transaction['approval_id']}.json"
            )
            if not approval_path.is_file():
                raise HarnessStateError(
                    "Case Plan transaction 对应 approval 不存在"
                )
            approval = json.loads(
                approval_path.read_text(encoding="utf-8")
            )
            validate_named(approval, "harness_approval.schema.json")
            if transaction["status"] == "committed":
                state, approval = self._finalize_committed(
                    state=state,
                    approval=approval,
                    approval_path=approval_path,
                    workspace=workspace,
                    transaction=transaction,
                )
                return state, approval, transaction
            if transaction["status"] in {"prepared", "committing"}:
                transaction = workspace.rollback_unfinished_commit()
            approval["status"] = "pending"
            approval["resolved_at"] = None
            approval["resolved_by"] = None
            approval["resolution_note"] = None
            validate_named(approval, "harness_approval.schema.json")
            atomic_write_json(approval_path, approval)
            record = state["stages"][0]
            record["status"] = "waiting_approval"
            record["completed_at"] = None
            state["status"] = "waiting_approval"
            state["current_stage"] = "case_plan"
            state["last_error"] = None
            self.store.save(state)
            self._append_event_once(
                state,
                "case_plan_commit_recovered",
                "case_plan",
                {
                    "approval_id": approval["approval_id"],
                    "transaction_id": transaction["transaction_id"],
                    "recovery": "rolled_back_to_pending",
                },
                approval_id=approval["approval_id"],
            )
            return state, approval, transaction

    def _finalize_committed(
        self,
        *,
        state: dict[str, Any],
        approval: dict[str, Any],
        approval_path: Path,
        workspace: CasePlanArtifactWorkspace,
        transaction: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if transaction["status"] != "committed":
            raise HarnessStateError(
                "只有 committed Case Plan transaction 可以完成 metadata"
            )
        if transaction["approval_id"] != approval.get("approval_id"):
            raise HarnessStateError("transaction 与 approval_id 不一致")
        for transaction_key, approval_key in (
            ("candidate_hash", "candidate_hash"),
            ("expected_target_hash", "expected_target_hash"),
            (
                "expected_upstream_fingerprint",
                "expected_upstream_fingerprint",
            ),
        ):
            if transaction[transaction_key] != approval.get(approval_key):
                raise HarnessStateError(
                    f"transaction 的 {transaction_key} 与 approval 不一致"
                )
        if file_hash(workspace.target_path) != transaction["candidate_hash"]:
            raise HarnessStateError(
                "committed transaction 的正式 Case Plan hash 已漂移"
            )
        workspace.finalize_commit_manifest(transaction)
        if approval["status"] not in {"pending", "approved"}:
            raise HarnessStateError(
                f"committed transaction 对应 approval 状态非法: {approval['status']}"
            )

        approval_event_existed = self._event_exists(
            str(state["run_id"]),
            "approval_resolved",
            approval_id=str(approval["approval_id"]),
        )
        approval["status"] = "approved"
        approval["resolved_at"] = approval.get("resolved_at") or utc_now()
        approval["resolved_by"] = transaction["approved_by"]
        approval["resolution_note"] = (
            approval.get("resolution_note")
            or f"transaction {transaction['transaction_id']} committed"
        )
        validate_named(approval, "harness_approval.schema.json")
        atomic_write_json(approval_path, approval)

        record = state["stages"][0]
        record["status"] = "succeeded"
        record["completed_at"] = record.get("completed_at") or utc_now()
        record["last_exit_code"] = 0
        state["status"] = "completed"
        state["current_stage"] = None
        state["last_error"] = None
        self.store.save(state)
        self._append_event_once(
            state,
            "approval_resolved",
            "case_plan",
            {
                "approval_id": approval["approval_id"],
                "status": "approved",
                "resolved_by": approval["resolved_by"],
            },
            approval_id=str(approval["approval_id"]),
        )
        if not approval_event_existed:
            self._dispatch_approval_resolved(state, approval)
        result = workspace._commit_result(transaction)
        self._append_event_once(
            state,
            "stage_committed",
            "case_plan",
            {
                "approval_id": approval["approval_id"],
                "target_path": result["target_path"],
                "committed_hash": result["committed_hash"],
                "transaction_id": result["transaction_id"],
            },
            approval_id=str(approval["approval_id"]),
        )
        invalidations_path = (
            self.store.run_dir(str(state["run_id"]))
            / "downstream_invalidations.json"
        )
        if invalidations_path.is_file():
            downstream = json.loads(
                invalidations_path.read_text(encoding="utf-8")
            )
        else:
            downstream = {
                "source_stage": "case_plan",
                "invalidated_stages": [
                    "testcases",
                    "traceability",
                    "review",
                    "strict_gate",
                ],
                "reason": "case_plan_truth_source_changed",
                "created_at": utc_now(),
            }
            atomic_write_json(invalidations_path, downstream)
        self._append_event_once(
            state,
            "stages_invalidated",
            "case_plan",
            downstream,
        )
        self._append_event_once(
            state,
            "stage_succeeded",
            "case_plan",
            {"mode": "agent"},
        )
        self._append_event_once(
            state,
            "run_completed",
            None,
            {"mode": "agent"},
        )
        finalize_persisted_telemetry(
            run_dir=self.store.run_dir(str(state["run_id"])),
            state=state,
            status="completed",
            stop_reason=None,
        )
        return state, approval

    def _append_event_once(
        self,
        state: dict[str, Any],
        event_type: str,
        stage_id: str | None,
        payload: dict[str, Any],
        approval_id: str | None = None,
    ) -> None:
        if self._event_exists(
            str(state["run_id"]),
            event_type,
            approval_id=approval_id,
        ):
            return
        self.store.append_event(state, event_type, stage_id, payload)

    def _event_exists(
        self,
        run_id: str,
        event_type: str,
        *,
        approval_id: str | None = None,
    ) -> bool:
        path = self.store.run_dir(run_id) / "events.jsonl"
        if not path.is_file():
            return False
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event_type") != event_type:
                continue
            if approval_id is not None and str(
                event.get("payload", {}).get("approval_id", "")
            ) != approval_id:
                continue
            return True
        return False

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
        if not approval_id or any(
            character
            not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
            for character in approval_id
        ):
            raise HarnessStateError(f"非法 approval_id: {approval_id!r}")
        with self.store.lock(run_id, force=force_unlock):
            state = self.store.load(run_id)
            if state["mode"] != "agent" or state["status"] != "waiting_approval":
                raise HarnessStateError(
                    "只有 waiting_approval 的 agent run 可以拒绝"
                )
            approval_path = (
                self.store.run_dir(run_id)
                / "approvals"
                / f"{approval_id}.json"
            )
            if not approval_path.is_file():
                raise HarnessStateError(f"approval 不存在: {approval_id}")
            approval = json.loads(approval_path.read_text(encoding="utf-8"))
            validate_named(approval, "harness_approval.schema.json")
            if approval["status"] != "pending" or approval["run_id"] != run_id:
                raise HarnessStateError("approval 状态或 run_id 不匹配")
            workspace = CasePlanArtifactWorkspace(
                item_root=self.item_root,
                run_dir=self.store.run_dir(run_id),
                work_item_level=str(state["work_item_level"]),
            )
            transaction = workspace.read_commit_transaction()
            if transaction is not None and transaction["status"] in {
                "prepared",
                "committing",
                "committed",
            }:
                raise HarnessStateError(
                    "Case Plan transaction 尚未恢复，"
                    "请先执行 recover-case-plan"
                )
            approval["status"] = "rejected"
            approval["resolved_at"] = utc_now()
            approval["resolved_by"] = rejected_by.strip()
            approval["resolution_note"] = reason.strip()
            validate_named(approval, "harness_approval.schema.json")
            atomic_write_json(approval_path, approval)

            record = state["stages"][0]
            record["status"] = "skipped"
            record["completed_at"] = utc_now()
            state["status"] = "cancelled"
            state["current_stage"] = None
            state["last_error"] = None
            self.store.save(state)
            self.store.append_event(
                state,
                "approval_resolved",
                "case_plan",
                {
                    "approval_id": approval_id,
                    "status": "rejected",
                    "resolved_by": approval["resolved_by"],
                },
            )
            self._dispatch_approval_resolved(state, approval)
            self.store.append_event(
                state,
                "run_cancelled",
                "case_plan",
                {"reason": "approval_rejected"},
            )
            finalize_persisted_telemetry(
                run_dir=self.store.run_dir(run_id),
                state=state,
                status="cancelled",
                stop_reason="approval_rejected",
            )
            return state, approval

    def _dispatch_approval_resolved(
        self,
        state: dict[str, Any],
        approval: dict[str, Any],
    ) -> None:
        self.hooks.dispatch(
            event="approval_resolved",
            state=state,
            run_dir=self.store.run_dir(str(state["run_id"])),
            stage_id="case_plan",
            payload={
                "approval_id": approval["approval_id"],
                "status": approval["status"],
                "resolved_by": approval.get("resolved_by"),
            },
            event_callback=lambda event_type, event_payload: self.store.append_event(
                state,
                event_type,
                "case_plan",
                event_payload,
            ),
        )

