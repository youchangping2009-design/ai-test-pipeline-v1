#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_feedback_application import (
    LAYER_PATHS,
    read_json,
    sha256,
    validate_feedback_application,
)


ROOT = Path(__file__).resolve().parents[1]


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def resolve_item_root(project_code: str, work_item_id: str) -> Path:
    return (
        ROOT
        / "assets"
        / "projects"
        / normalize_code(project_code)
        / "work_items"
        / normalize_code(work_item_id)
    )


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def feedback_fingerprint(item: dict[str, Any]) -> str:
    stable = {
        key: value
        for key, value in item.items()
        if key not in {"status", "application_note"}
    }
    encoded = json.dumps(
        stable, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def feedback_item(item_root: Path, feedback_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = read_json(item_root / "design" / "design_feedback.json")
    matches = [
        item
        for item in payload.get("feedback_items", [])
        if isinstance(item, dict) and item.get("feedback_id") == feedback_id
    ]
    if len(matches) != 1:
        raise ValueError(f"feedback_id 必须且只能匹配一条记录: {feedback_id}")
    return payload, matches[0]


def snapshot_path(item_root: Path, feedback_id: str) -> Path:
    return item_root / ".generation" / "feedback_applications" / f"{feedback_id}.before.json"


def select_targets(
    item_root: Path,
    target_layer: str,
    requested_targets: list[str] | None,
) -> list[str]:
    allowed = LAYER_PATHS.get(target_layer)
    if allowed is None:
        raise ValueError(f"feedback target_layer 非法: {target_layer}")
    targets = requested_targets or sorted(
        relative for relative in allowed if (item_root / relative).is_file()
    )
    if not targets:
        raise ValueError(f"目标设计层没有可冻结产物: {target_layer}")
    if len(targets) != len(set(targets)):
        raise ValueError("--target 不得重复")
    for relative in targets:
        if relative not in allowed:
            raise ValueError(f"目标路径不属于 {target_layer} 设计层: {relative}")
        if not (item_root / relative).is_file():
            raise ValueError(f"目标产物不存在: {relative}")
    return targets


def prepare_application(
    item_root: Path,
    feedback_id: str,
    requested_targets: list[str] | None = None,
) -> Path:
    item_root = item_root.resolve()
    feedback, item = feedback_item(item_root, feedback_id)
    if item.get("status") != "accepted":
        raise ValueError(f"{feedback_id} 必须处于 accepted，实际为 {item.get('status')}")
    target_layer = str(item.get("target_layer", "")).strip()
    targets = select_targets(item_root, target_layer, requested_targets)
    output = snapshot_path(item_root, feedback_id)
    if output.exists():
        raise ValueError(f"修改前快照已存在，拒绝覆盖: {output}")
    snapshot = {
        "schema_version": "1.0.0",
        "project_code": feedback.get("project_code"),
        "work_item_id": feedback.get("work_item_id"),
        "feedback_id": feedback_id,
        "target_layer": target_layer,
        "feedback_fingerprint": feedback_fingerprint(item),
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "artifacts": [
            {"path": relative, "before_sha256": sha256(item_root / relative)}
            for relative in targets
        ],
    }
    atomic_write_json(output, snapshot)
    return output


def _same_application(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return left == right


def record_application(item_root: Path, feedback_id: str) -> Path:
    item_root = item_root.resolve()
    feedback, item = feedback_item(item_root, feedback_id)
    if item.get("status") not in {"accepted", "applied"}:
        raise ValueError(
            f"{feedback_id} 必须处于 accepted，或处于待恢复的 applied，实际为 {item.get('status')}"
        )
    snapshot = read_json(snapshot_path(item_root, feedback_id))
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

    artifacts = snapshot.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("修改前快照 artifacts 必须为非空数组")
    allowed = LAYER_PATHS[str(item.get("target_layer"))]
    changes: list[dict[str, str]] = []
    for artifact in artifacts:
        relative = str(artifact.get("path", "")).strip()
        if relative not in allowed:
            raise ValueError(f"修改前快照包含越界路径: {relative}")
        current = item_root / relative
        if not current.is_file():
            raise ValueError(f"目标产物不存在: {relative}")
        before = str(artifact.get("before_sha256", "")).strip()
        after = sha256(current)
        if before != after:
            changes.append(
                {"path": relative, "before_sha256": before, "after_sha256": after}
            )
    if not changes:
        raise ValueError(f"{feedback_id} 的目标设计层没有发生变化")

    application = {
        "feedback_id": feedback_id,
        "target_layer": item.get("target_layer"),
        "artifacts": changes,
    }
    receipt_path = item_root / "design" / "feedback_application.json"
    if receipt_path.exists():
        receipt = read_json(receipt_path)
    else:
        receipt = {
            "project_code": feedback.get("project_code"),
            "work_item_id": feedback.get("work_item_id"),
            "applications": [],
        }
    if receipt.get("project_code") != feedback.get("project_code") or receipt.get(
        "work_item_id"
    ) != feedback.get("work_item_id"):
        raise ValueError("feedback_application 与 design_feedback 身份不一致")
    applications = receipt.get("applications")
    if not isinstance(applications, list):
        raise ValueError("feedback_application.applications 必须为数组")
    receipt_ids = {
        str(entry.get("feedback_id", "")).strip()
        for entry in applications
        if isinstance(entry, dict)
    }
    uncovered_applied = sorted(
        str(candidate.get("feedback_id", "")).strip()
        for candidate in feedback.get("feedback_items", [])
        if isinstance(candidate, dict)
        and candidate.get("status") == "applied"
        and candidate.get("feedback_id") != feedback_id
        and str(candidate.get("feedback_id", "")).strip() not in receipt_ids
    )
    if uncovered_applied:
        raise ValueError(
            f"已有 applied feedback 缺少回灌凭证，拒绝写入新状态: {uncovered_applied}"
        )
    existing = [entry for entry in applications if entry.get("feedback_id") == feedback_id]
    if existing:
        if len(existing) != 1 or not _same_application(existing[0], application):
            raise ValueError(f"{feedback_id} 已存在不同的回灌凭证")
    else:
        applications.append(application)
        atomic_write_json(receipt_path, receipt)

    if item.get("status") != "applied":
        item["status"] = "applied"
        atomic_write_json(item_root / "design" / "design_feedback.json", feedback)

    validate_feedback_application(item_root)
    return receipt_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="两阶段捕获 design feedback 回灌前置 hash 并生成凭证"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("prepare", "record"):
        child = subparsers.add_parser(command)
        child.add_argument("--project-code", required=True)
        child.add_argument("--work-item-id", required=True)
        child.add_argument("--feedback-id", required=True)
        if command == "prepare":
            child.add_argument(
                "--target",
                action="append",
                dest="targets",
                help="可重复；缺省冻结目标设计层当前存在的全部标准产物",
            )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    item_root = resolve_item_root(args.project_code, args.work_item_id)
    try:
        if args.command == "prepare":
            output = prepare_application(item_root, args.feedback_id, args.targets)
            print(f"feedback_application_snapshot: {output}")
            print("status: prepared")
        else:
            output = record_application(item_root, args.feedback_id)
            print(f"feedback_application_receipt: {output}")
            print("status: applied")
    except Exception as exc:
        print(f"❌ feedback application {args.command} 失败: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
