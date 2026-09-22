from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from harness.contracts import ContractError, validate_named
from harness.state_store import HarnessStateError, StateStore, atomic_write_json, utc_now


RECEIPT_NAME = "review_disposition.json"


def review_disposition_required(manifest: dict[str, Any]) -> bool:
    policy = manifest.get("pipeline_policy", {})
    return isinstance(policy, dict) and policy.get("review_disposition_required") is True


class ReviewDispositionService:
    def __init__(self, item_root: Path) -> None:
        self.item_root = item_root
        self.store = StateStore(item_root)

    def receipt_path(self, run_id: str) -> Path:
        return self.store.run_dir(run_id) / RECEIPT_NAME

    def declare_not_applicable(
        self,
        *,
        run_id: str,
        declared_by: str,
        reason: str,
        force_unlock: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        actor = declared_by.strip()
        explanation = reason.strip()
        if str(os.environ.get("CI", "")).strip().lower() in {"1", "true", "yes"}:
            raise HarnessStateError("CI 环境不得自行声明 Review not_applicable")
        if not actor:
            raise HarnessStateError("declared_by 不能为空")
        if not explanation:
            raise HarnessStateError("reason 不能为空")

        with self.store.lock(run_id, force=force_unlock):
            state = self.store.load(run_id)
            reopen_completed_review = self._assert_declarable_state(state)
            scope_binding = self._current_scope_binding()
            receipt = {
                "schema_version": "1.0.0",
                "disposition": "not_applicable",
                "run_id": run_id,
                "project_code": state["project_code"],
                "work_item_id": state["work_item_id"],
                "declared_by": actor,
                "declared_at": utc_now(),
                "reason": explanation,
                "code_review_scope": scope_binding,
            }
            path = self.receipt_path(run_id)
            if path.is_file():
                existing = json.loads(path.read_text(encoding="utf-8"))
                self.validate(run_id)
                comparable = ("disposition", "run_id", "project_code", "work_item_id", "declared_by", "reason", "code_review_scope")
                if any(existing.get(key) != receipt.get(key) for key in comparable):
                    raise HarnessStateError("Review disposition 已存在且声明内容冲突")
                if reopen_completed_review:
                    self._reopen_review_for_disposition(state)
                return state, existing

            validate_named(receipt, "harness_review_disposition.schema.json")
            atomic_write_json(path, receipt)
            self.store.append_event(
                state,
                "review_disposition_declared",
                "review",
                {
                    "disposition": "not_applicable",
                    "declared_by": actor,
                    "scope_sha256": scope_binding["sha256"],
                },
            )
            if reopen_completed_review:
                self._reopen_review_for_disposition(state)
            return state, receipt

    def load_valid(self, run_id: str, *, required: bool = False) -> dict[str, Any] | None:
        path = self.receipt_path(run_id)
        if not path.is_file():
            if required:
                raise HarnessStateError("Review not_applicable disposition 不存在")
            return None
        return self.validate(run_id)

    def validate(self, run_id: str) -> dict[str, Any]:
        path = self.receipt_path(run_id)
        if not path.is_file():
            raise HarnessStateError("Review not_applicable disposition 不存在")
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
            validate_named(receipt, "harness_review_disposition.schema.json")
        except (OSError, json.JSONDecodeError, ContractError) as exc:
            raise HarnessStateError(f"Review disposition 无效: {exc}") from exc
        state = self.store.load(run_id)
        for key in ("run_id", "project_code", "work_item_id"):
            if receipt.get(key) != state.get(key):
                raise HarnessStateError(f"Review disposition {key} 与 run 不一致")
        current = self._current_scope_binding(require_eligible=False)
        if receipt.get("code_review_scope") != current:
            raise HarnessStateError("Review disposition 绑定的 code review scope 已漂移")
        return receipt

    def _assert_declarable_state(self, state: dict[str, Any]) -> bool:
        if state.get("mode") != "validate":
            raise HarnessStateError("Review not_applicable 仅适用于 validate run")
        if state.get("status") not in {"paused", "failed"}:
            raise HarnessStateError("run 必须暂停或在 Review 失败后才能声明 not_applicable")
        records = {record.get("stage_id"): record for record in state.get("stages", [])}
        review = records.get("review")
        strict_gate = records.get("strict_gate")
        traceability = records.get("traceability")
        if not review or not strict_gate or not traceability:
            raise HarnessStateError("run 不包含完整的 traceability/review/strict_gate 阶段")
        if traceability.get("status") != "succeeded":
            raise HarnessStateError("Traceability 未成功，不能声明 Review not_applicable")
        if strict_gate.get("status") != "pending":
            raise HarnessStateError("Strict Gate 已执行，不能再声明 Review not_applicable")
        if review.get("status") not in {"pending", "failed", "succeeded"}:
            raise HarnessStateError("Review 已终结，不能再声明 not_applicable")
        return review.get("status") == "succeeded"

    def _reopen_review_for_disposition(self, state: dict[str, Any]) -> None:
        review = next(
            record
            for record in state["stages"]
            if record.get("stage_id") == "review"
        )
        review["status"] = "pending"
        review["input_fingerprint"] = ""
        review["started_at"] = None
        review["completed_at"] = None
        review["last_exit_code"] = None
        review["log_path"] = None
        state["status"] = "paused"
        state["current_stage"] = None
        state["last_error"] = None
        self.store.save(state)
        self.store.append_event(
            state,
            "stages_invalidated",
            "review",
            {"reason": "review_disposition_declared_after_completed_review"},
        )

    def _current_scope_binding(
        self,
        *,
        require_eligible: bool = True,
    ) -> dict[str, str]:
        manifest_path = self.item_root / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HarnessStateError(f"无法读取 manifest: {exc}") from exc
        code_reviews = manifest.get("artifacts", {}).get("code_reviews", {})
        relative_path = (
            str(code_reviews.get("scope", "")).strip()
            if isinstance(code_reviews, dict)
            else ""
        ) or "code_reviews/code_review_scope.json"
        scope_path = (self.item_root / relative_path).resolve()
        try:
            scope_path.relative_to(self.item_root.resolve())
        except ValueError as exc:
            raise HarnessStateError("code review scope 路径越界") from exc
        try:
            raw = scope_path.read_bytes()
            scope = json.loads(raw.decode("utf-8"))
            validate_named(scope, "code_review_scope.schema.json")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ContractError) as exc:
            raise HarnessStateError(f"code review scope 无效: {exc}") from exc
        frontend = scope.get("frontend_code_dirs", [])
        backend = scope.get("backend_code_dirs", [])
        if require_eligible and (
            scope.get("status") != "awaiting_code_directories" or frontend or backend
        ):
            raise HarnessStateError(
                "仅 code review scope 为 awaiting_code_directories 且前后端目录均为空时可声明 not_applicable"
            )
        return {
            "path": relative_path,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "status": "awaiting_code_directories",
        }
