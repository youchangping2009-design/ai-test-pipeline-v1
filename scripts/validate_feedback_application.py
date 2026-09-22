#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


LAYER_PATHS = {
    "testability_gate": {"acceptance/testability_gate.json", "acceptance/testability_gate.md"},
    "acceptance_examples": {"acceptance/acceptance_examples.json", "acceptance/acceptance_examples.md"},
    "verification_responsibility_map": {
        "design/verification_responsibility_map.json",
        "design/verification_responsibility_map.md",
    },
    "test_design_matrix": {"design/test_design_matrix.json", "design/test_design_matrix.md"},
    "case_plan": {"testcases/case_plan.json", "testcases/case_plan.md"},
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON 顶层必须是对象: {path}")
    return payload


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_feedback_application(item_root: Path) -> dict[str, Any]:
    item_root = item_root.resolve()
    feedback = read_json(item_root / "design" / "design_feedback.json")
    manifest = read_json(item_root / "manifest.json")
    policy = manifest.get("pipeline_policy", {})
    receipt_required = (
        isinstance(policy, dict)
        and policy.get("feedback_application_receipt_required") is True
    )
    feedback_by_id = {
        str(item.get("feedback_id", "")).strip(): item
        for item in feedback.get("feedback_items", [])
        if isinstance(item, dict)
    }
    applied_ids = {
        feedback_id
        for feedback_id, item in feedback_by_id.items()
        if item.get("status") == "applied"
    }
    receipt_path = item_root / "design" / "feedback_application.json"
    if not receipt_path.is_file():
        if receipt_required and applied_ids:
            raise ValueError(
                "pipeline policy 要求 applied feedback 提供 design/feedback_application.json"
            )
        return {
            "status": "legacy_compatible" if applied_ids else "not_applicable",
            "application_count": 0,
            "artifact_count": 0,
        }

    receipt = read_json(receipt_path)

    for field in ("project_code", "work_item_id"):
        if receipt.get(field) != feedback.get(field):
            raise ValueError(f"{field} 与 design_feedback 不一致")

    applications = receipt.get("applications")
    if not isinstance(applications, list) or not applications:
        raise ValueError("applications 必须是非空数组")

    seen: set[str] = set()
    changed_artifacts = 0
    artifact_chain_tips: dict[str, str] = {}
    for application in applications:
        if not isinstance(application, dict):
            raise ValueError("application 必须为对象")
        feedback_id = str(application.get("feedback_id", "")).strip()
        if not feedback_id or feedback_id in seen:
            raise ValueError(f"feedback_id 缺失或重复: {feedback_id}")
        seen.add(feedback_id)
        source = feedback_by_id.get(feedback_id)
        if source is None:
            raise ValueError(f"application 引用未知 feedback: {feedback_id}")
        if source.get("status") != "applied":
            raise ValueError(f"{feedback_id} 尚未标记 applied")
        target_layer = str(application.get("target_layer", "")).strip()
        if target_layer != source.get("target_layer"):
            raise ValueError(f"{feedback_id} target_layer 与 design_feedback 不一致")
        allowed_paths = LAYER_PATHS.get(target_layer)
        if allowed_paths is None:
            raise ValueError(f"{feedback_id} target_layer 非法: {target_layer}")

        artifacts = application.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            raise ValueError(f"{feedback_id} artifacts 必须是非空数组")
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                raise ValueError(f"{feedback_id} artifact 必须为对象")
            relative = str(artifact.get("path", "")).strip()
            if relative not in allowed_paths:
                raise ValueError(
                    f"{feedback_id} 只能修改 {target_layer} 设计层，非法路径: {relative}"
                )
            before = str(artifact.get("before_sha256", "")).strip()
            after = str(artifact.get("after_sha256", "")).strip()
            if not SHA256_PATTERN.fullmatch(before) or not SHA256_PATTERN.fullmatch(after):
                raise ValueError(f"{feedback_id} hash 必须为 64 位 sha256")
            if before == after:
                raise ValueError(f"{feedback_id} 未产生设计层变更: {relative}")
            previous_after = artifact_chain_tips.get(relative)
            if previous_after is not None and before != previous_after:
                raise ValueError(
                    f"{feedback_id} hash 链断裂: {relative} 的 before_sha256 "
                    "与上一条 application 的 after_sha256 不一致"
                )
            artifact_chain_tips[relative] = after
            changed_artifacts += 1

    for relative, expected in artifact_chain_tips.items():
        current = item_root / relative
        if not current.is_file():
            raise ValueError(f"记录的产物不存在: {relative}")
        if sha256(current) != expected:
            raise ValueError(f"链尾 after_sha256 与当前文件不一致: {relative}")

    missing_receipts = sorted(applied_ids - seen)
    if missing_receipts:
        raise ValueError(f"以下 applied feedback 缺少回灌凭证: {missing_receipts}")
    return {
        "status": "verified",
        "application_count": len(applications),
        "artifact_count": changed_artifacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 design feedback 仅回灌目标设计层且记录前后哈希")
    parser.add_argument("--item-root", required=True)
    args = parser.parse_args()
    try:
        result = validate_feedback_application(Path(args.item_root))
    except Exception as exc:
        print(f"❌ design feedback 回灌凭证校验失败: {exc}")
        return 1
    print("✅ design feedback 回灌凭证校验通过")
    for key, value in result.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
