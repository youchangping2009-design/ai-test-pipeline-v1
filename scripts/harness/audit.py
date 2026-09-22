from __future__ import annotations

import json
import hashlib
from collections import Counter
from pathlib import Path
from typing import Any

from harness.artifact_workspace import TARGET_RELATIVE_PATH, file_hash
from harness.contracts import ContractError, validate_named
from harness.generation_workspace import aggregate_hash
from harness.requirement_approval import (
    RECEIPT_RELATIVE_PATH,
    current_binding,
    receipt_matches_binding,
    requirement_approval_required,
)
from harness.review_disposition import ReviewDispositionService
from harness.state_store import HarnessStateError, StateStore, atomic_write_json, utc_now
from validate_feedback_action_journal import validate_feedback_action_journal


class HarnessRunAuditor:
    def __init__(self, item_root: Path) -> None:
        self.item_root = item_root
        self.store = StateStore(item_root)

    def audit(self, run_id: str) -> tuple[int, dict[str, Any]]:
        errors: list[str] = []
        checks: list[str] = []
        counts = {
            "events": 0,
            "actions": 0,
            "approvals": 0,
            "diagnostics": 0,
            "hooks": 0,
            "generation_candidates": 0,
            "publish_transactions": 0,
            "case_plan_commit_transactions": 0,
            "role_runtime_states": 0,
            "parallel_review_runtime_states": 0,
            "parallel_review_actions": 0,
            "parallel_review_findings": 0,
            "parallel_review_bundles": 0,
            "multi_role_recoveries": 0,
            "requirement_approvals": 0,
            "feedback_actions": 0,
            "review_dispositions": 0,
        }
        try:
            state = self.store.load(run_id)
            checks.append("run_state")
        except Exception as exc:
            state = {"run_id": run_id, "mode": "unknown", "status": "unknown"}
            errors.append(f"run_state: {exc}")

        run_dir = self.store.run_dir(run_id)
        events = self._audit_events(
            run_dir,
            run_id,
            checks,
            errors,
            counts,
        )
        actions = self._audit_json_documents(
            root=run_dir / "actions",
            pattern="*.json",
            schema_name="harness_model_action.schema.json",
            label="actions",
            checks=checks,
            errors=errors,
            counts=counts,
        )
        approvals = self._audit_json_documents(
            root=run_dir / "approvals",
            pattern="*.json",
            schema_name="harness_approval.schema.json",
            label="approvals",
            checks=checks,
            errors=errors,
            counts=counts,
        )
        hook_executions = self._audit_json_documents(
            root=run_dir / "hooks",
            pattern="*.json",
            schema_name="harness_hook_execution.schema.json",
            label="hooks",
            checks=checks,
            errors=errors,
            counts=counts,
        )
        self._audit_hook_linkage(
            events,
            hook_executions,
            checks,
            errors,
        )
        self._audit_action_linkage(events, actions, checks, errors)
        self._audit_approval_linkage(events, approvals, checks, errors)
        self._audit_requirement_approval(
            state,
            events,
            checks,
            errors,
            counts,
        )
        self._audit_feedback_actions(run_id, checks, errors, counts)
        self._audit_review_disposition(
            run_id,
            state,
            events,
            checks,
            errors,
            counts,
        )
        self._audit_diagnostics(run_dir, checks, errors, counts)
        self._audit_telemetry(run_dir, checks, errors)
        self._audit_terminal_state(run_dir, state, approvals, checks, errors)
        self._audit_case_plan_commit(
            run_dir,
            state,
            approvals,
            checks,
            errors,
            counts,
        )
        self._audit_generation(
            run_dir,
            state,
            approvals,
            checks,
            errors,
            counts,
        )
        self._audit_role_runtime(
            run_dir,
            state,
            checks,
            errors,
            counts,
        )
        self._audit_parallel_review(
            run_dir,
            state,
            events,
            checks,
            errors,
            counts,
        )
        self._audit_multi_role_recovery(
            run_dir,
            state,
            approvals,
            events,
            checks,
            errors,
            counts,
        )

        report = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "audited_at": utc_now(),
            "passed": not errors,
            "checks": checks,
            "errors": errors,
            "counts": counts,
        }
        validate_named(report, "harness_audit_report.schema.json")
        atomic_write_json(run_dir / "audit_report.json", report)
        return (0 if report["passed"] else 1), report

    def _audit_feedback_actions(
        self,
        run_id: str,
        checks: list[str],
        errors: list[str],
        counts: dict[str, int],
    ) -> None:
        feedback_path = self.item_root / "design" / "design_feedback.json"
        action_dir = (
            self.item_root / ".generation" / "feedback_applications" / "actions"
        )
        if not feedback_path.is_file() and not action_dir.exists():
            checks.append("feedback_action_journal")
            return
        try:
            result = validate_feedback_action_journal(self.item_root)
            counts["feedback_actions"] = int(
                result.get("actions_by_run", {}).get(run_id, 0)
            )
        except (OSError, ValueError, json.JSONDecodeError, ContractError) as exc:
            errors.append(f"feedback_action_journal: {exc}")
        checks.append("feedback_action_journal")

    def _audit_review_disposition(
        self,
        run_id: str,
        state: dict[str, Any],
        events: list[dict[str, Any]],
        checks: list[str],
        errors: list[str],
        counts: dict[str, int],
    ) -> None:
        service = ReviewDispositionService(self.item_root)
        path = service.receipt_path(run_id)
        records = {
            str(record.get("stage_id")): record
            for record in state.get("stages", [])
            if isinstance(record, dict)
        }
        review = records.get("review")
        disposition_events = [
            event
            for event in events
            if event.get("event_type") == "review_disposition_declared"
            and event.get("stage_id") == "review"
        ]
        terminal_events = [
            event
            for event in events
            if event.get("event_type") == "stage_not_applicable"
            and event.get("stage_id") == "review"
        ]
        if not path.is_file():
            if (
                state.get("mode") == "validate"
                and review
                and review.get("status") == "skipped"
            ):
                errors.append(
                    "review_disposition: Review skipped 但缺少 not_applicable receipt"
                )
            if disposition_events or terminal_events:
                errors.append("review_disposition: 有事件但 receipt 不存在")
            checks.append("review_disposition")
            return
        counts["review_dispositions"] += 1
        try:
            receipt = service.validate(run_id)
        except (HarnessStateError, OSError, ValueError) as exc:
            errors.append(f"review_disposition: {exc}")
            checks.append("review_disposition")
            return
        if len(disposition_events) != 1:
            errors.append(
                "review_disposition: declared event 数量应为 1，"
                f"实际 {len(disposition_events)}"
            )
        else:
            payload = disposition_events[0].get("payload", {})
            if payload.get("disposition") != receipt.get("disposition"):
                errors.append("review_disposition: declared event disposition 不一致")
            if payload.get("declared_by") != receipt.get("declared_by"):
                errors.append("review_disposition: declared event declared_by 不一致")
            if payload.get("scope_sha256") != receipt.get("code_review_scope", {}).get("sha256"):
                errors.append("review_disposition: declared event scope hash 不一致")
        if review and review.get("status") == "skipped":
            if review.get("attempts", 0) < 1 or review.get("last_exit_code") != 0:
                errors.append("review_disposition: skipped Review 未完成确定性校验")
            if len(terminal_events) != 1:
                errors.append(
                    "review_disposition: stage_not_applicable event 数量应为 1，"
                    f"实际 {len(terminal_events)}"
                )
            traceability = records.get("traceability")
            if not traceability or traceability.get("status") != "succeeded":
                errors.append("review_disposition: Review N/A 前 Traceability 未成功")
        elif terminal_events:
            errors.append("review_disposition: Review 未 skipped 但存在终结事件")
        if state.get("status") == "completed" and (
            not review or review.get("status") != "skipped"
        ):
            errors.append("review_disposition: completed run 未以 skipped 记录 Review N/A")
        checks.append("review_disposition")

    def _audit_events(
        self,
        run_dir: Path,
        run_id: str,
        checks: list[str],
        errors: list[str],
        counts: dict[str, int],
    ) -> list[dict[str, Any]]:
        path = run_dir / "events.jsonl"
        events: list[dict[str, Any]] = []
        if not path.is_file():
            errors.append("events: events.jsonl 不存在")
            return events
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            errors.append(f"events: {exc}")
            return events
        expected_sequence = 1
        for line_number, line in enumerate(
            lines,
            start=1,
        ):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                validate_named(event, "harness_event.schema.json")
                if event["sequence"] != expected_sequence:
                    errors.append(
                        f"events:{line_number} sequence 应为 {expected_sequence}，"
                        f"实际 {event['sequence']}"
                    )
                if event["run_id"] != run_id:
                    errors.append(f"events:{line_number} run_id 不匹配")
                events.append(event)
            except (json.JSONDecodeError, ContractError, KeyError) as exc:
                errors.append(f"events:{line_number}: {exc}")
            expected_sequence += 1
            counts["events"] += 1
        checks.append("events")
        return events

    def _audit_json_documents(
        self,
        *,
        root: Path,
        pattern: str,
        schema_name: str,
        label: str,
        checks: list[str],
        errors: list[str],
        counts: dict[str, int],
    ) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        if not root.exists():
            checks.append(label)
            return payloads
        for path in sorted(root.glob(pattern)):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                validate_named(payload, schema_name)
                payloads.append(payload)
            except (OSError, json.JSONDecodeError, ContractError) as exc:
                errors.append(f"{label}:{path.name}: {exc}")
            counts[label] += 1
        checks.append(label)
        return payloads

    def _audit_diagnostics(
        self,
        run_dir: Path,
        checks: list[str],
        errors: list[str],
        counts: dict[str, int],
    ) -> None:
        root = run_dir / "diagnostics"
        if root.exists():
            for path in sorted(root.rglob("*.json")):
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    if not isinstance(payload, list):
                        raise ContractError("diagnostic 文件必须是数组")
                    for diagnostic in payload:
                        validate_named(
                            diagnostic,
                            "harness_diagnostic.schema.json",
                        )
                        counts["diagnostics"] += 1
                except (OSError, json.JSONDecodeError, ContractError) as exc:
                    errors.append(f"diagnostics:{path.name}: {exc}")
        checks.append("diagnostics")

    @staticmethod
    def _audit_action_linkage(
        events: list[dict[str, Any]],
        actions: list[dict[str, Any]],
        checks: list[str],
        errors: list[str],
    ) -> None:
        event_ids = Counter(
            str(event.get("payload", {}).get("action_id", ""))
            for event in events
            if event.get("event_type") == "agent_action_received"
        )
        persisted_ids = Counter(
            str(action.get("action_id", "")) for action in actions
        )
        for action_id in sorted(set(event_ids) | set(persisted_ids)):
            if not action_id:
                errors.append("action_linkage: 存在空 action_id")
                continue
            if event_ids[action_id] != 1:
                errors.append(
                    f"action_linkage: {action_id} received event 数量应为 1，"
                    f"实际 {event_ids[action_id]}"
                )
            if persisted_ids[action_id] != 1:
                errors.append(
                    f"action_linkage: {action_id} action 文件数量应为 1，"
                    f"实际 {persisted_ids[action_id]}"
                )
        checks.append("action_linkage")

    @staticmethod
    def _audit_approval_linkage(
        events: list[dict[str, Any]],
        approvals: list[dict[str, Any]],
        checks: list[str],
        errors: list[str],
    ) -> None:
        requirement_approval_ids = {
            str(event.get("payload", {}).get("approval_id", ""))
            for event in events
            if event.get("event_type") == "approval_requested"
            and event.get("payload", {}).get("requested_action")
            == "approve_requirement_summary"
        }
        requested = Counter(
            str(event.get("payload", {}).get("approval_id", ""))
            for event in events
            if event.get("event_type") == "approval_requested"
            and str(event.get("payload", {}).get("approval_id", ""))
            not in requirement_approval_ids
        )
        requested_payloads: dict[str, list[dict[str, Any]]] = {}
        for event in events:
            if event.get("event_type") != "approval_requested":
                continue
            payload = event.get("payload", {})
            approval_id = str(payload.get("approval_id", ""))
            if approval_id in requirement_approval_ids:
                continue
            requested_payloads.setdefault(approval_id, []).append(payload)
        resolved_events: dict[str, list[str]] = {}
        for event in events:
            if event.get("event_type") != "approval_resolved":
                continue
            approval_id = str(
                event.get("payload", {}).get("approval_id", "")
            )
            if approval_id in requirement_approval_ids:
                continue
            resolved_events.setdefault(approval_id, []).append(
                str(event.get("payload", {}).get("status", ""))
            )
        persisted = Counter(
            str(approval.get("approval_id", "")) for approval in approvals
        )
        approval_by_id = {
            str(approval.get("approval_id", "")): approval
            for approval in approvals
        }
        all_ids = set(requested) | set(resolved_events) | set(persisted)
        for approval_id in sorted(all_ids):
            if not approval_id:
                errors.append("approval_linkage: 存在空 approval_id")
                continue
            if requested[approval_id] != 1:
                errors.append(
                    f"approval_linkage: {approval_id} requested event 数量应为 1，"
                    f"实际 {requested[approval_id]}"
                )
            if persisted[approval_id] != 1:
                errors.append(
                    f"approval_linkage: {approval_id} approval 文件数量应为 1，"
                    f"实际 {persisted[approval_id]}"
                )
                continue
            persisted_status = str(
                approval_by_id[approval_id].get("status", "")
            )
            if len(requested_payloads.get(approval_id, [])) == 1:
                request_payload = requested_payloads[approval_id][0]
                for key in ("requested_action", "candidate_hash"):
                    event_value = request_payload.get(key)
                    if (
                        event_value is not None
                        and event_value != approval_by_id[approval_id].get(key)
                    ):
                        errors.append(
                            f"approval_linkage: {approval_id} 的 {key} "
                            "与 requested event 不一致"
                        )
            statuses = resolved_events.get(approval_id, [])
            if persisted_status == "pending" and statuses:
                errors.append(
                    f"approval_linkage: pending 审批 {approval_id} 不应有 resolved event"
                )
            if persisted_status in {"approved", "rejected"} and statuses != [
                persisted_status
            ]:
                errors.append(
                    f"approval_linkage: {approval_id} resolved event 与状态不一致"
                )
        checks.append("approval_linkage")

    def _audit_requirement_approval(
        self,
        state: dict[str, Any],
        events: list[dict[str, Any]],
        checks: list[str],
        errors: list[str],
        counts: dict[str, int],
    ) -> None:
        manifest_path = self.item_root / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = {}
        if not requirement_approval_required(manifest):
            checks.append("requirement_approval")
            return
        path = self.item_root / RECEIPT_RELATIVE_PATH
        if not path.is_file():
            errors.append("requirement_approval: receipt 不存在")
            checks.append("requirement_approval")
            return
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
            validate_named(receipt, "requirement_approval.schema.json")
            counts["requirement_approvals"] += 1
        except (OSError, json.JSONDecodeError, ContractError) as exc:
            errors.append(f"requirement_approval: receipt 无效: {exc}")
            checks.append("requirement_approval")
            return
        run_id = str(state.get("run_id", ""))
        try:
            binding = current_binding(self.item_root, run_id)
        except Exception as exc:
            errors.append(f"requirement_approval: 无法计算 binding: {exc}")
            checks.append("requirement_approval")
            return
        if not receipt_matches_binding(receipt, binding):
            errors.append("requirement_approval: receipt hash/fingerprint/run 已漂移")
        approval_id = str(receipt.get("approval_id", ""))
        requested = [
            event
            for event in events
            if event.get("event_type") == "approval_requested"
            and event.get("payload", {}).get("approval_id") == approval_id
            and event.get("payload", {}).get("requested_action")
            == "approve_requirement_summary"
        ]
        resolved = [
            event
            for event in events
            if event.get("event_type") == "approval_resolved"
            and event.get("payload", {}).get("approval_id") == approval_id
        ]
        if len(requested) != 1:
            errors.append(
                "requirement_approval: approval_requested 事件必须且只能存在一次"
            )
        status = receipt.get("status")
        stage_record = next(
            (
                record
                for record in state.get("stages", [])
                if record.get("stage_id") == "requirement_intake"
            ),
            None,
        )
        expected_stage_status = {
            "pending": "waiting_approval",
            "approved": "succeeded",
            "rejected": "skipped",
        }.get(status)
        if (
            not isinstance(stage_record, dict)
            or stage_record.get("status") != expected_stage_status
        ):
            errors.append(
                "requirement_approval: receipt 与 requirement_intake stage 状态不一致"
            )
        if status == "pending":
            if resolved:
                errors.append("requirement_approval: pending receipt 不应有 resolved 事件")
            if state.get("status") != "waiting_approval":
                errors.append("requirement_approval: pending receipt 与 run state 不一致")
        else:
            resolved_statuses = [
                event.get("payload", {}).get("status") for event in resolved
            ]
            if resolved_statuses != [status]:
                errors.append("requirement_approval: resolved 事件与 receipt 不一致")
            expected_states = (
                {"paused", "running", "completed", "cancelled"}
                if status == "approved"
                else {"cancelled"}
            )
            if state.get("status") not in expected_states:
                errors.append(
                    f"requirement_approval: {status} receipt 与 run state 不一致"
                )
        checks.append("requirement_approval")

    @staticmethod
    def _audit_hook_linkage(
        events: list[dict[str, Any]],
        executions: list[dict[str, Any]],
        checks: list[str],
        errors: list[str],
    ) -> None:
        started = {
            event.get("payload", {}).get("execution_id")
            for event in events
            if event.get("event_type") == "hook_dispatch_started"
        }
        terminal = {
            event.get("payload", {}).get("execution_id")
            for event in events
            if event.get("event_type")
            in {"hook_dispatch_completed", "hook_dispatch_failed"}
        }
        persisted = {
            execution.get("execution_id")
            for execution in executions
        }
        for execution_id in sorted(
            value for value in started | terminal | persisted if value
        ):
            if execution_id not in started:
                errors.append(
                    f"hook_linkage: {execution_id} 缺少 started event"
                )
            if execution_id not in terminal:
                errors.append(
                    f"hook_linkage: {execution_id} 缺少 terminal event"
                )
            if execution_id not in persisted:
                errors.append(
                    f"hook_linkage: {execution_id} 缺少 execution 文件"
                )
        checks.append("hook_linkage")

    def _audit_telemetry(
        self,
        run_dir: Path,
        checks: list[str],
        errors: list[str],
    ) -> None:
        path = run_dir / "telemetry.json"
        if path.exists():
            try:
                validate_named(
                    json.loads(path.read_text(encoding="utf-8")),
                    "harness_telemetry.schema.json",
                )
            except (OSError, json.JSONDecodeError, ContractError) as exc:
                errors.append(f"telemetry: {exc}")
        checks.append("telemetry")

    def _audit_terminal_state(
        self,
        run_dir: Path,
        state: dict[str, Any],
        approvals: list[dict[str, Any]],
        checks: list[str],
        errors: list[str],
    ) -> None:
        status = state.get("status")
        pending = [
            approval
            for approval in approvals
            if approval.get("status") == "pending"
        ]
        requirement_receipt_pending = False
        receipt_path = self.item_root / RECEIPT_RELATIVE_PATH
        if receipt_path.is_file():
            try:
                requirement_receipt_pending = (
                    json.loads(receipt_path.read_text(encoding="utf-8")).get("status")
                    == "pending"
                )
            except (OSError, json.JSONDecodeError):
                requirement_receipt_pending = False
        if status == "waiting_approval" and not pending and not requirement_receipt_pending:
            errors.append("terminal_state: waiting_approval 但没有 pending approval")
        if status in {"completed", "cancelled"} and pending:
            errors.append(f"terminal_state: {status} 仍存在 pending approval")
        if state.get("mode") in {"agent", "multi_role"} and status in {
            "waiting_approval",
            "completed",
            "cancelled",
        }:
            state_name = (
                "role_runtime_state.json"
                if state.get("mode") == "multi_role"
                else "agent_state.json"
            )
            for name in (state_name, "telemetry.json", "run_summary.json"):
                if not (run_dir / name).is_file():
                    errors.append(f"terminal_state: 缺少 {name}")
        workspace_path = run_dir / "staging" / "case_plan_workspace.json"
        if workspace_path.exists():
            try:
                workspace = json.loads(
                    workspace_path.read_text(encoding="utf-8")
                )
                committed_hash = workspace.get("committed_hash")
                if committed_hash:
                    target = self.item_root / TARGET_RELATIVE_PATH
                    if file_hash(target) != committed_hash:
                        errors.append(
                            "terminal_state: committed Case Plan hash 已漂移"
                        )
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"terminal_state: case_plan workspace: {exc}")
        checks.append("terminal_state")

    def _audit_generation(
        self,
        run_dir: Path,
        state: dict[str, Any],
        approvals: list[dict[str, Any]],
        checks: list[str],
        errors: list[str],
        counts: dict[str, int],
    ) -> None:
        candidate_path = run_dir / "generation_candidate.json"
        transaction_path = run_dir / "publish_transaction.json"
        candidate: dict[str, Any] | None = None
        transaction: dict[str, Any] | None = None
        if candidate_path.exists():
            counts["generation_candidates"] += 1
            try:
                candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
                validate_named(
                    candidate,
                    "harness_generation_candidate.schema.json",
                )
                staged_entries: list[tuple[str, str | None]] = []
                target_entries: list[tuple[str, str | None]] = []
                for entry in candidate["files"]:
                    staged = run_dir / "staging" / "work_item" / entry["path"]
                    staged_hash = file_hash(staged)
                    if staged_hash != entry["sha256"]:
                        errors.append(
                            f"generation: staged hash 不匹配 {entry['path']}"
                        )
                    staged_entries.append((entry["path"], staged_hash))
                    target_entries.append(
                        (entry["path"], entry["expected_target_hash"])
                    )
                if (
                    aggregate_hash(staged_entries)
                    != candidate["candidate_hash"]
                ):
                    errors.append("generation: candidate aggregate hash 不匹配")
                if (
                    aggregate_hash(target_entries)
                    != candidate["expected_target_hash"]
                ):
                    errors.append("generation: expected target aggregate hash 不匹配")
            except (OSError, json.JSONDecodeError, ContractError, KeyError) as exc:
                errors.append(f"generation_candidate: {exc}")
        if transaction_path.exists():
            counts["publish_transactions"] += 1
            try:
                transaction = json.loads(
                    transaction_path.read_text(encoding="utf-8")
                )
                validate_named(
                    transaction,
                    "harness_publish_transaction.schema.json",
                )
            except (OSError, json.JSONDecodeError, ContractError) as exc:
                errors.append(f"publish_transaction: {exc}")
        generation_mode = state.get("mode") == "generation"
        multi_role_publish = state.get("mode") == "multi_role" and any(
            approval.get("requested_action") == "publish_generation"
            for approval in approvals
        )
        if generation_mode or multi_role_publish:
            status = state.get("status")
            pending = [
                approval
                for approval in approvals
                if approval.get("requested_action") == "publish_generation"
                and approval.get("status") == "pending"
            ]
            if status == "waiting_approval" and (
                candidate is None or len(pending) != 1
            ):
                errors.append(
                    "generation: waiting_approval 缺少 candidate 或唯一 pending approval"
                )
            if status == "completed":
                if transaction is None or transaction.get("status") != "committed":
                    errors.append("generation: completed 但 transaction 未 committed")
                if candidate:
                    for entry in candidate["files"]:
                        target = self.item_root / entry["path"]
                        if file_hash(target) != entry["sha256"]:
                            errors.append(
                                f"generation: published hash 不匹配 {entry['path']}"
                            )
            if transaction and transaction.get("status") in {
                "prepared",
                "publishing",
            }:
                errors.append("generation: 存在未恢复 publish transaction")
            if candidate:
                publish_approvals = [
                    approval
                    for approval in approvals
                    if approval.get("requested_action") == "publish_generation"
                ]
                for approval in publish_approvals:
                    for key in (
                        "candidate_hash",
                        "expected_target_hash",
                        "expected_upstream_fingerprint",
                    ):
                        if approval.get(key) != candidate.get(key):
                            errors.append(
                                f"generation: approval {approval.get('approval_id')} "
                                f"的 {key} 与 candidate 不一致"
                            )
                if transaction:
                    transaction_paths = {
                        str(entry.get("path", ""))
                        for entry in transaction.get("files", [])
                    }
                    candidate_paths = {
                        str(entry.get("path", ""))
                        for entry in candidate.get("files", [])
                    }
                    if transaction_paths != candidate_paths:
                        errors.append(
                            "generation: transaction 文件集与 candidate 不一致"
                        )
        checks.append("generation")

    def _audit_case_plan_commit(
        self,
        run_dir: Path,
        state: dict[str, Any],
        approvals: list[dict[str, Any]],
        checks: list[str],
        errors: list[str],
        counts: dict[str, int],
    ) -> None:
        path = run_dir / "case_plan_commit_transaction.json"
        if not path.is_file():
            checks.append("case_plan_commit")
            return
        counts["case_plan_commit_transactions"] += 1
        try:
            transaction = json.loads(path.read_text(encoding="utf-8"))
            validate_named(
                transaction,
                "harness_case_plan_commit_transaction.schema.json",
            )
        except (OSError, json.JSONDecodeError, ContractError) as exc:
            errors.append(f"case_plan_commit: {exc}")
            checks.append("case_plan_commit")
            return
        matching = [
            approval
            for approval in approvals
            if approval.get("approval_id") == transaction["approval_id"]
        ]
        if len(matching) != 1:
            errors.append(
                "case_plan_commit: transaction 缺少唯一对应 approval"
            )
            checks.append("case_plan_commit")
            return
        approval = matching[0]
        for transaction_key, approval_key in (
            ("candidate_hash", "candidate_hash"),
            ("expected_target_hash", "expected_target_hash"),
            (
                "expected_upstream_fingerprint",
                "expected_upstream_fingerprint",
            ),
        ):
            if transaction[transaction_key] != approval.get(approval_key):
                errors.append(
                    f"case_plan_commit: {transaction_key} 与 approval 不一致"
                )
        status = transaction["status"]
        target_hash = file_hash(self.item_root / TARGET_RELATIVE_PATH)
        if status in {"prepared", "committing"}:
            errors.append(
                f"case_plan_commit: 存在未恢复 transaction {status}"
            )
        elif status == "committed":
            if target_hash != transaction["candidate_hash"]:
                errors.append(
                    "case_plan_commit: committed target hash 不一致"
                )
            if approval.get("status") != "approved":
                errors.append(
                    "case_plan_commit: committed 但 approval 未 approved"
                )
            if state.get("status") != "completed":
                errors.append(
                    "case_plan_commit: committed 但 run 未 completed"
                )
        elif status == "rolled_back":
            if target_hash != transaction["expected_target_hash"]:
                errors.append(
                    "case_plan_commit: rolled_back target hash 不一致"
                )
            valid_terminal = (
                approval.get("status") == "pending"
                and state.get("status") == "waiting_approval"
            ) or (
                approval.get("status") == "rejected"
                and state.get("status") == "cancelled"
            )
            if not valid_terminal:
                errors.append(
                    "case_plan_commit: rolled_back 后 approval/run 状态不一致"
                )
        checks.append("case_plan_commit")

    def _audit_role_runtime(
        self,
        run_dir: Path,
        state: dict[str, Any],
        checks: list[str],
        errors: list[str],
        counts: dict[str, int],
    ) -> None:
        if state.get("mode") != "multi_role":
            checks.append("role_runtime")
            return
        path = run_dir / "role_runtime_state.json"
        if not path.is_file():
            errors.append("role_runtime: role_runtime_state.json 不存在")
            checks.append("role_runtime")
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            validate_named(payload, "harness_role_runtime.schema.json")
            counts["role_runtime_states"] += 1
            stage_ids = [record.get("stage_id") for record in state.get("stages", [])]
            if payload.get("role_order") != stage_ids:
                errors.append("role_runtime: role_order 与 run stages 不一致")
            statuses = [role.get("status") for role in payload.get("roles", [])]
            succeeded_prefix_ended = False
            for status in statuses:
                if status == "succeeded" and succeeded_prefix_ended:
                    errors.append("role_runtime: 后序角色成功但前序角色未成功")
                    break
                if status != "succeeded":
                    succeeded_prefix_ended = True
            if state.get("status") == "waiting_approval":
                current_role = payload.get("current_role")
                if current_role not in payload.get("role_order", []):
                    errors.append("role_runtime: waiting_approval 缺少 current_role")
            if state.get("status") == "completed" and any(
                status != "succeeded" for status in statuses
            ):
                errors.append("role_runtime: completed 但存在未成功角色")
            if state.get("status") == "cancelled" and payload.get("current_role") is not None:
                errors.append("role_runtime: cancelled 后 current_role 未清空")
        except (OSError, json.JSONDecodeError, ContractError) as exc:
            errors.append(f"role_runtime: {exc}")
        checks.append("role_runtime")

    def _audit_parallel_review(
        self,
        run_dir: Path,
        state: dict[str, Any],
        events: list[dict[str, Any]],
        checks: list[str],
        errors: list[str],
        counts: dict[str, int],
    ) -> None:
        root = run_dir / "parallel_review"
        runtime_path = root / "runtime_state.json"
        if not runtime_path.is_file():
            checks.append("parallel_review")
            return
        try:
            runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
            validate_named(
                runtime,
                "harness_parallel_review_runtime.schema.json",
            )
            counts["parallel_review_runtime_states"] += 1
        except (OSError, json.JSONDecodeError, ContractError) as exc:
            errors.append(f"parallel_review: runtime_state: {exc}")
            checks.append("parallel_review")
            return
        if state.get("mode") != "multi_role":
            errors.append("parallel_review: 仅允许存在于 multi_role run")
        reviewers = runtime.get("reviewers", [])
        succeeded = sum(
            1 for reviewer in reviewers if reviewer.get("status") == "succeeded"
        )
        barrier = runtime.get("barrier", {})
        if barrier.get("succeeded") != succeeded:
            errors.append("parallel_review: barrier succeeded 计数不一致")
        if bool(barrier.get("passed")) != (succeeded == 3):
            errors.append("parallel_review: barrier passed 与 3/3 状态不一致")
        if runtime.get("status") == "failed" and state.get("status") not in {
            "waiting_approval",
            "cancelled",
        }:
            errors.append("parallel_review: 失败终态未停在人工决策或取消")
        if not barrier.get("passed"):
            formatter = next(
                (
                    stage
                    for stage in state.get("stages", [])
                    if stage.get("stage_id") == "asset_formatter"
                ),
                None,
            )
            if formatter and formatter.get("status") not in {"pending", "skipped"}:
                errors.append("parallel_review: barrier 失败后 Asset Formatter 被执行")
        telemetry: dict[str, Any] = {}
        telemetry_path = run_dir / "telemetry.json"
        if telemetry_path.is_file():
            try:
                telemetry = json.loads(telemetry_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                telemetry = {}
        telemetry_reviewers = telemetry.get("parallel_reviewers", {})
        persisted_action_ids: Counter[str] = Counter()
        for reviewer_record in reviewers:
            reviewer = str(reviewer_record.get("reviewer", ""))
            actions_root = root / reviewer / "actions"
            action_count = 0
            if actions_root.exists():
                for action_path in sorted(actions_root.glob("*.json")):
                    try:
                        action = json.loads(action_path.read_text(encoding="utf-8"))
                        validate_named(
                            action,
                            "harness_subagent_action.schema.json",
                        )
                        if action.get("reviewer") != reviewer:
                            errors.append(
                                f"parallel_review: {action_path.name} reviewer 不一致"
                            )
                        persisted_action_ids[str(action.get("action_id", ""))] += 1
                    except (OSError, json.JSONDecodeError, ContractError) as exc:
                        errors.append(
                            f"parallel_review: action {action_path.name}: {exc}"
                        )
                    action_count += 1
                    counts["parallel_review_actions"] += 1
            if action_count != reviewer_record.get("action_count"):
                errors.append(
                    f"parallel_review: {reviewer} action_count 不一致"
                )
            findings_path = root / reviewer / "findings.json"
            finding_count = 0
            if findings_path.is_file():
                try:
                    payload = json.loads(findings_path.read_text(encoding="utf-8"))
                    if payload.get("reviewer") != reviewer:
                        errors.append(
                            f"parallel_review: {reviewer} findings reviewer 不一致"
                        )
                    findings = payload.get("findings")
                    if not isinstance(findings, list):
                        raise ContractError("findings 必须是数组")
                    for finding in findings:
                        validate_named(
                            finding,
                            "harness_review_finding.schema.json",
                        )
                        if finding.get("reviewer") != reviewer:
                            errors.append(
                                f"parallel_review: {reviewer} finding reviewer 不一致"
                            )
                        finding_count += 1
                        counts["parallel_review_findings"] += 1
                except (OSError, json.JSONDecodeError, ContractError) as exc:
                    errors.append(f"parallel_review: {reviewer} findings: {exc}")
            if reviewer_record.get("status") == "succeeded" and not findings_path.is_file():
                errors.append(f"parallel_review: {reviewer} 成功但缺少 findings.json")
            if finding_count != reviewer_record.get("finding_count"):
                errors.append(
                    f"parallel_review: {reviewer} finding_count 不一致"
                )
            telemetry_record = telemetry_reviewers.get(reviewer)
            if not isinstance(telemetry_record, dict):
                errors.append(f"parallel_review: telemetry 缺少 {reviewer}")
            else:
                for key in (
                    "calls",
                    "input_tokens",
                    "output_tokens",
                    "total_tokens",
                    "status",
                    "finding_count",
                ):
                    if telemetry_record.get(key) != reviewer_record.get(key):
                        errors.append(
                            f"parallel_review: {reviewer} telemetry.{key} 不一致"
                        )
                if abs(
                    float(telemetry_record.get("cost_usd", 0.0))
                    - float(reviewer_record.get("cost_usd", 0.0))
                ) > 0.00000001:
                    errors.append(
                        f"parallel_review: {reviewer} telemetry.cost_usd 不一致"
                    )
        event_action_ids = Counter(
            str(event.get("payload", {}).get("action_id", ""))
            for event in events
            if event.get("event_type") == "parallel_reviewer_action_received"
        )
        if event_action_ids != persisted_action_ids:
            errors.append("parallel_review: Action 文件与事件关联不一致")
        for reviewer in runtime.get("reviewer_order", []):
            started = sum(
                1
                for event in events
                if event.get("event_type") == "parallel_reviewer_started"
                and event.get("payload", {}).get("reviewer") == reviewer
            )
            completed = sum(
                1
                for event in events
                if event.get("event_type") == "parallel_reviewer_completed"
                and event.get("payload", {}).get("reviewer") == reviewer
            )
            if started != 1 or completed != 1:
                errors.append(
                    f"parallel_review: {reviewer} started/completed 事件不唯一"
                )
        barrier_events = [
            event
            for event in events
            if event.get("event_type")
            in {
                "parallel_review_barrier_passed",
                "parallel_review_barrier_failed",
            }
        ]
        expected_barrier_event = (
            "parallel_review_barrier_passed"
            if barrier.get("passed")
            else "parallel_review_barrier_failed"
        )
        if len(barrier_events) != 1 or barrier_events[0].get(
            "event_type"
        ) != expected_barrier_event:
            errors.append("parallel_review: barrier 事件与终态不一致")
        bundle_path = root / "review_bundle.json"
        if barrier.get("passed"):
            if not bundle_path.is_file():
                errors.append("parallel_review: 3/3 通过但缺少 review_bundle.json")
            else:
                counts["parallel_review_bundles"] += 1
                try:
                    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
                    validate_named(bundle, "harness_review_bundle.schema.json")
                    expected_hash = bundle.get("bundle_hash")
                    unsigned = dict(bundle)
                    unsigned.pop("bundle_hash", None)
                    actual_hash = hashlib.sha256(
                        json.dumps(
                            unsigned,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode("utf-8")
                    ).hexdigest()
                    if expected_hash != actual_hash:
                        errors.append("parallel_review: bundle hash 不匹配")
                    if runtime.get("bundle_hash") != expected_hash:
                        errors.append(
                            "parallel_review: runtime bundle_hash 不匹配"
                        )
                except (OSError, json.JSONDecodeError, ContractError) as exc:
                    errors.append(f"parallel_review: bundle: {exc}")
        elif bundle_path.exists():
            errors.append("parallel_review: barrier 失败时不得存在聚合 bundle")
        checks.append("parallel_review")

    def _audit_multi_role_recovery(
        self,
        run_dir: Path,
        state: dict[str, Any],
        approvals: list[dict[str, Any]],
        events: list[dict[str, Any]],
        checks: list[str],
        errors: list[str],
        counts: dict[str, int],
    ) -> None:
        path = run_dir / "multi_role_recovery.json"
        if not path.is_file():
            checks.append("multi_role_recovery")
            return
        try:
            recovery = json.loads(path.read_text(encoding="utf-8"))
            validate_named(
                recovery,
                "harness_multi_role_recovery.schema.json",
            )
            counts["multi_role_recoveries"] += 1
        except (OSError, json.JSONDecodeError, ContractError) as exc:
            errors.append(f"multi_role_recovery: {exc}")
            checks.append("multi_role_recovery")
            return
        if state.get("mode") != "multi_role":
            errors.append(
                "multi_role_recovery: recovery 仅允许 multi_role run"
            )
        if recovery["status"] != "completed":
            errors.append("multi_role_recovery: recovery 尚未完成")
        if state.get("status") != "cancelled":
            errors.append(
                "multi_role_recovery: 完成恢复后 run 必须 cancelled"
            )
        pending = [
            approval
            for approval in approvals
            if approval.get("status") == "pending"
        ]
        if pending:
            errors.append(
                "multi_role_recovery: 恢复后仍存在 pending approval"
            )
        role_path = run_dir / "role_runtime_state.json"
        if role_path.is_file():
            try:
                role_state = json.loads(
                    role_path.read_text(encoding="utf-8")
                )
                active = [
                    role.get("stage_id")
                    for role in role_state.get("roles", [])
                    if role.get("status")
                    in {"pending", "running", "waiting_approval"}
                ]
                if active:
                    errors.append(
                        "multi_role_recovery: 恢复后仍存在活动角色 "
                        + ",".join(str(item) for item in active)
                    )
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(
                    f"multi_role_recovery: role state 无法读取: {exc}"
                )
        expected_skipped = sorted(
            str(stage.get("stage_id"))
            for stage in state.get("stages", [])
            if stage.get("status") == "skipped"
        )
        if sorted(recovery.get("skipped_stages", [])) != expected_skipped:
            errors.append(
                "multi_role_recovery: skipped_stages 与 run state 不一致"
            )
        for relative in recovery.get("preserved_paths", []):
            if not (run_dir / relative).exists():
                errors.append(
                    f"multi_role_recovery: 保留证据不存在: {relative}"
                )
        recovery_events = [
            event
            for event in events
            if event.get("event_type") == "multi_role_run_recovered"
            and event.get("payload", {}).get("recovery_id")
            == recovery["recovery_id"]
        ]
        if len(recovery_events) != 1:
            errors.append(
                "multi_role_recovery: recovery 事件必须且只能存在一次"
            )
        cancelled_events = [
            event
            for event in events
            if event.get("event_type") == "run_cancelled"
            and event.get("payload", {}).get("reason")
            == "multi_role_crash_recovered"
        ]
        if len(cancelled_events) != 1:
            errors.append(
                "multi_role_recovery: crash recovery 取消事件不唯一"
            )
        if (
            recovery.get("parallel_review_status") == "partial"
            and (run_dir / "parallel_review" / "review_bundle.json").exists()
        ):
            errors.append(
                "multi_role_recovery: partial parallel review 不得产生 bundle"
            )
        checks.append("multi_role_recovery")
