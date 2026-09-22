#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from harness.contracts import ContractError, validate_named
from harness.state_store import HarnessStateError, StateStore
from validate_feedback_application import read_json, validate_feedback_application


def request_sha256(
    action: dict[str, Any],
    execution_context: dict[str, str] | None = None,
) -> str:
    payload: dict[str, Any] = action
    if execution_context is not None:
        payload = {
            "action": action,
            "execution_context": execution_context,
        }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_record(
    record: dict[str, Any],
    expected_type: str,
) -> dict[str, str] | None:
    validate_named(record, "harness_feedback_action_journal.schema.json")
    if record.get("record_type") != expected_type:
        raise ValueError(
            f"journal record_type 应为 {expected_type}: {record.get('action_id')}"
        )
    schema_version = record.get("schema_version")
    raw_context = record.get("execution_context")
    execution_context = raw_context if isinstance(raw_context, dict) else None
    if schema_version == "1.1.0" and execution_context is None:
        raise ValueError("1.1.0 journal 缺少 execution_context")
    if schema_version == "1.0.0" and raw_context is not None:
        raise ValueError("1.0.0 journal 不得声明 execution_context")
    if expected_type == "intent":
        action = record.get("action")
        if not isinstance(action, dict):
            raise ValueError("intent 缺少 action")
        validate_named(action, "harness_feedback_action.schema.json")
        if record.get("request_sha256") != request_sha256(
            action,
            execution_context,
        ):
            raise ValueError(f"intent request hash 不匹配: {record.get('action_id')}")
        if record.get("action_id") != action.get("action_id"):
            raise ValueError("intent action_id 与 action 不一致")
    elif not isinstance(record.get("observation"), dict):
        raise ValueError("result 缺少 observation")
    return execution_context


def _validate_execution_context(
    item_root: Path,
    execution_context: dict[str, str],
    feedback_payload: dict[str, Any],
) -> None:
    run_id = str(execution_context.get("run_id", ""))
    actor = str(execution_context.get("actor", "")).strip()
    provider = str(execution_context.get("provider", "")).strip()
    if not actor or not provider:
        raise ValueError("feedback action actor/provider 不能为空")
    try:
        state = StateStore(item_root).load(run_id)
    except (OSError, ValueError, json.JSONDecodeError, ContractError, HarnessStateError) as exc:
        raise ValueError(f"feedback action run 不存在或无效: {run_id}: {exc}") from exc
    for field in ("project_code", "work_item_id"):
        if state.get(field) != feedback_payload.get(field):
            raise ValueError(f"feedback action run 的 {field} 与工作项不匹配: {run_id}")


