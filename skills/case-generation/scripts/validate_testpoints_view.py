#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def load_case_plan_ids(path: Path) -> set[str]:
    payload = read_json(path)
    plans = payload.get("case_plans", [])
    if not isinstance(plans, list):
        return set()
    return {
        str(item.get("case_plan_id", "")).strip()
        for item in plans
        if isinstance(item, dict) and str(item.get("case_plan_id", "")).strip()
    }


def load_gate_ids(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    payload = read_json(path)
    items = payload.get("items", [])
    if not isinstance(items, list):
        return set()
    return {
        str(item.get("gate_id", "")).strip()
        for item in items
        if isinstance(item, dict) and str(item.get("gate_id", "")).strip()
    }


def validate(payload: dict[str, Any], case_plan_ids: set[str], gate_ids: set[str]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if payload.get("truth_source") != "testcases/case_plan.json":
        errors.append("testpoints.truth_source 必须为 testcases/case_plan.json")
    if payload.get("projection_only") is not True:
        errors.append("testpoints.projection_only 必须为 true，不能切换 testcase 真源")
    if payload.get("generated_from") != ["testcases/case_plan.json"]:
        errors.append("testpoints.generated_from 必须只包含 testcases/case_plan.json")
    items = payload.get("testpoints")
    if not isinstance(items, list):
        return errors + ["testpoints 必须为数组"], warnings

    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"第 {index} 个 testpoint 必须为对象")
            continue
        testpoint_id = str(item.get("testpoint_id", "")).strip()
        source_case_plan_id = str(item.get("source_case_plan_id", "")).strip()
        if not testpoint_id:
            errors.append(f"第 {index} 个 testpoint 缺少 testpoint_id")
        elif testpoint_id in seen:
            errors.append(f"testpoint_id 重复: {testpoint_id}")
        seen.add(testpoint_id)
        if source_case_plan_id not in case_plan_ids:
            errors.append(f"{testpoint_id or index} source_case_plan_id 不存在于 case_plan: {source_case_plan_id}")
        source_gate_ids = item.get("source_gate_ids", [])
        if not isinstance(source_gate_ids, list) or not source_gate_ids:
            errors.append(f"{testpoint_id or index} source_gate_ids 不能为空")
        elif gate_ids:
            for gate_id in source_gate_ids:
                if str(gate_id).strip() not in gate_ids:
                    errors.append(f"{testpoint_id or index} source_gate_id 不存在于 testability_gate: {gate_id}")
        for field in ["test_point", "assertion", "priority", "validation_path"]:
            if not str(item.get(field, "")).strip():
                errors.append(f"{testpoint_id or index} 字段 {field} 不能为空")
        if not str(item.get("page_name", "")).strip():
            warnings.append(f"{testpoint_id or index} 缺少 page_name，建议在 case_plan 中补充页面上下文")
        if not str(item.get("section_name", "")).strip():
            warnings.append(f"{testpoint_id or index} 缺少 section_name，建议在 case_plan 中补充板块上下文")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 testpoints 仍是 case_plan 的派生评审视图")
    parser.add_argument("--input", required=True)
    parser.add_argument("--case-plan", required=True)
    parser.add_argument("--testability-gate", required=False)
    args = parser.parse_args()

    try:
        payload = read_json(Path(args.input).resolve())
        case_plan_ids = load_case_plan_ids(Path(args.case_plan).resolve())
        gate_ids = load_gate_ids(Path(args.testability_gate).resolve()) if args.testability_gate else set()
    except Exception as exc:
        print(f"读取 testpoints 或来源产物失败: {exc}")
        return 1

    errors, warnings = validate(payload, case_plan_ids, gate_ids)
    if errors:
        print("❌ testpoints 校验失败")
        for error in errors:
            print(f"- {error}")
        print(f"共发现 {len(errors)} 个问题")
        return 1

    print("✅ testpoints 校验通过")
    print(f"testpoint_count: {len(payload.get('testpoints', []))}")
    if warnings:
        print(f"warnings: {len(warnings)}")
        for warning in warnings:
            print(f"- {warning}")
    print("truth_source: testcases/case_plan.json")
    print("projection_only: true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
