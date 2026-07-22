#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.testcase_markdown_utils import parse_testcase_document

DIMENSION_BY_CASE_TYPE = {
    "field_constraint": "field_rule",
    "save_block": "save_block",
    "prompt_display": "prompt_display",
    "data_persistence": "data_persistence",
    "linkage": "cross_surface_linkage",
    "ui_display": "ui_display",
    "backend_job": "backend_job",
    "permission_scope": "permission_scope",
    "risk_hardening": "risk_hardening",
}


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def load_testcase_context(testcase_path: Path | None) -> dict[str, dict[str, str]]:
    if testcase_path is None or not testcase_path.exists():
        return {}
    parsed = parse_testcase_document(testcase_path.read_text(encoding="utf-8"), strict=True)
    return {
        str(row.get("用例编号", "")).strip(): {
            "page_name": str(row.get("__page_name", "")).strip(),
            "section_name": str(row.get("__section_name", "")).strip(),
            "module_name": str(row.get("所属模块", "")).strip(),
            "feature_name": str(row.get("所属功能点", "")).strip(),
        }
        for row in parsed.get("rows", [])
        if str(row.get("用例编号", "")).strip()
    }


def build_testpoints(
    project_code: str,
    work_item_id: str,
    case_plan_path: Path,
    testcase_path: Path | None = None,
) -> dict[str, Any]:
    payload = read_json(case_plan_path)
    plans = payload.get("case_plans", [])
    if not isinstance(plans, list):
        raise ValueError("case_plan.case_plans must be an array")
    testcase_context = load_testcase_context(testcase_path)

    testpoints: list[dict[str, Any]] = []
    for index, plan in enumerate(plans, start=1):
        if not isinstance(plan, dict):
            continue
        case_plan_id = str(plan.get("case_plan_id", "")).strip()
        if not case_plan_id:
            continue
        case_type = str(plan.get("case_type", "")).strip()
        assertion = str(plan.get("assertion", "")).strip()
        title = str(plan.get("title", "")).strip()
        generated_testcase_ids = as_list(plan.get("generated_testcase_ids"))
        context = next(
            (testcase_context[case_id] for case_id in generated_testcase_ids if case_id in testcase_context),
            {},
        )
        testpoints.append(
            {
                "testpoint_id": f"TP-{index:03d}",
                "source_case_plan_id": case_plan_id,
                "source_gate_ids": as_list(plan.get("source_gate_ids")),
                "source_example_ids": as_list(plan.get("source_example_ids")),
                "source_responsibility_ids": as_list(plan.get("source_responsibility_ids")),
                "page_name": str(plan.get("page_name", "")).strip() or context.get("page_name", ""),
                "section_name": str(plan.get("section_name", "")).strip() or context.get("section_name", ""),
                "module_name": str(plan.get("module_name", plan.get("module", ""))).strip() or context.get("module_name", ""),
                "feature_name": str(plan.get("feature_name", plan.get("feature", ""))).strip() or context.get("feature_name", ""),
                "test_dimension": DIMENSION_BY_CASE_TYPE.get(case_type, case_type or "unspecified"),
                "test_point": title or assertion,
                "assertion": assertion,
                "priority": str(plan.get("priority", "")).strip(),
                "validation_path": str(plan.get("validation_path", "")).strip(),
                "should_generate_case": bool(plan.get("should_generate_case")),
                "generated_testcase_ids": generated_testcase_ids,
            }
        )

    return {
        "project_code": project_code,
        "work_item_id": work_item_id,
        "truth_source": "testcases/case_plan.json",
        "projection_only": True,
        "generated_from": [
            "testcases/case_plan.json",
            *(["testcases/testcases_main.md"] if testcase_path is not None else []),
        ],
        "testpoints": testpoints,
    }


def build_markdown(bundle: dict[str, Any]) -> str:
    rows = bundle.get("testpoints", [])
    lines = [
        "# Testpoints View",
        "",
        f"- Project: `{bundle.get('project_code', '')}`",
        f"- Work Item: `{bundle.get('work_item_id', '')}`",
        "- Truth Source: `testcases/case_plan.json`",
        "- Projection Only: `true`",
        "",
        "> This file is a review-friendly projection derived from `case_plan`; it is not a testcase truth source.",
        "",
        "| 测试点ID | 页面 | 板块 | 模块 | 功能点 | 测试维度 | 测试点 | 核心断言 | 优先级 | 来源 CasePlan | 是否生成用例 |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for item in rows:
        lines.append(
            "| {testpoint_id} | {page_name} | {section_name} | {module_name} | {feature_name} | {test_dimension} | {test_point} | {assertion} | {priority} | {source_case_plan_id} | {should_generate_case} |".format(
                **{
                    key: str(item.get(key, "")).replace("|", "\\|")
                    for key in [
                        "testpoint_id",
                        "page_name",
                        "section_name",
                        "module_name",
                        "feature_name",
                        "test_dimension",
                        "test_point",
                        "assertion",
                        "priority",
                        "source_case_plan_id",
                        "should_generate_case",
                    ]
                }
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="从 case_plan.json 派生人工评审用 testpoints 视图")
    parser.add_argument("--project-code", required=True)
    parser.add_argument("--work-item-id", required=True)
    parser.add_argument("--case-plan", required=True)
    parser.add_argument("--testcases", required=False)
    parser.add_argument("--json-output", required=True)
    parser.add_argument("--md-output", required=True)
    args = parser.parse_args()

    bundle = build_testpoints(
        args.project_code.strip().upper(),
        args.work_item_id.strip().upper(),
        Path(args.case_plan).resolve(),
        Path(args.testcases).resolve() if args.testcases else None,
    )
    json_output = Path(args.json_output).resolve()
    md_output = Path(args.md_output).resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_output.write_text(build_markdown(bundle), encoding="utf-8")
    print(f"testpoints json written: {json_output}")
    print(f"testpoints markdown written: {md_output}")
    print(f"testpoint_count: {len(bundle['testpoints'])}")
    print("truth_source: testcases/case_plan.json")
    print("projection_only: true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