def validate_feedback_action_journal(item_root: Path) -> dict[str, Any]:
    item_root = item_root.resolve()
    feedback_payload = read_json(item_root / "design" / "design_feedback.json")
    manifest = read_json(item_root / "manifest.json")
    policy = manifest.get("pipeline_policy", {})
    journal_required = (
        isinstance(policy, dict)
        and policy.get("feedback_action_journal_required") is True
    )
    identity_required = (
        isinstance(policy, dict)
        and policy.get("feedback_action_execution_identity_required") is True
    )
    feedback_by_id = {
        str(item.get("feedback_id")): item
        for item in feedback_payload.get("feedback_items", [])
        if isinstance(item, dict)
    }
    applied_ids = {
        feedback_id
        for feedback_id, item in feedback_by_id.items()
        if item.get("status") == "applied"
    }
    action_dir = item_root / ".generation" / "feedback_applications" / "actions"
    if not action_dir.exists():
        if (journal_required or identity_required) and applied_ids:
            raise ValueError(
                "pipeline policy 要求 applied feedback 提供 feedback Action journal"
            )
        return {
            "status": "legacy_compatible" if applied_ids else "no_actions",
            "actions": 0,
            "feedbacks": 0,
            "failed_actions": 0,
            "execution_identity_status": "not_applicable",
            "run_ids": [],
            "actors": [],
            "providers": [],
            "actions_by_run": {},
        }

    intent_paths = sorted(action_dir.glob("*.intent.json"))
    result_paths = sorted(action_dir.glob("*.result.json"))
    intents: dict[str, dict[str, Any]] = {}
    results: dict[str, dict[str, Any]] = {}
    contexts: dict[str, dict[str, str] | None] = {}
    for path, expected_type, target in (
        *((path, "intent", intents) for path in intent_paths),
        *((path, "result", results) for path in result_paths),
    ):
        record = read_json(path)
        execution_context = _validate_record(record, expected_type)
        action_id = str(record["action_id"])
        if action_id in target:
            raise ValueError(f"重复 action_id: {action_id}")
        target[action_id] = record
        contexts[f"{expected_type}:{action_id}"] = execution_context

    orphan_results = sorted(set(results) - set(intents))
    if orphan_results:
        raise ValueError(f"result 缺少 intent: {orphan_results}")
    unfinished = sorted(set(intents) - set(results))
    if unfinished:
        raise ValueError(f"存在未完成 feedback action intent: {unfinished}")

    feedback_actions: dict[str, list[dict[str, Any]]] = {}
    failed_actions = 0
    for action_id, intent in intents.items():
        result = results[action_id]
        intent_context = contexts[f"intent:{action_id}"]
        result_context = contexts[f"result:{action_id}"]
        if intent.get("schema_version") != result.get("schema_version"):
            raise ValueError(f"intent/result schema_version 不一致: {action_id}")
        if intent_context != result_context:
            raise ValueError(f"intent/result execution_context 不一致: {action_id}")
        if identity_required and intent_context is None:
            raise ValueError(f"pipeline policy 要求 action 绑定执行身份: {action_id}")
        if intent_context is not None:
            _validate_execution_context(item_root, intent_context, feedback_payload)
        if result.get("request_sha256") != intent.get("request_sha256"):
            raise ValueError(f"intent/result request hash 不一致: {action_id}")
        observation = result["observation"]
        action = intent["action"]
        if observation.get("action_type") != action.get("action_type"):
            raise ValueError(f"result observation 与 intent 不一致: {action_id}")
        if observation.get("ok") is not True:
            failed_actions += 1
            continue
        feedback_actions.setdefault(str(action["feedback_id"]), []).append(intent)

    for feedback_id, records in feedback_actions.items():
        records.sort(key=lambda record: (str(record["recorded_at"]), record["action_id"]))
        types = [record["action"]["action_type"] for record in records]
        if types[0] != "prepare_feedback_application":
            raise ValueError(f"{feedback_id} journal 未以 prepare 开始")
        if types.count("prepare_feedback_application") != 1:
            raise ValueError(f"{feedback_id} journal prepare 必须且只能有一次")
        if "propose_feedback_design_artifacts" not in types:
            raise ValueError(f"{feedback_id} journal 缺少 propose")
        if types[-1] != "record_feedback_application" or types.count(
            "record_feedback_application"
        ) != 1:
            raise ValueError(f"{feedback_id} journal 必须以唯一 record 结束")
        feedback = feedback_by_id.get(feedback_id)
        if feedback is None:
            raise ValueError(f"journal 引用了不存在的 feedback: {feedback_id}")
        if feedback.get("status") != "applied":
            raise ValueError(f"{feedback_id} journal 已完成但状态不是 applied")
        bound_runs = {
            contexts[f"intent:{record['action_id']}"]["run_id"]
            for record in records
            if contexts[f"intent:{record['action_id']}"] is not None
        }
        if len(bound_runs) > 1:
            raise ValueError(f"{feedback_id} journal 跨 Harness run 混用: {sorted(bound_runs)}")

    if journal_required:
        missing_journals = sorted(applied_ids - set(feedback_actions))
        if missing_journals:
            raise ValueError(
                f"applied feedback 缺少完整 Action journal: {missing_journals}"
            )

    if feedback_actions:
        validate_feedback_application(item_root)
    verified_contexts = [
        context
        for key, context in contexts.items()
        if key.startswith("intent:") and context is not None
    ]
    has_legacy_records = any(
        key.startswith("intent:") and context is None
        for key, context in contexts.items()
    )
    return {
        "status": "legacy_compatible" if has_legacy_records else "verified",
        "actions": len(intents),
        "feedbacks": len(feedback_actions),
        "failed_actions": failed_actions,
        "execution_identity_status": (
            "legacy_compatible" if has_legacy_records else "verified"
        ),
        "run_ids": sorted({context["run_id"] for context in verified_contexts}),
        "actors": sorted({context["actor"] for context in verified_contexts}),
        "providers": sorted({context["provider"] for context in verified_contexts}),
        "actions_by_run": {
            run_id: sum(1 for context in verified_contexts if context["run_id"] == run_id)
            for run_id in sorted({context["run_id"] for context in verified_contexts})
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 feedback Action 不可变 journal")
    parser.add_argument("--item-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = validate_feedback_action_journal(args.item_root)
    except (OSError, ValueError, json.JSONDecodeError, ContractError) as exc:
        print(f"❌ feedback action journal 校验失败: {exc}", file=sys.stderr)
        return 1
    print(f"feedback_action_journal_status: {result['status']}")
    print(f"feedback_action_count: {result['actions']}")
    print(f"feedback_action_feedbacks: {result['feedbacks']}")
    print(f"feedback_action_failures: {result.get('failed_actions', 0)}")
    print(
        "feedback_action_execution_identity: "
        f"{result.get('execution_identity_status', 'not_applicable')}"
    )
    print(f"feedback_action_runs: {','.join(result.get('run_ids', [])) or '-'}")
    print(f"feedback_action_actors: {','.join(result.get('actors', [])) or '-'}")
    print(f"feedback_action_providers: {','.join(result.get('providers', [])) or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
