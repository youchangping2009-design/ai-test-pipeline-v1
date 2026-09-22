from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness.contracts import ContractError, validate_named
from harness.state_store import HarnessStateError, StateStore
from manage_feedback_application import (
    feedback_fingerprint,
    feedback_item,
    prepare_application,
    read_json,
    record_application,
    snapshot_path,
)


class FeedbackActionDispatchError(RuntimeError):
    """Raised when a feedback action violates the restricted contract."""


ALLOWED_FEEDBACK_ACTIONS = (
    "prepare_feedback_application",
    "propose_feedback_design_artifacts",
    "record_feedback_application",
)


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _write_json_immutable(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        os.link(temporary, path)
    except FileExistsError as exc:
        raise FeedbackActionDispatchError(
            f"feedback action journal 已存在，拒绝覆盖: {path}"
        ) from exc
    finally:
        temporary.unlink(missing_ok=True)


def _request_sha256(
    action: dict[str, Any],
    execution_context: dict[str, str],
) -> str:
    encoded = json.dumps(
        {"action": action, "execution_context": execution_context},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FeedbackApplicationActionRuntime:
    item_root: Path
    run_id: str
    actor: str
    provider: str

    def __post_init__(self) -> None:
        self.item_root = self.item_root.resolve()
        self.run_id = self.run_id.strip()
        self.actor = self.actor.strip()
        self.provider = self.provider.strip()

    def _execution_context(self) -> dict[str, str]:
        if not self.run_id or not self.actor or not self.provider:
            raise FeedbackActionDispatchError(
                "feedback action 必须绑定非空 run_id、actor 和 provider"
            )
        try:
            state = StateStore(self.item_root).load(self.run_id)
            feedback = read_json(self.item_root / "design" / "design_feedback.json")
        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
            ContractError,
            HarnessStateError,
        ) as exc:
            raise FeedbackActionDispatchError(
                f"feedback action 执行上下文无效: {exc}"
            ) from exc
        for field in ("project_code", "work_item_id"):
            if state.get(field) != feedback.get(field):
                raise FeedbackActionDispatchError(
                    f"feedback action run 的 {field} 与工作项不匹配"
                )
        return {
            "run_id": self.run_id,
            "actor": self.actor,
            "provider": self.provider,
        }

    def dispatch(self, action: dict[str, Any]) -> dict[str, Any]:
        try:
            validate_named(action, "harness_feedback_action.schema.json")
        except ContractError as exc:
            raise FeedbackActionDispatchError(str(exc)) from exc

        execution_context = self._execution_context()
        request_sha256 = _request_sha256(action, execution_context)
        _intent_path, result_path, recovering = self._prepare_journal(
            action, request_sha256, execution_context
        )
        if result_path.is_file():
            result_record = read_json(result_path)
            self._validate_result_record(
                result_record,
                action,
                request_sha256,
                execution_context,
            )
            observation = result_record["observation"]
            if observation.get("ok") is not True:
                raise FeedbackActionDispatchError(
                    str(observation.get("result", {}).get("error", "action 执行失败"))
                )
            return observation

        action_type = str(action["action_type"])
        feedback_id = str(action["feedback_id"]).strip()
        arguments = action["arguments"]
        handlers = {
            "prepare_feedback_application": self._prepare,
            "propose_feedback_design_artifacts": self._propose,
            "record_feedback_application": self._record,
        }
        if action_type not in handlers:
            raise FeedbackActionDispatchError(
                f"不允许的 feedback action_type: {action_type}"
            )
        try:
            result = handlers[action_type](feedback_id, arguments, recovering)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            observation = {
                "ok": False,
                "action_type": action_type,
                "result": {"error": str(exc), "error_type": type(exc).__name__},
            }
            self._write_result(
                result_path,
                action["action_id"],
                request_sha256,
                execution_context,
                observation,
            )
            raise FeedbackActionDispatchError(str(exc)) from exc
        observation = {"ok": True, "action_type": action_type, "result": result}
        self._write_result(
            result_path,
            action["action_id"],
            request_sha256,
            execution_context,
            observation,
        )
        return observation

    @staticmethod
    def _write_result(
        result_path: Path,
        action_id: str,
        request_sha256: str,
        execution_context: dict[str, str],
        observation: dict[str, Any],
    ) -> None:
        result_record = {
            "schema_version": "1.1.0",
            "record_type": "result",
            "action_id": action_id,
            "request_sha256": request_sha256,
            "execution_context": execution_context,
            "observation": observation,
            "recorded_at": _utc_now(),
        }
        validate_named(result_record, "harness_feedback_action_journal.schema.json")
        if result_path.exists():
            raise FeedbackActionDispatchError(
                f"feedback action result 已存在，拒绝覆盖: {result_path}"
            )
        _write_json_immutable(result_path, result_record)

    def _prepare_journal(
        self,
        action: dict[str, Any],
        request_sha256: str,
        execution_context: dict[str, str],
    ) -> tuple[Path, Path, bool]:
        action_dir = self.item_root / ".generation" / "feedback_applications" / "actions"
        action_id = str(action["action_id"])
        intent_path = action_dir / f"{action_id}.intent.json"
        result_path = action_dir / f"{action_id}.result.json"
        if intent_path.is_file():
            intent = read_json(intent_path)
            validate_named(intent, "harness_feedback_action_journal.schema.json")
            if (
                intent.get("record_type") != "intent"
                or intent.get("action_id") != action_id
                or intent.get("request_sha256") != request_sha256
                or intent.get("action") != action
                or intent.get("execution_context") != execution_context
            ):
                raise FeedbackActionDispatchError(
                    f"action_id 已绑定不同请求，拒绝复用: {action_id}"
                )
            return intent_path, result_path, True
        if result_path.exists():
            raise FeedbackActionDispatchError(
                f"feedback action result 缺少 intent: {result_path}"
            )
        intent = {
            "schema_version": "1.1.0",
            "record_type": "intent",
            "action_id": action_id,
            "request_sha256": request_sha256,
            "execution_context": execution_context,
            "action": action,
            "recorded_at": _utc_now(),
        }
        validate_named(intent, "harness_feedback_action_journal.schema.json")
        _write_json_immutable(intent_path, intent)
        return intent_path, result_path, False

    @staticmethod
    def _validate_result_record(
        record: dict[str, Any],
        action: dict[str, Any],
        request_sha256: str,
        execution_context: dict[str, str],
    ) -> None:
        try:
            validate_named(record, "harness_feedback_action_journal.schema.json")
        except ContractError as exc:
            raise FeedbackActionDispatchError(str(exc)) from exc
        observation = record.get("observation")
        if (
            record.get("record_type") != "result"
            or record.get("action_id") != action.get("action_id")
            or record.get("request_sha256") != request_sha256
            or record.get("execution_context") != execution_context
            or not isinstance(observation, dict)
        ):
            raise FeedbackActionDispatchError("feedback action result 与请求不一致")

    def _prepare(
        self,
        feedback_id: str,
        arguments: dict[str, Any],
        recovering: bool,
    ) -> dict[str, Any]:
        unknown = set(arguments) - {"targets"}
        if unknown:
            raise ValueError(f"prepare 参数不在白名单: {sorted(unknown)}")
        targets = arguments.get("targets")
        if targets is not None and (
            not isinstance(targets, list)
            or not all(isinstance(path, str) and path.strip() for path in targets)
        ):
            raise ValueError("prepare.targets 必须是非空路径字符串数组")
        output = snapshot_path(self.item_root, feedback_id)
        if output.exists() and recovering:
            feedback, item = feedback_item(self.item_root, feedback_id)
            snapshot = read_json(output)
            for field, expected in (
                ("project_code", feedback.get("project_code")),
                ("work_item_id", feedback.get("work_item_id")),
                ("feedback_id", feedback_id),
                ("target_layer", item.get("target_layer")),
            ):
                if snapshot.get(field) != expected:
                    raise ValueError(f"修改前快照 {field} 已漂移")
            if snapshot.get("feedback_fingerprint") != feedback_fingerprint(item):
                raise ValueError(f"{feedback_id} 内容在 prepare 后发生漂移")
            frozen = [entry.get("path") for entry in snapshot.get("artifacts", [])]
            if targets is not None and frozen != targets:
                raise ValueError("恢复 prepare 时 targets 与既有快照不一致")
        else:
            output = prepare_application(self.item_root, feedback_id, targets)
        snapshot = read_json(output)
        return {
            "status": "prepared",
            "snapshot_path": str(output.relative_to(self.item_root)),
            "target_layer": snapshot["target_layer"],
            "targets": [item["path"] for item in snapshot["artifacts"]],
        }

    def _propose(
        self,
        feedback_id: str,
        arguments: dict[str, Any],
        _recovering: bool,
    ) -> dict[str, Any]:
        if set(arguments) != {"artifacts"}:
            raise ValueError("propose 只接受 artifacts 参数")
        artifacts = arguments.get("artifacts")
        if not isinstance(artifacts, dict) or not artifacts:
            raise ValueError("propose.artifacts 必须是非空 object")

        feedback, item = feedback_item(self.item_root, feedback_id)
        if item.get("status") != "accepted":
            raise ValueError(
                f"{feedback_id} 必须处于 accepted，实际为 {item.get('status')}"
            )
        snapshot = read_json(snapshot_path(self.item_root, feedback_id))
        for field, expected in (
            ("project_code", feedback.get("project_code")),
            ("work_item_id", feedback.get("work_item_id")),
            ("feedback_id", feedback_id),
            ("target_layer", item.get("target_layer")),
        ):
            if snapshot.get(field) != expected:
                raise ValueError(f"修改前快照 {field} 已漂移")
        if snapshot.get("feedback_fingerprint") != feedback_fingerprint(item):
            raise ValueError(f"{feedback_id} 内容在 prepare 后发生漂移")

        frozen_paths = {
            str(artifact.get("path", "")).strip()
            for artifact in snapshot.get("artifacts", [])
            if isinstance(artifact, dict)
        }
        normalized: dict[str, str] = {}
        for raw_path, raw_content in artifacts.items():
            relative = str(raw_path).strip()
            if relative not in frozen_paths:
                raise ValueError(f"propose 路径未被 prepare 冻结: {relative}")
            if isinstance(raw_content, (dict, list)):
                content = json.dumps(raw_content, ensure_ascii=False, indent=2) + "\n"
            elif isinstance(raw_content, str):
                content = raw_content
            else:
                raise ValueError(f"产物内容必须为 string/JSON: {relative}")
            normalized[relative] = content

        for relative, content in normalized.items():
            _atomic_write_text(self.item_root / relative, content)
        return {
            "status": "proposed",
            "target_layer": snapshot["target_layer"],
            "paths": sorted(normalized),
        }

    def _record(
        self,
        feedback_id: str,
        arguments: dict[str, Any],
        _recovering: bool,
    ) -> dict[str, Any]:
        if arguments:
            raise ValueError("record 不接受额外参数")
        output = record_application(self.item_root, feedback_id)
        return {
            "status": "applied",
            "receipt_path": str(output.relative_to(self.item_root)),
        }
