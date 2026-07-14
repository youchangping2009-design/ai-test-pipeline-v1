#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from build_testcase_bundle import build_bundle


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError("testcase_bundle 必须为 JSON object")
    return payload


def load_case_plan_ids(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    payload = read_json(path)
    plans = payload.get("case_plans", [])
    if not isinstance(plans, list):
        return set()
    return {
        str(plan.get("case_plan_id", "")).strip()
        for plan in plans
        if isinstance(plan, dict) and str(plan.get("case_plan_id", "")).strip()
    }


def validate_bundle(bundle: dict, expected: dict, known_case_plan_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if bundle.get("truth_source") != "testcases/testcases_main.md":
        errors.append("testcase_bundle.truth_source 必须为 testcases/testcases_main.md")
    if bundle.get("projection_only") is not True:
        errors.append("testcase_bundle.projection_only 必须为 true，当前阶段不能切换真源")
    if bundle.get("generated_from") != ["testcases/testcases_main.md"]:
        errors.append("testcase_bundle.generated_from 必须只包含 testcases/testcases_main.md")
    cases = bundle.get("cases")
    expected_cases = expected.get("cases", [])
    if not isinstance(cases, list):
        return errors + ["testcase_bundle.cases 必须为数组"]
    if len(cases) != len(expected_cases):
        errors.append(f"testcase_bundle.cases 数量与 testcases_main.md 不一致: {len(cases)} != {len(expected_cases)}")
    for index, expected_case in enumerate(expected_cases):
        if index >= len(cases):
            break
        actual_case = cases[index]
        if actual_case != expected_case:
            case_id = expected_case.get("testcase_id", f"index-{index + 1}")
            errors.append(f"testcase_bundle 第 {index + 1} 条与 testcases_main.md 派生结果不一致: {case_id}")
        if known_case_plan_ids:
            for case_plan_id in actual_case.get("source_case_plan_ids", []) or []:
                if case_plan_id not in known_case_plan_ids:
                    errors.append(f"{actual_case.get('testcase_id', '')} source_case_plan_id 不存在于 case_plan: {case_plan_id}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 testcase_bundle.json 仍是 testcases_main.md 的兼容投影")
    parser.add_argument("--input", required=True, help="testcase_bundle.json 路径")
    parser.add_argument("--testcases", required=True, help="testcases_main.md 路径")
    parser.add_argument("--case-plan", required=False, help="case_plan.json 路径")
    parser.add_argument("--project-code", required=True)
    parser.add_argument("--work-item-id", required=True)
    args = parser.parse_args()

    try:
        bundle = read_json(Path(args.input).resolve())
        expected = build_bundle(
            args.project_code.strip().upper(),
            args.work_item_id.strip().upper(),
            Path(args.testcases).resolve(),
        )
        known_case_plan_ids = load_case_plan_ids(Path(args.case_plan).resolve()) if args.case_plan else set()
    except Exception as exc:
        print(f"读取或派生 bundle 失败: {exc}", file=sys.stderr)
        return 1

    errors = validate_bundle(bundle, expected, known_case_plan_ids)
    if errors:
        print("❌ testcase_bundle 校验失败")
        for error in errors:
            print(f"- {error}")
        print(f"共发现 {len(errors)} 个问题")
        return 1

    print("✅ testcase_bundle 校验通过")
    print(f"case_count: {len(bundle.get('cases', []))}")
    print("truth_source: testcases/testcases_main.md")
    print("projection_only: true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
