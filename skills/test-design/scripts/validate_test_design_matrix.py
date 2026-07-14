#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PLACEHOLDER_PATTERNS = ("待补充", "TODO", "TEMPLATE", "示例", "example")
RISK_LEVELS = {"low", "medium", "high", "critical"}


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def has_placeholder(value: Any) -> bool:
    text = str(value or "").strip()
    return any(pattern.lower() in text.lower() for pattern in PLACEHOLDER_PATTERNS)


def index_items(payload: dict[str, Any], collection_name: str, id_field: str) -> dict[str, dict[str, Any]]:
    items = payload.get(collection_name, []) if isinstance(payload, dict) else []
    if not isinstance(items, list):
        return {}
    return {
        str(item.get(id_field, "")).strip(): item
        for item in items
        if isinstance(item, dict) and str(item.get(id_field, "")).strip()
    }


def validate_matrix(
    payload: dict[str, Any],
    testability_gate: dict[str, Any] | None,
    acceptance_examples: dict[str, Any] | None,
    responsibility_map: dict[str, Any] | None,
    case_plan: dict[str, Any] | None,
) -> list[str]:
    errors: list[str] = []
    items = payload.get("items")
    if not isinstance(items, list):
        return ["test_design_matrix.items 必须为数组"]
    if not items:
        errors.append("test_design_matrix.items 不能为空，L strict 阶段不能使用空模板")

    gates = index_items(testability_gate or {}, "items", "gate_id")
    examples = index_items(acceptance_examples or {}, "examples", "example_id")
    responsibilities = index_items(responsibility_map or {}, "responsibilities", "responsibility_id")
    plans = index_items(case_plan or {}, "case_plans", "case_plan_id")
    active_plan_ids = {
        plan_id
        for plan_id, plan in plans.items()
        if bool(plan.get("should_generate_case"))
    }
    covered_plan_ids: set[str] = set()
    seen_ids: set[str] = set()

    required = [
        "matrix_id",
        "source_rule_id",
        "gate_id",
        "example_id",
        "responsibility_id",
        "case_plan_id",
        "verification_side",
        "case_type",
        "coverage_focus",
        "assertion",
        "risk_level",
        "note",
    ]

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"第 {index} 条 test_design_matrix item 必须为对象")
            continue
        missing = [field for field in required if field not in item or item.get(field) in ("", None, [])]
        if missing:
            errors.append(f"第 {index} 条 test_design_matrix item 缺少必填字段: {missing}")
            continue

        matrix_id = str(item.get("matrix_id", "")).strip()
        source_rule_id = str(item.get("source_rule_id", "")).strip()
        gate_id = str(item.get("gate_id", "")).strip()
        example_id = str(item.get("example_id", "")).strip()
        responsibility_id = str(item.get("responsibility_id", "")).strip()
        case_plan_id = str(item.get("case_plan_id", "")).strip()
        risk_level = str(item.get("risk_level", "")).strip()

        if matrix_id in seen_ids:
            errors.append(f"matrix_id 重复: {matrix_id}")
        seen_ids.add(matrix_id)

        for field in required:
            if has_placeholder(item.get(field)):
                errors.append(f"{matrix_id} 字段 {field} 仍是模板/占位内容: {item.get(field)}")
        if risk_level not in RISK_LEVELS:
            errors.append(f"{matrix_id} risk_level 非法: {risk_level}")

        gate = gates.get(gate_id)
        example = examples.get(example_id)
        responsibility = responsibilities.get(responsibility_id)
        plan = plans.get(case_plan_id)

        if gates and not gate:
            errors.append(f"{matrix_id} gate_id 不存在于 testability_gate: {gate_id}")
        if examples and not example:
            errors.append(f"{matrix_id} example_id 不存在于 acceptance_examples: {example_id}")
        if responsibilities and not responsibility:
            errors.append(f"{matrix_id} responsibility_id 不存在于 verification_responsibility_map: {responsibility_id}")
        if plans and not plan:
            errors.append(f"{matrix_id} case_plan_id 不存在于 case_plan: {case_plan_id}")

        if gate and source_rule_id != str(gate.get("source_rule_id", "")).strip():
            errors.append(f"{matrix_id} source_rule_id 与 gate_id 对应规则不一致")
        if example:
            example_gate_ids = {str(value).strip() for value in example.get("source_gate_ids", []) or []}
            if gate_id not in example_gate_ids:
                errors.append(f"{matrix_id} example_id 与 gate_id 不一致")
        if responsibility and source_rule_id != str(responsibility.get("source_rule_id", "")).strip():
            errors.append(f"{matrix_id} responsibility_id 与 source_rule_id 不一致")
        if plan:
            covered_plan_ids.add(case_plan_id)
            if gate_id not in [str(value).strip() for value in plan.get("source_gate_ids", []) or []]:
                errors.append(f"{matrix_id} case_plan_id 与 gate_id 不一致")
            if example_id not in [str(value).strip() for value in plan.get("source_example_ids", []) or []]:
                errors.append(f"{matrix_id} case_plan_id 与 example_id 不一致")
            if responsibility_id not in [str(value).strip() for value in plan.get("source_responsibility_ids", []) or []]:
                errors.append(f"{matrix_id} case_plan_id 与 responsibility_id 不一致")
            if str(item.get("case_type", "")).strip() != str(plan.get("case_type", "")).strip():
                errors.append(f"{matrix_id} case_type 与 case_plan 不一致")

    for plan_id in sorted(active_plan_ids - covered_plan_ids):
        errors.append(f"生成正式用例的 case_plan 未被 test_design_matrix 覆盖: {plan_id}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 L 档 test_design_matrix.json")
    parser.add_argument("--input", required=True, help="test_design_matrix.json 路径")
    parser.add_argument("--testability-gate", required=False, help="testability_gate.json 路径")
    parser.add_argument("--acceptance-examples", required=False, help="acceptance_examples.json 路径")
    parser.add_argument("--responsibility-map", required=False, help="verification_responsibility_map.json 路径")
    parser.add_argument("--case-plan", required=False, help="case_plan.json 路径")
    args = parser.parse_args()

    try:
        payload = read_json(Path(args.input).resolve())
        testability_gate = read_json(Path(args.testability_gate).resolve()) if args.testability_gate else None
        acceptance_examples = read_json(Path(args.acceptance_examples).resolve()) if args.acceptance_examples else None
        responsibility_map = read_json(Path(args.responsibility_map).resolve()) if args.responsibility_map else None
        case_plan = read_json(Path(args.case_plan).resolve()) if args.case_plan else None
    except Exception as exc:
        print(f"读取文件失败: {exc}", file=sys.stderr)
        return 1

    errors = validate_matrix(payload, testability_gate, acceptance_examples, responsibility_map, case_plan)
    if errors:
        print("❌ test_design_matrix 校验失败")
        for error in errors:
            print(f"- {error}")
        print(f"共发现 {len(errors)} 个问题")
        return 1

    print("✅ test_design_matrix 校验通过")
    print(f"matrix_item_count: {len(payload.get('items', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
