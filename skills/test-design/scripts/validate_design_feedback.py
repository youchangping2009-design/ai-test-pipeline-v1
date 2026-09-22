#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PLACEHOLDER_PATTERNS = ("待补充", "TODO", "TEMPLATE", "示例", "example")
SOURCE_REVIEW_STAGES = {"frontend_code_review", "backend_code_review", "manual_review", "quality_gate"}
FEEDBACK_TYPES = {"case_gap", "implementation_gap", "invalid_case", "risk_note", "needs_confirmation", "no_action"}
TARGET_LAYERS = {
    "testability_gate",
    "acceptance_examples",
    "verification_responsibility_map",
    "test_design_matrix",
    "case_plan",
}
STATUSES = {"open", "accepted", "rejected", "applied"}


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def has_placeholder(value: Any) -> bool:
    text = str(value or "").strip()
    return any(pattern.lower() in text.lower() for pattern in PLACEHOLDER_PATTERNS)


def load_case_plan_ids(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    payload = read_json(path)
    plans = payload.get("case_plans", []) if isinstance(payload, dict) else []
    return {
        str(plan.get("case_plan_id", "")).strip()
        for plan in plans
        if isinstance(plan, dict) and str(plan.get("case_plan_id", "")).strip()
    }


def validate_feedback(payload: dict[str, Any], known_case_plan_ids: set[str]) -> list[str]:
    errors: list[str] = []
    items = payload.get("feedback_items")
    if not isinstance(items, list):
        return ["design_feedback.feedback_items 必须为数组"]

    seen_ids: set[str] = set()
    required = [
        "feedback_id",
        "source_review_stage",
        "source_confirmation_file",
        "source_case_plan_ids",
        "feedback_type",
        "target_layer",
        "title",
        "finding",
        "recommended_action",
        "must_not_directly_overwrite_testcase",
        "status",
    ]
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"第 {index} 条 design_feedback item 必须为对象")
            continue
        missing = [field for field in required if field not in item or item.get(field) in ("", None, [])]
        if missing:
            errors.append(f"第 {index} 条 design_feedback item 缺少必填字段: {missing}")
            continue

        feedback_id = str(item.get("feedback_id", "")).strip()
        source_review_stage = str(item.get("source_review_stage", "")).strip()
        feedback_type = str(item.get("feedback_type", "")).strip()
        target_layer = str(item.get("target_layer", "")).strip()
        status = str(item.get("status", "")).strip()
        source_case_plan_ids = [
            str(value).strip()
            for value in item.get("source_case_plan_ids", []) or []
            if str(value).strip()
        ]

        if feedback_id in seen_ids:
            errors.append(f"feedback_id 重复: {feedback_id}")
        seen_ids.add(feedback_id)
        if source_review_stage not in SOURCE_REVIEW_STAGES:
            errors.append(f"{feedback_id} source_review_stage 非法: {source_review_stage}")
        if feedback_type not in FEEDBACK_TYPES:
            errors.append(f"{feedback_id} feedback_type 非法: {feedback_type}")
        if target_layer not in TARGET_LAYERS:
            errors.append(f"{feedback_id} target_layer 必须是设计层产物，不能直接指向 testcase: {target_layer}")
        if status not in STATUSES:
            errors.append(f"{feedback_id} status 非法: {status}")
        if item.get("must_not_directly_overwrite_testcase") is not True:
            errors.append(f"{feedback_id} must_not_directly_overwrite_testcase 必须为 true")
        for field in ["title", "finding", "recommended_action", "source_confirmation_file"]:
            if has_placeholder(item.get(field)):
                errors.append(f"{feedback_id} 字段 {field} 仍是模板/占位内容: {item.get(field)}")
        if known_case_plan_ids:
            for case_plan_id in source_case_plan_ids:
                if case_plan_id not in known_case_plan_ids:
                    if not (feedback_type == "invalid_case" and status == "applied"):
                        errors.append(f"{feedback_id} source_case_plan_id 不存在于 case_plan: {case_plan_id}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 code review 映证反馈的 design_feedback.json")
    parser.add_argument("--input", required=True, help="design_feedback.json 路径")
    parser.add_argument("--case-plan", required=False, help="case_plan.json 路径")
    args = parser.parse_args()

    try:
        payload = read_json(Path(args.input).resolve())
        known_case_plan_ids = load_case_plan_ids(Path(args.case_plan).resolve()) if args.case_plan else set()
    except Exception as exc:
        print(f"读取文件失败: {exc}", file=sys.stderr)
        return 1

    errors = validate_feedback(payload, known_case_plan_ids)
    if errors:
        print("❌ design_feedback 校验失败")
        for error in errors:
            print(f"- {error}")
        print(f"共发现 {len(errors)} 个问题")
        return 1

    print("✅ design_feedback 校验通过")
    print(f"feedback_item_count: {len(payload.get('feedback_items', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
