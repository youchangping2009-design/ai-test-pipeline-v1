#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_dev_self_testcases import build_dev_self_markdown
from coverage_testcase_generator import generate_testcases_bundle
from coverage_testcase_generator import read_json


ROOT = Path(__file__).resolve().parents[1]


def normalize_code(value: str) -> str:
    return "-".join(value.strip().split()).upper()


def resolve_work_item_root(project_code: str, work_item_id: str) -> Path:
    return ROOT / "assets" / "projects" / project_code / "work_items" / work_item_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="根据 coverage_matrix 生成 testcases.md")
    parser.add_argument("--project-code", required=False, help="项目编码")
    parser.add_argument("--work-item-id", required=False, help="工作项 ID")
    parser.add_argument("--structured-prd", required=False, help="structured_prd.json 路径")
    parser.add_argument("--coverage-matrix", required=False, help="coverage_matrix.json 路径")
    parser.add_argument("--output", required=False, help="testcases.md 输出路径")
    parser.add_argument("--main-output", required=False, help="testcases_main.md 输出路径")
    parser.add_argument("--field-audit-output", required=False, help="field_audit.json 输出路径")
    parser.add_argument("--grouped-audit-output", required=False, help="grouped_audit.json 输出路径")
    parser.add_argument("--duplicate-report", required=False, help="duplicate_case_report.json 输出路径")
    parser.add_argument("--dev-self-output", required=False, help="dev_self_testcases.md 输出路径")
    parser.add_argument("--case-plan", required=False, help="case_plan.json 路径；提供后用例备注会写入来源 CasePlan 追溯")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.project_code and args.work_item_id:
        root = resolve_work_item_root(normalize_code(args.project_code), normalize_code(args.work_item_id))
        structured_prd_path = Path(args.structured_prd).resolve() if args.structured_prd else root / "structured_prd" / "structured_prd.json"
        coverage_matrix_path = Path(args.coverage_matrix).resolve() if args.coverage_matrix else root / "coverage" / "coverage_matrix.json"
        output_path = Path(args.output).resolve() if args.output else root / "testcases" / "testcases.md"
        main_output_path = Path(args.main_output).resolve() if args.main_output else root / "testcases" / "testcases_main.md"
        field_audit_output_path = Path(args.field_audit_output).resolve() if args.field_audit_output else root / "testcases" / "field_audit.json"
        grouped_audit_output_path = Path(args.grouped_audit_output).resolve() if args.grouped_audit_output else root / "testcases" / "grouped_audit.json"
        duplicate_report_path = Path(args.duplicate_report).resolve() if args.duplicate_report else root / "reviews" / "duplicate_case_report.json"
        dev_self_output_path = Path(args.dev_self_output).resolve() if args.dev_self_output else root / "testcases" / "dev_self_testcases.md"
        case_plan_path = Path(args.case_plan).resolve() if args.case_plan else root / "testcases" / "case_plan.json"
    else:
        if not (args.structured_prd and args.coverage_matrix and args.output):
            raise SystemExit("必须提供 --project-code + --work-item-id，或显式提供 --structured-prd --coverage-matrix --output")
        structured_prd_path = Path(args.structured_prd).resolve()
        coverage_matrix_path = Path(args.coverage_matrix).resolve()
        output_path = Path(args.output).resolve()
        main_output_path = Path(args.main_output).resolve() if args.main_output else output_path.parent / "testcases_main.md"
        field_audit_output_path = Path(args.field_audit_output).resolve() if args.field_audit_output else output_path.parent / "field_audit.json"
        grouped_audit_output_path = Path(args.grouped_audit_output).resolve() if args.grouped_audit_output else output_path.parent / "grouped_audit.json"
        duplicate_report_path = Path(args.duplicate_report).resolve() if args.duplicate_report else output_path.parent / "duplicate_case_report.json"
        dev_self_output_path = Path(args.dev_self_output).resolve() if args.dev_self_output else output_path.parent / "dev_self_testcases.md"
        case_plan_path = Path(args.case_plan).resolve() if args.case_plan else None

    structured_prd = read_json(structured_prd_path)
    coverage_matrix = read_json(coverage_matrix_path)
    case_plan = read_json(case_plan_path) if case_plan_path and case_plan_path.exists() else None
    bundle = generate_testcases_bundle(structured_prd, coverage_matrix, case_plan)
    markdown = bundle["main_markdown"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    main_output_path.parent.mkdir(parents=True, exist_ok=True)
    main_output_path.write_text(markdown, encoding="utf-8")
    field_audit_output_path.parent.mkdir(parents=True, exist_ok=True)
    field_audit_output_path.write_text(
        json.dumps(bundle["field_audit"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    grouped_audit_output_path.parent.mkdir(parents=True, exist_ok=True)
    grouped_audit_output_path.write_text(
        json.dumps(bundle["grouped_audit"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    duplicate_report_path.parent.mkdir(parents=True, exist_ok=True)
    duplicate_report_path.write_text(
        json.dumps(bundle["duplicate_case_report"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    dev_self_markdown, dev_self_count = build_dev_self_markdown(main_output_path)
    dev_self_output_path.parent.mkdir(parents=True, exist_ok=True)
    dev_self_output_path.write_text(dev_self_markdown, encoding="utf-8")
    print(f"testcases: {output_path}")
    print(f"testcases_main: {main_output_path}")
    print(f"dev_self_testcases: {dev_self_output_path}")
    print(f"field_audit: {field_audit_output_path}")
    print(f"grouped_audit: {grouped_audit_output_path}")
    print(f"source: {coverage_matrix_path}")
    if case_plan_path and case_plan_path.exists():
        print(f"case_plan: {case_plan_path}")
    else:
        print("case_plan: not supplied")
    print(f"duplicate_report: {duplicate_report_path}")
    print(f"case_drafts_before_merge: {bundle['case_count_before_merge']}")
    print(f"cases_after_merge: {bundle['case_count_after_merge']}")
    print(f"main_case_count: {bundle['main_case_count']}")
    print(f"dev_self_case_count: {dev_self_count}")
    print(f"field_audit_count: {bundle['field_audit']['item_count']}")
    print(f"grouped_audit_count: {bundle['grouped_audit']['group_count']}")
    print(f"case_plan_trace_count: {bundle.get('case_plan_trace_count', 0)}")
    print(f"untraced_case_count_filtered: {bundle.get('untraced_case_count_filtered', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
