from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from harness.contracts import ContractError, validate_named
from harness.hook_dispatcher import HookDispatcher
from harness.state_store import HarnessStateError, StateStore, atomic_write_json, utc_now


RECEIPT_RELATIVE_PATH = "inputs/requirement_approval.json"
SUMMARY_RELATIVE_PATH = "inputs/requirement_summary.md"
SOURCE_MANIFEST_RELATIVE_PATH = "inputs/source_manifest.json"
_BINDING_FIELDS = (
    "run_id",
    "requirement_summary_sha256",
    "source_manifest_sha256",
    "raw_inputs_fingerprint",
    "requirement_version",
)


def _file_sha256(path: Path) -> str:
    if not path.is_file():
        raise HarnessStateError(f"审批绑定文件不存在: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_inputs_fingerprint(item_root: Path) -> str:
    inputs_root = item_root / "inputs"
    digest = hashlib.sha256()
    excluded = {
        Path(SUMMARY_RELATIVE_PATH),
        Path(SOURCE_MANIFEST_RELATIVE_PATH),
        Path(RECEIPT_RELATIVE_PATH),
    }
    if inputs_root.is_dir():
        for path in sorted(candidate for candidate in inputs_root.rglob("*") if candidate.is_file()):
            relative = path.relative_to(item_root)
            if relative in excluded:
                continue
            digest.update(relative.as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def requirement_approval_required(manifest: dict[str, Any]) -> bool:
    policy = manifest.get("pipeline_policy")
    return (
        isinstance(policy, dict)
        and policy.get("requirement_approval_required") is True
    )


def current_binding(item_root: Path, run_id: str) -> dict[str, str]:
    manifest_path = item_root / "manifest.json"
    if not manifest_path.is_file():
        raise HarnessStateError(f"manifest.json 不存在: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "run_id": run_id,
        "requirement_summary_sha256": _file_sha256(
            item_root / SUMMARY_RELATIVE_PATH
        ),
        "source_manifest_sha256": _file_sha256(
            item_root / SOURCE_MANIFEST_RELATIVE_PATH
        ),
        "raw_inputs_fingerprint": raw_inputs_fingerprint(item_root),
        "requirement_version": str(manifest.get("requirement_version", "")),
    }


def receipt_matches_binding(
    receipt: dict[str, Any],
    binding: dict[str, str],
    *,
    include_run_id: bool = True,
) -> bool:
    fields = _BINDING_FIELDS if include_run_id else _BINDING_FIELDS[1:]
    return all(receipt.get(field) == binding.get(field) for field in fields)


def _binding_fingerprint(binding: dict[str, str]) -> str:
    serialized = json.dumps(
        binding,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def canonical_binding_fingerprint(item_root: Path, run_id: str) -> str:
    return _binding_fingerprint(current_binding(item_root, run_id))


def validate_requirement_approval(
    item_root: Path,
    manifest: dict[str, Any],
) -> list[str]:
    if not requirement_approval_required(manifest):
        return []
    path = item_root / RECEIPT_RELATIVE_PATH
    if not path.is_file():
        return [f"{RECEIPT_RELATIVE_PATH} 不存在（policy required）"]
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        validate_named(receipt, "requirement_approval.schema.json")
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        return [f"{RECEIPT_RELATIVE_PATH} 无效: {exc}"]
    errors: list[str] = []
    if receipt.get("status") != "approved":
        errors.append(
            f"{RECEIPT_RELATIVE_PATH} status 必须为 approved，"
            f"实际 {receipt.get('status')}"
        )
    try:
        binding = current_binding(item_root, str(receipt.get("run_id", "")))
    except (HarnessStateError, json.JSONDecodeError) as exc:
        errors.append(f"{RECEIPT_RELATIVE_PATH} 无法计算当前绑定: {exc}")
        return errors
    for field in _BINDING_FIELDS[1:]:
        if receipt.get(field) != binding[field]:
            errors.append(
                f"{RECEIPT_RELATIVE_PATH} {field} 与当前内容不匹配"
            )
    return errors


class RequirementApprovalService:
    def __init__(
        self,
        item_root: Path,
        hooks: HookDispatcher | None = None,
    ) -> None:
        self.item_root = item_root
        self.store = StateStore(item_root)
        self.hooks = hooks or HookDispatcher()
        self.receipt_path = item_root / RECEIPT_RELATIVE_PATH

    def policy_required(self) -> bool:
        manifest = json.loads(
            (self.item_root / "manifest.json").read_text(encoding="utf-8")
        )
        return requirement_approval_required(manifest)

    def checkpoint_fingerprint(self, run_id: str) -> str:
        return canonical_binding_fingerprint(self.item_root, run_id)

    def request(
        self,
        *,
        state: dict[str, Any],
        record: dict[str, Any],
    ) -> dict[str, Any]:
        run_id = str(state["run_id"])
        binding = current_binding(self.item_root, run_id)
        approval_id = (
            f"{run_id}-requirement-{_binding_fingerprint(binding)[:24]}"
        )
        receipt = {
            "schema_version": "1.0.0",
            "approval_id": approval_id,
            "status": "pending",
            "reviewed_by": None,
            "reviewed_at": None,
            "note": None,
            **binding,
        }
        validate_named(receipt, "requirement_approval.schema.json")
        atomic_write_json(self.receipt_path, receipt)
        self._finalize_pending_state(state, record, receipt)
        return receipt

    def approve(
        self,
        *,
        run_id: str,
        reviewed_by: str,
        note: str,
        force_unlock: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        return self._resolve(
            run_id=run_id,
            status="approved",
            reviewed_by=reviewed_by,
            note=note,
            force_unlock=force_unlock,
        )

    def reject(
        self,
        *,
        run_id: str,
        reviewed_by: str,
        note: str,
        force_unlock: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        return self._resolve(
            run_id=run_id,
            status="rejected",
            reviewed_by=reviewed_by,
            note=note,
            force_unlock=force_unlock,
        )

    def recover(
        self,
        *,
        run_id: str,
        force_unlock: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        with self.store.lock(run_id, force=force_unlock):
            state = self.store.load(run_id)
            receipt = self._load_receipt()
            self._assert_run_and_binding(receipt, run_id)
            record = self._requirement_record(state)
            if receipt["status"] == "pending":
                self._finalize_pending_state(state, record, receipt)
            elif receipt["status"] == "approved":
                self._finalize_approved_state(state, record, receipt)
            else:
                self._finalize_rejected_state(state, record, receipt)
            return state, receipt

    def guard_resume(
        self,
        *,
        state: dict[str, Any],
    ) -> None:
        if not self.policy_required():
            return
        record = self._requirement_record(state)
        receipt = self._load_receipt(required=False)
        run_id = str(state["run_id"])
        binding = current_binding(self.item_root, run_id)
        if (
            receipt is None
            or not receipt_matches_binding(receipt, binding)
        ):
            self._invalidate_all_stages(state)
            self.request(state=state, record=record)
            raise HarnessStateError(
                "requirement approval 绑定内容已漂移，已重新进入 waiting_approval"
            )
        if receipt["status"] == "pending":
            self._finalize_pending_state(state, record, receipt)
            raise HarnessStateError(
                "requirement approval 仍为 pending，resume 被拒绝"
            )
        if receipt["status"] == "rejected":
            self._finalize_rejected_state(state, record, receipt)
            raise HarnessStateError("requirement approval 已 rejected，run 不能恢复")
        if state.get("status") == "waiting_approval":
            self._finalize_approved_state(state, record, receipt)

    def _resolve(
        self,
        *,
        run_id: str,
        status: str,
        reviewed_by: str,
        note: str,
        force_unlock: bool,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        reviewer = reviewed_by.strip()
        resolution_note = note.strip()
        if status == "approved" and str(
            os.environ.get("CI", "")
        ).strip().lower() in {
            "1",
            "true",
            "yes",
        }:
            raise HarnessStateError(
                "CI 环境不得自批准 requirement approval"
            )
        if not reviewer:
            raise HarnessStateError("reviewed_by 不能为空，禁止伪造 reviewer")
        if not resolution_note:
            raise HarnessStateError("note 不能为空")
        with self.store.lock(run_id, force=force_unlock):
            state = self.store.load(run_id)
            receipt = self._load_receipt()
            self._assert_run_and_binding(receipt, run_id)
            existing_status = str(receipt["status"])
            if existing_status == status:
                if (
                    receipt.get("reviewed_by") != reviewer
                    or receipt.get("note") != resolution_note
                ):
                    raise HarnessStateError("重复动作的 reviewer/note 冲突")
            elif existing_status != "pending":
                raise HarnessStateError(
                    f"审批冲突：receipt 已 {existing_status}，不能改为 {status}"
                )
            else:
                receipt["status"] = status
                receipt["reviewed_by"] = reviewer
                receipt["reviewed_at"] = utc_now()
                receipt["note"] = resolution_note
                validate_named(receipt, "requirement_approval.schema.json")
                atomic_write_json(self.receipt_path, receipt)
            record = self._requirement_record(state)
            if status == "approved":
                self._finalize_approved_state(state, record, receipt)
            else:
                self._finalize_rejected_state(state, record, receipt)
            return state, receipt

    def _load_receipt(
        self,
        *,
        required: bool = True,
    ) -> dict[str, Any] | None:
        if not self.receipt_path.is_file():
            if required:
                raise HarnessStateError(
                    f"requirement approval receipt 不存在: {self.receipt_path}"
                )
            return None
        receipt = json.loads(self.receipt_path.read_text(encoding="utf-8"))
        validate_named(receipt, "requirement_approval.schema.json")
        return receipt

    def _assert_run_and_binding(
        self,
        receipt: dict[str, Any],
        run_id: str,
    ) -> None:
        binding = current_binding(self.item_root, run_id)
        if not receipt_matches_binding(receipt, binding):
            raise HarnessStateError(
                "requirement approval receipt 与当前 run/content 绑定不一致"
            )

    @staticmethod
    def _requirement_record(state: dict[str, Any]) -> dict[str, Any]:
        for record in state["stages"]:
            if record["stage_id"] == "requirement_intake":
                return record
        raise HarnessStateError("run 不包含 requirement_intake stage")

    def _finalize_pending_state(
        self,
        state: dict[str, Any],
        record: dict[str, Any],
        receipt: dict[str, Any],
    ) -> None:
        record["status"] = "waiting_approval"
        state["status"] = "waiting_approval"
        state["current_stage"] = "requirement_intake"
        state["last_error"] = None
        self.store.save(state)
        self._append_event_once(
            state,
            "approval_requested",
            {
                "approval_id": receipt["approval_id"],
                "requested_action": "approve_requirement_summary",
                "receipt_path": RECEIPT_RELATIVE_PATH,
            },
        )

    def _finalize_approved_state(
        self,
        state: dict[str, Any],
        record: dict[str, Any],
        receipt: dict[str, Any],
    ) -> None:
        record["status"] = "succeeded"
        record["completed_at"] = record.get("completed_at") or utc_now()
        record["last_exit_code"] = 0
        state["status"] = "paused"
        state["current_stage"] = None
        state["last_error"] = None
        self.store.save(state)
        self._append_event_once(
            state,
            "approval_resolved",
            {
                "approval_id": receipt["approval_id"],
                "status": "approved",
                "resolved_by": receipt["reviewed_by"],
            },
        )

    def _finalize_rejected_state(
        self,
        state: dict[str, Any],
        record: dict[str, Any],
        receipt: dict[str, Any],
    ) -> None:
        record["status"] = "skipped"
        record["completed_at"] = record.get("completed_at") or utc_now()
        state["status"] = "cancelled"
        state["current_stage"] = None
        state["last_error"] = None
        self.store.save(state)
        self._append_event_once(
            state,
            "approval_resolved",
            {
                "approval_id": receipt["approval_id"],
                "status": "rejected",
                "resolved_by": receipt["reviewed_by"],
            },
        )
        self._append_event_once(
            state,
            "run_cancelled",
            {
                "reason": "requirement_approval_rejected",
                "approval_id": receipt["approval_id"],
            },
        )

    def _append_event_once(
        self,
        state: dict[str, Any],
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        events_path = self.store.run_dir(str(state["run_id"])) / "events.jsonl"
        approval_id = str(payload.get("approval_id", ""))
        if events_path.is_file():
            for line in events_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = json.loads(line)
                if (
                    event.get("event_type") == event_type
                    and str(event.get("payload", {}).get("approval_id", ""))
                    == approval_id
                ):
                    return
        self.store.append_event(
            state,
            event_type,
            "requirement_intake",
            payload,
        )

    def _invalidate_all_stages(self, state: dict[str, Any]) -> None:
        for record in state["stages"]:
            record["status"] = "pending"
            record["input_fingerprint"] = ""
            record["started_at"] = None
            record["completed_at"] = None
            record["last_exit_code"] = None
            record["log_path"] = None
        self.store.save(state)
