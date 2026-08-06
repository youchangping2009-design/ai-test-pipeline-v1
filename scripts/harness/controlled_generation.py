from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from generate_regeneration_bundle import build_existing_bundle
from harness.contracts import validate_named
from harness.generation_workspace import (
    ControlledGenerationError,
    ControlledGenerationWorkspace,
)
from harness.hook_dispatcher import HookDispatcher
from harness.stage_registry import ROOT, StageSpec
from harness.state_store import (
    HarnessStateError,
    StateStore,
    atomic_write_json,
    utc_now,
)


def _no_commands(
    _item_root: Path,
    _project_code: str,
    _work_item_id: str,
    _work_item_level: str,
    _strict: bool,
) -> list[list[str]]:
    return []


class ControlledGenerationService:
    def __init__(
        self,
        *,
        item_root: Path,
        project_code: str,
        work_item_id: str,
        work_item_level: str,
        hooks: HookDispatcher | None = None,
    ) -> None:
        self.item_root = item_root
        self.project_code = project_code
        self.work_item_id = work_item_id
        self.work_item_level = work_item_level.upper()
        self.store = StateStore(item_root)
        self.hooks = hooks or HookDispatcher()

    def start(
        self,
        *,
        run_id: str,
        provider: str,
        provider_command: list[str] | None = None,
        timeout_seconds: int = 300,
        force_unlock: bool = False,
    ) -> tuple[int, dict[str, Any]]:
        if provider not in {"existing", "command"}:
            raise HarnessStateError(f"不支持 generation provider: {provider}")
        if provider == "command" and not provider_command:
            raise HarnessStateError("provider=command 必须提供可信 argv")
        if not 1 <= timeout_seconds <= 1800:
            raise HarnessStateError("provider timeout 必须在 1..1800 秒")
        stage = StageSpec(
            stage_id="full_pipeline",
            kind="generation",
            levels=frozenset({"S", "M", "L"}),
            required_files=("manifest.json",),
            command_factory=_no_commands,
        )
        with self.store.lock(run_id, force=force_unlock):
            state = self.store.create(
                run_id=run_id,
                project_code=self.project_code,
                work_item_id=self.work_item_id,
                work_item_level=self.work_item_level,
                strict=True,
                stop_at="full_pipeline",
                stages=[stage],
                mode="generation",
            )
            record = state["stages"][0]
            record["status"] = "running"
            record["attempts"] = 1
            record["started_at"] = utc_now()
            state["status"] = "running"
            state["current_stage"] = "full_pipeline"
            self.store.save(state)
            self.store.append_event(
                state,
                "generation_started",
                "full_pipeline",
                {"provider": provider},
            )
            try:
                run_manifest = self._prepare_generation_tasks(run_id)
                if provider == "existing":
                    bundle = build_existing_bundle(
                        self.item_root,
                        run_manifest,
                    )
                else:
                    bundle = self._call_provider(
                        run_id=run_id,
                        command=provider_command or [],
                        run_manifest=run_manifest,
                        timeout_seconds=timeout_seconds,
                    )
                bundle["work_item_level"] = self.work_item_level
                self.store.append_event(
                    state,
                    "generation_bundle_received",
                    "full_pipeline",
                    {
                        "provider": provider,
                        "artifact_count": len(bundle.get("artifacts", {})),
                    },
                )
                workspace = self._workspace(run_id)
                candidate = workspace.stage_and_validate(
                    run_id=run_id,
                    provider=provider,
                    bundle=bundle,
                )
                self.store.append_event(
                    state,
                    "generation_candidate_validated",
                    "full_pipeline",
                    {
                        "candidate_hash": candidate["candidate_hash"],
                        "file_count": len(candidate["files"]),
                    },
                )
                approval = self._write_approval(state, candidate)
                record["status"] = "waiting_approval"
                record["completed_at"] = utc_now()
                record["last_exit_code"] = 0
                state["status"] = "waiting_approval"
                state["current_stage"] = None
                state["last_error"] = None
                self.store.save(state)
                self.store.append_event(
                    state,
                    "run_paused",
                    "full_pipeline",
                    {
                        "reason": "generation_publish_approval_required",
                        "approval_id": approval["approval_id"],
                    },
                )
                self._dispatch_approval_hook(
                    state,
                    "approval_requested",
                    approval,
                )
                return 0, state
            except (Exception, SystemExit) as exc:
                record["status"] = "failed"
                record["completed_at"] = utc_now()
                record["last_exit_code"] = 1
                state["status"] = "failed"
                state["current_stage"] = None
                state["last_error"] = {
                    "stage_id": "full_pipeline",
                    "exit_code": 1,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
                self.store.save(state)
                self.store.append_event(
                    state,
                    "stage_failed",
                    "full_pipeline",
                    state["last_error"],
                )
                self.store.append_event(
                    state,
                    "run_failed",
                    "full_pipeline",
                    state["last_error"],
                )
                return 1, state

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
                raise HarnessStateError("approval 不允许发布 generation candidate")
            if approval.get("candidate_hash") != candidate_hash:
                raise HarnessStateError("candidate_hash 与 approval 不一致")
            workspace = self._workspace(run_id)
            binding = workspace.approval_binding()
            for key in (
                "candidate_hash",
                "expected_target_hash",
                "expected_upstream_fingerprint",
            ):
                if approval.get(key) != binding[key]:
                    raise ControlledGenerationError(
                        f"approval 绑定的 {key} 已漂移"
                    )
            self.store.append_event(
                state,
                "generation_publish_started",
                "full_pipeline",
                {
                    "approval_id": approval_id,
                    "candidate_hash": candidate_hash,
                },
            )
            try:
                transaction = workspace.publish(
                    formal_validator=self._formal_strict_validator,
                )
            except Exception as exc:
                self.store.append_event(
                    state,
                    "generation_publish_rolled_back",
                    "full_pipeline",
                    {"approval_id": approval_id, "error": str(exc)},
                )
                raise
            approval["status"] = "approved"
            approval["resolved_at"] = utc_now()
            approval["resolved_by"] = approved_by.strip()
            validate_named(approval, "harness_approval.schema.json")
            atomic_write_json(approval_path, approval)
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
                "approval_resolved",
                "full_pipeline",
                {
                    "approval_id": approval_id,
                    "status": "approved",
                    "resolved_by": approval["resolved_by"],
                },
            )
            self._dispatch_approval_hook(
                state,
                "approval_resolved",
                approval,
            )
            self.store.append_event(
                state,
                "generation_publish_completed",
                "full_pipeline",
                {
                    "approval_id": approval_id,
                    "transaction_id": transaction["transaction_id"],
                },
            )
            self.store.append_event(
                state,
                "stage_succeeded",
                "full_pipeline",
                {"mode": "generation"},
            )
            self.store.append_event(
                state,
                "run_completed",
                None,
                {"mode": "generation"},
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
                "full_pipeline",
                {
                    "approval_id": approval_id,
                    "status": "rejected",
                    "resolved_by": approval["resolved_by"],
                },
            )
            self._dispatch_approval_hook(
                state,
                "approval_resolved",
                approval,
            )
            self.store.append_event(
                state,
                "run_cancelled",
                "full_pipeline",
                {"reason": "generation_publish_rejected"},
            )
            return state, approval

    def recover(
        self,
        *,
        run_id: str,
        force_unlock: bool = False,
    ) -> bool:
        with self.store.lock(run_id, force=force_unlock):
            return self._workspace(run_id).recover_unfinished()

    def _prepare_generation_tasks(self, run_id: str) -> dict[str, Any]:
        output_dir = f".generation/runs/{run_id}/generation_tasks"
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
            raise ControlledGenerationError(
                "生成 regeneration tasks 失败: "
                + ((result.stdout or "") + (result.stderr or ""))[-2000:]
            )
        path = self.store.run_dir(run_id) / "generation_tasks" / "run_manifest.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def _call_provider(
        self,
        *,
        run_id: str,
        command: list[str],
        run_manifest: dict[str, Any],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        request = {
            "protocol_version": "1.0.0",
            "run_id": run_id,
            "project_code": self.project_code,
            "work_item_id": self.work_item_id,
            "work_item_level": self.work_item_level,
            "run_manifest": run_manifest,
            "expected_output": {
                "cleanup_targets": "array of repository-relative paths",
                "artifacts": "object mapping repository-relative paths to full text",
            },
        }
        started = time.monotonic()
        result = subprocess.run(
            command,
            cwd=ROOT,
            input=json.dumps(request, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        if result.returncode != 0:
            raise ControlledGenerationError(
                f"generation provider 失败，exit={result.returncode}: "
                + (result.stderr or "")[-2000:]
            )
        stdout = result.stdout or ""
        if len(stdout) > 20_000_000:
            raise ControlledGenerationError("generation provider 输出超过 20MB")
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise ControlledGenerationError(
                f"generation provider 未返回合法 JSON: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise ControlledGenerationError("generation provider 必须返回 object")
        bundle = payload.get("bundle", payload)
        if not isinstance(bundle, dict):
            raise ControlledGenerationError("provider bundle 必须是 object")
        metadata = {
            "schema_version": "1.0.0",
            "duration_ms": duration_ms,
            "runtime": payload.get("runtime"),
            "usage": payload.get("usage"),
        }
        atomic_write_json(
            self.store.run_dir(run_id) / "generation_provider.json",
            metadata,
        )
        return bundle

    def _write_approval(
        self,
        state: dict[str, Any],
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        approval = {
            "approval_id": f"{state['run_id']}-full-pipeline-publish",
            "run_id": state["run_id"],
            "stage_id": "full_pipeline",
            "status": "pending",
            "reason": (
                "隔离候选已通过 normalizer 与 strict；发布将替换"
                f" {len(candidate['files'])} 个正式资产文件。"
            ),
            "options": ["approve_publish", "reject_publish"],
            "recommended_option": "approve_publish_after_diff_review",
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
        validate_named(approval, "harness_approval.schema.json")
        approval_path = (
            self.store.run_dir(str(state["run_id"]))
            / "approvals"
            / f"{approval['approval_id']}.json"
        )
        atomic_write_json(approval_path, approval)
        self.store.append_event(
            state,
            "approval_requested",
            "full_pipeline",
            {
                "approval_id": approval["approval_id"],
                "requested_action": "publish_generation",
                "candidate_hash": candidate["candidate_hash"],
            },
        )
        return approval

    def _load_pending_approval(
        self,
        run_id: str,
        approval_id: str,
    ) -> tuple[dict[str, Any], dict[str, Any], Path]:
        state = self.store.load(run_id)
        if state["mode"] != "generation" or state["status"] != "waiting_approval":
            raise HarnessStateError(
                "只有 waiting_approval 的 generation run 可以处理审批"
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
        if approval["run_id"] != run_id or approval["status"] != "pending":
            raise HarnessStateError("approval run/status 不匹配")
        return state, approval, approval_path

    def _formal_strict_validator(self) -> tuple[bool, str]:
        command = [
            sys.executable,
            str(ROOT / "scripts" / "validate_work_item.py"),
            "--project-code",
            self.project_code,
            "--work-item-id",
            self.work_item_id,
            "--work-item-level",
            self.work_item_level,
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

    def _workspace(self, run_id: str) -> ControlledGenerationWorkspace:
        return ControlledGenerationWorkspace(
            item_root=self.item_root,
            run_dir=self.store.run_dir(run_id),
            project_code=self.project_code,
            work_item_id=self.work_item_id,
            work_item_level=self.work_item_level,
        )

    def _dispatch_approval_hook(
        self,
        state: dict[str, Any],
        event: str,
        approval: dict[str, Any],
    ) -> None:
        self.hooks.dispatch(
            event=event,
            state=state,
            run_dir=self.store.run_dir(str(state["run_id"])),
            stage_id="full_pipeline",
            payload={
                "approval_id": approval["approval_id"],
                "status": approval["status"],
                "requested_action": approval["requested_action"],
            },
            event_callback=lambda event_type, payload: self.store.append_event(
                state,
                event_type,
                "full_pipeline",
                payload,
            ),
        )

